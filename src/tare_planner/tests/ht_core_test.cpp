#include "ht_cost/ht_cost_core.h"
#include "ht_cost/directed_graph.h"
#include "ht_cost/grid_edge_support.h"
#include <iostream>
#include <stdexcept>
using namespace ht_cost_ns;
int checks=0;
void check(bool condition) {
  ++checks;
  if (!condition) throw std::runtime_error("Failed check "+std::to_string(checks));
}
void near(double a,double b) { check(std::abs(a-b)<1e-5); }
int main() {
  // Garage run 2: the robot at (6.8218, 26.2809) cannot cut through
  // cell (5,22) on its way from center (6.6,25.8) to (7.8,27.0).
  using Cell = std::array<int,3>;
  const Cell anchor{5,21,0}, turn{6,21,0}, next{6,22,0};
  auto supported = [](const Cell& c) {
    return c[0]>=5 && c[0]<=6 && c[1]>=21 && c[1]<=22 && c[2]==0 &&
           c!=Cell{5,22,0};
  };
  check(!gridEdgeSupported(anchor,next,supported));
  check(!gridEdgeSupported(next,anchor,supported));
  check(gridEdgeSupported(anchor,turn,supported));
  check(gridEdgeSupported(turn,next,supported));
  check(!gridEdgeSupported(anchor,Cell{7,21,0},supported));
  auto open = [](const Cell&) { return true; };
  check(gridEdgeSupported(anchor,next,open));
  check(gridEdgeSupported(Cell{0,0,0},Cell{1,1,1},open));
  check(!gridEdgeSupported(Cell{0,0,0},Cell{1,1,1},
                          [](const Cell& c) { return c!=Cell{1,0,1}; }));
  check(!gridEdgeSupported(anchor,turn,[](const Cell&) { return false; }));
  std::vector<Cell> cells{anchor,turn,next};
  std::vector<std::vector<int>> supported_graph(3);
  std::vector<std::vector<double>> supported_weights(3);
  for (int i=0;i<3;++i) for (int j=0;j<3;++j) {
    if (i!=j && gridEdgeSupported(cells[i],cells[j],supported)) {
      supported_graph[i].push_back(j);
      supported_weights[i].push_back(std::hypot(cells[i][0]-cells[j][0],cells[i][1]-cells[j][1]));
    }
  }
  std::vector<int> safe_path;
  near(shortestPath(supported_graph,supported_weights,0,2,safe_path),2);
  check(safe_path==std::vector<int>({0,1,2}));

  // Regression: CMU stopped 0.163 m from a vertex while HT kept targeting it.
  check(waypointReached({0.50818896,0.46558198,0.75},{0.6,0.6,0.76019478},0.3));
  check(waypointReached({0,0,0},{0.3,0,0},0.3));
  check(waypointReached({0,0,0},{0.1,0,1.0},0.3));
  check(!waypointReached({0,0,0},{0.4,0,0},0.3));
  Map m; m.rows=20;m.cols=20;m.resolution=0.5;m.stamp=10;
  m.valid.assign(400,1);
  for (int k=0;k<8;++k) m.probabilities[k].assign(400,(k+1)*0.1f);
  check(m.wellFormed());
  for (int k=0;k<8;++k) near(m.sample(0,0,k*kPi/4),(k+1)*0.1);
  near(m.sample(0,0,2*kPi),0.1);
  near(m.sample(0,0,-kPi/4),0.8);
  check(std::isnan(m.sample(6,0,0)));
  check(m.fresh(10.5,1));check(!m.fresh(12,1));check(!m.fresh(9,1));
  auto f=segment(&m,{-1,0,0},{1,0,0},0.1);
  auto r=segment(&m,{1,0,0},{-1,0,0},0.1);
  near(f.risk,2*-std::log(0.1));near(r.risk,2*-std::log(0.5));
  near(f.risk,segment(&m,{-1,0,0},{1,0,0},0.02).risk);
  near(segment(nullptr,{0,0,0},{2,0,0},0.1).total(1,2),6);
  near(segment(&m,{0,0,0},{0,0,0},0.1).length,0);
  m.yaw=kPi/2;
  near(m.sample(0,0,kPi/2),0.1);
  m.heading_offset=kPi/4;
  near(m.sample(0,0,3*kPi/4),0.1);
  m.channel_order={{7,6,5,4,3,2,1,0}};
  near(m.sample(0,0,3*kPi/4),0.8);
  m.yaw=0;m.heading_offset=0;m.channel_order={{0,1,2,3,4,5,6,7}};
  m.probabilities[0][0]=0.99;
  near(m.sample(4.75,4.75,0),0.99);
  m.center_x=10;m.center_y=20;m.yaw=kPi/2;
  near(m.sample(5.25,24.75,kPi/2),0.99);
  m.valid[0]=0;check(std::isnan(m.sample(5.25,24.75,kPi/2)));
  m.valid[0]=1;m.probabilities[0][0]=2;
  check(std::isnan(m.sample(5.25,24.75,kPi/2)));
  bool threw=false;
  try {segment(&m,{},{1,0,0},0);} catch(const std::invalid_argument&) {threw=true;}
  check(threw);
  std::vector<std::vector<int>> graph{{1,2},{0,2},{0,1}};
  std::vector<int> path;
  near(shortestPath(graph,{{1,4},{9,1},{1,9}},0,2,path),2);
  check(path==std::vector<int>({0,1,2}));
  near(shortestPath(graph,{{1,4},{9,1},{1,9}},2,0,path),1);
  check(path==std::vector<int>({2,0}));
  check(std::isinf(shortestPath({{},{}},{{},{}},0,1,path)) && path.empty());
  near(shortestPath(graph,{{1,4},{9,1},{1,9}},1,1,path),0);
  check(path==std::vector<int>({1}));
  // A: 2 m at P=.2; B: 3 m at P=.9. Higher HT weight selects B.
  auto a=Cost{2,2*-std::log(.2),0,true};
  auto b=Cost{3,3*-std::log(.9),0,true};
  check(a.total(0,2)<b.total(0,2));
  check(a.total(1,2)>b.total(1,2));
  std::cout<<"PASS: "<<checks<<" HT core checks\n";
}
