#include "sensor_coverage_planner/sensor_coverage_planner_ground.h"
#include <gtest/gtest.h>

namespace sensor_coverage_planner_3d_ns {
struct InputCallbackTestAccess {
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
};
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
