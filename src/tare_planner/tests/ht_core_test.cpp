#include "ht_cost/ht_cost_core.h"
#include "ht_cost/execution_policy.h"
#include "ht_cost/directed_graph.h"
#include "ht_cost/grid_edge_support.h"
#include "ht_cost/xytheta_planner.h"
#include "ht_cost/target_commitment.h"
#include "ht_cost/exploration_progress.h"
#include "ht_cost/heading_reserve.h"
#include "ht_cost/search_schedule.h"
#include "ht_cost/tare_waypoint_route.h"
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
  // Upstream rush-home publishes HOME even if native lookahead returns false
  // and leaves the output absent inside its 8/5 m local-short threshold.
  const Point no_lookahead{NAN,NAN,NAN},home_goal{0,0,.75};
  const auto effective=effectiveTareLookahead(no_lookahead,true,home_goal);
  near(effective.x,0);near(effective.y,0);near(effective.z,.75);
  check(!std::isfinite(effectiveTareLookahead(no_lookahead,false,home_goal).x));
  near(effectiveTareLookahead({5,2,.75},true,home_goal).x,0);
  near(effectiveTareLookahead({5,2,.75},false,home_goal).x,5);
  const auto home_goal_branch=tareBranch({{1.2,0,.75},effective},{true,false},home_goal);
  check(home_goal_branch.size()==2);near(tarePrefix(home_goal_branch,4.).x,0);

  // U-shaped native route: a remote target must not be clipped diagonally.
  const std::vector<Point> u{{0,0,0},{0,3,0},{3,3,0},{3,0,0}};
  auto branch=tareBranch(u,{true,false,false,false},{3,0,0});
  check(branch.size()==4);auto prefix=tarePrefix(branch,4.);near(prefix.x,1.);near(prefix.y,3.);
  auto backward=tareBranch({{3,0,0},{3,3,0},{0,3,0},{0,0,0}},
                           {false,false,false,true},{3,0,0});
  check(backward.size()==4);near(tarePrefix(backward,4.).x,1.);
  check(tareBranch(u,{true,false,false,false},{8,8,0}).empty());
  auto loop=tareBranch({{0,0,0},{0,3,0},{3,3,0},{3,0,0},{0,0,0}},
                        {true,false,false,false,true},{3,0,0});
  check(loop.size()==2);near(tarePrefix(loop,1.).x,1.);near(tarePrefix(loop,1.).y,0.);
  check(tareBranch(u,{true},{3,0,0}).empty());

  // Captured garage stop: the TARE anchor is ahead of continuous odometry.
  // Integer prefixes are outside a short supported interval; adaptive
  // candidates must include that interval without changing the branch.
  const Point stopped_robot{12.566203,30.956604,0};
  const std::vector<Point> stopped_branch{{12.970318,31.367440,0},
    {14.170318,32.567440,0},{18.211219,36.625272,0}};
  auto short_support=[](double arc){return arc<=.25;};
  for(double arc:{4.,3.,2.,1.}) check(!short_support(arc));
  const auto short_targets=tareAdaptivePrefixes(stopped_branch,stopped_robot,.1);
  check(!short_targets.empty());near(short_targets.front().arc,0);
  check(short_targets.front().distance>.57 && short_targets.front().distance<.59);
  check(std::any_of(short_targets.begin(),short_targets.end(),[&](const auto& t){return short_support(t.arc);}));
  for(size_t i=0;i<short_targets.size();++i) {
    const auto& t=short_targets[i];const auto expected=tarePrefix(stopped_branch,t.arc);
    near(t.point.x,expected.x);near(t.point.y,expected.y);
    check(t.arc>=0 && t.arc<=4.+1e-9 && t.distance>=.4);
    if(i) check(t.distance+1e-9>=short_targets[i-1].distance);
  }
  // A stale grid anchor behind odometry must not become a reverse target.
  const auto forward_targets=tareAdaptivePrefixes({{0,0,0},{5,0,0}},{.8,0,0},.1);
  check(!forward_targets.empty());
  for(const auto& t:forward_targets) check(t.point.x>=1.2-1e-9);
  // Folded routes retain their actual polyline; no diagonal to the waypoint.
  for(const auto& t:tareAdaptivePrefixes(u,{-.6,0,0},.1)) {
    check((std::abs(t.point.x)<1e-9 && t.point.y>=0 && t.point.y<=3) ||
          (std::abs(t.point.y-3)<1e-9 && t.point.x>=0 && t.point.x<=1));
  }
  check(tareAdaptivePrefixes({},stopped_robot,.1).empty());
  check(tareAdaptivePrefixes(stopped_branch,stopped_robot,0).empty());
  check(tareAdaptivePrefixes(stopped_branch,{NAN,0,0},.1).empty());
  const auto degenerate=tareAdaptivePrefixes({{.6,0,0},{.6,0,0}},{0,0,0},.1);
  check(degenerate.size()==1);near(degenerate.front().arc,0);

  // Captured35s stop: open local recovery behind the vehicle takes thousands
  // of graph validity queries. A checked spin/straight connection reaches it
  // without spending those graph expansions or weakening the predicate.
  XYThetaConfig connector;connector.headings=32;connector.turn_angles={kPi/16,kPi/8};
  connector.goal_radius=.35;connector.max_search_seconds=1;connector.max_expansions=1;
  const Pose2 captured_root{13.107903480529785,5.560585975646973,1.813777685165405};
  const Point captured_goal{12.75,2.85,0};
  auto connector_open=[](Pose2,Pose2,double){return true;};
  check(!planXYTheta(captured_root,captured_goal,connector,connector_open).reached);
  connector.try_direct_connection=true;
  size_t connection_queries=0;
  auto counted_open=[&](Pose2,Pose2,double){++connection_queries;return true;};
  const auto direct=planXYTheta(captured_root,captured_goal,connector,counted_open);
  check(direct.reached && direct.direct_connection && direct.expanded==0);
  check(connection_queries<200);
  for(size_t i=1;i<direct.poses.size();++i) {
    const auto& a=direct.poses[i-1];const auto& b=direct.poses[i];
    const double dx=b.x-a.x,dy=b.y-a.y,d=std::hypot(dx,dy);
    check(d<=.050001);check(std::abs(wrapYaw(b.yaw-a.yaw))<=.050001);
    if(d>1e-9) {
      check(std::abs(wrapYaw(b.yaw-a.yaw))<1e-9);
      check(std::abs(-std::sin(b.yaw)*dx+std::cos(b.yaw)*dy)<1e-9);
    }
  }
  // Reverse is an actual body-axis motion, not a sideways shortcut.
  const auto direct_reverse=planXYTheta({},Point{-1,0,0},connector,connector_open);
  check(direct_reverse.reached && direct_reverse.direct_connection);
  for(const auto& p:direct_reverse.poses) {near(p.y,0);near(p.yaw,0);}
  // A blocked direct line falls back to the existing curved graph search.
  connector.max_expansions=8000;
  auto connector_obstacle=[](Pose2,Pose2 p,double){return !(p.x>.6 && p.x<1.4 && std::abs(p.y)<.55);};
  const auto connector_detour=planXYTheta({},Point{2,0,0},connector,connector_obstacle);
  check(connector_detour.reached && !connector_detour.direct_connection);
  for(const auto& p:connector_detour.poses) check(connector_obstacle({},p,0));
  // Rejected intermediate orientations cannot be jumped over.
  auto sealed_heading=[](Pose2,Pose2 p,double){return std::hypot(p.x,p.y)<1e-9 && std::abs(p.yaw)<.01;};
  check(!planXYTheta({},Point{0,2,0},connector,sealed_heading).reached);
  auto direct_invalid_root=[](Pose2,Pose2,double){return false;};
  check(planXYTheta({},Point{2,0,0},connector,direct_invalid_root).termination==XYThetaTermination::INVALID_START);
  connector.max_search_seconds=1e-12;
  check(planXYTheta({},Point{2,0,0},connector,connector_open).termination==XYThetaTermination::TIME_LIMIT);
  connector.max_search_seconds=1;connector.max_radius=.5;
  check(!planXYTheta({},Point{2,0,0},connector,connector_open).reached);
  // Stage32: each primary search consumes0.15s and fails; a short safe
  // recovery would take0.02s, but the sequential queue never reaches it
  // inside the0.35s cycle. Test scheduling with a deterministic clock.
  auto recoveryWithinBudget=[](const std::vector<std::size_t>& order) {
    double elapsed=0;
    for (auto i:order) {
      const double remaining=.35-elapsed;
      if (remaining<=.001) continue;
      const double cost=i<4?.15:.02;
      if (i>=4 && cost<=remaining) return true;
      elapsed+=std::min(cost,remaining);
    }
    return false;
  };
  check(!recoveryWithinBudget({0,1,2,3,4,5,6,7,8,9,10,11}));
  check(recoveryWithinBudget(targetSearchOrder(12,4,12)));
  check(targetSearchOrder(6,4,4)==std::vector<std::size_t>({0,1,2,3,4,5}));
  check(targetSearchOrder(4,0,4)==std::vector<std::size_t>({0,1,2,3}));
  check(targetSearchOrder(2,0,0)==std::vector<std::size_t>({0,1}));
  check(targetSearchOrder(0,0,0).empty());
  for (std::size_t total=0;total<16;++total)
    for (std::size_t primary=0;primary<=total;++primary)
      for (std::size_t recovery=primary;recovery<=total;++recovery) {
        auto order=targetSearchOrder(total,primary,recovery);
        check(order.size()==total);
        if (primary) check(order.front()==0);  // committed primary remains first
        auto sorted=order;std::sort(sorted.begin(),sorted.end());
        for(std::size_t i=0;i<total;++i) check(sorted[i]==i);
        // Backtrack retains its original tail position and order.
        for(std::size_t i=recovery;i<total;++i) check(order[i]==i);
      }
  bool invalid=false;
  try {targetSearchOrder(2,2,1);} catch(const std::invalid_argument&) {invalid=true;}
  check(invalid);
  // A narrow circular lane needs the old22.5degree arc. Refining the key
  // must not remove that control in favor of only wider11.25degree arcs.
  XYThetaConfig mixed;mixed.headings=32;mixed.goal_radius=.02;
  mixed.max_search_seconds=.1;mixed.turn_angles={kPi/16};
  const double radius=mixed.drive_step/(kPi/8);
  const Point arc_goal{radius*std::sin(kPi/8),radius*(1-std::cos(kPi/8)),0};
  auto narrow_arc=[&](Pose2 a,Pose2 b,double v) {
    if (std::hypot(b.x,b.y)<1e-9 && std::abs(b.yaw)<1e-9) return true;
    if (v<=0 || b.yaw<0 || b.yaw>kPi/8+1e-9) return false;
    (void)a;
    return std::abs(std::hypot(b.x,b.y-radius)-radius)<.001;
  };
  check(!planXYTheta({},arc_goal,mixed,narrow_arc).reached);
  mixed.turn_angles.push_back(kPi/8);
  const auto retained_arc=planXYTheta({},arc_goal,mixed,narrow_arc);
  check(retained_arc.reached);near(retained_arc.seconds,.8);
  mixed.headings=64;
  check(planXYTheta({},arc_goal,mixed,narrow_arc).reached);
  mixed.turn_angles={std::numeric_limits<double>::quiet_NaN()};
  check(!planXYTheta({},arc_goal,mixed,narrow_arc).reached);
  // Captured failure: about0.0003rad of heading drift crossed22.5degrees
  // into a forbidden HT channel. Keep successor headings clear of that edge,
  // while a nominally valid measured root can still turn inward.
  const auto nominal_heading=[](Pose2 p){return std::abs(wrapYaw(p.yaw))<kPi/8;};
  const Pose2 near_boundary{0,0,.39255702495574946};
  check(nominal_heading(near_boundary));
  check(successorHeadingReserve(near_boundary,near_boundary,near_boundary,.05,nominal_heading));
  const Pose2 toward_boundary{0,0,.3926};
  check(nominal_heading(toward_boundary));
  check(!successorHeadingReserve(near_boundary,near_boundary,toward_boundary,.05,nominal_heading));
  const Pose2 inward{0,0,near_boundary.yaw-kPi/16};
  check(successorHeadingReserve(near_boundary,near_boundary,inward,.05,nominal_heading));
  XYThetaConfig heading_config;heading_config.goal_radius=.25;heading_config.max_search_seconds=.3;
  const auto corridor=[&](Pose2 root,Pose2 a,Pose2 b,double) {
    if (!nominal_heading(a)||!nominal_heading(b)||std::abs(b.y-.2*b.x)>.12) return false;
    return successorHeadingReserve(root,a,b,.05,nominal_heading);
  };
  Pose2 centered{};
  auto centered_valid=[&](Pose2 a,Pose2 b,double v){return corridor(centered,a,b,v);};
  heading_config.headings=16;
  check(!planXYTheta(centered,{3,.6,0},heading_config,centered_valid).reached);
  heading_config.headings=32;
  auto heading_route=planXYTheta(centered,{3,.6,0},heading_config,centered_valid);
  check(heading_route.reached);
  heading_config.turn_angles={kPi/16,kPi/8};
  check(planXYTheta(centered,{3,.6,0},heading_config,centered_valid).reached);
  auto inward_valid=[&](Pose2 a,Pose2 b,double v){return corridor(near_boundary,a,b,v);};
  check(planXYTheta(near_boundary,{3,.6,0},heading_config,inward_valid).reached);
  const Pose2 already_blocked{0,0,.3928570151329041};
  auto blocked_valid=[&](Pose2 a,Pose2 b,double v){return corridor(already_blocked,a,b,v);};
  check(!planXYTheta(already_blocked,{3,.6,0},heading_config,blocked_valid).reached);
  for(size_t i=1;i<heading_route.poses.size();++i) {
    check(nominal_heading(heading_route.poses[i]));
    check(successorHeadingReserve(centered,heading_route.poses[i-1],heading_route.poses[i],.05,nominal_heading));
  }
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
  // Regression: alternating global guides used to renew both stall timers.
  GuideProgress alternating;
  alternating.stationary_stall_seconds=0; // Test cumulative history separately.
  for (int epoch=0;epoch<8;++epoch) {
    const Point target=epoch%2 ? Point{0,20,0}:Point{20,0,0};
    const double start=epoch*16;
    check(alternating.select(target,{0,0,0},start));
    for (int tick=1;tick<=16;++tick) alternating.observe({0,0,0},start+tick,true);
  }
  check(!alternating.active);
  check(alternating.cooling({0,20,0},129));
  check(alternating.cooling({20,0,0},129));
  check(alternating.select({20,0,0},{0,0,0},400));
  near(alternating.idle_seconds,0);
  alternating.observe({19.5,0,0},401,true);
  check(!alternating.select({20,0,0},{19.5,0,0},402));
  // A -> local delegation -> A is one pending world task, not a reason to
  // turn toward B. Tour omissions must preserve progress and local commitment.
  GuideProgress delegated;
  delegated.stationary_stall_seconds=0;
  check(delegated.select({20,0,0},{0,0,0},0,42));
  bool pending=true;
  auto task_state=[&](int id){check(id==42);return pending;};
  for (int t=1;t<=61;++t) {
    const bool in_tour=(t/8)%2==0;
    check(delegated.taskStillPending(in_tour,task_state));
    // Keeping the goal does not waive its independent no-progress timeout.
    const auto event=delegated.observe({0,0,0},t,true);
    check(event==(t==61?GuideProgress::Event::Stalled:GuideProgress::Event::None));
  }
  check(!delegated.active);check(delegated.cooling({20,0,0},62));
  pending=false;
  check(!delegated.taskStillPending(true,task_state)); // stale tour after coverage
  GuideProgress legacy_guide;
  check(legacy_guide.select({0,20,0},{0,0,0},0));
  check(!legacy_guide.taskStillPending(false,task_state)); // no task identity
  check(legacy_guide.taskStillPending(true,{}));
  GuideProgress stopped;
  check(stopped.select({20,0,0},{0,0,0},0));
  for(int t=1;t<13;++t) check(stopped.observe({0,0,0},t,true)==GuideProgress::Event::None);
  check(stopped.observe({0,0,0},13,true)==GuideProgress::Event::Stalled);
  check(stopped.cooling({20,0,0},14));
  GuideProgress creeping;
  check(creeping.select({20,0,0},{0,0,0},0));
  for(int t=1;t<=30;++t)
    check(creeping.observe({t*.025,0,0},t,true)==GuideProgress::Event::None);
  GuideProgress interrupted;
  check(interrupted.select({20,0,0},{0,0,0},0));
  for(int t=1;t<=10;++t) interrupted.observe({0,0,0},t,true);
  interrupted.observe({0,0,0},11,false);
  near(interrupted.stationary_seconds,0);
  check(interrupted.observe({0,0,0},40,true)==GuideProgress::Event::None);
  // Reached recovery targets cannot immediately form a zero-gain circuit;
  // productive sensing and later necessary backtracking remain available.
  TargetCommitment recovery_goal;
  recovery_goal.commit({2,0,0},{0,0,0},1,false);
  recovery_goal.observe({1.5,0,0},5);
  check(recovery_goal.cooling({2.2,0,0},6));
  check(!recovery_goal.cooling({2.2,0,0},6,true));
  check(!recovery_goal.failureCooling({2.2,0,0},6));
  check(!recovery_goal.cooling({2,0,0},66));
  recovery_goal.commit({4,0,0},{2,0,0},70,true);
  recovery_goal.observe({3.5,0,0},75);
  check(!recovery_goal.cooling({4,0,0},76));
  recovery_goal.commit({6,0,0},{4,0,0},80);recovery_goal.reject(81);
  check(recovery_goal.failureCooling({6,0,0},82));
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
  StartupPrior fixed;fixed.assume_traversable=true;fixed.radius=1.5;fixed.initialize({},10);
  fixed.update({2,0,0},11);check(fixed.contains(0,0));check(!fixed.contains(2,0));
  fixed.update({},39.999);check(fixed.contains(1.49,0));
  fixed.update({},40);check(!fixed.contains(0,0));
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
  // Return dead zone: a checkpoint 0.328 m away is already "reached" by
  // the 0.35 m search, while the former 0.30 m consumer never advanced it.
  XYThetaConfig returning=cfg;returning.goal_radius=.35;
  const auto near_checkpoint=planXYTheta({0,0,0},{.328,0,0},returning,all_valid);
  check(near_checkpoint.reached);check(near_checkpoint.poses.size()==1);
  ReturnProgress returning_route;returning_route.checkpoints={{.328,0,0},{2,0,0}};
  returning_route.advance({},.3);check(returning_route.next==0);
  returning_route.advance({},returning.goal_radius+.15,.5);check(returning_route.next==1);
  const auto onward=planXYTheta({0,0,0},returning_route.checkpoints[returning_route.next],returning,all_valid);
  check(onward.reached && onward.poses.size()>1);
  ReturnProgress final_home;final_home.checkpoints={{.4,0,0},{.55,0,0}};
  final_home.advance({},.6,.5);check(final_home.next==1); // Never enlarge the home completion radius.
  final_home.advance({.1,0,0},.6,.5);check(final_home.next==2);
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
