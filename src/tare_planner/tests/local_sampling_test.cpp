#include <gtest/gtest.h>
#include "local_coverage_planner/local_coverage_planner.h"
#include <set>

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
