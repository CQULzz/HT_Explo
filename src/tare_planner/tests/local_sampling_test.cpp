#include <gtest/gtest.h>
#include "local_coverage_planner/local_coverage_planner.h"
#include <set>
#include <thread>
#include <chrono>
#include <cstdlib>

namespace local_coverage_planner_ns {
struct LocalCoveragePlannerTestAccess {
  static std::int64_t seed(const LocalCoveragePlanner& p) { return p.sampling_seed_; }
  static std::vector<int> select(LocalCoveragePlanner& p,
      const std::vector<std::pair<int,int>>& queue,int point_count,bool frontier=false) {
    std::vector<int> selected;
    p.SelectViewPoint(queue,std::vector<bool>(point_count,false),selected,frontier);
    return selected;
  }
};
}
using local_coverage_planner_ns::LocalCoveragePlanner;
using local_coverage_planner_ns::LocalCoveragePlannerTestAccess;

struct SamplingFixture {
  rclcpp::Node::SharedPtr node;
  std::shared_ptr<viewpoint_manager_ns::ViewPointManager> manager;
  std::unique_ptr<LocalCoveragePlanner> planner;
  explicit SamplingFixture(std::int64_t seed=-1,int window=3) {
    if (!rclcpp::ok()) rclcpp::init(0,nullptr);
    rclcpp::NodeOptions options;
    options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
    options.parameter_overrides({rclcpp::Parameter("ht_enabled",false),
      rclcpp::Parameter("tare_sampling_seed",seed),
      rclcpp::Parameter("kMinAddPointNumSmall",40),
      rclcpp::Parameter("kMinAddFrontierPointNum",15),
      rclcpp::Parameter("kGreedyViewPointSampleRange",window)});
    node=std::make_shared<rclcpp::Node>("tare_planner_node",options);
    for (const auto& entry:node->get_node_parameters_interface()->get_parameter_overrides())
      if (entry.first.rfind("ht_",0)!=0 && !node->has_parameter(entry.first))
        node->declare_parameter(entry.first,entry.second);
    manager=std::make_shared<viewpoint_manager_ns::ViewPointManager>(node);
    planner=std::make_unique<LocalCoveragePlanner>(node);
    planner->SetViewPointManager(manager);
  }
  std::vector<int> repeatedEquivalentChoice(int count) {
    // All viewpoints see the same points: one choice completes this batch,
    // isolating RNG replay from the separately audited shrinking-queue case.
    for (int id=0;id<3;++id) {
      manager->ResetViewPointCoveredPointList(id);
      for (int i=0;i<80;++i) manager->AddUncoveredPoint(id,i);
    }
    std::vector<int> sequence;
    for (int i=0;i<count;++i) {
      auto selected=LocalCoveragePlannerTestAccess::select(*planner,{{80,0},{80,1},{80,2}},80);
      EXPECT_EQ(selected.size(),1u);
      if (!selected.empty()) sequence.push_back(selected.front());
    }
    return sequence;
  }
};

TEST(TareSamplingSeed, SameExplicitSeedReplaysProductionSelectorStream) {
  SamplingFixture a(42),b(42);
  auto first=a.repeatedEquivalentChoice(30),second=b.repeatedEquivalentChoice(30);
  EXPECT_EQ(first,second);
  EXPECT_GT(std::set<int>(first.begin(),first.end()).size(),1u);
}
TEST(TareSamplingSeed, DefaultsRemainUncontrolledAndUint32BoundsAreValidated) {
  SamplingFixture legacy;
  EXPECT_EQ(LocalCoveragePlannerTestAccess::seed(*legacy.planner),-1);
  EXPECT_NO_THROW(SamplingFixture(0));
  EXPECT_NO_THROW(SamplingFixture(4294967295LL));
  EXPECT_THROW(SamplingFixture(-2),std::invalid_argument);
  EXPECT_THROW(SamplingFixture(4294967296LL),std::invalid_argument);
}

TEST(TareSamplingQueue, ShrinkingQueueNeverSamplesAnErasedEntry) {
  ::testing::FLAGS_gtest_death_test_style="threadsafe";
  EXPECT_EXIT({
    std::thread([]{std::this_thread::sleep_for(std::chrono::seconds(5));std::_Exit(124);}).detach();
    SamplingFixture f(42);
    for(int id=0;id<2;++id) {
      f.manager->ResetViewPointCoveredPointList(id);
      for(int i=0;i<80;++i)f.manager->AddUncoveredPoint(id,id*80+i);
    }
    auto selected=LocalCoveragePlannerTestAccess::select(*f.planner,{{80,0},{80,1}},160);
    const std::set<int> unique(selected.begin(),selected.end());
    std::_Exit(selected.size()==2 && unique==std::set<int>({0,1}) ? 0:3);
  },::testing::ExitedWithCode(0),"");
}
TEST(TareSamplingQueue, FrontierRemainderUsesItsOwnAcceptedThreshold) {
  SamplingFixture f(42);
  for(int id=0;id<2;++id) {
    f.manager->ResetViewPointCoveredPointList(id);
    for(int i=0;i<15;++i)f.manager->AddUncoveredFrontierPoint(id,id*15+i);
  }
  auto selected=LocalCoveragePlannerTestAccess::select(*f.planner,{{15,0},{15,1}},30,true);
  EXPECT_EQ(selected.size(),2u);
  EXPECT_EQ(std::set<int>(selected.begin(),selected.end()),std::set<int>({0,1}));
}
TEST(TareSamplingQueue, UpdatedResidualGainBelowThresholdIsNotSampled) {
  ::testing::FLAGS_gtest_death_test_style="threadsafe";
  EXPECT_EXIT({
    std::thread([]{std::this_thread::sleep_for(std::chrono::seconds(5));std::_Exit(124);}).detach();
    SamplingFixture f(9);
    for(int id=0;id<3;++id)f.manager->ResetViewPointCoveredPointList(id);
    for(int i=0;i<80;++i)f.manager->AddUncoveredPoint(0,i);
    for(int i=0;i<40;++i)f.manager->AddUncoveredPoint(1,i);
    for(int i=80;i<120;++i)f.manager->AddUncoveredPoint(1,i);
    for(int i=0;i<70;++i)f.manager->AddUncoveredPoint(2,i);
    for(int i=120;i<130;++i)f.manager->AddUncoveredPoint(2,i);
    auto selected=LocalCoveragePlannerTestAccess::select(*f.planner,{{80,0},{80,1},{80,2}},130);
    std::vector<bool> observed(130,false);
    for(int id:selected) {
      int gain=0;for(int p:f.manager->GetViewPointCoveredPointList(id))if(!observed[p])++gain;
      if(gain<40)std::_Exit(4);
      for(int p:f.manager->GetViewPointCoveredPointList(id))observed[p]=true;
    }
    std::_Exit(selected.size()==2?0:5);
  },::testing::ExitedWithCode(0),"");
}

TEST(TareSamplingQueue, InvalidSamplingWindowFailsBeforePlanning) {
  EXPECT_THROW(SamplingFixture(42,0),std::invalid_argument);
}
