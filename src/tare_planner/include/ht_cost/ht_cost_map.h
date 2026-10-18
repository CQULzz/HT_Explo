#pragma once
#include "ht_cost/execution_policy.h"
#include "ht_cost/xytheta_planner.h"
#include <rclcpp/rclcpp.hpp>
#include <grid_map_msgs/msg/grid_map.hpp>
#include <std_msgs/msg/bool.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <mutex>
#include <memory>

namespace ht_cost_ns {
class HtCostMap {
 public:
  explicit HtCostMap(rclcpp::Node::SharedPtr node,bool publish_permission=true);
  bool enabled() const { return enabled_; }
  void beginCycle();
  bool ready() const;
  std::string status() const;
  double cost(const Point& a, const Point& b) const;
  bool knownSegment(const Point& a, const Point& b) const;
  Support support(const Point& a, const Point& b) const;
  Support poseSupport(double x,double y,double yaw) const;
  // Shared swept gate for search, publication and tracking. Includes body
  // heading changes and travel direction, including reverse motion.
  Support motionSupport(Pose2 a,Pose2 b) const;
  bool permits(Support s) const { return s==Support::KNOWN || s==Support::STARTUP_PRIOR ||
    (s==Support::UNKNOWN && geometric_fallback_ && !budget_.exhausted()); }
  void start(Point p) { prior_.initialize(p,clock_->now().seconds()); }
  void updateExecution(Point p,bool was_fallback) {
    const double now=clock_->now().seconds();prior_.update(p,now);budget_.update(now,p,was_fallback);
  }
  const FallbackBudget& budget() const { return budget_; }
  double fallbackLookahead() const { return fallback_lookahead_; }
  double fallbackSpeed() const { return fallback_speed_; }
  void publishPermission(bool allowed);
  double lookahead() const { return lookahead_; }
  double reachedDistance() const { return reached_distance_; }
  double step() const { return step_; }
  double cycleStamp() const { return cycle_ ? cycle_->stamp : -1.; }
 private:
  Support supportDirected(const Point& a,const Point& b,double heading) const;
  void receive(grid_map_msgs::msg::GridMap::ConstSharedPtr msg);
  rclcpp::Clock::SharedPtr clock_;
  rclcpp::Logger logger_;
  StartupPrior prior_;
  FallbackBudget budget_;
  bool geometric_fallback_=false;
  bool require_reversible_motion_=false;
  bool configuration_scores_=false;
  double fallback_lookahead_=0.5, fallback_speed_=0.2;
  bool enabled_=false, calibrated_=false;
  double min_probability_=0.5, timeout_=1, step_=0.02, lookahead_=2;
  double footprint_radius_=0.6, heading_offset_=0;
  double reached_distance_=0.3;
  std::array<int,8> channel_order_{{0,1,2,3,4,5,6,7}};
  std::string frame_;
  std::string latest_error_="HT_MAP_MISSING", cycle_error_="HT_MAP_MISSING";
  std::mutex mutex_;
  std::shared_ptr<Map> latest_, cycle_;
  tf2_ros::Buffer buffer_;
  std::unique_ptr<tf2_ros::TransformListener> listener_;
  rclcpp::CallbackGroup::SharedPtr map_callback_group_;
  rclcpp::Subscription<grid_map_msgs::msg::GridMap>::SharedPtr subscription_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr permission_;
};
}
