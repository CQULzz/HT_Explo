#include <rclcpp/rclcpp.hpp>
#include "sensor_coverage_planner/sensor_coverage_planner_ground.h"

int main(int argc, char** argv)
{
  rclcpp::init(argc, argv);
  auto node = std::make_shared<sensor_coverage_planner_3d_ns::SensorCoveragePlanner3D>();
  node->initialize();
  // The HT subscription has its own callback group, so long planning cycles
  // cannot prevent fresh map reception. Other planner callbacks remain in the
  // default mutually-exclusive group.
  rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(), 2);
  executor.add_node(node);
  executor.spin();
  rclcpp::shutdown();
  return 0;
}
