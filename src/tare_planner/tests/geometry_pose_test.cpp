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
