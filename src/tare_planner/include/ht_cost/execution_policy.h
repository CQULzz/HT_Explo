#pragma once
#include "ht_cost/ht_cost_core.h"
namespace ht_cost_ns {
// A mission-local assumption, never an observation or a moving free-space bubble.
struct StartupPrior {
  Point anchor{};
  double radius=1.2, lifetime=30, start=0;
  bool initialized=false, retired=false, assume_traversable=false;
  void initialize(Point p,double now) { if (!initialized) {anchor=p;start=now;initialized=true;} }
  void update(Point p,double now) {
    if (initialized && (now<start || now-start>=lifetime ||
        (!assume_traversable && std::hypot(p.x-anchor.x,p.y-anchor.y)>radius))) retired=true;
  }
  bool contains(double x,double y) const {
    return initialized && !retired && radius>0 && std::hypot(x-anchor.x,y-anchor.y)<=radius;
  }
};
struct FallbackBudget {
  double seconds=0,distance=0,max_seconds=60,max_distance=10;
  double previous_time=0;
  Point previous{};
  bool initialized=false;
  void update(double now,Point p,bool was_fallback) {
    if (initialized && was_fallback) {
      seconds+=std::max(0.0,now-previous_time);
      distance+=std::hypot(p.x-previous.x,p.y-previous.y);
    }
    previous=p;previous_time=now;initialized=true;
  }
  bool exhausted() const {return seconds>=max_seconds || distance>=max_distance;}
};
struct HomeCompletion {
  double radius=0.5,speed_limit=0.05,dwell=1.0,since=-1;
  bool completed=false;
  bool update(double now,bool returning,bool healthy,double distance,double speed) {
    if (completed) return true;
    if (!returning || !healthy || !std::isfinite(distance) || !std::isfinite(speed) ||
        distance>radius || speed>=speed_limit) {since=-1;return false;}
    if (since<0 || now<since) since=now;
    completed=now-since>=dwell;
    return completed;
  }
};
enum class Support { KNOWN, STARTUP_PRIOR, UNKNOWN, BLOCKED, FAULT };
// Return checkpoints are consumed monotonically. Re-snapping a graph start every
// cycle can resurrect a checkpoint already passed and make the vehicle oscillate.
struct ReturnProgress {
  std::vector<Point> checkpoints;
  size_t next=0;
  void advance(Point robot,double reached,double home_reached=-1) {
    while (next<checkpoints.size()) {
      const double radius=next+1==checkpoints.size() && home_reached>=0 ? home_reached : reached;
      if (!waypointReached(robot,checkpoints[next],radius)) break;
      ++next;
    }
  }
};
struct ExecutionTarget { Point point; Support support=Support::KNOWN; bool valid=false; };
// Nodes are ordered travel targets (the synthetic initial ROBOT anchor is omitted).
// Continue past a nearby node only along a nearly straight, checked route.
// This avoids repeatedly commanding a 0.3-0.5 m endpoint to a controller
// that brakes near every endpoint, while preserving bends as mandatory turns.
template<class Geometry,class Assess,class Permit>
ExecutionTarget checkedLookahead(Point robot,const std::vector<Point>& route,
    double reached,double lookahead,double fallback_lookahead,
    Geometry geometry,Assess assess,Permit permit) {
  ExecutionTarget result{robot};
  Point previous=robot;
  double used=0,previous_dx=0,previous_dy=0;
  bool have_direction=false;
  for (const auto& target:route) {
    if (waypointReached(robot,target,reached)) continue;
    const double dx=target.x-previous.x,dy=target.y-previous.y,dz=target.z-previous.z;
    const double length=std::hypot(std::hypot(dx,dy),dz);
    if (!std::isfinite(length) || length<=0) break;
    if (have_direction) {
      const double prev_norm=std::hypot(previous_dx,previous_dy);
      const double next_norm=std::hypot(dx,dy);
      if (prev_norm<=1e-9 || next_norm<=1e-9 ||
          (previous_dx*dx+previous_dy*dy)/(prev_norm*next_norm)<std::cos(20.0*3.14159265358979323846/180.0))
        break;
    }
    auto at=[&](double d) {return Point{previous.x+dx*d/length,previous.y+dy*d/length,previous.z+dz*d/length};};
    const double limit=std::min(length,lookahead-used);
    if (limit<=0) break;
    bool checked_to_end=true;
    for (double d=std::min(0.1,limit);;d=std::min(d+0.1,limit)) {
      const auto point=at(d);
      if (!geometry(point)) {checked_to_end=false;break;}
      const auto support=assess(robot,point);
      if (!permit(support) || (support==Support::UNKNOWN && used+d>fallback_lookahead+1e-9)) {
        checked_to_end=false;break;
      }
      result.point=point;result.support=support;
      if (d>=limit) break;
    }
    if (!checked_to_end || limit<length) break;
    used+=length;
    previous=target;
    previous_dx=dx;previous_dy=dy;
    have_direction=true;
    if (used>=lookahead) break;
  }
  result.valid=!waypointReached(robot,result.point,reached);
  return result;
}
}  // namespace ht_cost_ns
