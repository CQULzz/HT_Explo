#pragma once
#include "ht_cost/ht_cost_core.h"
namespace ht_cost_ns {
// A mission-local assumption, never an observation or a moving free-space bubble.
struct StartupPrior {
  Point anchor{};
  double radius=1.2, lifetime=30, start=0;
  bool initialized=false, retired=false;
  void initialize(Point p,double now) { if (!initialized) {anchor=p;start=now;initialized=true;} }
  void update(Point p,double now) {
    if (initialized && (now<start || now-start>=lifetime ||
        std::hypot(p.x-anchor.x,p.y-anchor.y)>radius)) retired=true;
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
enum class Support { KNOWN, STARTUP_PRIOR, UNKNOWN, FAULT };
struct ExecutionTarget { Point point; Support support=Support::KNOWN; bool valid=false; };
// Nodes are ordered travel targets (the synthetic initial ROBOT anchor is omitted).
// Never skip a blocked turn to reach a later vertex or an unchecked home shortcut.
template<class Geometry,class Assess,class Permit>
ExecutionTarget checkedLookahead(Point robot,const std::vector<Point>& route,
    double reached,double lookahead,double fallback_lookahead,
    Geometry geometry,Assess assess,Permit permit) {
  ExecutionTarget result{robot};
  for (const auto& target:route) {
    if (waypointReached(robot,target,reached)) continue;
    const double dx=target.x-robot.x,dy=target.y-robot.y,dz=target.z-robot.z;
    const double length=std::hypot(std::hypot(dx,dy),dz);
    if (!std::isfinite(length) || length<=0) return result;
    auto at=[&](double d) {return Point{robot.x+dx*d/length,robot.y+dy*d/length,robot.z+dz*d/length};};
    double limit=std::min(length,lookahead);
    if (assess(robot,at(limit))==Support::UNKNOWN) limit=std::min(limit,fallback_lookahead);
    for (double d=std::min(0.1,limit);;d=std::min(d+0.1,limit)) {
      const auto point=at(d);
      if (!geometry(point)) break;
      const auto support=assess(robot,point);
      if (!permit(support)) break;
      result.point=point;result.support=support;
      if (d>=limit) break;
    }
    break;
  }
  result.valid=!waypointReached(robot,result.point,reached);
  return result;
}
}  // namespace ht_cost_ns
