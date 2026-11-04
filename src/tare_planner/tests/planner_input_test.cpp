#include "sensor_coverage_planner/sensor_coverage_planner_ground.h"
#include <gtest/gtest.h>
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <thread>

namespace sensor_coverage_planner_3d_ns {
struct InputCallbackTestAccess {
  static void parameters(SensorCoveragePlanner3D& n) {n.ReadParameters();}
  static void odom(SensorCoveragePlanner3D& n,double t,double x=0) {
    auto m=std::make_shared<nav_msgs::msg::Odometry>();m->header.frame_id="map";
    m->header.stamp=rclcpp::Time(int64_t(t*1e9));m->pose.pose.orientation.w=1;m->pose.pose.position.x=x;
    n.StateEstimationCallback(m);
  }
  static void scan(SensorCoveragePlanner3D& n,double t) {
    auto m=std::make_shared<sensor_msgs::msg::PointCloud2>();m->header.frame_id="map";
    m->header.stamp=rclcpp::Time(int64_t(t*1e9));m->width=1;m->height=1;
    // Node is intentionally not initialized: validate input ordering only,
    // before point-cloud processing or any timers/publishers are created.
    n.RegisteredScanCallback(m);
  }
  static size_t pending(const SensorCoveragePlanner3D& n){return n.pending_scans_.size();}
  static double scanStamp(const SensorCoveragePlanner3D& n){return n.scan_stamp_;}
  static double odomStamp(const SensorCoveragePlanner3D& n){return n.odom_stamp_;}
  static std::string fault(const SensorCoveragePlanner3D& n){return n.input_fault_;}
  static void offset(SensorCoveragePlanner3D& n) {n.sensor_origin_offset_={.1725,0,.5502};}
  static geometry_msgs::msg::Point sensor(const SensorCoveragePlanner3D& n){return n.sensor_position_;}
  // Exercise the real publication boundary without starting the planner timer,
  // sensors, follower or command bridge.
  static std::shared_ptr<ht_cost_ns::HtCostMap> publication(SensorCoveragePlanner3D& n) {
    n.ReadParameters();
    n.viewpoint_manager_=std::make_shared<viewpoint_manager_ns::ViewPointManager>(n.shared_from_this());
    n.waypoint_pub_=n.create_publisher<geometry_msgs::msg::PointStamped>("test_waypoint",1);
    n.speed_pub_=n.create_publisher<std_msgs::msg::Float32>("test_speed",1);
    n.mission_state_pub_=n.create_publisher<std_msgs::msg::String>("test_mission",1);
    n.execution_status_pub_=n.create_publisher<std_msgs::msg::String>("test_execution",1);
    n.mission_completed_pub_=n.create_publisher<std_msgs::msg::Bool>("test_completed",1);
    n.exploration_finish_pub_=n.create_publisher<std_msgs::msg::Bool>("test_finish",1);
    n.robot_position_=geometry_msgs::msg::Point();n.robot_yaw_=0.;
    n.lookahead_point_=Eigen::Vector3d(1.,0.,0.);
    n.tare_command_waypoint_=geometry_msgs::msg::Point();n.tare_command_waypoint_.x=1.;
    n.initialized_=true;
    return n.viewpoint_manager_->HT();
  }
  static void publishCandidate(SensorCoveragePlanner3D& n) {
    n.force_hold_=false;n.lookahead_point_update_=true;
    n.PublishWaypoint();
  }
};

TEST(PlannerPublication, RefreshesExpiredSnapshotAndRejectsNewUnsafeEvidence) {
  if(!rclcpp::ok())rclcpp::init(0,nullptr);
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("use_sim_time",true),
    rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("ht_directions_calibrated",true),
    rclcpp::Parameter("ht_topic","/test_publication_map"),
    rclcpp::Parameter("ht_exploration_mode","tare_waypoint"),
    rclcpp::Parameter("ht_score_semantics","configuration"),rclcpp::Parameter("ht_map_timeout",1.),
    rclcpp::Parameter("viewpoint_manager/number_x",10),rclcpp::Parameter("viewpoint_manager/number_y",10),
    rclcpp::Parameter("viewpoint_manager/number_z",1)});
  auto n=std::make_shared<SensorCoveragePlanner3D>(options);
  auto clock=n->get_clock()->get_clock_handle();
  ASSERT_EQ(rcl_enable_ros_time_override(clock),RCL_RET_OK);
  ASSERT_EQ(rcl_set_ros_time_override(clock,100000000000LL),RCL_RET_OK);
  auto ht=InputCallbackTestAccess::publication(*n);
  auto pub=n->create_publisher<grid_map_msgs::msg::GridMap>("/test_publication_map",1);
  bool permission=false;int received=0;
  auto sub=n->create_subscription<std_msgs::msg::Bool>("/ht_navigation_allowed",1,
    [&](std_msgs::msg::Bool::ConstSharedPtr m){permission=m->data;++received;});
  auto spin=[&](){
    for(int i=0;i<15;++i) {rclcpp::spin_some(n);std::this_thread::sleep_for(std::chrono::milliseconds(5));}
  };
  spin();
  grid_map::GridMap map;map.setFrameId("map");
  map.setGeometry(grid_map::Length(4,4),.1);
  map.add("ht_valid",1.f);map.add("ht_observation_valid",1.f);map.add("ht_obstacle",0.f);
  map.add("ht_elevation",-.6f);
  for(int k=0;k<8;++k)map.add("ht_dir_"+std::to_string(k),.9f);
  auto send=[&](int64_t stamp){map.setTimestamp(stamp);pub->publish(*grid_map::GridMapRosConverter::toMessage(map));spin();};
  send(99500000000LL);ht->beginCycle();ASSERT_TRUE(ht->ready());
  // A search holds the 99.5s map. At publication (100.6s) that snapshot is
  // expired, but a genuinely newer 100.3s map has already been committed.
  ASSERT_EQ(rcl_set_ros_time_override(clock,100600000000LL),RCL_RET_OK);
  send(100300000000LL);ASSERT_FALSE(ht->ready());
  const int before=received;
  InputCallbackTestAccess::publishCandidate(*n);spin();
  ASSERT_GT(received,before);EXPECT_TRUE(permission);
  EXPECT_NEAR(ht->cycleStamp(),100.3,1e-6);
  // The reverse case must not publish permission using the older safe map.
  map["ht_obstacle"].setConstant(1.f);send(100400000000LL);
  InputCallbackTestAccess::publishCandidate(*n);spin();EXPECT_FALSE(permission);
  EXPECT_EQ(ht->poseRejection(0,0,0),"HT_CURRENT_POSE_OCCUPIED");
  map["ht_obstacle"].setZero();map["ht_observation_valid"].setZero();send(100450000000LL);
  InputCallbackTestAccess::publishCandidate(*n);spin();EXPECT_FALSE(permission);
  EXPECT_EQ(ht->poseRejection(0,0,0),"HT_CURRENT_POSE_MISSING_SUPPORT");
  map["ht_observation_valid"].setConstant(1.f);map["ht_dir_0"].setConstant(.1f);send(100500000000LL);
  InputCallbackTestAccess::publishCandidate(*n);spin();EXPECT_FALSE(permission);
  EXPECT_EQ(ht->poseRejection(0,0,0),"HT_CURRENT_HEADING_LOW_SCORE");
  map["ht_dir_0"].setConstant(.9f);send(100550000000LL);
  ASSERT_EQ(rcl_set_ros_time_override(clock,101600000000LL),RCL_RET_OK);
  InputCallbackTestAccess::publishCandidate(*n);spin();EXPECT_FALSE(permission);
  EXPECT_EQ(ht->status(),"HT_MAP_STALE");
}
TEST(PlannerParameters, FrontierDefaultAndOverridesReachBothConsumers) {
  if(!rclcpp::ok())rclcpp::init(0,nullptr);
  for(int setting:{-1,0,1}) {
    rclcpp::NodeOptions options;
    if(setting>=0) options.parameter_overrides({rclcpp::Parameter("kUseFrontier",setting==1)});
    auto n=std::make_shared<SensorCoveragePlanner3D>(options);
    InputCallbackTestAccess::parameters(*n);
    ASSERT_TRUE(n->has_parameter("kUseFrontier"));
    const bool expected=setting!=0;
    EXPECT_EQ(n->get_parameter("kUseFrontier").as_bool(),expected);
    viewpoint_manager_ns::ViewPointManagerParameter vp;
    planning_env_ns::PlanningEnvParameters env;
    // Sentinels make a failed read deterministic, without reading invalid bools.
    vp.kUseFrontier=!expected;env.kUseFrontier=!expected;
    ASSERT_TRUE(vp.ReadParameters(n));env.ReadParameters(n);
    EXPECT_EQ(vp.kUseFrontier,expected);EXPECT_EQ(env.kUseFrontier,expected);
  }
}
TEST(PlannerInputs, DelayedMatchingOdometryDrainsBufferedScansWithoutStarvation) {
  if(!rclcpp::ok())rclcpp::init(0,nullptr);
  auto n=std::make_shared<SensorCoveragePlanner3D>();double t=n->now().seconds()-.3;
  InputCallbackTestAccess::odom(*n,t);
  InputCallbackTestAccess::scan(*n,t+.06);
  EXPECT_EQ(InputCallbackTestAccess::pending(*n),1u);EXPECT_LT(InputCallbackTestAccess::scanStamp(*n),0);
  InputCallbackTestAccess::odom(*n,t+.1,.05);
  EXPECT_EQ(InputCallbackTestAccess::pending(*n),0u);
  EXPECT_NEAR(InputCallbackTestAccess::scanStamp(*n),t+.06,1e-6);
}
TEST(PlannerInputs, PendingStorageIsBoundedAndOldOdometryDoesNotRewindState) {
  if(!rclcpp::ok())rclcpp::init(0,nullptr);
  auto n=std::make_shared<SensorCoveragePlanner3D>();double t=n->now().seconds()-.3;
  InputCallbackTestAccess::odom(*n,t);
  for(int i=0;i<25;++i)InputCallbackTestAccess::scan(*n,t+.06+i*.001);
  EXPECT_EQ(InputCallbackTestAccess::pending(*n),10u);
  InputCallbackTestAccess::odom(*n,t-.01);
  EXPECT_NEAR(InputCallbackTestAccess::odomStamp(*n),t,1e-6);
  InputCallbackTestAccess::odom(*n,t+.1,3.);
  EXPECT_EQ(InputCallbackTestAccess::fault(*n),"ODOM_JUMP_RESTART_REQUIRED");
}
TEST(PlannerInputs, ObservationOriginUsesScanTimePoseWhileVehicleRemainsCurrent) {
  if(!rclcpp::ok())rclcpp::init(0,nullptr);
  auto n=std::make_shared<SensorCoveragePlanner3D>();double t=n->now().seconds()-.3;
  InputCallbackTestAccess::offset(*n);
  InputCallbackTestAccess::odom(*n,t,0);
  InputCallbackTestAccess::odom(*n,t+.1,.1);
  InputCallbackTestAccess::scan(*n,t+.04);
  const auto sensor=InputCallbackTestAccess::sensor(*n);
  EXPECT_NEAR(sensor.x,.04+.1725,1e-6);EXPECT_NEAR(sensor.z,.5502,1e-12);
  EXPECT_NEAR(InputCallbackTestAccess::odomStamp(*n),t+.1,1e-6);
  EXPECT_NEAR(InputCallbackTestAccess::scanStamp(*n),t+.04,1e-6);
}
} // namespace
