#include "local_coverage_planner/local_coverage_planner.h"
#include "ht_cost/search_schedule.h"
#include <algorithm>
#include <cmath>
#include <limits>
#include <unordered_set>

namespace local_coverage_planner_ns {
namespace {
struct ScopedSearchRuntime {
  int& microseconds;
  std::chrono::steady_clock::time_point started=std::chrono::steady_clock::now();
  ~ScopedSearchRuntime() {microseconds+=static_cast<int>(std::chrono::duration_cast<std::chrono::microseconds>(
    std::chrono::steady_clock::now()-started).count());}
};
}


exploration_path_ns::ExplorationPath LocalCoveragePlanner::SolveHTTSP(
    const std::vector<int>& selected,std::vector<int>& ordered) {
  ScopedSearchRuntime measured{find_path_runtime_};
  using namespace exploration_path_ns;
  ExplorationPath result;
  ordered.clear();
  ht_candidate_path_.poses.clear();
  ht_candidate_target_=-1;
  ht_last_cost_=std::numeric_limits<double>::infinity();
  auto ht=viewpoint_manager_->HT();
  if (!ht->ready() || !std::isfinite(robot_yaw_)) return result;
  const double now=node_->now().seconds();
  // During bootstrap the global path and its navigation boundaries can both
  // be empty. Distant coverage-selected viewpoints are still valid guides.
  // This preserves the old bootstrap source while making its identity stable.
  if (!ht_has_global_guide_) {
    double nearest=std::numeric_limits<double>::infinity();
    for (int id:selected) {
      if (id==robot_viewpoint_ind_ || !viewpoint_manager_->InRange(id)) continue;
      const auto p=viewpoint_manager_->GetViewPointPosition(id);
      const double d=std::hypot(p.x-robot_position_.x(),p.y-robot_position_.y());
      if (d>xytheta_config_.max_radius && d<nearest &&
          !ht_guide_progress_.cooling({p.x,p.y,p.z},now)) {
        nearest=d;ht_global_guide_=Eigen::Vector3d(p.x,p.y,p.z);
      }
    }
    if (std::isfinite(nearest)) SetHTGuide(ht_global_guide_,false,now);
  }

  struct Target {int id;double utility;double gain;double progress;bool recovery=false;bool backtrack=false;};
  std::vector<Target> targets;
  auto supported_endpoint=[&](int id) {
    const auto p=viewpoint_manager_->GetViewPointPosition(id);
    if (viewpoint_manager_->InCollisionAtPose(Eigen::Vector3d(p.x,p.y,robot_position_.z()),ht_tracking_margin_)) return false;
    for (int k=0;k<8;++k)
      if (ht->permits(ht->poseSupport(p.x,p.y,k*ht_cost_ns::kPi/4))) return true;
    return false;
  };
  // Coverage sampling alone does not know whether HT permits the chosen
  // endpoints. Include other gain-bearing candidates before pruning to the
  // bounded XYtheta search shortlist, so an unsafe top-scoring cluster cannot
  // hide every reachable alternative.
  std::vector<int> pool=selected;
  for (int id:viewpoint_manager_->GetViewPointCandidateIndices()) {
    if (viewpoint_manager_->ViewPointVisited(id) ||
        !viewpoint_manager_->ViewPointInExploringCell(id)) continue;
    if (viewpoint_manager_->GetViewPointCoveredPointNum(id)>0 ||
        viewpoint_manager_->GetViewPointCoveredFrontierPointNum(id)>0) pool.push_back(id);
  }
  std::sort(pool.begin(),pool.end());pool.erase(std::unique(pool.begin(),pool.end()),pool.end());
  for (int id:pool) {
    if (id==robot_viewpoint_ind_ || !viewpoint_manager_->InRange(id)) continue;
    const auto p=viewpoint_manager_->GetViewPointPosition(id);
    const double distance=std::hypot(p.x-robot_position_.x(),p.y-robot_position_.y());
    if (distance<std::max(0.8,xytheta_config_.goal_radius+0.2) || distance>xytheta_config_.max_radius) continue;
    const double gain=std::max(0,viewpoint_manager_->GetViewPointCoveredPointNum(id))+
      2.0*std::max(0,viewpoint_manager_->GetViewPointCoveredFrontierPointNum(id));
    if (ht_commitment_.cooling({p.x,p.y,p.z},now,gain>0)) continue;
    if (!supported_endpoint(id)) continue;
    double utility=gain/(1.0+distance);
    if (gain<=0) {
      if ((id!=start_viewpoint_ind_ && id!=end_viewpoint_ind_) || distance<1.0) continue;
      if (ht_has_global_guide_ &&
          (ht_global_guide_.head<2>()-Eigen::Vector2d(p.x,p.y)).norm()>=
          (ht_global_guide_-robot_position_).head<2>().norm()-0.3) continue;
      utility=-8.0+distance/(1.0+distance);
    } else if (id==ht_previous_target_) {
      utility*=1.15;
    }
    const double progress=ht_has_global_guide_ ? (ht_global_guide_-robot_position_).head<2>().norm()-
      std::hypot(p.x-ht_global_guide_.x(),p.y-ht_global_guide_.y()) : 0;
    utility-=2*ht_visits_.penalty({p.x,p.y,p.z});
    targets.push_back({id,utility,gain,progress});
  }
  std::sort(targets.begin(),targets.end(),[](const Target& a,const Target& b) {
    return a.utility>b.utility;
  });
  if (targets.size()>4) targets.resize(4);
  // The HT map is a rolling ~10 m window, while TARE's global boundary can
  // be farther away. Move to a reachable candidate inside the current map,
  // then replan as the window follows the robot.
  if (ht_has_global_guide_) {
    const auto& distant=ht_global_guide_;
    const double distant_range=(distant-robot_position_).head<2>().norm();
    std::vector<Target> stepping;
    for (int id:viewpoint_manager_->GetViewPointCandidateIndices()) {
      if (id==robot_viewpoint_ind_) continue;
      const auto p=viewpoint_manager_->GetViewPointPosition(id);
      if (ht_commitment_.cooling({p.x,p.y,p.z},now)) continue;
      const double range=std::hypot(p.x-robot_position_.x(),p.y-robot_position_.y());
      if (range<1.0 || range>std::min(4.0,xytheta_config_.max_radius-1.0)) continue;
      const double remaining=std::hypot(p.x-distant.x(),p.y-distant.y());
      const double progress=distant_range-remaining;
      if (progress<0.8) continue;
      if (!supported_endpoint(id)) continue;
      stepping.push_back({id,ht_cost_ns::transitScore(progress,
        ht_visits_.penalty({p.x,p.y,p.z}),range/xytheta_config_.forward_speed),0,progress});
    }
    std::sort(stepping.begin(),stepping.end(),[](const Target& a,const Target& b) {
      return a.utility>b.utility;
    });
    for (size_t i=0;i<std::min<size_t>(8,stepping.size());++i) targets.push_back(stepping[i]);
  }
  int committed_id=-1;
  if (ht_commitment_.active) {
    const auto& p=ht_commitment_.goal;
    committed_id=viewpoint_manager_->GetNearestCandidateViewPointInd(Eigen::Vector3d(p.x,p.y,p.z));
    if (committed_id>=0 && viewpoint_manager_->InRange(committed_id)) {
      const auto q=viewpoint_manager_->GetViewPointPosition(committed_id);
      if (std::hypot(q.x-p.x,q.y-p.y)<0.8 && supported_endpoint(committed_id)) {
        const double gain=std::max(0,viewpoint_manager_->GetViewPointCoveredPointNum(committed_id))+
          2.0*std::max(0,viewpoint_manager_->GetViewPointCoveredFrontierPointNum(committed_id));
        const double progress=ht_has_global_guide_ ? (ht_global_guide_-robot_position_).head<2>().norm()-
          std::hypot(q.x-ht_global_guide_.x(),q.y-ht_global_guide_.y()) : 0;
        targets.insert(targets.begin(),{committed_id,0,gain,progress});
      } else committed_id=-1;
    } else committed_id=-1;
    if (committed_id<0) ht_commitment_.reject(now);
  }
  // Straight-line progress toward a distant guide can reject the sideways
  // move required to get around an obstacle. Reserve search slots for safe
  // local escape viewpoints, preferring positions the vehicle has not visited.
  // This is a recovery utility, never a relaxation of HT risk or unknown gates.
  std::vector<Target> recovery,backtrack;
  std::unordered_set<int> primary_ids;
  for (const auto& t:targets) primary_ids.insert(t.id);
  for (int id:viewpoint_manager_->GetViewPointCandidateIndices()) {
    if (id==robot_viewpoint_ind_ || primary_ids.count(id)) continue;
    const auto p=viewpoint_manager_->GetViewPointPosition(id);
    const double dx=p.x-robot_position_.x(),dy=p.y-robot_position_.y();
    const double range=std::hypot(dx,dy);
    if (range<0.8 || range>std::min(4.0,xytheta_config_.max_radius) ||
        ht_commitment_.failureCooling({p.x,p.y,p.z},now) || !supported_endpoint(id)) continue;
    const double revisit=ht_visits_.penalty({p.x,p.y,p.z});
    const double alignment=(dx*std::cos(robot_yaw_)+dy*std::sin(robot_yaw_))/range;
    const double progress=ht_has_global_guide_ ? (ht_global_guide_-robot_position_).head<2>().norm()-
      std::hypot(p.x-ht_global_guide_.x(),p.y-ht_global_guide_.y()) : 0;
    const double utility=ht_cost_ns::transitScore(progress,revisit,range/xytheta_config_.forward_speed)+0.3*alignment;
    if (ht_commitment_.cooling({p.x,p.y,p.z},now))
      backtrack.push_back({id,utility,0,progress,true,true});
    else recovery.push_back({id,utility,0,progress,true});
  }
  std::sort(recovery.begin(),recovery.end(),[](const Target& a,const Target& b){return a.utility>b.utility;});
  if (!recovery.empty() && targets.size()>4) targets.resize(4);
  const size_t primary_count=targets.size();
  // Sample different bearings before filling remaining slots in score order.
  std::array<bool,8> sectors{};std::unordered_set<int> recovery_ids;
  for (const auto& t:recovery) {
    const auto p=viewpoint_manager_->GetViewPointPosition(t.id);
    const double angle=std::atan2(p.y-robot_position_.y(),p.x-robot_position_.x());
    const int sector=static_cast<int>(std::floor((angle+ht_cost_ns::kPi)/(ht_cost_ns::kPi/4)))%8;
    if (sectors[sector]) continue;
    sectors[sector]=true;targets.push_back(t);recovery_ids.insert(t.id);
    if (targets.size()-primary_count>=8) break;
  }
  for (const auto& t:recovery) {
    if (targets.size()-primary_count>=8) break;
    if (recovery_ids.insert(t.id).second) targets.push_back(t);
  }
  const size_t recovery_end=targets.size();
  // A recently reached transit goal is discouraged, not a permanent barrier
  // to necessary backtracking. Try it only if ordinary safe searches fail.
  // Search/execution failures retain their separate cooldown and hard gates.
  std::sort(backtrack.begin(),backtrack.end(),[](const Target& a,const Target& b){return a.utility>b.utility;});
  for (size_t i=0;i<std::min<size_t>(2,backtrack.size());++i) targets.push_back(backtrack[i]);
  const ht_cost_ns::Pose2 start{robot_position_.x(),robot_position_.y(),robot_yaw_};
  RCLCPP_INFO_THROTTLE(node_->get_logger(),*node_->get_clock(),3000,
    "XYtheta candidates=%zu selected=%zu start=(%.2f,%.2f,%.2f) HT_start=%d collision=%d",
    targets.size(),selected.size(),start.x,start.y,start.yaw,
    static_cast<int>(ht->poseSupport(start.x,start.y,start.yaw)),
    viewpoint_manager_->InCollisionAtPose(robot_position_));
  int attempted=0;
  int recovery_attempted=0,backtrack_attempted=0;
  int best_target=-1;
  double best_score=-std::numeric_limits<double>::infinity();
  double best_gain=0;
  ht_cost_ns::XYThetaPlan best_plan;
  std::unordered_set<int> attempted_ids;
  bool best_recovery=false;
  const auto search_started=std::chrono::steady_clock::now();
  for (const size_t ti:ht_cost_ns::targetSearchOrder(targets.size(),primary_count,recovery_end)) {
    const auto& target=targets[ti];
    if (target.backtrack && best_target>=0) break;
    // Recovery is interleaved with primary goals. A known gain route skips
    // recovery, without skipping the remaining primary comparisons.
    if (target.recovery && best_target>=0 && best_gain>0) continue;
    if (attempted>=6 && !target.backtrack && !backtrack.empty()) continue;
    if (!attempted_ids.insert(target.id).second) continue;
    if (attempted>=8) break;
    const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-search_started).count();
    const double remaining=ht_cycle_search_seconds_-elapsed-
      (!target.backtrack && !backtrack.empty()?std::min(.1,ht_cycle_search_seconds_/3):0);
    if (remaining<=.001) continue;
    ++attempted;
    if (target.backtrack) ++backtrack_attempted;
    else if (target.recovery) ++recovery_attempted;
    const auto goal=viewpoint_manager_->GetViewPointPosition(target.id);
    int geometry_rejections=0,ht_rejections=0,memory_rejections=0,reserve_rejections=0,geometry_queries=0;
    double geometry_seconds=0;
    auto valid=[&](ht_cost_ns::Pose2 previous,ht_cost_ns::Pose2 next,double v) {
      const Eigen::Vector3d point(next.x,next.y,robot_position_.z());
      if (!viewpoint_manager_->InLocalPlanningHorizon(point)) {++geometry_rejections;return false;}
      const auto geometry_started=std::chrono::steady_clock::now();
      const bool colliding=viewpoint_manager_->InCollisionAtPose(point,std::abs(v)>1e-9 ? ht_tracking_margin_:0.0);
      geometry_seconds+=std::chrono::duration<double>(std::chrono::steady_clock::now()-geometry_started).count();
      ++geometry_queries;
      if (colliding) {++geometry_rejections;return false;}
      (void)v;
      if (!ht->permits(ht->motionSupport(previous,next))) {++ht_rejections;return false;}
      if (!ht_execution_failures_.permits(previous,next,now)) {++memory_rejections;return false;}
      if (!ht_cost_ns::successorHeadingReserve(start,previous,next,ht_heading_margin_,
            [&](ht_cost_ns::Pose2 p){return ht->permits(ht->poseSupport(p.x,p.y,p.yaw));})) {
        ++reserve_rejections;return false;
      }
      return true;
    };
    auto config=xytheta_config_;
    config.try_direct_connection=true;
    config.max_search_seconds=std::min(config.max_search_seconds,remaining);
    const auto query_started=std::chrono::steady_clock::now();
    const auto plan=ht_cost_ns::planXYTheta(start,{goal.x,goal.y,goal.z},config,valid);
    const double query_seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-query_started).count();
    RCLCPP_INFO(node_->get_logger(),
      "HT_SEARCH_AUDIT target=%d goal=(%.6f,%.6f) gain=%.1f recovery=%d backtrack=%d ht_stamp=%.9f termination=%s elapsed_s=%.6f budget_s=%.6f expanded=%d expansion_limit=%d geometry_queries=%d geometry_s=%.6f geometry_reject=%d ht_reject=%d memory_reject=%d reserve_reject=%d direct=%d dominated_pruned=%d",
      target.id,goal.x,goal.y,target.gain,target.recovery,target.backtrack,ht->cycleStamp(),
      ht_cost_ns::terminationName(plan.termination),query_seconds,config.max_search_seconds,plan.expanded,
      config.max_expansions,geometry_queries,geometry_seconds,geometry_rejections,ht_rejections,memory_rejections,reserve_rejections,plan.direct_connection,plan.dominated_edges_pruned);
    if (!plan.reached || plan.poses.size()<2) {
      if (target.id==committed_id) ht_commitment_.reject(now);
      RCLCPP_INFO_THROTTLE(node_->get_logger(),*node_->get_clock(),3000,
        "XYtheta no route to %d (%.1f,%.1f), expanded=%d geometry_reject=%d ht_reject=%d",
        target.id,goal.x,goal.y,plan.expanded,geometry_rejections,ht_rejections);
      continue;
    }
    // Exploration decisions use the executable XYtheta route's travel time,
    // including turns and reverse motion, rather than straight-line XY range.
    // The LiDAR coverage gain is position-based because this sensor scans 360°.
    const double score=target.gain>0 ?
      target.gain/(1.0+plan.seconds)*(target.id==ht_previous_target_?1.15:1.0) :
      ht_cost_ns::transitScore(target.progress,ht_visits_.penalty({goal.x,goal.y,goal.z}),plan.seconds);
    if (score<=best_score) continue;
    best_score=score;
    best_target=target.id;
    best_gain=target.gain;
    best_plan=plan;
    best_recovery=target.recovery;
    // A safe, progressing committed goal wins before comparing new utilities.
    // It is re-searched and hard-checked against this cycle's current map.
    if (target.id==committed_id) break;
  }
  RCLCPP_INFO(node_->get_logger(),"HT_SEARCH_SUMMARY targets=%zu primary=%zu attempts=%d cycle_budget_s=%.6f elapsed_s=%.6f output_target=%d ht_stamp=%.9f recovery_attempts=%d backtrack_attempts=%d",
    targets.size(),primary_count,attempted,ht_cycle_search_seconds_,
    std::chrono::duration<double>(std::chrono::steady_clock::now()-search_started).count(),best_target,ht->cycleStamp(),recovery_attempted,backtrack_attempted);
  if (best_target<0) return result;
  ht_candidate_target_=best_target;
  ht_last_cost_=-best_score;
  ht_candidate_path_.header.frame_id="map";
  ht_candidate_path_.header.stamp=node_->now();
    Node first(robot_position_);first.type_=NodeType::ROBOT;
    result.Append(first);
    for (size_t i=0;i<best_plan.poses.size();++i) {
      const auto& p=best_plan.poses[i];
      geometry_msgs::msg::PoseStamped stamped;
      stamped.header=ht_candidate_path_.header;
      stamped.pose.position.x=p.x;stamped.pose.position.y=p.y;
      stamped.pose.position.z=robot_position_.z();
      stamped.pose.orientation.z=std::sin(p.yaw/2);
      stamped.pose.orientation.w=std::cos(p.yaw/2);
      ht_candidate_path_.poses.push_back(stamped);
      if (i==0) continue;
      Node node(Eigen::Vector3d(p.x,p.y,robot_position_.z()));
      node.type_=i+1==best_plan.poses.size() ? NodeType::LOCAL_VIEWPOINT : NodeType::LOCAL_VIA_POINT;
      node.local_viewpoint_ind_=i+1==best_plan.poses.size() ? best_target : -1;
      result.Append(node);
    }
    ordered.push_back(robot_viewpoint_ind_);
    ordered.push_back(best_target);
    RCLCPP_INFO_THROTTLE(node_->get_logger(),*node_->get_clock(),1000,
      "XYtheta exploration target=%d gain=%.1f score=%.2f states=%zu expanded=%d travel=%.2fs candidates=%d held=%d goal=(%.2f,%.2f) guide=(%.2f,%.2f) recovery=%d guide_active=%d guide_idle=%.1f revisit=%.2f",
      best_target,best_gain,best_score,best_plan.poses.size(),best_plan.expanded,best_plan.seconds,attempted,
      best_target==committed_id,best_plan.poses.back().x,best_plan.poses.back().y,
      ht_global_guide_.x(),ht_global_guide_.y(),best_recovery,ht_has_global_guide_,ht_guide_progress_.idle_seconds,
      ht_visits_.penalty({best_plan.poses.back().x,best_plan.poses.back().y,0}));
    return result;
}

exploration_path_ns::ExplorationPath LocalCoveragePlanner::PlanHTReturn(const Eigen::Vector3d& target,double search_seconds) {
  ScopedSearchRuntime measured{find_path_runtime_};
  using namespace exploration_path_ns;
  ExplorationPath result;
  ht_output_path_.poses.clear();
  const auto ht=viewpoint_manager_->HT();
  if (!ht->ready() || !std::isfinite(robot_yaw_)) return result;
  const ht_cost_ns::Pose2 start{robot_position_.x(),robot_position_.y(),robot_yaw_};
  auto valid=[&](ht_cost_ns::Pose2 previous,ht_cost_ns::Pose2 next,double v) {
    const Eigen::Vector3d point(next.x,next.y,robot_position_.z());
    if (!viewpoint_manager_->InLocalPlanningHorizon(point) ||
        viewpoint_manager_->InCollisionAtPose(point,std::abs(v)>1e-9 ? ht_tracking_margin_:0.0) ||
        !ht->permits(ht->motionSupport(previous,next)) ||
        !ht_execution_failures_.permits(previous,next,node_->now().seconds()) ||
        !ht_cost_ns::successorHeadingReserve(start,previous,next,ht_heading_margin_,
          [&](ht_cost_ns::Pose2 p){return ht->permits(ht->poseSupport(p.x,p.y,p.yaw));})) return false;
    (void)v;
    return true;
  };
  auto config=xytheta_config_;
  if(ht->tareCoverage()) config.try_direct_connection=true;
  if(search_seconds>=0) config.max_search_seconds=std::min(config.max_search_seconds,search_seconds);
  const auto plan=ht_cost_ns::planXYTheta(start,{target.x(),target.y(),target.z()},
                                         config,valid);
  RCLCPP_INFO(node_->get_logger(),"HT_WAYPOINT_SEARCH target=(%.3f,%.3f) reached=%d termination=%s poses=%zu expanded=%d direct=%d pruned=%zu",
    target.x(),target.y(),plan.reached,ht_cost_ns::terminationName(plan.termination),plan.poses.size(),plan.expanded,
    plan.direct_connection,static_cast<size_t>(plan.dominated_edges_pruned));
  if (!plan.reached || plan.poses.size()<2) {
    RCLCPP_WARN_THROTTLE(node_->get_logger(),*node_->get_clock(),3000,
      "HT return search failed: robot=(%.3f,%.3f) checkpoint=(%.3f,%.3f) distance=%.3f reached=%d poses=%zu expanded=%d",
      start.x,start.y,target.x(),target.y(),std::hypot(target.x()-start.x,target.y()-start.y),
      plan.reached,plan.poses.size(),plan.expanded);
    return result;
  }
  ht_output_path_.header.frame_id="map";
  ht_output_path_.header.stamp=node_->now();
  for (size_t i=0;i<plan.poses.size();++i) {
    const auto& p=plan.poses[i];
    geometry_msgs::msg::PoseStamped stamped;
    stamped.header=ht_output_path_.header;
    stamped.pose.position.x=p.x;stamped.pose.position.y=p.y;
    stamped.pose.position.z=robot_position_.z();
    stamped.pose.orientation.z=std::sin(p.yaw/2);
    stamped.pose.orientation.w=std::cos(p.yaw/2);
    ht_output_path_.poses.push_back(stamped);
    Node node(Eigen::Vector3d(p.x,p.y,robot_position_.z()));
    node.type_=i==0 ? NodeType::ROBOT :
      (i+1==plan.poses.size() ? NodeType::HOME : NodeType::LOCAL_VIA_POINT);
    result.Append(node);
  }
  return result;
}
}  // namespace local_coverage_planner_ns
