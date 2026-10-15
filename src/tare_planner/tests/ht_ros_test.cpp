#include "ht_cost/ht_cost_map.h"
#include <gtest/gtest.h>
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_core/iterators/GridMapIterator.hpp>
#include <tf2_ros/static_transform_broadcaster.h>
#include <chrono>
#include <thread>

using namespace std::chrono_literals;
using ht_cost_ns::Point;

class HtRosTest : public ::testing::Test {
 protected:
  rclcpp::Node::SharedPtr node;
  std::unique_ptr<ht_cost_ns::HtCostMap> ht;
  rclcpp::Publisher<grid_map_msgs::msg::GridMap>::SharedPtr pub;

  void SetUp() override {
    if (!rclcpp::ok()) rclcpp::init(0, nullptr);
    rclcpp::NodeOptions options;
    options.parameter_overrides({
      rclcpp::Parameter("ht_enabled", true),
      rclcpp::Parameter("ht_directions_calibrated", true),
      rclcpp::Parameter("ht_topic", "/ht_test_map"),
      rclcpp::Parameter("ht_map_timeout", 2.0)});
    node = std::make_shared<rclcpp::Node>("ht_ros_test", options);
    ht = std::make_unique<ht_cost_ns::HtCostMap>(node);
    pub = node->create_publisher<grid_map_msgs::msg::GridMap>("/ht_test_map", 1);
    spin(150ms);
  }
  void spin(std::chrono::milliseconds duration) {
    const auto end = std::chrono::steady_clock::now() + duration;
    do {
      rclcpp::spin_some(node);
      std::this_thread::sleep_for(5ms);
    } while (std::chrono::steady_clock::now() < end);
    ht->beginCycle();
  }
  grid_map::GridMap grid() {
    grid_map::GridMap map;
    map.setFrameId("map");
    map.setGeometry(grid_map::Length(8, 6), 0.25);
    for (int k=0; k<8; ++k) map.add("ht_dir_"+std::to_string(k), 0.1f*(k+1));
    map.add("ht_valid", 1.0f);
    map.setTimestamp(node->now().nanoseconds());
    return map;
  }
  void send(const grid_map_msgs::msg::GridMap& msg) {
    pub->publish(msg);
    spin(100ms);
  }
  void send(const grid_map::GridMap& map) {
    send(*grid_map::GridMapRosConverter::toMessage(map));
  }
};

TEST_F(HtRosTest, DirectionalCostsAndValidSupport) {
  send(grid());
  ASSERT_TRUE(ht->ready());
  EXPECT_TRUE(std::isinf(ht->cost({-1,0,0}, {1,0,0})));
  EXPECT_NEAR(ht->cost({1,0,0}, {-1,0,0}), 2, 1e-5);
  EXPECT_EQ(ht->support({-1,0,0}, {1,0,0}),ht_cost_ns::Support::BLOCKED);
  EXPECT_FALSE(ht->permits(ht->support({-1,0,0}, {1,0,0})));
  EXPECT_TRUE(ht->knownSegment({1,0,0}, {-1,0,0}));
  EXPECT_FALSE(ht->knownSegment({3.5,0,0}, {3.9,0,0}));
}

TEST_F(HtRosTest, CircularBufferPreservesSpatialCells) {
  auto map = grid();
  map.move(grid_map::Position(0.75, -0.5));
  ASSERT_NE(map.getStartIndex().matrix().squaredNorm(), 0);
  for (grid_map::GridMapIterator it(map); !it.isPastEnd(); ++it) {
    grid_map::Position p;
    map.getPosition(*it,p);
    map.at("ht_valid",*it)=1;
    for (int k=0;k<8;++k) map.at("ht_dir_"+std::to_string(k),*it)=p.x()>0 ? 0.8f : 0.2f;
  }
  send(map);
  ASSERT_TRUE(ht->ready());
  EXPECT_NEAR(ht->cost({1,0,0}, {2,0,0}), 1, 1e-5);
  EXPECT_TRUE(std::isinf(ht->cost({-2,0,0}, {-1,0,0})));
}

TEST_F(HtRosTest, OffCenterHazardIsHardBlockedAtPlanningAndExecution) {
  auto map=grid();
  for (int k=0;k<8;++k) map["ht_dir_"+std::to_string(k)].setConstant(0.8f);
  grid_map::Index hazard;
  ASSERT_TRUE(map.getIndex(grid_map::Position(0,0.5),hazard));
  map.at("ht_dir_0",hazard)=0.2f;
  send(map);
  ASSERT_TRUE(ht->ready());
  EXPECT_EQ(ht->support({-1,0,0},{1,0,0}),ht_cost_ns::Support::BLOCKED);
  EXPECT_TRUE(std::isinf(ht->cost({-1,0,0},{1,0,0})));
  EXPECT_FALSE(ht->permits(ht->support({-1,0,0},{1,0,0})));
  EXPECT_NEAR(ht->cost({1,0,0},{-1,0,0}),2,1e-5);
}

TEST_F(HtRosTest, RotatedTranslatedFrameRotatesChannels) {
  tf2_ros::StaticTransformBroadcaster broadcaster(node);
  geometry_msgs::msg::TransformStamped tf;
  tf.header.frame_id="map";
  tf.child_frame_id="ht_rotated";
  tf.header.stamp=node->now();
  tf.transform.translation.x=10;
  tf.transform.translation.y=20;
  tf.transform.rotation.z=std::sqrt(0.5);
  tf.transform.rotation.w=std::sqrt(0.5);
  broadcaster.sendTransform(tf);
  spin(250ms);
  auto map=grid();
  map.setFrameId("ht_rotated");
  send(map);
  ASSERT_TRUE(ht->ready());
  EXPECT_TRUE(std::isinf(ht->cost({10,19,0}, {10,21,0})));
  EXPECT_NEAR(ht->cost({10,21,0}, {10,19,0}), 2, 1e-5);
}

TEST_F(HtRosTest, MissingLayerRevokesPreviousMap) {
  auto map=grid(); send(map); ASSERT_TRUE(ht->ready());
  map.erase("ht_dir_7"); send(map); EXPECT_FALSE(ht->ready());
}

TEST_F(HtRosTest, InvalidProbabilityPreventsExecution) {
  auto map=grid();
  map["ht_dir_3"].setConstant(std::numeric_limits<float>::quiet_NaN());
  send(map);
  EXPECT_FALSE(ht->knownSegment({}, {1,0,0}));
  map["ht_dir_3"].setConstant(1.1f); send(map);
  EXPECT_FALSE(ht->knownSegment({}, {1,0,0}));
}

TEST_F(HtRosTest, StaleFutureAndMissingTransformHold) {
  auto map=grid();
  map.setTimestamp(node->now().nanoseconds()-3000000000LL); send(map);
  EXPECT_FALSE(ht->ready());
  map.setTimestamp(node->now().nanoseconds()+3000000000LL); send(map);
  EXPECT_FALSE(ht->ready());
  map.setTimestamp(node->now().nanoseconds()); map.setFrameId("missing_tf"); send(map);
  EXPECT_FALSE(ht->ready());
}

TEST_F(HtRosTest, NonFinitePoseRejected) {
  auto msg=grid_map::GridMapRosConverter::toMessage(grid());
  msg->info.pose.orientation.x=std::numeric_limits<double>::quiet_NaN();
  send(*msg);
  EXPECT_FALSE(ht->ready());
}

TEST_F(HtRosTest, MalformedMessagesDoNotEnterUnsafeConverter) {
  const auto good=grid_map::GridMapRosConverter::toMessage(grid());
  auto bad=*good; bad.info.resolution=0; send(bad); EXPECT_FALSE(ht->ready());
  bad=*good; bad.data[0].layout.dim.clear(); send(bad); EXPECT_FALSE(ht->ready());
  bad=*good; bad.data[0].data.pop_back(); send(bad); EXPECT_FALSE(ht->ready());
  bad=*good; bad.outer_start_index=500; send(bad); EXPECT_FALSE(ht->ready());
  bad=*good; bad.data[0].layout.data_offset=1; send(bad); EXPECT_FALSE(ht->ready());
  send(*good); EXPECT_TRUE(ht->ready());
}

TEST_F(HtRosTest, CalibrationRequiredAndParametersChecked) {
  auto uncalibrated=std::make_shared<rclcpp::Node>("ht_uncalibrated",
    rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("ht_enabled",true)}));
  ht_cost_ns::HtCostMap held(uncalibrated);
  held.beginCycle(); EXPECT_FALSE(held.ready());
  auto invalid=std::make_shared<rclcpp::Node>("ht_invalid",
    rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("ht_channel_order",std::vector<int64_t>{0,0})}));
  EXPECT_THROW(ht_cost_ns::HtCostMap rejected(invalid),std::invalid_argument);
  auto bad_threshold=std::make_shared<rclcpp::Node>("ht_bad_threshold",
    rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("ht_min_probability",1.1)}));
  EXPECT_THROW(ht_cost_ns::HtCostMap rejected(bad_threshold),std::invalid_argument);
}

TEST_F(HtRosTest, StartupPriorIsBoundedAndDoesNotOverwriteObservedRisk) {
  auto map=grid();map["ht_valid"].setZero();send(map);
  ht->start({0,0,0});
  EXPECT_EQ(ht->support({}, {.3,0,0}),ht_cost_ns::Support::STARTUP_PRIOR);
  EXPECT_FALSE(ht->knownSegment({}, {.3,0,0}));
  EXPECT_NEAR(ht->cost({}, {.3,0,0}),.3,1e-5);
  EXPECT_EQ(ht->support({}, {1,0,0}),ht_cost_ns::Support::UNKNOWN); // Whole footprint matters.
  EXPECT_FALSE(ht->permits(ht->support({}, {1,0,0})));
  map["ht_valid"].setOnes();send(map);
  EXPECT_EQ(ht->support({}, {.3,0,0}),ht_cost_ns::Support::BLOCKED);
  EXPECT_TRUE(std::isinf(ht->cost({}, {.3,0,0})));
  ht->updateExecution({2,0,0},false);map["ht_valid"].setZero();send(map);
  EXPECT_EQ(ht->support({}, {.3,0,0}),ht_cost_ns::Support::UNKNOWN);
  auto broken=map;broken.erase("ht_dir_7");send(broken);
  EXPECT_EQ(ht->support({}, {.3,0,0}),ht_cost_ns::Support::FAULT);
  EXPECT_FALSE(ht->permits(ht->support({}, {.3,0,0})));
}
TEST_F(HtRosTest, UnknownAndObservedRiskBothBlockEdges) {
  auto map=grid();
  for (grid_map::GridMapIterator it(map); !it.isPastEnd(); ++it) {
    grid_map::Position p;map.getPosition(*it,p);
    if (p.x()>0) map.at("ht_valid",*it)=0;
  }
  send(map);
  EXPECT_EQ(ht->support({-1,0,0},{1,0,0}),ht_cost_ns::Support::BLOCKED);
  EXPECT_TRUE(std::isinf(ht->cost({-1,0,0},{1,0,0})));
  EXPECT_TRUE(std::isinf(ht->cost({1,0,0},{-1,0,0})));
}
TEST_F(HtRosTest, StrictPolicyAllowsOnlyKnownOrBoundedStartup) {
  ht.reset();node.reset();
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("ht_enabled",true),
    rclcpp::Parameter("ht_directions_calibrated",true),rclcpp::Parameter("ht_unknown_policy","strict"),
    rclcpp::Parameter("ht_topic","/ht_test_map")});
  node=std::make_shared<rclcpp::Node>("ht_strict_test",options);
  ht=std::make_unique<ht_cost_ns::HtCostMap>(node);spin(150ms);
  auto map=grid();map["ht_valid"].setZero();send(map);ht->start({});
  EXPECT_TRUE(ht->permits(ht->support({}, {.3,0,0})));
  EXPECT_FALSE(ht->permits(ht->support({}, {1,0,0})));
}

TEST_F(HtRosTest, RecordedGarageUnknownCornerCannotPassAsAnUnsplitEdge) {
  // Geometry and invalid receptive-field corner from the recorded 102s stop.
  // The old 2cm samples passed a ~10cm edge, while two ~5cm subedges failed.
  constexpr double res=0.04093567251461988;
  grid_map::GridMap map;map.setFrameId("map");
  map.setGeometry(grid_map::Length(241*res,241*res),res,
                  grid_map::Position(1.4327485380116958,11.584795321637427));
  map.setTimestamp(node->now().nanoseconds());map.add("ht_valid",1.f);
  for (int k=0;k<8;++k) map.add("ht_dir_"+std::to_string(k),1.f);
  for (int r=62;r<=112;++r) for (int c=134;c<=184;++c) map["ht_valid"](r,c)=0;
  send(map);ASSERT_TRUE(ht->ready());
  const ht_cost_ns::Pose2 a{1.4449336528778076,11.569907188415527,-2.5809493849671568};
  const ht_cost_ns::Pose2 b{1.3629863430039204,11.51266551583492,-2.4827746145424756};
  EXPECT_EQ(ht->motionSupport(a,b),ht_cost_ns::Support::UNKNOWN);
  for (int pieces:{2,3,5,7}) {
    bool allowed=true;
    for (int i=0;i<pieces;++i) {
      auto interpolate=[&](double t){return ht_cost_ns::Pose2{
        a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),a.yaw+t*(b.yaw-a.yaw)};};
      allowed &= ht->permits(ht->motionSupport(interpolate(double(i)/pieces),interpolate(double(i+1)/pieces)));
    }
    EXPECT_FALSE(allowed) << "pieces=" << pieces;
  }
}

TEST_F(HtRosTest, HeadingSweepChecksIntermediateDirectionsAndWrapsAtPi) {
  auto map=grid();
  for (int k=0;k<8;++k) map["ht_dir_"+std::to_string(k)].setConstant(1.f);
  map["ht_dir_1"].setConstant(.1f);send(map);
  EXPECT_EQ(ht->poseSupport(0,0,0),ht_cost_ns::Support::KNOWN);
  EXPECT_EQ(ht->poseSupport(0,0,ht_cost_ns::kPi/2),ht_cost_ns::Support::KNOWN);
  EXPECT_EQ(ht->motionSupport({0,0,0},{0,0,ht_cost_ns::kPi/2}),ht_cost_ns::Support::BLOCKED);
  EXPECT_EQ(ht->motionSupport({0,0,3.1},{0,0,-3.1}),ht_cost_ns::Support::KNOWN);
}
