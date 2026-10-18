#include "ht_cost/ht_cost_map.h"
#include <gtest/gtest.h>
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_core/iterators/GridMapIterator.hpp>
#include <tf2_ros/static_transform_broadcaster.h>
#include <chrono>
#include <thread>
#include <fstream>
#include <cstdlib>
#include "ht_cost/heading_reserve.h"

using namespace std::chrono_literals;
using ht_cost_ns::Point;

class HtRosTest : public ::testing::Test {
 protected:
  rclcpp::Node::SharedPtr node;
  std::unique_ptr<ht_cost_ns::HtCostMap> ht;
  rclcpp::Publisher<grid_map_msgs::msg::GridMap>::SharedPtr pub;
  virtual std::string scoreSemantics() const {return "point";}

  void SetUp() override {
    if (!rclcpp::ok()) rclcpp::init(0, nullptr);
    rclcpp::NodeOptions options;
    options.parameter_overrides({
      rclcpp::Parameter("ht_enabled", true),
      rclcpp::Parameter("ht_directions_calibrated", true),
      rclcpp::Parameter("ht_topic", "/ht_test_map"),
      rclcpp::Parameter("ht_score_semantics",scoreSemantics()),
      rclcpp::Parameter("ht_map_timeout", 3600.0)});
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
    if (scoreSemantics()=="configuration") {
      map.add("ht_observation_valid",1.f);map.add("ht_obstacle",0.f);
    }
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
  grid_map::GridMap capturedGrid(const char* filename,ht_cost_ns::Pose2& start) {
    std::ifstream file(filename);int rows,cols;double resolution,cx,cy;
    if (!(file>>rows>>cols>>resolution>>cx>>cy>>start.x>>start.y>>start.yaw) ||
        rows<=0 || cols<=0 || rows>1000 || cols>1000) throw std::runtime_error("Invalid captured grid header");
    std::vector<float> values(rows*cols*10);
    for(auto& value:values) if(!(file>>value)) throw std::runtime_error("Truncated captured grid");
    grid_map::GridMap result;result.setFrameId("map");
    result.setGeometry(grid_map::Length(rows*resolution,cols*resolution),resolution,grid_map::Position(cx,cy));
    for(int k=0;k<8;++k)result.add("ht_dir_"+std::to_string(k));
    result.add("ht_valid");result.add("ht_observation_valid");
    for(grid_map::GridMapIterator it(result);!it.isPastEnd();++it) {
      grid_map::Position p;result.getPosition(*it,p);
      const int r=std::floor(rows*.5-(p.x()-cx)/resolution),c=std::floor(cols*.5-(p.y()-cy)/resolution);
      if(r<0||r>=rows||c<0||c>=cols)throw std::runtime_error("Captured grid index mismatch");
      const size_t offset=(r*cols+c)*10;
      for(int k=0;k<8;++k)result.at("ht_dir_"+std::to_string(k),*it)=values[offset+k];
      result.at("ht_valid",*it)=values[offset+8];result.at("ht_observation_valid",*it)=values[offset+9];
    }
    return result;
  }
};

class HtConfigurationRosTest : public HtRosTest {
 protected:
  std::string scoreSemantics() const override {return "configuration";}
};

TEST_F(HtConfigurationRosTest, NeighbouringVehicleScoresAreNotPointObstacles) {
  auto map=grid();
  for(int k=0;k<8;++k)map["ht_dir_"+std::to_string(k)].setConstant(.8f);
  grid_map::Index side;ASSERT_TRUE(map.getIndex(grid_map::Position(0,.5),side));
  map.at("ht_dir_0",side)=.2f;send(map);ASSERT_TRUE(ht->ready());
  EXPECT_EQ(ht->support({-1,0,0},{1,0,0}),ht_cost_ns::Support::KNOWN);
  EXPECT_EQ(ht->poseSupport(0,.5,0),ht_cost_ns::Support::BLOCKED);
  // A measurement-space obstacle at the very same side cell blocks the body,
  // even if that cell has no neural prediction at all.
  map.at("ht_obstacle",side)=1;map.at("ht_valid",side)=0;
  for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),side)=NAN;
  send(map);EXPECT_EQ(ht->poseSupport(0,0,0),ht_cost_ns::Support::BLOCKED);
  EXPECT_EQ(ht->poseSupport(0,0,ht_cost_ns::kPi),ht_cost_ns::Support::BLOCKED);
}

TEST_F(HtConfigurationRosTest, MissingBodyObservationsAndUnscoredReferenceStillReject) {
  auto map=grid();for(int k=0;k<8;++k)map["ht_dir_"+std::to_string(k)].setConstant(.8f);
  grid_map::Index side;ASSERT_TRUE(map.getIndex(grid_map::Position(0,.5),side));
  map.at("ht_observation_valid",side)=0;send(map);
  EXPECT_EQ(ht->poseSupport(0,0,0),ht_cost_ns::Support::UNKNOWN);
  map.at("ht_observation_valid",side)=1;map["ht_valid"].setZero();send(map);
  EXPECT_EQ(ht->poseSupport(0,0,0),ht_cost_ns::Support::UNKNOWN);
}

TEST_F(HtConfigurationRosTest, MissingOrInvalidPhysicalContractCannotEnableDriving) {
  auto map=grid();map.erase("ht_obstacle");send(map);EXPECT_FALSE(ht->ready());
  map.add("ht_obstacle",0.f);send(map);EXPECT_TRUE(ht->ready());
  map["ht_obstacle"](0,0)=NAN;send(map);EXPECT_FALSE(ht->ready());
  map["ht_obstacle"].setZero();map.erase("ht_observation_valid");send(map);EXPECT_FALSE(ht->ready());
}

TEST_F(HtConfigurationRosTest, CapturedMixedTurnStopHasAnExitWithoutInflatingVehicleScores) {
  const char* filename=std::getenv("HT_CONFIGURATION_FIXTURE");
  if(!filename) GTEST_SKIP()<<"Set HT_CONFIGURATION_FIXTURE to the74s mixed-turn stop";
  ht_cost_ns::Pose2 start;auto map=capturedGrid(filename,start);map.add("ht_obstacle",0.f);
  // Old producer did not serialize the obstacle layer. Its explicit override
  // set all eight probabilities exactly zero. This is a reconstruction for
  // this archived fixture only, never a substitute for the new live layer.
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    bool all_zero=true;
    for(int k=0;k<8;++k)all_zero &= map.at("ht_dir_"+std::to_string(k),*it)==0.f;
    map.at("ht_obstacle",*it)=all_zero?1.f:0.f;
  }
  map.setTimestamp(node->now().nanoseconds());send(map);ASSERT_TRUE(ht->ready());
  ht_cost_ns::XYThetaConfig config;config.headings=32;config.turn_angles={ht_cost_ns::kPi/16,ht_cost_ns::kPi/8};
  config.goal_radius=.35;config.max_search_seconds=.3;
  auto valid=[&](ht_cost_ns::Pose2 a,ht_cost_ns::Pose2 b,double){return ht->permits(ht->motionSupport(a,b));};
  ASSERT_TRUE(valid(start,start,0));
  const auto plan=ht_cost_ns::planXYTheta(start,{start.x+2,start.y,0},config,valid);
  ASSERT_TRUE(plan.reached);ASSERT_GT(plan.poses.size(),1u);
  for(size_t i=1;i<plan.poses.size();++i)EXPECT_TRUE(valid(plan.poses[i-1],plan.poses[i],0));
}

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

TEST_F(HtRosTest, SeparatePhysicalObservationDoesNotInflateContextTwice) {
  auto map=grid();
  for(int k=0;k<8;++k) map["ht_dir_"+std::to_string(k)].setConstant(.8f);
  map.add("ht_observation_valid",1.f);
  grid_map::Index side;
  ASSERT_TRUE(map.getIndex(grid_map::Position(0,.5),side));
  map.at("ht_valid",side)=0;
  for(int k=0;k<8;++k) map.at("ht_dir_"+std::to_string(k),side)=NAN;
  send(map);
  EXPECT_EQ(ht->support({-1,0,0},{1,0,0}),ht_cost_ns::Support::KNOWN);
  // Actual under-body missing data remains forbidden.
  map.at("ht_observation_valid",side)=0;send(map);
  EXPECT_EQ(ht->support({-1,0,0},{1,0,0}),ht_cost_ns::Support::UNKNOWN);
  map.at("ht_observation_valid",side)=1;
  map.at("ht_valid",side)=1;
  for(int k=0;k<8;++k) map.at("ht_dir_"+std::to_string(k),side)=.8f;
  map.at("ht_dir_0",side)=.2f;send(map);
  EXPECT_EQ(ht->support({-1,0,0},{1,0,0}),ht_cost_ns::Support::BLOCKED);
  // Physical observations cannot authorize an unscored current pose.
  map["ht_valid"].setConstant(0);send(map);
  EXPECT_EQ(ht->poseSupport(-1,0,0),ht_cost_ns::Support::UNKNOWN);
}

TEST_F(HtRosTest, CapturedTunnelReturnKeepsRiskThresholdAndReachesHome) {
  const char* filename=std::getenv("HT_TUNNEL_FIXTURE");
  if (!filename) GTEST_SKIP()<<"Set HT_TUNNEL_FIXTURE using export_ht_tunnel_fixture.py";
  std::ifstream file(filename);ASSERT_TRUE(file.good());
  int rows,cols;double resolution,cx,cy,x,y,yaw;
  ASSERT_TRUE(bool(file>>rows>>cols>>resolution>>cx>>cy>>x>>y>>yaw));
  std::vector<float> values(rows*cols*10);
  for(auto& value:values) ASSERT_TRUE(bool(file>>value));
  grid_map::GridMap map;map.setFrameId("map");
  map.setGeometry(grid_map::Length(rows*resolution,cols*resolution),resolution,grid_map::Position(cx,cy));
  for(int k=0;k<8;++k)map.add("ht_dir_"+std::to_string(k));
  map.add("ht_valid");map.add("ht_observation_valid");
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    grid_map::Position p;map.getPosition(*it,p);
    const int r=std::floor(rows*.5-(p.x()-cx)/resolution),c=std::floor(cols*.5-(p.y()-cy)/resolution);
    ASSERT_GE(r,0);ASSERT_LT(r,rows);ASSERT_GE(c,0);ASSERT_LT(c,cols);
    const size_t offset=(r*cols+c)*10;
    for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),*it)=values[offset+k];
    map.at("ht_valid",*it)=values[offset+8];map.at("ht_observation_valid",*it)=values[offset+9];
  }
  map.setTimestamp(node->now().nanoseconds());send(map);ASSERT_TRUE(ht->ready());
  ht_cost_ns::XYThetaConfig config;config.goal_radius=.35;config.max_search_seconds=.5;
  auto valid=[&](ht_cost_ns::Pose2 a,ht_cost_ns::Pose2 b,double){return ht->permits(ht->motionSupport(a,b));};
  auto repaired=ht_cost_ns::planXYTheta({x,y,yaw},{0,0,0},config,valid);
  ASSERT_TRUE(repaired.reached);ASSERT_GT(repaired.poses.size(),1u);
  for(size_t i=1;i<repaired.poses.size();++i) EXPECT_TRUE(valid(repaired.poses[i-1],repaired.poses[i],0));
  // Removing only the new physical-observation layer reproduces the original
  // stopped-map failure, with exactly the same old probabilities and poses.
  map.erase("ht_observation_valid");map.setTimestamp(node->now().nanoseconds());send(map);
  auto original=ht_cost_ns::planXYTheta({x,y,yaw},{0,0,0},config,valid);
  EXPECT_FALSE(original.reached);
}

TEST_F(HtRosTest, CapturedMapSearchResolutionAudit) {
  const char* filename=std::getenv("HT_STUCK_FIXTURE");
  if (!filename) GTEST_SKIP()<<"Set HT_STUCK_FIXTURE to audit a captured stop";
  std::ifstream file(filename);ASSERT_TRUE(file.good());
  int rows,cols;double resolution,cx,cy,x,y,yaw;
  ASSERT_TRUE(bool(file>>rows>>cols>>resolution>>cx>>cy>>x>>y>>yaw));
  std::vector<float> values(rows*cols*10);
  for(auto& value:values) ASSERT_TRUE(bool(file>>value));
  grid_map::GridMap map;map.setFrameId("map");
  map.setGeometry(grid_map::Length(rows*resolution,cols*resolution),resolution,grid_map::Position(cx,cy));
  for(int k=0;k<8;++k)map.add("ht_dir_"+std::to_string(k));
  map.add("ht_valid");map.add("ht_observation_valid");
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    grid_map::Position p;map.getPosition(*it,p);
    const int r=std::floor(rows*.5-(p.x()-cx)/resolution),c=std::floor(cols*.5-(p.y()-cy)/resolution);
    ASSERT_GE(r,0);ASSERT_LT(r,rows);ASSERT_GE(c,0);ASSERT_LT(c,cols);
    const size_t offset=(r*cols+c)*10;
    for(int k=0;k<8;++k)map.at("ht_dir_"+std::to_string(k),*it)=values[offset+k];
    map.at("ht_valid",*it)=values[offset+8];map.at("ht_observation_valid",*it)=values[offset+9];
  }
  struct Profile {const char* name;double cell,step;int headings;};
  const Profile profiles[]={{"production",.3,.4,16},{"heading32",.3,.4,32},
    {"heading64",.3,.4,64},{"short16",.15,.2,16},{"fine32",.15,.2,32},{"fine64",.1,.15,64}};
  std::vector<ht_cost_ns::Point> goals{{4.3,12.7,0}};
  for(int k=0;k<8;++k)goals.push_back({x+2*std::cos(k*ht_cost_ns::kPi/4),y+2*std::sin(k*ht_cost_ns::kPi/4),0});
  for(const auto& profile:profiles) for(size_t gi=0;gi<goals.size();++gi) {
    map.setTimestamp(node->now().nanoseconds());send(map);ASSERT_TRUE(ht->ready());
    ht_cost_ns::XYThetaConfig config;config.cell=profile.cell;config.drive_step=profile.step;
    config.headings=profile.headings;config.goal_radius=.35;config.max_search_seconds=.7;
    config.max_expansions=80000;
    auto valid=[&](ht_cost_ns::Pose2 a,ht_cost_ns::Pose2 b,double){return ht->permits(ht->motionSupport(a,b));};
    const auto started=std::chrono::steady_clock::now();
    const auto plan=ht_cost_ns::planXYTheta({x,y,yaw},goals[gi],config,valid);
    const double seconds=std::chrono::duration<double>(std::chrono::steady_clock::now()-started).count();
    std::cout<<"RESOLUTION_AUDIT profile="<<profile.name<<" goal="<<gi<<" reached="<<plan.reached
      <<" expanded="<<plan.expanded<<" poses="<<plan.poses.size()<<" seconds="<<seconds<<std::endl;
    if(plan.reached) for(size_t i=1;i<plan.poses.size();++i) EXPECT_TRUE(valid(plan.poses[i-1],plan.poses[i],0));
  }
}

TEST_F(HtRosTest, CapturedSafeRootNeedsFinerHeadingSearchToEscape) {
  const char* filename=std::getenv("HT_FINE_ESCAPE_FIXTURE");
  if (!filename) GTEST_SKIP()<<"Set HT_FINE_ESCAPE_FIXTURE to the zero-command-only stopped map";
  ht_cost_ns::Pose2 start;auto map=capturedGrid(filename,start);
  map.setTimestamp(node->now().nanoseconds());send(map);ASSERT_TRUE(ht->ready());
  const ht_cost_ns::Point goal{start.x+2,start.y,0};
  ht_cost_ns::XYThetaConfig config;config.headings=16;config.cell=.3;config.drive_step=.4;
  config.goal_radius=.35;config.max_search_seconds=.15;
  auto valid=[&](ht_cost_ns::Pose2 a,ht_cost_ns::Pose2 b,double){return ht->permits(ht->motionSupport(a,b));};
  ASSERT_TRUE(valid(start,start,0));
  const auto coarse=ht_cost_ns::planXYTheta(start,goal,config,valid);
  EXPECT_FALSE(coarse.reached);
  config.headings=32;
  const auto fine=ht_cost_ns::planXYTheta(start,goal,config,valid);
  ASSERT_TRUE(fine.reached);ASSERT_GT(fine.poses.size(),1u);
  for(size_t i=1;i<fine.poses.size();++i) EXPECT_TRUE(valid(fine.poses[i-1],fine.poses[i],0));
  config.turn_angles={ht_cost_ns::kPi/16,ht_cost_ns::kPi/8};
  const auto mixed=ht_cost_ns::planXYTheta(start,goal,config,valid);
  ASSERT_TRUE(mixed.reached);
  for(size_t i=1;i<mixed.poses.size();++i) EXPECT_TRUE(valid(mixed.poses[i-1],mixed.poses[i],0));
}

TEST_F(HtRosTest, ReversibleMotionRejectsAOneWayEntranceWithoutChangingRawScores) {
  rclcpp::NodeOptions options;
  options.parameter_overrides({rclcpp::Parameter("ht_enabled",true),
    rclcpp::Parameter("ht_directions_calibrated",true),
    rclcpp::Parameter("ht_topic","/ht_test_map"),
    rclcpp::Parameter("ht_require_reversible_motion",true),
    rclcpp::Parameter("ht_map_timeout",2.0)});
  auto guarded_node=std::make_shared<rclcpp::Node>("ht_reversible_test",options);
  ht_cost_ns::HtCostMap guarded(guarded_node,false);
  auto map=grid();
  for(int k=0;k<8;++k)map["ht_dir_"+std::to_string(k)].setConstant(.8f);
  // A car can enter this predicted one-way corridor under the old rule,
  // but cannot retrace it while preserving its body heading.
  map["ht_dir_4"].setConstant(.2f);
  auto load=[&]() {
    map.setTimestamp(node->now().nanoseconds());pub->publish(*grid_map::GridMapRosConverter::toMessage(map));
    const auto until=std::chrono::steady_clock::now()+150ms;
    do {rclcpp::spin_some(node);rclcpp::spin_some(guarded_node);std::this_thread::sleep_for(5ms);}
    while(std::chrono::steady_clock::now()<until);
    ht->beginCycle();guarded.beginCycle();
  };
  load();ASSERT_TRUE(guarded.ready());
  const ht_cost_ns::Pose2 a{0,0,0},b{.4,0,0};
  EXPECT_TRUE(ht->permits(ht->motionSupport(a,b)));
  EXPECT_FALSE(ht->permits(ht->motionSupport(b,a)));
  EXPECT_EQ(guarded.poseSupport(0,0,0),ht_cost_ns::Support::KNOWN);
  EXPECT_EQ(guarded.support({0,0,0},{.4,0,0}),ht_cost_ns::Support::KNOWN);
  EXPECT_EQ(guarded.support({.4,0,0},{0,0,0}),ht_cost_ns::Support::BLOCKED);
  EXPECT_EQ(guarded.motionSupport(a,b),ht_cost_ns::Support::BLOCKED);
  EXPECT_EQ(guarded.motionSupport(b,a),ht_cost_ns::Support::BLOCKED);
  map["ht_dir_4"].setConstant(.8f);load();
  EXPECT_EQ(guarded.motionSupport(a,b),ht_cost_ns::Support::KNOWN);
  EXPECT_EQ(guarded.motionSupport(b,a),ht_cost_ns::Support::KNOWN);
  EXPECT_EQ(guarded.motionSupport(a,{0,0,.3}),ht_cost_ns::Support::KNOWN);
  // The extra check does not waive an original low-probability rejection.
  map["ht_dir_0"].setConstant(.2f);load();
  EXPECT_EQ(guarded.motionSupport(a,b),ht_cost_ns::Support::BLOCKED);
}

TEST_F(HtRosTest, CapturedHeadingBoundaryHasPlanningReserveWithoutRelaxingMeasuredRoot) {
  const char* filename=std::getenv("HT_BOUNDARY_FIXTURE");
  if(!filename) GTEST_SKIP()<<"Set HT_BOUNDARY_FIXTURE to the recorded84.262s crossing";
  ht_cost_ns::Pose2 root;auto map=capturedGrid(filename,root);
  map.setTimestamp(node->now().nanoseconds());send(map);ASSERT_TRUE(ht->ready());
  const auto allowed=[&](ht_cost_ns::Pose2 p){return ht->permits(ht->poseSupport(p.x,p.y,p.yaw));};
  ASSERT_TRUE(allowed(root));
  auto crossed=root;crossed.yaw+=.0003;
  EXPECT_FALSE(allowed(crossed));
  // The observed root has no *extra* reserve. It is still a legal measured
  // state under the unchanged0.5threshold, so the initial check must pass.
  EXPECT_TRUE(ht_cost_ns::successorHeadingReserve(root,root,root,.05,allowed));
  auto near=root;near.yaw-=.001;
  EXPECT_TRUE(allowed(near));
  EXPECT_FALSE(ht_cost_ns::successorHeadingReserve(root,root,near,.05,allowed));
  auto inward=root;inward.yaw-=ht_cost_ns::kPi/16;
  EXPECT_TRUE(ht->permits(ht->motionSupport(root,inward)));
  EXPECT_TRUE(ht_cost_ns::successorHeadingReserve(root,root,inward,.05,allowed));
  // Already forbidden terrain is never made valid by the root exception.
  EXPECT_FALSE(ht->permits(ht->motionSupport(crossed,crossed)));
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
  EXPECT_EQ(ht->support({}, {.1,0,0}),ht_cost_ns::Support::STARTUP_PRIOR);
  EXPECT_FALSE(ht->knownSegment({}, {.1,0,0}));
  EXPECT_NEAR(ht->cost({}, {.1,0,0}),.1,1e-5);
  // With0.25m cells, the actual raster footprint at x=.3 touches the cell
  // (1.125,.625), outside the1.2m prior. The former smaller res/2 scan missed
  // that unknown cell despite the precomputed footprint declaring it unknown.
  EXPECT_EQ(ht->support({}, {.3,0,0}),ht_cost_ns::Support::UNKNOWN);
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
  EXPECT_TRUE(ht->permits(ht->support({}, {.1,0,0})));
  EXPECT_FALSE(ht->permits(ht->support({}, {.3,0,0})));
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

TEST_F(HtConfigurationRosTest, FrozenPostfilterStopResolutionAudit) {
  const char* filename=std::getenv("HT_FIELD11_FIXTURE");ASSERT_NE(filename,nullptr);
  std::ifstream file(filename);int rows,cols;double res,cx,cy;ht_cost_ns::Pose2 root;
  ASSERT_TRUE(bool(file>>rows>>cols>>res>>cx>>cy>>root.x>>root.y>>root.yaw));
  std::vector<float> values(rows*cols*11);for(auto& v:values)ASSERT_TRUE(bool(file>>v));
  grid_map::GridMap map;map.setFrameId("map");map.setGeometry(grid_map::Length(rows*res,cols*res),res,grid_map::Position(cx,cy));
  const std::vector<std::string> names={"ht_dir_0","ht_dir_1","ht_dir_2","ht_dir_3","ht_dir_4","ht_dir_5","ht_dir_6","ht_dir_7","ht_valid","ht_observation_valid","ht_obstacle"};
  for(const auto& name:names)map.add(name);
  for(grid_map::GridMapIterator it(map);!it.isPastEnd();++it) {
    grid_map::Position p;map.getPosition(*it,p);const int r=std::floor(rows*.5-(p.x()-cx)/res),c=std::floor(cols*.5-(p.y()-cy)/res);
    ASSERT_GE(r,0);ASSERT_LT(r,rows);ASSERT_GE(c,0);ASSERT_LT(c,cols);
    for(size_t k=0;k<11;++k)map.at(names[k],*it)=values[(r*cols+c)*11+k];
  }
  map.setTimestamp(node->now().nanoseconds());send(map);ASSERT_TRUE(ht->ready());
  ASSERT_TRUE(ht->permits(ht->poseSupport(root.x,root.y,root.yaw)));
  struct Profile {const char* name;int headings;double cell,step,budget;};
  for(const auto& profile:std::vector<Profile>{{"current",32,.3,.4,.7},{"fine_xy",32,.1,.2,.7},{"fine_h",64,.1,.2,.7},{"small_step",64,.05,.1,.7},{"longer_budget",32,.3,.4,2.}}) {
    ht_cost_ns::XYThetaConfig config;config.headings=profile.headings;config.cell=profile.cell;config.drive_step=profile.step;
    config.turn_angles={ht_cost_ns::kPi/16,ht_cost_ns::kPi/8};config.max_search_seconds=profile.budget;config.max_expansions=80000;
    config.max_radius=5.;config.goal_radius=.4;
    for(double radius:{.8,2.})for(int k=0;k<8;++k) {
      const ht_cost_ns::Point goal{root.x+radius*std::cos(k*ht_cost_ns::kPi/4),root.y+radius*std::sin(k*ht_cost_ns::kPi/4),0};
      int rejects=0;auto valid=[&](ht_cost_ns::Pose2 a,ht_cost_ns::Pose2 b,double){const bool ok=ht->permits(ht->motionSupport(a,b));rejects+=!ok;return ok;};
      const auto began=std::chrono::steady_clock::now();const auto plan=ht_cost_ns::planXYTheta(root,goal,config,valid);
      const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-began).count();
      std::cout<<"QUERY "<<profile.name<<" radius="<<radius<<" bearing="<<k<<" reached="<<plan.reached<<" expanded="<<plan.expanded<<" rejects="<<rejects<<" elapsed_s="<<elapsed<<" poses="<<plan.poses.size()<<std::endl;
    }
  }
}
