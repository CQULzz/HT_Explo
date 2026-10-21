#include "ht_cost/input_pose_buffer.h"
#include "ht_cost/xytheta_planner.h"
#include <gtest/gtest.h>
#include <limits>

using namespace ht_cost_ns;
TEST(InputPose, InvalidQuaternionsAndNonfiniteCoordinatesAreRejected) {
  InputPose p{1,{0,0,0},{0,0,0,1}};EXPECT_TRUE(validInputPose(p));
  p.q={0,0,0,0};EXPECT_FALSE(validInputPose(p));
  p.q={0,0,0,2};EXPECT_FALSE(validInputPose(p));
  p.q={0,0,0,1};p.xyz[0]=NAN;EXPECT_FALSE(validInputPose(p));
  p.xyz[0]=0;p.stamp=0;EXPECT_FALSE(validInputPose(p));
}
TEST(InputPose, ScanTimeInterpolationPreservesGeometryAcrossYawWrap) {
  InputPoseBuffer b;
  const double a=179*kPi/180,c=-179*kPi/180;
  ASSERT_TRUE(b.add({10,{1,2,3},{0,0,std::sin(a/2),std::cos(a/2)}}));
  ASSERT_TRUE(b.add({10.08,{3,4,5},{0,0,std::sin(c/2),std::cos(c/2)}}));
  auto mid=b.at(10.04,.05);ASSERT_TRUE(mid);
  EXPECT_NEAR(mid->xyz[0],2,1e-9);EXPECT_NEAR(mid->xyz[2],4,1e-9);
  EXPECT_NEAR(std::abs(mid->q[2]),1,1e-8);EXPECT_NEAR(mid->q[3],0,1e-8);
  EXPECT_FALSE(b.at(11,.05));EXPECT_FALSE(b.at(9,.05));
}
TEST(InputPose, GapsAndOutOfOrderPacketsCannotMutateTheLatestPose) {
  InputPoseBuffer b;ASSERT_TRUE(b.add({10,{0,0,0},{0,0,0,1}}));
  EXPECT_FALSE(b.add({9,{5,0,0},{0,0,0,1}}));
  EXPECT_FALSE(b.add({10,{9,0,0},{0,0,0,1}}));
  ASSERT_TRUE(b.add({10.5,{.1,0,0},{0,0,0,1}}));
  EXPECT_FALSE(b.at(10.25,.05));EXPECT_DOUBLE_EQ(b.latestStamp(),10.5);
}
TEST(InputPose, DetectsLargePoseJumpsWithoutTreatingQuaternionSignAsAJump) {
  InputPoseBuffer b;b.add({10,{0,0,0},{0,0,0,1}});
  EXPECT_FALSE(b.jump({10.02,{.01,0,0},{0,0,0,-1}}));
  EXPECT_TRUE(b.jump({10.02,{2,0,0},{0,0,0,1}}));
  EXPECT_TRUE(b.jump({10.02,{0,0,0},{0,0,1,0}}));
}
TEST(CommandInterval, UsesElapsedPublishTimeAndCapsLongGapsConservatively) {
  CommandInterval timer;EXPECT_DOUBLE_EQ(timer.elapsed(1),0);
  timer.published(1);EXPECT_NEAR(timer.elapsed(1.01),.01,1e-12);
  EXPECT_NEAR(timer.elapsed(1.04),.04,1e-12);
  EXPECT_DOUBLE_EQ(timer.elapsed(2),.05);EXPECT_DOUBLE_EQ(timer.elapsed(.5),0);
  // Candidate formed at1.01, published at1.03: a<=limit at publication too.
  const double delta=.5*timer.elapsed(1.01);
  EXPECT_LE(delta/(1.03-1),.5);
  timer.published(1.03);EXPECT_NEAR(timer.elapsed(1.04),.01,1e-12);
}
TEST(PlannerInput, RejectsAllNonfiniteAndNonpositivePlanningScalesBeforeCallingValidity) {
  const double invalid[]={NAN,INFINITY,0,-1};
  for(int field=0;field<8;++field)for(double value:invalid) {
    XYThetaConfig c;
    double* fields[]={&c.cell,&c.drive_step,&c.forward_speed,&c.reverse_speed,
                     &c.max_yaw_rate,&c.goal_radius,&c.max_radius,&c.max_search_seconds};
    *fields[field]=value;bool called=false;
    auto plan=planXYTheta({0,0,0},{1,0,0},c,[&](Pose2,Pose2,double){called=true;return true;});
    EXPECT_EQ(plan.termination,XYThetaTermination::INVALID_INPUT);EXPECT_FALSE(called);
  }
  EXPECT_TRUE(std::isnan(wrapYaw(INFINITY)));EXPECT_TRUE(std::isfinite(wrapYaw(1e300)));
}
