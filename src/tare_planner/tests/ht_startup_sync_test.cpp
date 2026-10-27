#include "ht_cost/ht_cost_map.h"
#include <gtest/gtest.h>
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <thread>
using namespace std::chrono_literals;
using ht_cost_ns::Support;

class StartupSync : public ::testing::Test {
 protected:
  // Initialize ROS before constructing the fixture's executor member.
  static void SetUpTestSuite() {if(!rclcpp::ok())rclcpp::init(0,nullptr);}
  rclcpp::Node::SharedPtr planner,follower;
  std::unique_ptr<ht_cost_ns::HtCostMap> owner,consumer;
  rclcpp::Publisher<grid_map_msgs::msg::GridMap>::SharedPtr maps;
  rclcpp::executors::SingleThreadedExecutor executor;
  rclcpp::Node::SharedPtr makeNode(const char* name) {
    auto n=std::make_shared<rclcpp::Node>(name,rclcpp::NodeOptions().parameter_overrides({
      rclcpp::Parameter("use_sim_time",true),rclcpp::Parameter("ht_enabled",true),
      rclcpp::Parameter("ht_directions_calibrated",true),
      rclcpp::Parameter("ht_exploration_mode","legacy_xytheta_greedy"),
      rclcpp::Parameter("ht_score_semantics","configuration"),
      rclcpp::Parameter("ht_startup_radius",1.2),rclcpp::Parameter("ht_startup_duration",30.),
      rclcpp::Parameter("ht_topic","/offline_startup/map"),
      rclcpp::Parameter("ht_startup_topic","/offline_startup/prior")}));
    setTime(n,100.);return n;
  }
  static void setTime(rclcpp::Node::SharedPtr n,double t) {
    ASSERT_EQ(rcl_enable_ros_time_override(n->get_clock()->get_clock_handle()),RCL_RET_OK);
    ASSERT_EQ(rcl_set_ros_time_override(n->get_clock()->get_clock_handle(),int64_t(t*1e9)),RCL_RET_OK);
  }
  void spin() {
    for(int i=0;i<30;++i){executor.spin_some();std::this_thread::sleep_for(10ms);}
  }
  void SetUp() override {
    if(!rclcpp::ok())rclcpp::init(0,nullptr);
    planner=makeNode("startup_owner");owner=std::make_unique<ht_cost_ns::HtCostMap>(planner);
    executor.add_node(planner);maps=planner->create_publisher<grid_map_msgs::msg::GridMap>("/offline_startup/map",1);
  }
  void join(double t) {
    follower=makeNode("startup_consumer");setTime(follower,t);
    consumer=std::make_unique<ht_cost_ns::HtCostMap>(follower,false);executor.add_node(follower);spin();
  }
  void map(bool known=false,bool obstacle=false,bool low=false) {
    grid_map::GridMap g;g.setFrameId("map");g.setGeometry(grid_map::Length(8,8),.1);
    g.setTimestamp(planner->now().nanoseconds());
    g.add("ht_valid",known ? 1.f:0.f);g.add("ht_observation_valid",known ? 1.f:0.f);
    g.add("ht_obstacle",obstacle ? 1.f:0.f);
    for(int k=0;k<8;++k)g.add("ht_dir_"+std::to_string(k),low ? .1f:1.f);
    maps->publish(*grid_map::GridMapRosConverter::toMessage(g));spin();
    owner->beginCycle();if(consumer)consumer->beginCycle();
  }
};
TEST_F(StartupSync,LateFollowerImportsOriginalAnchorAndDeadline) {
  owner->start({.1,.2,.3});join(110.);
  const auto p=owner->startupPrior(),f=consumer->startupPrior();
  ASSERT_TRUE(f.initialized);EXPECT_DOUBLE_EQ(f.start,p.start);EXPECT_DOUBLE_EQ(f.lifetime,p.lifetime);
  EXPECT_DOUBLE_EQ(f.anchor.x,.1);EXPECT_DOUBLE_EQ(f.anchor.y,.2);EXPECT_DOUBLE_EQ(f.anchor.z,.3);
  EXPECT_DOUBLE_EQ(f.radius,1.2);
  // Calling start on a consumer or repeatedly on the owner cannot recenter it.
  consumer->start({9,9,0});owner->start({9,9,0});spin();
  EXPECT_DOUBLE_EQ(consumer->startupPrior().anchor.x,.1);
  setTime(planner,110.);map();
  EXPECT_EQ(owner->poseSupport(.1,.2,0),Support::STARTUP_PRIOR);
  EXPECT_EQ(consumer->poseSupport(.1,.2,0),Support::STARTUP_PRIOR);
  setTime(planner,130.);setTime(follower,130.);map();
  EXPECT_EQ(owner->poseSupport(.1,.2,0),Support::UNKNOWN);
  EXPECT_EQ(consumer->poseSupport(.1,.2,0),Support::UNKNOWN);
}
TEST_F(StartupSync,ExpiredLateJoinAndRepeatedStartCannotGrantFreshTime) {
  owner->start({});join(131.);ASSERT_TRUE(consumer->startupPrior().retired);
  setTime(planner,131.);owner->start({});map();
  EXPECT_TRUE(consumer->startupPrior().retired);
  EXPECT_EQ(consumer->poseSupport(0,0,0),Support::UNKNOWN);
}
TEST_F(StartupSync,LeavingDiskRetiresStateForLateJoinAndCannotRevive) {
  owner->start({});owner->updateExecution({1.3,0,0},false);owner->updateExecution({},false);
  join(101.);ASSERT_TRUE(consumer->startupPrior().retired);
  owner->start({});spin();EXPECT_TRUE(consumer->startupPrior().retired);
}
TEST_F(StartupSync,ConsumerWaitsForAuthorityButKnownGroundNeedsNoPrior) {
  join(100.);consumer->start({});EXPECT_FALSE(consumer->startupPrior().initialized);
  map();EXPECT_EQ(consumer->poseSupport(0,0,0),Support::UNKNOWN);
  map(true);EXPECT_EQ(consumer->poseSupport(0,0,0),Support::KNOWN);
}
TEST_F(StartupSync,AssumptionNeverOverridesPhysicalObstacleOrLowScore) {
  owner->start({});join(100.);map(false,true);
  EXPECT_EQ(owner->poseSupport(0,0,0),Support::BLOCKED);
  EXPECT_EQ(consumer->poseSupport(0,0,0),Support::BLOCKED);
  map(true,false,true);EXPECT_EQ(consumer->poseSupport(0,0,0),Support::BLOCKED);
}
TEST_F(StartupSync,ChangedDeadlineLatchesConflictRatherThanRenewingMission) {
  owner->start({});join(100.);
  auto pub=planner->create_publisher<tare_planner::msg::StartupPrior>("/offline_startup/prior",rclcpp::QoS(1).reliable().transient_local());
  tare_planner::msg::StartupPrior m;m.header.frame_id="map";m.header.stamp=rclcpp::Time(100000000000LL);
  m.expires_at=rclcpp::Time(131000000000LL);m.radius=1.2;pub->publish(m);spin();
  EXPECT_FALSE(consumer->ready());EXPECT_EQ(consumer->status(),"HT_STARTUP_PRIOR_CONFLICT");
}
TEST_F(StartupSync,UncalibratedOwnerCanAnchorWithoutGrantingNavigation) {
  // Start is independent of readiness, as used before the planner's HT gate.
  auto node=std::make_shared<rclcpp::Node>("uncalibrated_start_owner",rclcpp::NodeOptions().parameter_overrides({
    rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("ht_directions_calibrated",false),
    rclcpp::Parameter("ht_startup_topic","/offline_startup/uncalibrated")}));
  ht_cost_ns::HtCostMap h(node);h.start({1,2,3});
  EXPECT_TRUE(h.startupPrior().initialized);EXPECT_FALSE(h.ready());EXPECT_EQ(h.status(),"HT_UNCALIBRATED");
}
