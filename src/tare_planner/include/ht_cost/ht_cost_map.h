#pragma once
#include "ht_cost/execution_policy.h"
#include "ht_cost/xytheta_planner.h"
#include <rclcpp/rclcpp.hpp>
#include <grid_map_msgs/msg/grid_map.hpp>
#include <std_msgs/msg/bool.hpp>
#include <tare_planner/msg/startup_prior.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include <mutex>
#include <memory>
#include <map>

namespace ht_cost_ns {
class HtCostMap {
 public:
  explicit HtCostMap(rclcpp::Node::SharedPtr node,bool publish_permission=true);
  bool enabled() const { return enabled_; }
  bool tareCoverage() const { return enabled_ && tare_coverage_; }
  struct TerrainCell { double x=0,y=0,height=std::numeric_limits<double>::quiet_NaN(),stamp=0; bool feasible=false; };
  std::vector<TerrainCell> terrainWindow(double x,double y,double radius);
  // Unknown historical guidance cells stay optimistic; execution is strict.
  bool terrainAdmissible(double x,double y);
  std::vector<bool> terrainAdmissible(const std::vector<Point>& points);
  void beginCycle();
  bool ready() const;
  std::string status() const;
  double cost(const Point& a, const Point& b) const;
  bool knownSegment(const Point& a, const Point& b) const;
  Support support(const Point& a, const Point& b) const;
  Support poseSupport(double x,double y,double yaw) const;
  // Shared swept gate for search, publication and tracking. Configuration
  // scores use actual body yaw throughout the sweep, including reverse.
  // Legacy point/travel scores additionally check translation direction.
  Support motionSupport(Pose2 a,Pose2 b) const;
  bool permits(Support s) const { return s==Support::KNOWN || s==Support::STARTUP_PRIOR ||
    (s==Support::UNKNOWN && geometric_fallback_ && !budget_.exhausted()); }
  // Only the planner owns initialization; followers import its immutable epoch.
  void start(Point p);
  void updateExecution(Point p,bool was_fallback);
  StartupPrior startupPrior() const;
  const FallbackBudget& budget() const { return budget_; }
  double fallbackLookahead() const { return fallback_lookahead_; }
  double fallbackSpeed() const { return fallback_speed_; }
  void publishPermission(bool allowed);
  double lookahead() const { return lookahead_; }
  double reachedDistance() const { return reached_distance_; }
  double step() const { return step_; }
  double resolution() const { return cycle_ ? cycle_->resolution : 0.; }
  double cycleStamp() const { return cycle_ ? cycle_->stamp : -1.; }
 private:
  Support supportDirected(const Point& a,const Point& b,double heading) const;
  void receive(grid_map_msgs::msg::GridMap::ConstSharedPtr msg);
  rclcpp::Clock::SharedPtr clock_;
  rclcpp::Logger logger_;
  StartupPrior prior_;
  bool owns_prior_=false, startup_sync_fault_=false;
  mutable std::mutex prior_mutex_;
  rclcpp::Publisher<tare_planner::msg::StartupPrior>::SharedPtr startup_pub_;
  rclcpp::Subscription<tare_planner::msg::StartupPrior>::SharedPtr startup_sub_;
  void publishStartupPrior();
  void receiveStartupPrior(const tare_planner::msg::StartupPrior& msg);
  FallbackBudget budget_;
  bool geometric_fallback_=false;
  // Extra opposite travel-channel gate for point/travel scores only. A
  // static configuration sweep is already checked in both traversal orders
  // by inspecting the same positions and body headings; it has no separate
  // velocity-conditioned prediction and must not invent a theta+pi demand.
  bool require_reversible_motion_=false;
  bool configuration_scores_=false;
  double fallback_lookahead_=0.5, fallback_speed_=0.2;
  bool enabled_=false, calibrated_=false, tare_coverage_=true;
  double min_probability_=0.5, timeout_=1, step_=0.02, lookahead_=2;
  double footprint_radius_=0.6, heading_offset_=0;
  double reached_distance_=0.3;
  std::array<int,8> channel_order_{{0,1,2,3,4,5,6,7}};
  std::string frame_;
  std::string latest_error_="HT_MAP_MISSING", cycle_error_="HT_MAP_MISSING";
  std::mutex mutex_;
  bool collect_terrain_=false;
  std::map<std::pair<int,int>,TerrainCell> terrain_history_;
  std::shared_ptr<Map> latest_, cycle_;
  tf2_ros::Buffer buffer_;
  std::unique_ptr<tf2_ros::TransformListener> listener_;
  rclcpp::CallbackGroup::SharedPtr map_callback_group_;
  rclcpp::Subscription<grid_map_msgs::msg::GridMap>::SharedPtr subscription_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr permission_;
};
}
