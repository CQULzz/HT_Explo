cmake_minimum_required(VERSION 3.5)
project(tare_planner)

# Default to C99
if(NOT CMAKE_C_STANDARD)
  set(CMAKE_C_STANDARD 99)
endif()

# Default to C++14
if(NOT CMAKE_CXX_STANDARD)
  set(CMAKE_CXX_STANDARD 17)
endif()

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
# Resolve ROS/PCL's system Eigen before exposing the OR-Tools prefix. The
# bundled Eigen config exports an incompatible legacy EIGEN3_DEFINITIONS value.
find_package(Eigen3 REQUIRED)
# Load the complete, matching dependency graph (including Protobuf/Abseil).
# Linking only libortools.so omits symbols used by the HT solver time limit.
set(TARE_ORTOOLS_DEFAULT "${CMAKE_CURRENT_SOURCE_DIR}/or-tools")
if(CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
  get_filename_component(TARE_ORTOOLS_DEFAULT
    "${CMAKE_CURRENT_SOURCE_DIR}/../../.local_deps/ortools-arm64" ABSOLUTE)
endif()
set(TARE_ORTOOLS_ROOT "${TARE_ORTOOLS_DEFAULT}" CACHE PATH "Native OR-Tools 9.8 C++ installation")
if(NOT EXISTS "${TARE_ORTOOLS_ROOT}/lib/cmake/ortools/ortoolsConfig.cmake")
  message(FATAL_ERROR "Set TARE_ORTOOLS_ROOT to an OR-Tools 9.8 installation matching the target architecture")
endif()
list(PREPEND CMAKE_PREFIX_PATH "${TARE_ORTOOLS_ROOT}")
find_package(ortools 9.8 CONFIG REQUIRED PATHS "${TARE_ORTOOLS_ROOT}" NO_DEFAULT_PATH)
# Exported copies on exFAT/ZIP can retain the versioned ELF file while losing
# its SONAME symlink. Stage a private regular copy for build-tree execution;
# do not repair or mutate the caller's third-party installation in place.
get_target_property(TARE_ORTOOLS_LIBRARY ortools::ortools IMPORTED_LOCATION_RELEASE)
get_target_property(TARE_ORTOOLS_SONAME ortools::ortools IMPORTED_SONAME_RELEASE)
if(NOT EXISTS "${TARE_ORTOOLS_LIBRARY}" OR NOT TARE_ORTOOLS_SONAME)
  message(FATAL_ERROR "OR-Tools must provide its native runtime file and SONAME")
endif()
set(TARE_ORTOOLS_RUNTIME_DIR "${CMAKE_CURRENT_BINARY_DIR}/ortools_runtime")
file(MAKE_DIRECTORY "${TARE_ORTOOLS_RUNTIME_DIR}")
configure_file("${TARE_ORTOOLS_LIBRARY}"
  "${TARE_ORTOOLS_RUNTIME_DIR}/${TARE_ORTOOLS_SONAME}" COPYONLY)
list(APPEND CMAKE_BUILD_RPATH "${TARE_ORTOOLS_RUNTIME_DIR}")
find_package(rclcpp REQUIRED)
find_package(std_msgs REQUIRED)
find_package(nav_msgs REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)
rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/StartupPrior.msg"
  DEPENDENCIES std_msgs geometry_msgs builtin_interfaces)
rosidl_get_typesupport_target(tare_typesupport ${PROJECT_NAME} "rosidl_typesupport_cpp")
ament_export_dependencies(rosidl_default_runtime)
find_package(sensor_msgs REQUIRED)
find_package(visualization_msgs REQUIRED)
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)
find_package(tf2 REQUIRED)
find_package(PCL REQUIRED)
find_package(pcl_conversions REQUIRED)
find_package(pcl_ros REQUIRED)
find_package(grid_map_core REQUIRED)
find_package(grid_map_ros REQUIRED)
find_package(grid_map_msgs REQUIRED)
find_package(OpenCV REQUIRED COMPONENTS imgproc)

# grid_map_core defines Eigen plugins at directory scope. Every Eigen user
# therefore needs its include path, including targets that do not link ht_cost.
if(TARGET grid_map_core::grid_map_core)
  get_target_property(GRID_MAP_EIGEN_INCLUDE_DIRS grid_map_core::grid_map_core INTERFACE_INCLUDE_DIRECTORIES)
else()
  set(GRID_MAP_EIGEN_INCLUDE_DIRS ${grid_map_core_INCLUDE_DIRS})
endif()
include_directories(SYSTEM ${GRID_MAP_EIGEN_INCLUDE_DIRS})

 include_directories(
  ${catkin_INCLUDE_DIRS}
  ${PCL_INCLUDE_DIRS}
  ${grid_map_core_INCLUDE_DIRS}
  include
  ${EIGEN3_INCLUDE_DIR}
  # /usr/local/include
  # /usr/include
)
include_directories(SYSTEM "${TARE_ORTOOLS_ROOT}/include")

# Interface generators can import BUILD_SHARED_LIBS=ON via middleware. TARE's
# existing mutually dependent internal libraries must retain static linkage.
set(BUILD_SHARED_LIBS OFF)
add_library(ht_cost src/ht_cost/ht_cost_map.cpp)
ament_target_dependencies(ht_cost rclcpp std_msgs grid_map_core grid_map_ros grid_map_msgs tf2 tf2_ros tf2_geometry_msgs)
target_link_libraries(ht_cost ${OpenCV_LIBS} "${tare_typesupport}")

get_property(dirs DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} PROPERTY INCLUDE_DIRECTORIES)
foreach(dir ${dirs})
  message(STATUS "dir='${dir}'")
endforeach()

# ## Specify additional locations for library files
# link_directories(
#   /usr/local/lib # Location when using 'make system_install'
#   /usr/lib       # More usual location (e.g. when installing using a package)
#   or-tools/lib
# )

add_library(lidar_model src/lidar_model/lidar_model.cpp)
ament_target_dependencies(lidar_model rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 visualization_msgs pcl_ros pcl_conversions)
# target_link_libraries(lidar_model ${catkin_LIBRARIES} ${PCL_LIBRARIES})

add_library(graph src/graph/graph.cpp)
ament_target_dependencies(graph rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
# target_link_libraries(graph ${catkin_LIBRARIES})

add_library(misc_utils src/utils/misc_utils.cpp)
ament_target_dependencies(misc_utils rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
# target_link_libraries(misc_utils ${catkin_LIBRARIES} ${PCL_LIBRARIES})

add_library(pointcloud_utils src/utils/pointcloud_utils.cpp)
ament_target_dependencies(pointcloud_utils rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
# target_link_libraries(pointcloud_utils ${catkin_LIBRARIES} ${PCL_LIBRARIES})

add_library(tsp_solver src/tsp_solver/tsp_solver.cpp)
ament_target_dependencies(tsp_solver rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(tsp_solver ortools::ortools)

add_library(viewpoint src/viewpoint/viewpoint.cpp)
ament_target_dependencies(viewpoint rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(viewpoint ${catkin_LIBRARIES} lidar_model)

add_library(rolling_grid src/rolling_grid/rolling_grid.cpp)
ament_target_dependencies(rolling_grid rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
target_link_libraries(rolling_grid ${catkin_LIBRARIES} misc_utils pointcloud_utils)

add_library(viewpoint_manager src/viewpoint_manager/viewpoint_manager.cpp)
ament_target_dependencies(viewpoint_manager rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(viewpoint_manager ${catkin_LIBRARIES} rolling_grid viewpoint grid_world ht_cost)

add_library(local_coverage_planner src/local_coverage_planner/tare_original.cpp src/local_coverage_planner/local_coverage_planner.cpp src/local_coverage_planner/ht_route.cpp)
ament_target_dependencies(local_coverage_planner rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(local_coverage_planner ${catkin_LIBRARIES} viewpoint_manager tsp_solver)

add_library(grid_world src/grid_world/tare_original.cpp src/grid_world/grid_world.cpp)
ament_target_dependencies(grid_world rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(grid_world ${catkin_LIBRARIES} viewpoint_manager tsp_solver keypose_graph exploration_path)

add_library(pointcloud_manager src/pointcloud_manager/pointcloud_manager.cpp)
ament_target_dependencies(pointcloud_manager rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
target_link_libraries(pointcloud_manager ${catkin_LIBRARIES})

add_library(keypose_graph src/keypose_graph/keypose_graph.cpp)
ament_target_dependencies(keypose_graph rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(keypose_graph ${catkin_LIBRARIES} ${PCL_LIBRARIES} viewpoint_manager)

add_library(rolling_occupancy_grid src/rolling_occupancy_grid/rolling_occupancy_grid.cpp)
ament_target_dependencies(rolling_occupancy_grid rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
target_link_libraries(rolling_occupancy_grid ${catkin_LIBRARIES})

add_library(planning_env src/planning_env/planning_env.cpp)
ament_target_dependencies(planning_env rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(planning_env ${catkin_LIBRARIES} ${PCL_LIBRARIES} rolling_occupancy_grid ht_cost)

add_library(exploration_path src/exploration_path/exploration_path.cpp)
ament_target_dependencies(exploration_path rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
target_link_libraries(exploration_path ${catkin_LIBRARIES} ${PCL_LIBRARIES})

add_library(tare_visualizer src/tare_visualizer/tare_visualizer.cpp)
ament_target_dependencies(tare_visualizer rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions visualization_msgs)
target_link_libraries(tare_visualizer ${catkin_LIBRARIES} ${PCL_LIBRARIES})

add_library(sensor_coverage_planner_ground src/sensor_coverage_planner/tare_waypoint_router.cpp src/sensor_coverage_planner/tare_original.cpp src/sensor_coverage_planner/sensor_coverage_planner_ground.cpp)
ament_target_dependencies(sensor_coverage_planner_ground rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(sensor_coverage_planner_ground ${catkin_LIBRARIES} graph planning_env keypose_graph viewpoint_manager pointcloud_manager grid_world local_coverage_planner tare_visualizer)

add_executable(navigationBoundary src/navigation_boundary_publisher/navigationBoundary.cpp)
ament_target_dependencies(navigationBoundary rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2 pcl_ros pcl_conversions)
target_link_libraries(navigationBoundary ${catkin_LIBRARIES} ${PCL_LIBRARIES})

add_executable(tare_planner_node src/tare_planner_node/tare_planner_node.cpp)
ament_target_dependencies(tare_planner_node rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs tf2_ros tf2_geometry_msgs tf2)
target_link_libraries(tare_planner_node ${catkin_LIBRARIES} sensor_coverage_planner_ground)

add_executable(xytheta_follower src/ht_cost/xytheta_follower.cpp)
ament_target_dependencies(xytheta_follower rclcpp std_msgs nav_msgs geometry_msgs sensor_msgs)
target_link_libraries(xytheta_follower ht_cost ${PCL_LIBRARIES})

# Read-only historical GridMap queries. This tool never publishes navigation
# paths, permission or velocity commands and does not launch any hardware.
add_executable(ht_xytheta_offline tools/ht_xytheta_offline.cpp)
ament_target_dependencies(ht_xytheta_offline rclcpp grid_map_msgs)
target_link_libraries(ht_xytheta_offline ht_cost)

#############
## Install ##
#############

install(TARGETS
  navigationBoundary
  tare_planner_node
  xytheta_follower
  ht_xytheta_offline
  DESTINATION lib/${PROJECT_NAME})

# A regular (non-symlink) colcon install must also find OR-Tools at runtime.
set_target_properties(tare_planner_node PROPERTIES INSTALL_RPATH "$ORIGIN")
install(FILES
  "${TARE_ORTOOLS_RUNTIME_DIR}/${TARE_ORTOOLS_SONAME}"
  "${TARE_ORTOOLS_LIBRARY}"
  DESTINATION lib/${PROJECT_NAME})

install(DIRECTORY launch/
        DESTINATION share/${PROJECT_NAME}/
        )
install(DIRECTORY rviz/
        DESTINATION share/${PROJECT_NAME}/
        )
install(DIRECTORY config/
        DESTINATION share/${PROJECT_NAME}
      )
install(DIRECTORY data/
        DESTINATION share/${PROJECT_NAME}
      )

# Keep the inference entry, sibling modules and weights in this workspace's
# install tree. No adjacent workspace or source-absolute script path is used.
install(PROGRAMS ../../tools/ht_cupy_bridge/cupy_to_ht.py DESTINATION lib/${PROJECT_NAME})
install(DIRECTORY ../../tools/ht_cupy_bridge/ DESTINATION lib/${PROJECT_NAME}
        FILES_MATCHING PATTERN "*.py" PATTERN "*.pth"
        PATTERN "cupy_to_ht.py" EXCLUDE PATTERN "test_*" EXCLUDE
        PATTERN "__pycache__" EXCLUDE)

if(BUILD_TESTING)
  enable_testing()
  add_executable(ht_core_test tests/ht_core_test.cpp)
  add_test(NAME ht_core_test COMMAND ht_core_test)
  find_package(ament_cmake_gtest REQUIRED)
  ament_add_gtest(geometry_pose_test tests/geometry_pose_test.cpp TIMEOUT 45)
  target_sources(geometry_pose_test PRIVATE tests/tare_waypoint_test.cpp)
  target_compile_definitions(geometry_pose_test PRIVATE HT_SOURCE_ROOT="${CMAKE_CURRENT_SOURCE_DIR}")
  target_link_libraries(geometry_pose_test viewpoint_manager "-Wl,--whole-archive" planning_env "-Wl,--no-whole-archive" pointcloud_manager)
  ament_add_gtest(ht_ros_test tests/ht_ros_test.cpp TIMEOUT 60)
  target_link_libraries(ht_ros_test ht_cost)
  ament_add_gtest(ht_startup_sync_test tests/ht_startup_sync_test.cpp TIMEOUT 30)
  target_link_libraries(ht_startup_sync_test ht_cost)
  ament_add_gtest(input_pose_test tests/input_pose_test.cpp TIMEOUT 15)
  ament_add_gtest(planner_input_test tests/planner_input_test.cpp TIMEOUT 20)
  ament_target_dependencies(planner_input_test rclcpp nav_msgs sensor_msgs)
  target_link_libraries(planner_input_test sensor_coverage_planner_ground)
  ament_add_gtest(xytheta_follower_test tests/xytheta_follower_test.cpp TIMEOUT 90)
  ament_target_dependencies(xytheta_follower_test rclcpp nav_msgs geometry_msgs sensor_msgs std_msgs)
  target_link_libraries(xytheta_follower_test ht_cost ${PCL_LIBRARIES})
endif()
ament_package()
