#include <gtest/gtest.h>
#include "viewpoint_manager/viewpoint_manager.h"
#include <fstream>
#include <sstream>

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
  const double radius=.5+.5*std::hypot(.2,.2);
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
