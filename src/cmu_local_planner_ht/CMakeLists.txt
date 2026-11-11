cmake_minimum_required(VERSION 3.5)
project(cmu_local_planner_ht)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 14)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(grid_map_msgs REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS imgproc)
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(message_filters REQUIRED)
find_package(pcl_conversions REQUIRED)
find_package(pcl_ros REQUIRED)

include_directories(${OpenCV_INCLUDE_DIRS})
add_executable(localPlanner src/localPlanner.cpp)
add_executable(pathFollower src/pathFollower.cpp)
ament_target_dependencies(localPlanner rclcpp std_msgs sensor_msgs nav_msgs geometry_msgs tf2 tf2_ros tf2_geometry_msgs message_filters pcl_ros pcl_conversions grid_map_msgs)
ament_target_dependencies(pathFollower rclcpp std_msgs sensor_msgs nav_msgs geometry_msgs tf2 tf2_ros tf2_geometry_msgs message_filters pcl_ros pcl_conversions grid_map_msgs)

install(TARGETS
  localPlanner
  pathFollower
  DESTINATION lib/${PROJECT_NAME})

target_link_libraries(localPlanner ${OpenCV_LIBS})
target_link_libraries(pathFollower ${OpenCV_LIBS})
ament_package()
add_executable(ht_gate_test src/ht_gate_test.cpp)
ament_target_dependencies(ht_gate_test rclcpp std_msgs grid_map_msgs geometry_msgs sensor_msgs)
target_link_libraries(ht_gate_test ${OpenCV_LIBS})
add_executable(ht_recovery_test src/ht_recovery_test.cpp)
ament_target_dependencies(ht_recovery_test rclcpp std_msgs grid_map_msgs geometry_msgs sensor_msgs nav_msgs)
target_link_libraries(ht_recovery_test ${OpenCV_LIBS})
