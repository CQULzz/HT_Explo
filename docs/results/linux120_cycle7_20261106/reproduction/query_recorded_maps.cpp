#include <bits/stdc++.h>
#include <rclcpp/rclcpp.hpp>
#include <grid_map_msgs/msg/grid_map.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/string.hpp>
#include <tare_planner/msg/startup_prior.hpp>
#include <tf2_ros/buffer.h>
#include <tf2_ros/transform_listener.h>
#include "ht_cost/execution_policy.h"
#include "ht_cost/xytheta_planner.h"
// Read-only offline audit: feed recorded CDR directly to the production decoder.
#define private public
#include "ht_cost/ht_cost_map.h"
#undef private
int main(int argc,char** argv) {
  if(argc!=4)return 2;
  rclcpp::init(0,nullptr);
  auto n=std::make_shared<rclcpp::Node>("offline_recorded_pose_query",rclcpp::NodeOptions().parameter_overrides({
    rclcpp::Parameter("use_sim_time",true),rclcpp::Parameter("ht_enabled",true),
    rclcpp::Parameter("ht_directions_calibrated",true),rclcpp::Parameter("ht_score_semantics","configuration"),
    rclcpp::Parameter("ht_exploration_mode","legacy_xytheta_greedy"),
    rclcpp::Parameter("ht_topic","/offline_recorded_map"),rclcpp::Parameter("ht_map_timeout",1.),
    rclcpp::Parameter("ht_startup_topic","/offline_recorded_prior"),
    rclcpp::Parameter("ht_startup_radius",1.5),rclcpp::Parameter("ht_startup_duration",60.),
    rclcpp::Parameter("ht_startup_assume_traversable",true)}));
  auto clock=n->get_clock()->get_clock_handle();
  if(rcl_enable_ros_time_override(clock)!=RCL_RET_OK)return 3;
  ht_cost_ns::HtCostMap ht(n);
  std::ifstream input(argv[2]);int64_t mission;ht_cost_ns::Point anchor;
  input>>mission>>anchor.x>>anchor.y>>anchor.z;
  if(rcl_set_ros_time_override(clock,mission)!=RCL_RET_OK)return 4;
  ht.start(anchor);
  int64_t stamp,query;double x,y,yaw;
  std::ofstream out(argv[3]);out<<std::setprecision(17);
  rclcpp::Serialization<grid_map_msgs::msg::GridMap> serializer;
  while(input>>stamp>>query>>x>>y>>yaw) {
    std::ifstream file(std::string(argv[1])+"/"+std::to_string(stamp)+".cdr",std::ios::binary);
    if(!file)return 5;
    std::vector<uint8_t> bytes((std::istreambuf_iterator<char>(file)),{});
    rclcpp::SerializedMessage serialized(bytes.size());auto& b=serialized.get_rcl_serialized_message();
    std::memcpy(b.buffer,bytes.data(),bytes.size());b.buffer_length=bytes.size();
    auto msg=std::make_shared<grid_map_msgs::msg::GridMap>();serializer.deserialize_message(&serialized,msg.get());
    if(rcl_set_ros_time_override(clock,query)!=RCL_RET_OK)return 6;
    ht.receive(msg);ht.beginCycle();
    if(!ht.latest_)return 7;
    const auto actual=ht.poseSupport(x,y,yaw);
    const auto prior=ht.prior_;ht.prior_.retired=true;
    const auto terrain=ht.poseSupport(x,y,yaw);
    const auto reason=ht.poseRejection(x,y,yaw);ht.prior_=prior;
    out<<"{\"source_ns\":"<<stamp<<",\"query_ns\":"<<query
       <<",\"mission_s\":"<<double(query-mission)/1e9<<",\"with_recorded_prior\":"<<int(actual)
       <<",\"without_prior\":"<<int(terrain)<<",\"pose_reason_without_prior\":\""<<reason<<"\"}\n";
  }
  rclcpp::shutdown();return 0;
}
