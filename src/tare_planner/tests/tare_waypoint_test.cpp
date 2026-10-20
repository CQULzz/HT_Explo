#include <gtest/gtest.h>
#include "viewpoint_manager/viewpoint_manager.h"
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_core/iterators/GridMapIterator.hpp>
#include <chrono>
#include <thread>
#include "ht_cost/tare_waypoint_route.h"

class TareTerrainGraph : public ::testing::Test {
 protected:
  rclcpp::Node::SharedPtr node;
  std::unique_ptr<viewpoint_manager_ns::ViewPointManager> manager;
  rclcpp::Publisher<grid_map_msgs::msg::GridMap>::SharedPtr pub;
  grid_map::GridMap map;
  void spin(int count) {for(int i=0;i<count;++i){rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(10));}}
  void SetUp() override {
    if(!rclcpp::ok())rclcpp::init(0,nullptr);
    rclcpp::NodeOptions options;
    options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
    options.parameter_overrides({rclcpp::Parameter("ht_enabled",true),
      rclcpp::Parameter("ht_exploration_mode","tare_waypoint"),
      rclcpp::Parameter("ht_score_semantics","configuration"),
      rclcpp::Parameter("ht_directions_calibrated",true),
      rclcpp::Parameter("ht_map_timeout",60.),rclcpp::Parameter("ht_topic","/tare_graph_fixture")});
    node=std::make_shared<rclcpp::Node>("tare_planner_node",options);
    for(const auto& entry:node->get_node_parameters_interface()->get_parameter_overrides())
      if(entry.first.rfind("ht_",0)!=0 && !node->has_parameter(entry.first))node->declare_parameter(entry.first,entry.second);
    manager=std::make_unique<viewpoint_manager_ns::ViewPointManager>(node);
    manager->UpdateRobotPosition(Eigen::Vector3d(0,0,.75));
    for(int i=0;i<manager->GetViewPointNum();++i) {
      manager->SetViewPointCollision(i,false);manager->SetViewPointInLineOfSight(i,true);manager->SetViewPointHeight(i,.75);
    }
    map.setFrameId("map");map.setGeometry(grid_map::Length(40,40),.1);
    for(int k=0;k<8;++k)map.add("ht_dir_"+std::to_string(k),1.f);
    map.add("ht_valid",1.f);map.add("ht_observation_valid",1.f);map.add("ht_obstacle",0.f);map.add("ht_elevation",0.f);
    pub=node->create_publisher<grid_map_msgs::msg::GridMap>("/tare_graph_fixture",1);spin(20);
  }
  void send(bool band) {
    for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
      grid_map::Position p;map.getPosition(*it,p);
      const float score=band && p.x()>1 && p.x()<3 ? .1f:1.f;
      for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),*it)=score;
    }
    map.setTimestamp(node->now().nanoseconds());pub->publish(*grid_map::GridMapRosConverter::toMessage(map));spin(40);
    manager->HT()->beginCycle();ASSERT_TRUE(manager->HT()->ready());
  }
  int target() {return manager->GetViewPointInd(Eigen::Vector3d(5,0,.75));}
};
TEST_F(TareTerrainGraph, KnownBlockedBandCannotYieldConnectedCandidate) {
  send(true);ASSERT_FALSE(manager->HT()->terrainAdmissible(2,0));ASSERT_TRUE(manager->HT()->terrainAdmissible(5,0));
  manager->CheckViewPointConnectivity();manager->GetViewPointCandidate();ASSERT_TRUE(manager->InRange(target()));
  EXPECT_FALSE(manager->ViewPointConnected(target()));EXPECT_FALSE(manager->IsViewPointCandidate(target()));
}
TEST_F(TareTerrainGraph, AsyncMapCannotRemoveVerticesBetweenBfsAndCandidateGraph) {
  send(false);manager->CheckViewPointConnectivity();manager->GetViewPointCandidate();
  ASSERT_TRUE(manager->IsViewPointCandidate(target()));
  const auto start=manager->GetNearestCandidateViewPointInd(Eigen::Vector3d(0,0,.75));
  ASSERT_FALSE(manager->GetViewPointShortestPath(start,target()).poses.empty());
  // Arrives after BFS: the same coarse planning snapshot must complete its
  // graph. Fresh HT execution checks still reject motion through the band.
  send(true);manager->GetViewPointCandidate();
  EXPECT_TRUE(manager->IsViewPointCandidate(target()));
  EXPECT_FALSE(manager->GetViewPointShortestPath(start,target()).poses.empty());
  EXPECT_FALSE(manager->HT()->permits(manager->HT()->motionSupport({0,0,0},{5,0,0})));
  manager->CheckViewPointConnectivity();manager->GetViewPointCandidate();
  EXPECT_FALSE(manager->ViewPointConnected(target()));EXPECT_FALSE(manager->IsViewPointCandidate(target()));
  send(false);manager->CheckViewPointConnectivity();manager->GetViewPointCandidate();
  EXPECT_TRUE(manager->IsViewPointCandidate(target()));
  EXPECT_FALSE(manager->GetViewPointShortestPath(start,target()).poses.empty());
}

TEST_F(TareTerrainGraph, ShortNativePrefixStillRequiresAndPassesFullHtPath) {
  // A short known patch ahead of the robot, followed by a rejected band.
  // The old four targets never launch search even though moving onto the
  // unchanged native branch is feasible under the very same hard HT gate.
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    grid_map::Position p;map.getPosition(*it,p);
    const float score=std::max(p.x(),p.y())>.7 ? .1f:1.f;
    for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),*it)=score;
  }
  map.setTimestamp(node->now().nanoseconds());pub->publish(*grid_map::GridMapRosConverter::toMessage(map));spin(40);
  auto ht=manager->HT();ht->beginCycle();ASSERT_TRUE(ht->ready());
  manager->CheckViewPointCollision(std::make_shared<pcl::PointCloud<pcl::PointXYZI>>());
  manager->CheckViewPointConnectivity();manager->GetViewPointCandidate();
  const std::vector<ht_cost_ns::Point> branch{{.404115,.410836,0},{1.604115,1.610836,0},{5.645016,5.668668,0}};
  auto supported=[&](ht_cost_ns::Point p) {
    for(int k=0;k<8;++k)if(ht->permits(ht->poseSupport(p.x,p.y,k*ht_cost_ns::kPi/4)))return true;
    return false;
  };
  for(double arc:{4.,3.,2.,1.}) EXPECT_FALSE(supported(ht_cost_ns::tarePrefix(branch,arc)));
  ht_cost_ns::XYThetaConfig config;config.try_direct_connection=true;
  config.headings=32;config.goal_radius=.35;config.max_search_seconds=.15;
  auto valid=[&](ht_cost_ns::Pose2 a,ht_cost_ns::Pose2 b,double) {
    return ht->permits(ht->motionSupport(a,b)) &&
      !manager->InCollisionAtPose(Eigen::Vector3d(b.x,b.y,.75),0.);
  };
  const ht_cost_ns::Pose2 robot{0,0,.6414};bool reached=false;
  for(const auto& target:ht_cost_ns::tareAdaptivePrefixes(branch,{0,0,0},ht->resolution())) {
    if(!supported(target.point))continue;
    const auto plan=ht_cost_ns::planXYTheta(robot,target.point,config,valid);
    if(plan.reached && plan.poses.size()>1) {
      reached=true;EXPECT_LT(target.arc,1.);
      for(size_t i=1;i<plan.poses.size();++i) EXPECT_TRUE(valid(plan.poses[i-1],plan.poses[i],0));
      break;
    }
  }
  EXPECT_TRUE(reached);
  // Endpoint green beyond a separating band is still not a valid path.
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    grid_map::Position p;map.getPosition(*it,p);
    const float score=p.x()>1 && p.x()<2 ? .1f:1.f;
    for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),*it)=score;
  }
  map.setTimestamp(node->now().nanoseconds());pub->publish(*grid_map::GridMapRosConverter::toMessage(map));spin(40);ht->beginCycle();
  ASSERT_TRUE(supported({3,0,0}));
  EXPECT_FALSE(ht_cost_ns::planXYTheta({0,0,0},{3,0,0},config,
    [&](ht_cost_ns::Pose2 a,ht_cost_ns::Pose2 b,double){return ht->permits(ht->motionSupport(a,b));}).reached);
}
