#include <gtest/gtest.h>
#include "local_coverage_planner/local_coverage_planner.h"
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_core/iterators/GridMapIterator.hpp>
#include <thread>
#include <chrono>
#include <cmath>

class LocalCompletion : public ::testing::Test {
protected:
  rclcpp::Node::SharedPtr node;
  std::shared_ptr<viewpoint_manager_ns::ViewPointManager> manager;
  std::unique_ptr<local_coverage_planner_ns::LocalCoveragePlanner> planner;
  rclcpp::Publisher<grid_map_msgs::msg::GridMap>::SharedPtr pub;
  grid_map::GridMap map;
  int target=-1;
  void spin(int n=40) {
    for(int i=0;i<n;++i) {rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(5));}
  }
  void SetUp() override {
    if(!rclcpp::ok())rclcpp::init(0,nullptr);
    rclcpp::NodeOptions opts;
    opts.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
    opts.parameter_overrides({rclcpp::Parameter("ht_enabled",true),
      rclcpp::Parameter("ht_exploration_mode","tare_waypoint"),
      rclcpp::Parameter("ht_score_semantics","configuration"),
      rclcpp::Parameter("ht_directions_calibrated",true),
      rclcpp::Parameter("ht_map_timeout",60.),
      rclcpp::Parameter("ht_topic","/completion_fixture"),
      rclcpp::Parameter("tare_sampling_seed",42),
      rclcpp::Parameter("kMinAddPointNumSmall",40),
      rclcpp::Parameter("kMinAddFrontierPointNum",15),
      rclcpp::Parameter("kLocalPathOptimizationItrMax",1)});
    node=std::make_shared<rclcpp::Node>("tare_planner_node",opts);
    for(const auto& p:node->get_node_parameters_interface()->get_parameter_overrides())
      if(p.first.rfind("ht_",0)!=0 && !node->has_parameter(p.first))node->declare_parameter(p.first,p.second);
    manager=std::make_shared<viewpoint_manager_ns::ViewPointManager>(node);
    manager->UpdateRobotPosition(Eigen::Vector3d(0,0,.75));
    for(int i=0;i<manager->GetViewPointNum();++i) {
      manager->SetViewPointCollision(i,false);manager->SetViewPointInLineOfSight(i,true);
      manager->SetViewPointHeight(i,.75);manager->SetViewPointVisited(i,false);
    }
    map.setFrameId("map");map.setGeometry(grid_map::Length(40,40),.1);
    for(int k=0;k<8;++k)map.add("ht_dir_"+std::to_string(k),1.f);
    map.add("ht_valid",1.f);map.add("ht_observation_valid",1.f);
    map.add("ht_obstacle",0.f);map.add("ht_elevation",0.f);
    pub=node->create_publisher<grid_map_msgs::msg::GridMap>("/completion_fixture",1);
    spin();refresh();
    target=manager->GetNearestCandidateViewPointInd(Eigen::Vector3d(4,0,.75));
    ASSERT_TRUE(manager->InRange(target));
    planner=std::make_unique<local_coverage_planner_ns::LocalCoveragePlanner>(node);
    planner->SetViewPointManager(manager);planner->SetRobotPosition(Eigen::Vector3d(0,0,.75));
    planner->SetLookAheadPoint(Eigen::Vector3d(0,0,.75));
  }
  void refresh() {
    map.setTimestamp(node->now().nanoseconds());pub->publish(*grid_map::GridMapRosConverter::toMessage(map));spin();
    manager->HT()->beginCycle();ASSERT_TRUE(manager->HT()->ready());
    manager->CheckViewPointCollision(std::make_shared<pcl::PointCloud<pcl::PointXYZI>>());
    manager->CheckViewPointConnectivity();manager->GetViewPointCandidate();
    for(int id:manager->GetViewPointCandidateIndices())manager->SetViewPointInExploringCell(id,true);
  }
  void add(int surface,int frontier=0) {
    manager->ResetViewPointCoveredPointList(target);
    for(int i=0;i<surface;++i)manager->AddUncoveredPoint(target,i);
    for(int i=0;i<frontier;++i)manager->AddUncoveredFrontierPoint(target,i);
  }
  exploration_path_ns::ExplorationPath solve(int points,int frontier=0) {
    return planner->SolveLocalCoverageProblem(exploration_path_ns::ExplorationPath{},points,frontier);
  }
  void assertReachable() {
    ASSERT_TRUE(manager->IsViewPointCandidate(target));
    const int robot=manager->GetNearestCandidateViewPointInd(Eigen::Vector3d(0,0,.75));
    ASSERT_FALSE(manager->GetViewPointShortestPath(robot,target).poses.empty());
    const auto point=manager->GetViewPointPosition(target);
    ASSERT_GT(std::hypot(point.x,point.y),2.);
    ASSERT_TRUE(manager->HT()->permits(manager->HT()->motionSupport({0,0,0},{point.x,point.y,0})));
  }
};

TEST_F(LocalCompletion, ReachableSurfaceAtExactAcceptedThresholdMustNotComplete) {
  assertReachable();add(40);auto route=solve(40);
  EXPECT_FALSE(planner->IsLocalCoverageComplete());EXPECT_GT(route.nodes_.size(),1u);
}
TEST_F(LocalCompletion, ReachableFrontierAtExactAcceptedThresholdMustNotComplete) {
  assertReachable();add(0,15);auto route=solve(0,15);
  EXPECT_FALSE(planner->IsLocalCoverageComplete());EXPECT_GT(route.nodes_.size(),1u);
}
TEST_F(LocalCompletion, AboveThresholdKeepsPlanningAndDrainedTaskCanFinish) {
  assertReachable();add(41);solve(41);EXPECT_FALSE(planner->IsLocalCoverageComplete());
  add(0);solve(0);EXPECT_TRUE(planner->IsLocalCoverageComplete());
}
TEST_F(LocalCompletion, BelowThresholdOrAlreadyVisitedTasksDoNotPreventNormalCompletion) {
  assertReachable();add(39,14);solve(39,14);EXPECT_TRUE(planner->IsLocalCoverageComplete());
  add(41);manager->SetViewPointVisited(target,true);solve(41);EXPECT_TRUE(planner->IsLocalCoverageComplete());
}
TEST_F(LocalCompletion, UnknownTerrainDoesNotCreateExecutionPermission) {
  assertReachable();add(40);
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    grid_map::Position p;map.getPosition(*it,p);
    if(p.x()>1 && p.x()<3) {
      map.at("ht_valid",*it)=0;map.at("ht_observation_valid",*it)=0;
      for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),*it)=.1f;
    }
  }
  refresh();const auto point=manager->GetViewPointPosition(target);
  EXPECT_FALSE(manager->HT()->permits(manager->HT()->motionSupport({0,0,0},{point.x,point.y,0})));
  solve(40);
  EXPECT_FALSE(manager->HT()->permits(manager->HT()->motionSupport({0,0,0},{point.x,point.y,0})));
}
