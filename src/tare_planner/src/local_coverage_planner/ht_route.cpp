#include "local_coverage_planner/local_coverage_planner.h"
#include "tsp_solver/tsp_solver.h"
#include <limits>

namespace local_coverage_planner_ns {
exploration_path_ns::ExplorationPath LocalCoveragePlanner::SolveHTTSP(
    const std::vector<int>& selected,std::vector<int>& ordered) {
  using namespace operations_research;
  using namespace exploration_path_ns;
  ExplorationPath result;
  ordered.clear();
  ht_last_cost_=std::numeric_limits<double>::infinity();
  if (!viewpoint_manager_->HT()->ready()) return result;
  std::vector<int> ids{robot_viewpoint_ind_};
  for (int id:selected)
    if (std::find(ids.begin(),ids.end(),id)==ids.end()) ids.push_back(id);
  // Preserve a global-boundary endpoint, but always execute from the robot.
  int end_id=start_viewpoint_ind_!=robot_viewpoint_ind_ ? start_viewpoint_ind_ : end_viewpoint_ind_;
  if (end_id<0) end_id=robot_viewpoint_ind_;
  if (std::find(ids.begin(),ids.end(),end_id)==ids.end()) ids.push_back(end_id);
  const int n=static_cast<int>(ids.size());
  const int end=static_cast<int>(std::find(ids.begin(),ids.end(),end_id)-ids.begin());
  std::vector<std::vector<double>> cost(n,std::vector<double>(n,0));
  std::vector<std::vector<nav_msgs::msg::Path>> paths(n,std::vector<nav_msgs::msg::Path>(n));
  for (int i=0;i<n;++i) for (int j=0;j<n;++j) {
    cost[i][j]=viewpoint_manager_->GetHTShortestPath(ids[i],ids[j],paths[i][j]);
    // Do not turn missing graph connections into zero-length routes.
    if (!std::isfinite(cost[i][j]) || cost[i][j]>1e9) return result;
  }
  RoutingIndexManager manager(n,1,
    std::vector<RoutingIndexManager::NodeIndex>{RoutingIndexManager::NodeIndex(0)},
    std::vector<RoutingIndexManager::NodeIndex>{RoutingIndexManager::NodeIndex(end)});
  RoutingModel routing(manager);
  const int callback=routing.RegisterTransitCallback([&](int64_t from,int64_t to)->int64_t {
    return static_cast<int64_t>(std::llround(1000*cost[manager.IndexToNode(from).value()]
                                                   [manager.IndexToNode(to).value()]));
  });
  routing.SetArcCostEvaluatorOfAllVehicles(callback);
  auto parameters=DefaultRoutingSearchParameters();
  parameters.set_first_solution_strategy(FirstSolutionStrategy::PATH_CHEAPEST_ARC);
  parameters.mutable_time_limit()->set_nanos(200000000);
  const Assignment* solution=routing.SolveWithParameters(parameters);
  if (!solution) return result;
  std::vector<int> route;
  int64_t index=routing.Start(0);
  while (!routing.IsEnd(index)) {
    route.push_back(manager.IndexToNode(index).value());
    index=solution->Value(routing.NextVar(index));
  }
  route.push_back(manager.IndexToNode(index).value());
  Node first(viewpoint_manager_->GetViewPointPosition(ids[0]),NodeType::ROBOT);
  first.local_viewpoint_ind_=ids[0];
  result.Append(first);
  ordered.push_back(ids[0]);
  ht_last_cost_=0;
  for (size_t i=1;i<route.size();++i) {
    const int a=route[i-1],b=route[i];
    ht_last_cost_+=cost[a][b];
    const auto& path=paths[a][b];
    for (size_t j=1;j<path.poses.size();++j) {
      const bool endpoint=j+1==path.poses.size();
      Node node(path.poses[j].pose.position,endpoint ? NodeType::LOCAL_VIEWPOINT : NodeType::LOCAL_VIA_POINT);
      node.local_viewpoint_ind_=endpoint ? ids[b] : -1;
      if (endpoint && i+1==route.size())
        node.type_=ids[b]==robot_viewpoint_ind_ ? NodeType::ROBOT : NodeType::LOCAL_PATH_END;
      result.Append(node);
    }
    ordered.push_back(ids[b]);
  }
  return result;
}
}
