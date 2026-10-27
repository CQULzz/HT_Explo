#include <gtest/gtest.h>
#include "viewpoint_manager/viewpoint_manager.h"
#include <fstream>
#include <sstream>
#include "../../../docs/fixes/evidence/2026-10-20_successor_pruning/baseline_search.h"

TEST(SearchPruning, SameAcceptedRoutesWithFewerHardQueries) {
  using namespace ht_cost_ns;
  XYThetaConfig config;config.headings=32;config.turn_angles={kPi/16,kPi/8};
  config.max_search_seconds=10;config.max_expansions=256;config.goal_radius=.35;
  size_t old_queries=0,new_queries=0,pruned=0,reached_cases=0;
  for (double yaw:{0.,.7,1.6}) for (Point goal:std::vector<Point>{{2,0,0},{1,1,0},{-2,0,0}})
    for (bool direct:{false,true}) {
      config.try_direct_connection=direct;
      // A wall with an opening and an orientation-dependent patch require
      // intermediate edge validation, rather than endpoint-only acceptance.
      auto admissible=[](Pose2,Pose2 b,double) {
        if (b.x>.7 && b.x<1.2 && b.y<.5) return false;
        if (b.x<-.5 && std::cos(b.yaw)<-.3) return false;
        return true;
      };
      auto original=planXYThetaBaseline(Pose2{0,0,yaw},goal,config,
        [&](Pose2 a,Pose2 b,double v){++old_queries;return admissible(a,b,v);});
      auto optimized=planXYTheta(Pose2{0,0,yaw},goal,config,
        [&](Pose2 a,Pose2 b,double v){++new_queries;return admissible(a,b,v);});
      ASSERT_EQ(original.termination,optimized.termination);
      ASSERT_EQ(original.expanded,optimized.expanded);
      ASSERT_EQ(original.poses.size(),optimized.poses.size());
      if (original.reached) {
        ++reached_cases;
        ASSERT_DOUBLE_EQ(original.seconds,optimized.seconds);
        for (size_t i=0;i<original.poses.size();++i) {
          EXPECT_DOUBLE_EQ(original.poses[i].x,optimized.poses[i].x);
          EXPECT_DOUBLE_EQ(original.poses[i].y,optimized.poses[i].y);
          EXPECT_DOUBLE_EQ(original.poses[i].yaw,optimized.poses[i].yaw);
        }
      }
      pruned+=optimized.dominated_edges_pruned;
    }
  EXPECT_GT(pruned,0u);
  EXPECT_GT(reached_cases,0u);
  EXPECT_LT(new_queries,old_queries);
}

TEST(GeometryPose, CapturedContinuousRootDoesNotInheritNeighbourCollision) {
  if (!rclcpp::ok()) rclcpp::init(0,nullptr);
  rclcpp::NodeOptions options;
  options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
  options.automatically_declare_parameters_from_overrides(true);
  auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);
  viewpoint_manager_ns::ViewPointManager manager(node);
  manager.UpdateRobotPosition(Eigen::Vector3d(0,0,0.7439746856689453));
  const Eigen::Vector3d robot(11.358543395996094,1.208035945892334,0.7468403577804565);
  manager.UpdateRobotPosition(robot);
  auto cloud=std::make_shared<pcl::PointCloud<pcl::PointXYZI>>();
  std::ifstream stream(HT_SOURCE_ROOT "/../../docs/results/ht_latency_diagnosis_10min_2026-10-18/geometry_capture/collision_points.csv");
  ASSERT_TRUE(stream.good());std::string line;std::getline(stream,line);
  while(std::getline(stream,line)) {
    std::replace(line.begin(),line.end(),',',' ');std::istringstream row(line);
    pcl::PointXYZI point;ASSERT_TRUE(bool(row>>point.x>>point.y>>point.z>>point.intensity));cloud->push_back(point);
  }
  ASSERT_GT(cloud->size(),25000u);
  manager.CheckViewPointCollision(cloud);
  // Regression expectation: an actual pose must not inherit a neighbouring
  // quantized viewpoint's collision mark when its physical envelope is clear.
  EXPECT_TRUE(manager.InCollision(robot));  // Actual old implementation reproduces the failure.
  EXPECT_FALSE(manager.InCollisionAtPose(robot));
  // Nominal driving must leave a tracking tube; actual-root checks retain
  // the original physical boundary and never bypass an overlap.
  EXPECT_TRUE(manager.InCollisionAtPose(robot,.12));
  EXPECT_TRUE(manager.InCollisionAtPose(robot,-.01));
  // The same observed obstacle must still reject an actually colliding root.
  EXPECT_TRUE(manager.InCollisionAtPose(Eigen::Vector3d(11.15774,1.8920302,robot.z())));
  EXPECT_TRUE(manager.InCollisionAtPose(Eigen::Vector3d(std::numeric_limits<double>::quiet_NaN(),1,robot.z())));
  EXPECT_TRUE(manager.InCollisionAtPose(Eigen::Vector3d(100,100,robot.z())));
  // A real keep-out boundary remains authoritative at the continuous position.
  geometry_msgs::msg::Polygon polygon;
  for(const auto& delta:std::vector<Eigen::Vector2d>{{-1,-1},{1,-1},{1,1},{-1,1}}) {
    geometry_msgs::msg::Point32 p;p.x=robot.x()+delta.x();p.y=robot.y()+delta.y();polygon.points.push_back(p);
  }
  manager.UpdateNogoBoundary({polygon});
  EXPECT_TRUE(manager.InCollisionAtPose(robot));
}

TEST(GeometryPose, HeightSliceMatchesBruteForceAtBoundariesAndOtherHeights) {
  if (!rclcpp::ok())rclcpp::init(0,nullptr);
  rclcpp::NodeOptions options;
  options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
  options.automatically_declare_parameters_from_overrides(true);
  auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);
  node->set_parameter(rclcpp::Parameter("kViewPointCollisionMarginZPlus",.2));
  node->set_parameter(rclcpp::Parameter("kViewPointCollisionMarginZMinus",.7));
  viewpoint_manager_ns::ViewPointManager manager(node);
  manager.UpdateRobotPosition(Eigen::Vector3d(0,0,.75));
  auto cloud=std::make_shared<pcl::PointCloud<pcl::PointXYZI>>();
  for(const auto& p:std::vector<Eigen::Vector3d>{{5,5,.95},{2,2,.05},{-2,3,1.1},{5.000001,5.000001,.95}}) {
    pcl::PointXYZI v;v.x=p.x();v.y=p.y();v.z=p.z();cloud->push_back(v);
  }
  manager.CheckViewPointCollision(cloud);
  for(int i=0;i<manager.GetViewPointNum();++i) {
    manager.SetViewPointInLineOfSight(i,true);manager.SetViewPointConnected(i,true);
  }
  manager.GetViewPointCandidate();
  // Compute the oracle radius from runtime parameters too. Constant-folded
  // hypot(.2,.2) differs from libm by one ULP on ARM64 at the equality boundary.
  const double radius=node->get_parameter("kViewPointCollisionMargin").as_double()+
      .5*std::hypot(node->get_parameter("kCollisionGridResolutionX").as_double(),
                    node->get_parameter("kCollisionGridResolutionY").as_double());
  int checked=0;
  for(double z:{.75,.74999997,.75000003,.9,.4})
    for(int k=0;k<32;++k)for(double offset:{-1e-5,-1e-7,0.,1e-7,1e-5}) {
      const double theta=k*ht_cost_ns::kPi/16;
      const Eigen::Vector3d query(5+(radius+offset)*std::cos(theta),5+(radius+offset)*std::sin(theta),z);
      bool expected=false;
      for(const auto& obstacle:cloud->points) {
        const double dz=obstacle.z-query.z();
        expected|=dz<=.2 && dz>=-.7 && std::hypot(obstacle.x-query.x(),obstacle.y-query.y())<=radius+1e-7;
      }
      EXPECT_EQ(manager.InCollisionAtPose(query),expected)<<"q="<<query.transpose();++checked;
    }
  EXPECT_EQ(checked,800);
}

TEST(GeometryPose, UnlabelledCoverageCellDoesNotInvalidateFreeContinuousRoot) {
  if (!rclcpp::ok()) rclcpp::init(0,nullptr);
  rclcpp::NodeOptions options;
  options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
  options.automatically_declare_parameters_from_overrides(true);
  auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);
  viewpoint_manager_ns::ViewPointManager manager(node);
  const Eigen::Vector3d root(0.04,0.06,.75);
  manager.UpdateRobotPosition(root);
  const int index=manager.GetViewPointInd(root);ASSERT_GE(index,0);
  manager.SetViewPointHeight(index,root.z());
  auto cloud=std::make_shared<pcl::PointCloud<pcl::PointXYZI>>();
  manager.CheckViewPointCollision(cloud);
  manager.SetViewPointCandidate(index,false);manager.SetViewPointCollision(index,false);
  EXPECT_FALSE(manager.InLocalPlanningHorizon(root)); // Native TARE meaning stays intact.
  EXPECT_FALSE(manager.InCollisionAtPose(root));
  EXPECT_TRUE(manager.InCollisionAtPose(Eigen::Vector3d(100,100,root.z())));
  EXPECT_TRUE(manager.InCollisionAtPose(Eigen::Vector3d(root.x(),root.y(),root.z()+2)));
  EXPECT_TRUE(manager.InCollisionAtPose(Eigen::Vector3d(NAN,root.y(),root.z())));
  // A real obstacle is still rejected at that exact same continuous root.
  for(int k=0;k<4;++k) {
    pcl::PointXYZI point;point.x=root.x();point.y=root.y();point.z=root.z();cloud->push_back(point);
  }
  manager.CheckViewPointCollision(cloud);
  EXPECT_TRUE(manager.InCollisionAtPose(root));
}

TEST(SearchAudit, SeparatesDeadlineExpansionLimitAndExhaustedComponent) {
  using namespace ht_cost_ns;
  XYThetaConfig config;config.max_search_seconds=10;
  auto open=[](Pose2,Pose2,double){return true;};
  auto blocked=[](Pose2,Pose2,double){return false;};
  EXPECT_EQ(planXYTheta(Pose2{},Point{1,0,0},config,blocked).termination,XYThetaTermination::INVALID_START);
  EXPECT_EQ(planXYTheta(Pose2{},Point{},config,open).termination,XYThetaTermination::REACHED);
  auto sealed=[](Pose2,Pose2 p,double){return std::hypot(p.x,p.y)<1e-9 && std::abs(p.yaw)<1e-9;};
  EXPECT_EQ(planXYTheta(Pose2{},Point{1,0,0},config,sealed).termination,XYThetaTermination::EXHAUSTED);
  config.max_expansions=1;
  EXPECT_EQ(planXYTheta(Pose2{},Point{3,0,0},config,open).termination,XYThetaTermination::EXPANSION_LIMIT);
  config.max_expansions=8000;config.max_search_seconds=1e-12;
  EXPECT_EQ(planXYTheta(Pose2{},Point{3,0,0},config,open).termination,XYThetaTermination::TIME_LIMIT);
}

// Real GridWorld/ViewPointManager regression, based on stage29 (24,0) task loss.
#include <gtest/gtest.h>
#include "viewpoint_manager/viewpoint_manager.h"
#include "grid_world/grid_world.h"

class PendingCell : public ::testing::Test {
 protected:
  std::shared_ptr<viewpoint_manager_ns::ViewPointManager> manager;
  std::unique_ptr<grid_world_ns::GridWorld> world;
  int cell;
  virtual bool htMode() const {return true;}
  void SetUp() override {
    if(!rclcpp::ok())rclcpp::init(0,nullptr);
    rclcpp::NodeOptions options;
    options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
    options.parameter_overrides({rclcpp::Parameter("ht_enabled",htMode()),rclcpp::Parameter("ht_exploration_mode","legacy_xytheta_greedy")});
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
    ASSERT_EQ(manager->HT()->enabled(),htMode());
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

TEST_F(PendingCell, FrontierOnlyObservationRegistersGlobalTodo) {
  manager->ResetViewPointCoveredPointList(0);
  for(int i=0;i<31;++i)manager->AddUncoveredFrontierPoint(0,i);
  world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
}
TEST_F(PendingCell, ZeroGainDoesNotCreateGlobalTodo) {
  manager->ResetViewPointCoveredPointList(0);world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::UNSEEN);
}
TEST_F(PendingCell, VisitedViewpointDoesNotCreateGlobalTodo) {
  manager->SetViewPointVisited(0,true);world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::UNSEEN);
}
TEST_F(PendingCell, NoCandidateDoesNotInventObservedGain) {
  manager->candidate_indices_.clear();world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::UNSEEN);
}
TEST_F(PendingCell, ExistingZeroGainTaskCanStillBecomeCovered) {
  world->SetCellStatus(cell,grid_world_ns::CellStatus::EXPLORING);
  manager->ResetViewPointCoveredPointList(0);world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::COVERED);
}
TEST_F(PendingCell, OtherSelectedGoalDoesNotHidePendingCell) {
  geometry_msgs::msg::Point pos;pos.x=18;pos.y=.15;pos.z=.75;
  manager->SetViewPointPosition(1,pos);manager->SetViewPointCandidate(1,true);
  manager->SetViewPointSelected(1,true);manager->SetViewPointVisited(1,false);
  manager->candidate_indices_.push_back(1);
  for(int i=0;i<150;++i)manager->AddUncoveredPoint(1,i);
  world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
  EXPECT_EQ(world->GetCellStatus(world->GetCellInd(pos.x,pos.y,pos.z)),grid_world_ns::CellStatus::EXPLORING);
}
TEST_F(PendingCell, CoveredCellReopeningKeepsExistingHysteresis) {
  world->SetCellStatus(cell,grid_world_ns::CellStatus::COVERED);world->UpdateCellStatus(manager);
  // One positive-gain candidate is below the existing10-candidate reopening threshold.
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::COVERED);
}
class LegacyPendingCell : public PendingCell {
 protected:bool htMode() const override {return false;}
};
TEST_F(LegacyPendingCell, DisabledHtPreservesLegacySelectedActivation) {
  world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::UNSEEN);
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

TEST_F(PendingCell, FreshZeroGainCanDischargeRememberedPendingTask) {
  world->UpdateCellStatus(manager);ASSERT_EQ(world->PendingHTCoverageCells(),1u);
  manager->candidate_indices_.clear();world->UpdateCellStatus(manager);
  EXPECT_EQ(world->PendingHTCoverageCells(),1u);
  manager->candidate_indices_={0};manager->ResetViewPointCoveredPointList(0);
  world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::COVERED);
  EXPECT_EQ(world->PendingHTCoverageCells(),0u);
}
TEST_F(PendingCell, NavigationOnlyTaskDoesNotInventRememberedGain) {
  manager->ResetViewPointCoveredPointList(0);manager->SetViewPointSelected(0,true);
  world->UpdateCellStatus(manager);
  ASSERT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::EXPLORING);
  EXPECT_EQ(world->PendingHTCoverageCells(),0u);
  manager->SetViewPointSelected(0,false);manager->candidate_indices_.clear();world->UpdateCellStatus(manager);
  EXPECT_EQ(world->GetCellStatus(cell),grid_world_ns::CellStatus::COVERED);
}
TEST_F(PendingCell, ExternalCoveredOrResetClearsPendingRegistry) {
  world->UpdateCellStatus(manager);ASSERT_EQ(world->PendingHTCoverageCells(),1u);
  world->SetCellStatus(cell,grid_world_ns::CellStatus::COVERED_BY_OTHERS);
  EXPECT_EQ(world->PendingHTCoverageCells(),0u);
  world->SetCellStatus(cell,grid_world_ns::CellStatus::UNSEEN);
  world->UpdateCellStatus(manager);ASSERT_EQ(world->PendingHTCoverageCells(),1u);
  world->Reset();EXPECT_EQ(world->PendingHTCoverageCells(),0u);
}
