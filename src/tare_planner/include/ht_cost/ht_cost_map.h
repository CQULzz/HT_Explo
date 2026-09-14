#pragma once
#include "ht_cost/ht_cost_core.h"
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
  explicit HtCostMap(rclcpp::Node::SharedPtr node);
  bool enabled() const { return enabled_; }
  void beginCycle();
  bool ready() const;
  double cost(const Point& a, const Point& b) const;
  bool knownSegment(const Point& a, const Point& b) const;
  void publishPermission(bool allowed);
  double lookahead() const { return lookahead_; }
  double reachedDistance() const { return reached_distance_; }
  double step() const { return step_; }
 private:
  void receive(grid_map_msgs::msg::GridMap::ConstSharedPtr msg);
  rclcpp::Clock::SharedPtr clock_;
  rclcpp::Logger logger_;
  bool enabled_=false, calibrated_=false;
  double weight_=1, unknown_penalty_=2, timeout_=1, step_=0.02, lookahead_=2;
  double footprint_radius_=0.6, heading_offset_=0;
  double reached_distance_=0.3;
  std::array<int,8> channel_order_{{0,1,2,3,4,5,6,7}};
  std::string frame_;
  std::mutex mutex_;
  std::shared_ptr<Map> latest_, cycle_;
  tf2_ros::Buffer buffer_;
  tf2_ros::TransformListener listener_;
  rclcpp::Subscription<grid_map_msgs::msg::GridMap>::SharedPtr subscription_;
  rclcpp::Publisher<std_msgs::msg::Bool>::SharedPtr permission_;
};
}
