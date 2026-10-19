#include <gtest/gtest.h>
#include "viewpoint_manager/viewpoint_manager.h"
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_core/iterators/GridMapIterator.hpp>
#include <chrono>
#include <thread>

TEST(TareTerrainConnectivity, KnownBlockedBandCannotYieldConnectedCandidate) {
  if(!rclcpp::ok())rclcpp::init(0,nullptr);
  rclcpp::NodeOptions options;
  options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
  options.parameter_overrides({rclcpp::Parameter("ht_enabled",true),
    rclcpp::Parameter("ht_exploration_mode","tare_waypoint"),
    rclcpp::Parameter("ht_score_semantics","configuration"),
    rclcpp::Parameter("ht_directions_calibrated",true),
    rclcpp::Parameter("ht_map_timeout",60.),rclcpp::Parameter("ht_topic","/tare_connectivity_probe")});
  auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);
  for(const auto& entry:node->get_node_parameters_interface()->get_parameter_overrides())
    if(entry.first.rfind("ht_",0)!=0 && !node->has_parameter(entry.first))node->declare_parameter(entry.first,entry.second);
  viewpoint_manager_ns::ViewPointManager manager(node);manager.UpdateRobotPosition(Eigen::Vector3d(0,0,.75));
  for(int i=0;i<manager.GetViewPointNum();++i) {
    manager.SetViewPointCollision(i,false);manager.SetViewPointInLineOfSight(i,true);manager.SetViewPointHeight(i,.75);
  }
  grid_map::GridMap map;map.setFrameId("map");map.setGeometry(grid_map::Length(40,40),.1);
  for(int k=0;k<8;++k)map.add("ht_dir_"+std::to_string(k),1.f);
  map.add("ht_valid",1.f);map.add("ht_observation_valid",1.f);map.add("ht_obstacle",0.f);map.add("ht_elevation",0.f);
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    grid_map::Position p;map.getPosition(*it,p);
    if(p.x()>1 && p.x()<3)for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),*it)=.1f;
  }
  auto pub=node->create_publisher<grid_map_msgs::msg::GridMap>("/tare_connectivity_probe",1);
  for(int i=0;i<30;++i){rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(10));}
  map.setTimestamp(node->now().nanoseconds());pub->publish(*grid_map::GridMapRosConverter::toMessage(map));
  for(int i=0;i<50;++i){rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(10));}
  manager.HT()->beginCycle();ASSERT_TRUE(manager.HT()->ready());ASSERT_FALSE(manager.HT()->terrainAdmissible(2,0));
  ASSERT_TRUE(manager.HT()->terrainAdmissible(5,0));
  manager.CheckViewPointConnectivity();manager.GetViewPointCandidate();
  const int target=manager.GetViewPointInd(Eigen::Vector3d(5,0,.75));ASSERT_TRUE(manager.InRange(target));
  const int start=manager.GetNearestCandidateViewPointInd(Eigen::Vector3d(0,0,.75));ASSERT_GE(start,0);
  std::cout<<"BAND_PROBE target_connected="<<manager.ViewPointConnected(target)<<" target_candidate="<<manager.IsViewPointCandidate(target)<<"\n";
  if(manager.IsViewPointCandidate(target)) {
    const auto path=manager.GetViewPointShortestPath(start,target);
    std::cout<<"BAND_PROBE falsely_connected_shortest_path_poses="<<path.poses.size()<<"\n";
  }
  // An all-heading forbidden band cuts this finite native view graph in two.
  // An optimistic unseen horizon must not bridge an already known barrier.
  EXPECT_FALSE(manager.ViewPointConnected(target));EXPECT_FALSE(manager.IsViewPointCandidate(target));
}
