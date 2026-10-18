#include <gtest/gtest.h>
#include "viewpoint_manager/viewpoint_manager.h"
#include "grid_world/grid_world.h"

class PendingCell : public ::testing::Test {
 protected:
  std::shared_ptr<viewpoint_manager_ns::ViewPointManager> manager;
  std::unique_ptr<grid_world_ns::GridWorld> world;
  int cell;
  void SetUp() override {
    if(!rclcpp::ok())rclcpp::init(0,nullptr);
    rclcpp::NodeOptions options;
    options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
    options.parameter_overrides({rclcpp::Parameter("ht_enabled",true)});
    auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);
    for(const auto& entry:node->get_node_parameters_interface()->get_parameter_overrides())
      if(entry.first.rfind("ht_",0)!=0 && !node->has_parameter(entry.first))node->declare_parameter(entry.first,entry.second);
    manager=std::make_shared<viewpoint_manager_ns::ViewPointManager>(node);
    manager->UpdateRobotPosition(Eigen::Vector3d(0,0,.75));
    geometry_msgs::msg::Point origin;origin.z=.75;
    world=std::make_unique<grid_world_ns::GridWorld>(11,11,1,6.,3.,5);
    world->UpdateNeighborCells(origin);
    geometry_msgs::msg::Point robot;robot.x=9.267491;robot.y=-14.360244;robot.z=.75;
    world->UpdateNeighborCells(robot);world->UpdateRobotPosition(robot);
    geometry_msgs::msg::Point position;position.x=24;position.y=.15;position.z=.75;
    manager->SetViewPointPosition(0,position);manager->SetViewPointCandidate(0,true);
    manager->SetViewPointSelected(0,false);manager->SetViewPointVisited(0,false);
    manager->candidate_indices_={0};cell=world->GetCellInd(position.x,position.y,position.z);
    for(int i=0;i<235;++i)manager->AddUncoveredPoint(0,i);
    for(int i=0;i<63;++i)manager->AddUncoveredFrontierPoint(0,i);
    ASSERT_TRUE(manager->HT()->enabled());
  }
};
TEST_F(PendingCell, GainWithoutSelectedLocalGoalMustEnterGlobalTodo) {
  ASSERT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::UNSEEN);
  world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
}
TEST_F(PendingCell, PositiveGainMustSurviveLeavingLocalNeighbourhood) {
  world->SetCellStatus(cell,grid_world_ns::CellStatus::EXPLORING);
  world->UpdateCellStatus(manager);
  ASSERT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
  geometry_msgs::msg::Point robot;robot.x=8.950212;robot.y=-14.518620;robot.z=.75;
  manager->candidate_indices_.clear();world->UpdateNeighborCells(robot);world->UpdateRobotPosition(robot);
  world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
}

TEST_F(PendingCell, LastObservedGainSurvivesTemporaryNoCandidates) {
  world->UpdateCellStatus(manager);
  ASSERT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
  manager->candidate_indices_.clear();world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
}
TEST_F(PendingCell, LastObservedGainSurvivesNoCandidatesNearRobot) {
  world->UpdateCellStatus(manager);
  ASSERT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
  world->CellAddVisitCount(cell);
  geometry_msgs::msg::Point robot;robot.x=24;robot.y=0;robot.z=.75;
  world->UpdateNeighborCells(robot);world->UpdateRobotPosition(robot);
  manager->candidate_indices_.clear();world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
}
