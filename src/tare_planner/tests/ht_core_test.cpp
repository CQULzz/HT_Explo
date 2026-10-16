#include "ht_cost/ht_cost_core.h"
#include "ht_cost/execution_policy.h"
#include "ht_cost/directed_graph.h"
#include "ht_cost/grid_edge_support.h"
#include "ht_cost/xytheta_planner.h"
#include "ht_cost/target_commitment.h"
#include "ht_cost/exploration_progress.h"
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
  ExecutionFailureMemory failures;
  failures.add({0,0,0},{.1,0,0},10);
  check(!failures.permits({-.1,0,0},{.2,0,0},11));
  check(failures.permits({.2,0,kPi},{-.1,0,kPi},11)); // Reverse direction is distinct.
  check(failures.permits({0,.3,0},{.1,.3,0},11));
  check(failures.permits({0,0,0},{.1,0,0},16)); // New data can restore the edge.
  failures.add({0,0,0},{0,0,.2},20);
  check(!failures.permits({0,0,0},{0,0,.2},21));
  check(failures.permits({0,0,kPi},{0,0,kPi-.2},21));
  TargetCommitment commitment;
  commitment.commit({4,0,0},{0,0,0},1);
  commitment.observe({0,0,0},5);check(commitment.active);
  // Re-evaluating the same world target must not renew the stall deadline.
  commitment.commit({4,0,0},{0,0,0},10);
  commitment.observe({0,0,0},13);check(!commitment.active);
  check(commitment.cooling({4.3,0,0},14));
  check(!commitment.cooling({4,0,0},34));
  commitment.commit({4,0,0},{0,0,0},35);
  commitment.observe({1,0,0},45);check(commitment.active);
  commitment.observe({1,0,0},55);check(commitment.active);
  commitment.observe({3.6,0,0},56);check(!commitment.active);
  commitment.commit({8,0,0},{4,0,0},60);
  commitment.reject(61);check(!commitment.active);check(commitment.cooling({8,0,0},62));
  // Completing many short goals cannot hide a stalled global destination.
  GuideProgress guide;
  check(guide.select({20,0,0},{0,0,0},0));
  for (int t=1;t<=61;++t) {
    commitment.commit({0,1,0},{0,0,0},t);
    commitment.observe({0,1,0},t);
    const auto event=guide.observe({0,t%2?0.0:1.0,0},t,true);
    check(event==(t==61?GuideProgress::Event::Stalled:GuideProgress::Event::None));
  }
  check(!guide.active);check(guide.cooling({21,0,0},62));
  check(!guide.select({20.5,0,0},{0,0,0},62));
  check(guide.select({0,20,0},{0,0,0},62));
  check(!guide.cooling({20,0,0},242));
  // A nearby replacement grid index must not reset the same guide's timer.
  guide.observe({0,0,0},63,true);guide.observe({0,0,0},64,true);
  const double idle=guide.idle_seconds;
  check(guide.select({0,20.5,0},{0,0,0},64));near(guide.idle_seconds,idle);
  guide.observe({0,1,0},65,true);near(guide.idle_seconds,0);
  guide.observe({0,1,0},66,true);near(guide.idle_seconds,1);
  guide.observe({0,1,0},67,false);guide.observe({0,1,0},100,true);
  near(guide.idle_seconds,1);guide.observe({0,1,0},101,true);near(guide.idle_seconds,2);
  guide.observe({0,1,0},120,true);near(guide.idle_seconds,2); // Missing callbacks do not consume budget.
  guide.observe({0,19.5,0},121,true);check(!guide.active);
  ExplorationVisits visits;
  visits.observe({0.2,0.2,0});const double first=visits.penalty({0.3,0.3,0});
  for(int i=0;i<100;++i) visits.observe({0.2,0.2,0});
  near(visits.penalty({0.3,0.3,0}),first);
  visits.observe({1.2,0.2,0});visits.observe({0.2,0.2,0});
  check(visits.penalty({0.3,0.3,0})>first);near(visits.penalty({5,5,0}),0);
  // A longer route and repeated visits must never improve zero-gain score.
  check(transitScore(-2,first,4)>transitScore(-2,first,12));
  check(transitScore(1,0,4)>transitScore(1,first,4));
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
  std::vector<std::vector<int>> graph{{1,2},{0,2},{0,1}};
  std::vector<int> path;
  near(shortestPath(graph,{{1,4},{9,1},{1,9}},0,2,path),2);
  check(path==std::vector<int>({0,1,2}));
  near(shortestPath(graph,{{1,4},{9,1},{1,9}},2,0,path),1);
  check(path==std::vector<int>({2,0}));
  check(std::isinf(shortestPath({{},{}},{{},{}},0,1,path)) && path.empty());
  near(shortestPath(graph,{{1,4},{9,1},{1,9}},1,1,path),0);
  check(path==std::vector<int>({1}));
  StartupPrior prior;
  check(!prior.contains(0,0));prior.initialize({0,0,0},10);
  check(prior.contains(1,0));prior.initialize({10,0,0},11);
  check(!prior.contains(10,0)); // Starting at the origin must not reset the anchor.
  prior.update({1.3,0,0},11);check(!prior.contains(0,0));
  prior.update({0,0,0},12);check(!prior.contains(0,0));
  StartupPrior expired;expired.initialize({},10);expired.update({},40);check(!expired.contains(0,0));
  FallbackBudget budget;budget.max_seconds=2;budget.max_distance=1;
  budget.update(0,{},false);budget.update(1,{0.6,0,0},true);check(!budget.exhausted());
  budget.update(10,{5,0,0},false);near(budget.seconds,1);near(budget.distance,0.6);
  budget.update(11,{5.5,0,0},true);check(budget.exhausted());
  budget.update(12,{5.5,0,0},false);check(budget.exhausted());
  HomeCompletion home;
  check(!home.update(0,true,true,2,0)); // Stopping away from home is not completion.
  check(!home.update(1,false,true,0,0));
  check(!home.update(2,true,true,0.2,0.1)); // Must actually stop.
  check(!home.update(3,true,true,0.2,0));
  check(!home.update(4,true,false,0.2,0)); // Sensor failure resets dwell.
  check(!home.update(5,true,true,0.2,0));
  check(home.update(6,true,true,0.2,0));
  auto known=[](Point,Point) {return Support::KNOWN;};
  auto allow=[](Support s) {return s!=Support::FAULT;};
  auto free=[](Point) {return true;};
  check(!checkedLookahead({},std::vector<Point>{},.3,2,.5,free,known,allow).valid);
  check(!checkedLookahead({},std::vector<Point>{{0,0,0}},.3,2,.5,free,known,allow).valid);
  const std::vector<Point> bent{{1,0,0},{1,1,0},{0,1,0}};
  auto turn_target=checkedLookahead({},bent,.3,2,.5,free,known,allow);
  check(turn_target.valid);near(turn_target.point.x,1);near(turn_target.point.y,0);
  const std::vector<Point> straight{{.4,0,0},{1,0,0},{3,0,0}};
  auto straight_target=checkedLookahead({},straight,.3,2,.5,free,known,allow);
  check(straight_target.valid);near(straight_target.point.x,2);near(straight_target.point.y,0);
  auto checked_wall=[](Point p) {return p.x<.85;};
  auto before_wall=checkedLookahead({},straight,.3,2,.5,checked_wall,known,allow);
  check(before_wall.valid);check(before_wall.point.x<.85);
  auto wall=[](Point p) {return p.x<.2;};
  check(!checkedLookahead({},bent,.3,2,.5,wall,known,allow).valid);
  auto unknown=[](Point,Point) {return Support::UNKNOWN;};
  auto degraded=checkedLookahead({},bent,.3,2,.5,free,unknown,allow);
  check(degraded.valid);near(degraded.point.x,.5);
  auto straight_unknown=checkedLookahead({},straight,.3,2,.5,free,unknown,allow);
  check(straight_unknown.valid);near(straight_unknown.point.x,.5);
  auto strict=[](Support s) {return s==Support::KNOWN || s==Support::STARTUP_PRIOR;};
  check(!checkedLookahead({},bent,.3,2,.5,free,unknown,strict).valid);
  ReturnProgress back;back.checkpoints={{1,0,0},{0,0,0}};
  back.advance({1.2,0,0},.3);check(back.next==1);
  back.advance({.6,0,0},.3);check(back.next==1); // Must not resurrect the passed x=1 anchor.
  back.advance({.2,0,0},.3);check(back.next==2);
  XYThetaConfig cfg;cfg.max_search_seconds=1.0;
  auto all_valid=[](Pose2,Pose2,double) {return true;};
  auto xy_straight=planXYTheta({0,0,0},{2,0,0},cfg,all_valid);
  check(xy_straight.reached);check(xy_straight.poses.size()>2);
  check(std::hypot(xy_straight.poses.back().x-2,xy_straight.poses.back().y)<cfg.goal_radius);
  for (size_t i=1;i<xy_straight.poses.size();++i)
    check(std::hypot(xy_straight.poses[i].x-xy_straight.poses[i-1].x,
                     xy_straight.poses[i].y-xy_straight.poses[i-1].y)<=0.101);
  auto xy_reverse=planXYTheta({0,0,0},{-1,0,0},cfg,all_valid);
  check(xy_reverse.reached);check(xy_reverse.poses.back().x<-.6);
  auto blocked=[](Pose2,Pose2 p,double) {return !(p.x>.6 && p.x<1.4 && std::abs(p.y)<.55);};
  auto detour=planXYTheta({0,0,0},{2,0,0},cfg,blocked);
  check(detour.reached);
  for (const auto& p:detour.poses) check(!(p.x>.6 && p.x<1.4 && std::abs(p.y)<.55));
  std::cout<<"PASS: "<<checks<<" HT core checks\n";
}
