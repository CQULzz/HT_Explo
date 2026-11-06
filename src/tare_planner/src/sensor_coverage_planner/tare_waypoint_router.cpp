#include <iomanip>
#include <map>
#include <sstream>
#include "sensor_coverage_planner/sensor_coverage_planner_ground.h"
#include "ht_cost/tare_waypoint_route.h"
namespace sensor_coverage_planner_3d_ns {
bool SensorCoveragePlanner3D::RouteTareWaypoint(const exploration_path_ns::ExplorationPath& route) {
  using ht_cost_ns::Point;
  auto visual=route.GetPath();visual.header.frame_id="map";visual.header.stamp=now();
  tare_route_pub_->publish(visual);
  local_coverage_planner_->ClearHTPath();
  std::map<std::string,int> rejected_headings;
  auto diagnostic=[&](const char* reason,size_t checked,int unsupported,int too_close,int searches) {
    std::ostringstream data;
    data << std::setprecision(17) << "{\"stage\":\"route\",\"reason\":" << std::quoted(reason)
         << ",\"sim_time_s\":" << now().seconds()
         << ",\"map_source_s\":" << viewpoint_manager_->HT()->cycleStamp()
         << ",\"checked\":" << checked << ",\"unsupported_endpoints\":" << unsupported
         << ",\"too_close\":" << too_close << ",\"searches\":" << searches
         << ",\"rejected_headings\":{";
    bool first=true;
    for(const auto& item:rejected_headings) {
      if(!first)data << ',';
      first=false;data << std::quoted(item.first) << ':' << item.second;
    }
    data << "}}";
    std_msgs::msg::String message;message.data=data.str();decision_diagnostics_pub_->publish(message);
  };

  if(!lookahead_point_update_ || route.nodes_.empty()) {
    diagnostic("NO_NATIVE_ROUTE",0,0,0,0);return false;
  }
  const auto ht=viewpoint_manager_->HT();
  ht->beginCycle();
  if(!ht->permits(ht->poseSupport(robot_position_.x,robot_position_.y,robot_yaw_))) {
    RCLCPP_WARN_THROTTLE(get_logger(),*get_clock(),3000,
      "TARE_ROUTE start rejected: %s",ht->poseRejection(robot_position_.x,robot_position_.y,robot_yaw_).c_str());
    diagnostic("CURRENT_POSE_REJECTED",0,0,0,0);return false;
  }
  if(viewpoint_manager_->InCollisionAtPose(Eigen::Vector3d(robot_position_.x,robot_position_.y,robot_position_.z))) {
    RCLCPP_WARN_THROTTLE(get_logger(),*get_clock(),3000,
      "TARE_ROUTE physical start occupied; do not repeat identical invalid-start searches");
    diagnostic("CURRENT_GEOMETRY_BLOCKED",0,0,0,0);return false;
  }
  std::vector<Point> points;std::vector<bool> robots;
  for(const auto& n:route.nodes_) {
    points.push_back({n.position_.x(),n.position_.y(),n.position_.z()});
    robots.push_back(n.type_==exploration_path_ns::NodeType::ROBOT);
  }
  const Point raw{lookahead_point_.x(),lookahead_point_.y(),lookahead_point_.z()};
  auto branch=ht_cost_ns::tareBranch(points,robots,raw);
  // Native rush-home path has a ROBOT anchor and HOME endpoint as well.
  if(branch.empty()) {
    RCLCPP_WARN(get_logger(),"TARE_ROUTE missing native branch; holding without changing TSP goal");
    diagnostic("NO_NATIVE_BRANCH",0,0,0,0);return false;
  }
  // Match upstream PublishWaypoint's extension and rush-home rule. The zero
  // distance guard prevents its undefined dx/r case without selecting a goal.
  Point native=raw;
  if(exploration_finished_ && near_home_ && kRushHome) {
    native={initial_position_.x(),initial_position_.y(),initial_position_.z()};
  } else {
    double dx=raw.x-robot_position_.x,dy=raw.y-robot_position_.y;
    const double d=std::hypot(dx,dy);
    const double extension=lookahead_point_in_line_of_sight_ ? kExtendWayPointDistanceBig:kExtendWayPointDistanceSmall;
    if(kExtendWayPoint && d>1e-6 && d<extension) {
      native.x=robot_position_.x+dx/d*extension;native.y=robot_position_.y+dy/d*extension;
    }
  }
  geometry_msgs::msg::PointStamped goal;goal.header=visual.header;
  goal.point.x=native.x;goal.point.y=native.y;goal.point.z=native.z;tare_command_waypoint_=goal.point;tare_waypoint_pub_->publish(goal);
  if(std::hypot(native.x-branch.back().x,native.y-branch.back().y)>1e-6) branch.push_back(native);
  nav_msgs::msg::Path selected;selected.header=visual.header;
  for(const auto& p:branch) {geometry_msgs::msg::PoseStamped pose;pose.header=visual.header;
    pose.pose.position.x=p.x;pose.pose.position.y=p.y;pose.pose.position.z=p.z;pose.pose.orientation.w=1;
    selected.poses.push_back(pose);}
  tare_branch_pub_->publish(selected);
  const auto started=std::chrono::steady_clock::now();
  std::vector<Point> checked;
  int unsupported=0,too_close=0,searches=0;
  bool start_rejected=false;
  auto attempt=[&](Point p,double length,bool adaptive) {
    for(const auto& previous:checked)
      if(std::hypot(p.x-previous.x,p.y-previous.y)<1e-6) return false;
    checked.push_back(p);
    if(std::hypot(p.x-robot_position_.x,p.y-robot_position_.y)<.4) {++too_close;return false;}
    // Each target is an independent search. A previous attempt must not
    // pin all subsequent prefixes to an expired map when new evidence has
    // arrived. Never change the snapshot inside PlanHTReturn itself.
    ht->beginCycle();
    if(!ht->permits(ht->poseSupport(robot_position_.x,robot_position_.y,robot_yaw_))) {
      start_rejected=true;return false;
    }
    bool supported=false;
    for(int k=0;k<8;++k) {
      const double heading=k*ht_cost_ns::kPi/4;
      if(ht->permits(ht->poseSupport(p.x,p.y,heading))) {supported=true;break;}
      ++rejected_headings[ht->poseRejection(p.x,p.y,heading)];
    }
    if(!supported) {++unsupported;return false;}
    const double remaining=.35-std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    if(remaining<=0) return false;
    ++searches;
    auto path=local_coverage_planner_->PlanHTReturn(Eigen::Vector3d(p.x,p.y,p.z),remaining);
    goal.point.x=p.x;goal.point.y=p.y;goal.point.z=p.z;ht_route_goal_pub_->publish(goal);
    RCLCPP_INFO(get_logger(),"TARE_ROUTE native=(%.3f,%.3f) lookahead=(%.3f,%.3f) local=(%.3f,%.3f) prefix=%.3f branch=%zu poses=%zu success=%d adaptive=%d distance=%.3f map_stamp=%.9f",
      native.x,native.y,raw.x,raw.y,p.x,p.y,length,branch.size(),path.nodes_.size(),!path.nodes_.empty(),adaptive,
      std::hypot(p.x-robot_position_.x,p.y-robot_position_.y),viewpoint_manager_->HT()->cycleStamp());
    if(!path.nodes_.empty()) diagnostic("ROUTE_FOUND",checked.size(),unsupported,too_close,searches);
    return !path.nodes_.empty();
  };
  // Preserve the existing fast path and its behavior when an integer target
  // works. All fallbacks share its original 0.35s wall-time search budget.
  for(double length:{4.,3.,2.,1.}) {
    if(start_rejected || std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()>=.35) break;
    if(attempt(ht_cost_ns::tarePrefix(branch,length),length,false)) return true;
  }
  if(!start_rejected && std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()<.35) {
    const auto targets=ht_cost_ns::tareAdaptivePrefixes(branch,
      {robot_position_.x,robot_position_.y,robot_position_.z},viewpoint_manager_->HT()->resolution());
    for(const auto& target:targets) {
      if(start_rejected || std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count()>=.35) break;
      if(attempt(target.point,target.arc,true)) return true;
    }
  }
  RCLCPP_WARN(get_logger(),"TARE_ROUTE failed same-goal prefixes; holding native=(%.3f,%.3f) checked=%zu unsupported=%d too_close=%d searches=%d elapsed=%.6f map_stamp=%.9f",
    native.x,native.y,checked.size(),unsupported,too_close,searches,
    std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count(),viewpoint_manager_->HT()->cycleStamp());
  diagnostic(start_rejected ? "CURRENT_POSE_CHANGED":"NO_EXECUTABLE_PREFIX",
             checked.size(),unsupported,too_close,searches);
  return false;
}
}
