#include "local_coverage_planner/local_coverage_planner.h"
#include <algorithm>
#include <cmath>
#include <limits>

namespace local_coverage_planner_ns {

exploration_path_ns::ExplorationPath LocalCoveragePlanner::SolveHTTSP(
    const std::vector<int>& selected,std::vector<int>& ordered) {
  using namespace exploration_path_ns;
  ExplorationPath result;
  ordered.clear();
  ht_candidate_path_.poses.clear();
  ht_candidate_target_=-1;
  ht_last_cost_=std::numeric_limits<double>::infinity();
  auto ht=viewpoint_manager_->HT();
  if (!ht->ready() || !std::isfinite(robot_yaw_)) return result;

  struct Target {int id;double utility;double gain;double progress;};
  std::vector<Target> targets;
  for (int id:selected) {
    if (id==robot_viewpoint_ind_ || !viewpoint_manager_->InRange(id)) continue;
    const auto p=viewpoint_manager_->GetViewPointPosition(id);
    const double distance=std::hypot(p.x-robot_position_.x(),p.y-robot_position_.y());
    if (distance<xytheta_config_.goal_radius || distance>xytheta_config_.max_radius) continue;
    const double gain=std::max(0,viewpoint_manager_->GetViewPointCoveredPointNum(id))+
      2.0*std::max(0,viewpoint_manager_->GetViewPointCoveredFrontierPointNum(id));
    double utility=gain/(1.0+distance);
    if (gain<=0) {
      if ((id!=start_viewpoint_ind_ && id!=end_viewpoint_ind_) || distance<1.0) continue;
      utility=-8.0+distance/(1.0+distance);
    } else if (id==ht_previous_target_) {
      utility*=1.15;
    }
    targets.push_back({id,utility,gain,0});
  }
  std::sort(targets.begin(),targets.end(),[](const Target& a,const Target& b) {
    return a.utility>b.utility;
  });
  if (targets.size()>4) targets.resize(4);
  // The HT map is a rolling ~10 m window, while TARE's global boundary can
  // be farther away. Move to a reachable candidate inside the current map,
  // then replan as the window follows the robot.
  int distant_id=-1;
  double distant_range=std::numeric_limits<double>::infinity();
  for (int id:selected) {
    if (id==robot_viewpoint_ind_ || !viewpoint_manager_->InRange(id)) continue;
    const auto p=viewpoint_manager_->GetViewPointPosition(id);
    const double d=std::hypot(p.x-robot_position_.x(),p.y-robot_position_.y());
    if (d>xytheta_config_.max_radius && d<distant_range) {distant_range=d;distant_id=id;}
  }
  if (distant_id>=0) {
    const auto distant=viewpoint_manager_->GetViewPointPosition(distant_id);
    std::vector<Target> stepping;
    for (int id:viewpoint_manager_->GetViewPointCandidateIndices()) {
      if (id==robot_viewpoint_ind_) continue;
      const auto p=viewpoint_manager_->GetViewPointPosition(id);
      const double range=std::hypot(p.x-robot_position_.x(),p.y-robot_position_.y());
      if (range<1.0 || range>std::min(4.0,xytheta_config_.max_radius-1.0)) continue;
      const double remaining=std::hypot(p.x-distant.x,p.y-distant.y);
      const double progress=distant_range-remaining;
      if (progress<0.8) continue;
      stepping.push_back({id,-10.0+progress/(1.0+range),0,progress});
    }
    std::sort(stepping.begin(),stepping.end(),[](const Target& a,const Target& b) {
      return a.utility>b.utility;
    });
    for (size_t i=0;i<std::min<size_t>(4,stepping.size());++i) targets.push_back(stepping[i]);
  }
  const ht_cost_ns::Pose2 start{robot_position_.x(),robot_position_.y(),robot_yaw_};
  RCLCPP_INFO_THROTTLE(node_->get_logger(),*node_->get_clock(),3000,
    "XYtheta candidates=%zu selected=%zu start=(%.2f,%.2f,%.2f) HT_start=%d collision=%d",
    targets.size(),selected.size(),start.x,start.y,start.yaw,
    static_cast<int>(ht->poseSupport(start.x,start.y,start.yaw)),
    viewpoint_manager_->InCollision(robot_position_));
  int attempted=0;
  int best_target=-1;
  double best_score=-std::numeric_limits<double>::infinity();
  double best_gain=0;
  ht_cost_ns::XYThetaPlan best_plan;
  for (const auto& target:targets) {
    if (attempted++>=8) break;
    const auto goal=viewpoint_manager_->GetViewPointPosition(target.id);
    int geometry_rejections=0,ht_rejections=0;
    auto valid=[&](ht_cost_ns::Pose2 previous,ht_cost_ns::Pose2 next,double v) {
      const Eigen::Vector3d point(next.x,next.y,robot_position_.z());
      if (!viewpoint_manager_->InLocalPlanningHorizon(point) ||
          viewpoint_manager_->InCollision(point)) {++geometry_rejections;return false;}
      if (!ht->permits(ht->poseSupport(next.x,next.y,next.yaw))) {++ht_rejections;return false;}
      if (std::abs(v)>1e-9) {
        const ht_cost_ns::Point a{previous.x,previous.y,robot_position_.z()};
        const ht_cost_ns::Point b{next.x,next.y,robot_position_.z()};
        if (!ht->permits(ht->support(a,b))) {++ht_rejections;return false;}
      }
      return true;
    };
    const auto plan=ht_cost_ns::planXYTheta(start,{goal.x,goal.y,goal.z},
                                          xytheta_config_,valid);
    if (!plan.reached || plan.poses.size()<2) {
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
      -8.0+target.progress/(1.0+plan.seconds);
    if (score<=best_score) continue;
    best_score=score;
    best_target=target.id;
    best_gain=target.gain;
    best_plan=plan;
  }
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
      "XYtheta exploration target=%d gain=%.1f score=%.2f states=%zu expanded=%d travel=%.2fs candidates=%d",
      best_target,best_gain,best_score,best_plan.poses.size(),best_plan.expanded,best_plan.seconds,attempted);
    return result;
}

exploration_path_ns::ExplorationPath LocalCoveragePlanner::PlanHTReturn(const Eigen::Vector3d& target) {
  using namespace exploration_path_ns;
  ExplorationPath result;
  ht_output_path_.poses.clear();
  const auto ht=viewpoint_manager_->HT();
  if (!ht->ready() || !std::isfinite(robot_yaw_)) return result;
  const ht_cost_ns::Pose2 start{robot_position_.x(),robot_position_.y(),robot_yaw_};
  auto valid=[&](ht_cost_ns::Pose2 previous,ht_cost_ns::Pose2 next,double v) {
    const Eigen::Vector3d point(next.x,next.y,robot_position_.z());
    if (!viewpoint_manager_->InLocalPlanningHorizon(point) ||
        viewpoint_manager_->InCollision(point) ||
        !ht->permits(ht->poseSupport(next.x,next.y,next.yaw))) return false;
    if (std::abs(v)>1e-9) {
      const ht_cost_ns::Point a{previous.x,previous.y,robot_position_.z()};
      const ht_cost_ns::Point b{next.x,next.y,robot_position_.z()};
      if (!ht->permits(ht->support(a,b))) return false;
    }
    return true;
  };
  const auto plan=ht_cost_ns::planXYTheta(start,{target.x(),target.y(),target.z()},
                                         xytheta_config_,valid);
  if (!plan.reached || plan.poses.size()<2) return result;
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
