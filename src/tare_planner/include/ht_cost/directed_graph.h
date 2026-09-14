#pragma once
#include <algorithm>
#include <cmath>
#include <functional>
#include <limits>
#include <queue>
#include <vector>

namespace ht_cost_ns {
inline double shortestPath(const std::vector<std::vector<int>>& graph,
                           const std::vector<std::vector<double>>& weights,
                           int start, int goal, std::vector<int>& path) {
  path.clear();
  const double inf=std::numeric_limits<double>::infinity();
  if (start<0 || goal<0 || start>=static_cast<int>(graph.size()) ||
      goal>=static_cast<int>(graph.size()) || weights.size()!=graph.size()) return inf;
  std::vector<double> distance(graph.size(),inf);
  std::vector<int> parent(graph.size(),-1);
  using Item=std::pair<double,int>;
  std::priority_queue<Item,std::vector<Item>,std::greater<Item>> queue;
  distance[start]=0; queue.emplace(0,start);
  while (!queue.empty()) {
    auto [d,u]=queue.top(); queue.pop();
    if (d!=distance[u]) continue;
    if (u==goal) break;
    if (graph[u].size()!=weights[u].size()) return inf;
    for (size_t i=0;i<graph[u].size();++i) {
      const int v=graph[u][i]; const double w=weights[u][i];
      if (v<0 || v>=static_cast<int>(graph.size()) || !std::isfinite(w) || w<0) continue;
      if (d+w<distance[v]) {
        distance[v]=d+w; parent[v]=u; queue.emplace(distance[v],v);
      }
    }
  }
  if (!std::isfinite(distance[goal])) return inf;
  for (int u=goal;u!=-1;u=parent[u]) path.push_back(u);
  std::reverse(path.begin(),path.end());
  return distance[goal];
}
}
