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
  explicit SamplingFixture(std::int64_t seed=-1) {
    if (!rclcpp::ok()) rclcpp::init(0,nullptr);
    rclcpp::NodeOptions options;
    options.arguments({"--ros-args","--params-file",HT_SOURCE_ROOT "/config/indoor.yaml"});
    options.parameter_overrides({rclcpp::Parameter("ht_enabled",false),
      rclcpp::Parameter("tare_sampling_seed",seed),
      rclcpp::Parameter("kMinAddPointNumSmall",40),
      rclcpp::Parameter("kMinAddFrontierPointNum",15),
      rclcpp::Parameter("kGreedyViewPointSampleRange",3)});
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

TEST(TareResidualSampling, NeverChoosesAViewWhoseUpdatedGainIsBelowThreshold) {
  ::testing::FLAGS_gtest_death_test_style="threadsafe";
  EXPECT_EXIT({
    std::thread([] {std::this_thread::sleep_for(std::chrono::seconds(15));std::_Exit(124);}).detach();
    // Different first draws exercise every branch, including shrinking the
    // eligible prefix to one while a below-threshold entry remains allocated.
    for (int seed=0;seed<32;++seed) {
      SamplingFixture f(seed);
      for (int id=0;id<3;++id) f.manager->ResetViewPointCoveredPointList(id);
      for (int p=0;p<80;++p) f.manager->AddUncoveredPoint(0,p);
      for (int p=0;p<40;++p) f.manager->AddUncoveredPoint(1,p);
      for (int p=80;p<120;++p) f.manager->AddUncoveredPoint(1,p);
      for (int p=0;p<70;++p) f.manager->AddUncoveredPoint(2,p);
      for (int p=120;p<130;++p) f.manager->AddUncoveredPoint(2,p);
      const auto selected=LocalCoveragePlannerTestAccess::select(
        *f.planner,{{80,0},{80,1},{80,2}},130);
      std::vector<bool> observed(130,false);
      for (const int id:selected) {
        if (id<0 || id>=3) std::_Exit(2);
        int gain=0;
        for (const int p:f.manager->GetViewPointCoveredPointList(id))
          if (!observed[p]) ++gain;
        if (gain<40) std::_Exit(3);
        for (const int p:f.manager->GetViewPointCoveredPointList(id)) observed[p]=true;
      }
      if (selected.size()!=2) std::_Exit(4);
    }
    std::_Exit(0);
  },::testing::ExitedWithCode(0),"");
}

TEST(TareResidualSampling, DisjointEligibleViewsAreSelectedExactlyOnce) {
  ::testing::FLAGS_gtest_death_test_style="threadsafe";
  EXPECT_EXIT({
    std::thread([] {std::this_thread::sleep_for(std::chrono::seconds(5));std::_Exit(124);}).detach();
    SamplingFixture f(42);
    for (int id=0;id<3;++id) {
      f.manager->ResetViewPointCoveredPointList(id);
      for (int p=0;p<80;++p) f.manager->AddUncoveredPoint(id,80*id+p);
    }
    const auto selected=LocalCoveragePlannerTestAccess::select(
      *f.planner,{{80,0},{80,1},{80,2}},240);
    const std::set<int> unique(selected.begin(),selected.end());
    std::_Exit(selected.size()==3 && unique==std::set<int>({0,1,2}) ? 0:5);
  },::testing::ExitedWithCode(0),"");
}
