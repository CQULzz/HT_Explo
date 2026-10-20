#pragma once
#include "ht_cost/ht_cost_core.h"
namespace ht_cost_ns {
inline Point effectiveTareLookahead(Point raw,bool rush_home,Point home) {
  return rush_home ? home : raw;
}
// A TARE tour can contain the robot twice (a closed local TSP). Choose a
// contiguous branch ending at the exact native lookahead; never clip toward
// a remote endpoint through a bend in the tour.
inline std::vector<Point> tareBranch(const std::vector<Point>& route,
                                     const std::vector<bool>& robots,Point target) {
  std::vector<Point> best;double best_length=std::numeric_limits<double>::infinity();
  if(route.size()!=robots.size()) return best;
  for(size_t start=0;start<route.size();++start) if(robots[start]) for(int dir:{-1,1}) {
    std::vector<Point> branch{route[start]};double length=0;
    for(int i=static_cast<int>(start)+dir;i>=0 && i<static_cast<int>(route.size());i+=dir) {
      const auto& a=branch.back();const auto& b=route[i];
      length+=std::hypot(b.x-a.x,b.y-a.y);branch.push_back(b);
      if(std::hypot(b.x-target.x,b.y-target.y)<1e-5) {
        if(length<best_length) {best_length=length;best=branch;}break;
      }
      if(robots[i]) break;
    }
  }
  return best;
}
inline Point tarePrefix(const std::vector<Point>& branch,double length) {
  if(branch.empty() || !std::isfinite(length) || length<0) return {};
  for(size_t i=1;i<branch.size();++i) {
    const auto& a=branch[i-1];const auto& b=branch[i];
    const double d=std::hypot(b.x-a.x,b.y-a.y);
    if(d>1e-9 && d>=length) {const double t=length/d;return {a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),a.z+t*(b.z-a.z)};}
    length-=d;
  }
  return branch.back();
}

struct TarePrefixTarget { Point point; double arc=0, distance=0; };
// A TARE ROBOT node is a grid anchor, not the continuous odometry pose. In a
// captured stop it was 0.576m ahead of the robot, and only prefix 0..0.25m had
// HT support. Integer prefixes 1..4m therefore never entered path search.
// Sample the SAME chosen branch without changing its waypoint or tour. Start
// at the robot's projection so a grid anchor behind it cannot be chased.
inline std::vector<TarePrefixTarget> tareAdaptivePrefixes(
    const std::vector<Point>& branch,Point robot,double resolution,
    double max_arc=4.,double min_distance=.4) {
  std::vector<TarePrefixTarget> result;
  if(branch.empty() || !std::isfinite(robot.x) || !std::isfinite(robot.y) ||
     !std::isfinite(resolution) || resolution<=0 ||
     !std::isfinite(max_arc) || max_arc<=0 ||
     !std::isfinite(min_distance) || min_distance<=0) return result;
  for(const auto& p:branch)
    if(!std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) return result;
  double arc=0,projected_arc=0;
  double nearest=std::hypot(robot.x-branch.front().x,robot.y-branch.front().y);
  for(size_t i=1;i<branch.size();++i) {
    const auto& a=branch[i-1];const auto& b=branch[i];
    const double dx=b.x-a.x,dy=b.y-a.y,length=std::hypot(dx,dy);
    const double t=length>1e-9 ? std::clamp(((robot.x-a.x)*dx+(robot.y-a.y)*dy)/(length*length),0.,1.):0.;
    const double distance=std::hypot(robot.x-a.x-t*dx,robot.y-a.y-t*dy);
    // Prefer the earlier arc at self-intersections; no jump to a later branch.
    if(distance<nearest-1e-9) {nearest=distance;projected_arc=arc+t*length;}
    arc+=length;
  }
  const double limit=std::min(max_arc,arc);
  if(projected_arc>limit+1e-9) return result;
  auto append=[&](double prefix) {
    const auto p=tarePrefix(branch,prefix);
    const double distance=std::hypot(p.x-robot.x,p.y-robot.y);
    if(distance<min_distance) return;
    for(const auto& previous:result)
      if(std::hypot(p.x-previous.point.x,p.y-previous.point.y)<1e-6) return;
    result.push_back({p,prefix,distance});
  };
  // Half a map cell resolves narrow support intervals; cap the number of
  // probes even for unusually fine grids. This is not permission to move.
  const double spacing=std::clamp(resolution*.5,.02,.1);
  append(projected_arc);
  for(double prefix=std::ceil(projected_arc/spacing)*spacing;
      prefix<limit;prefix+=spacing) append(prefix);
  append(limit);
  std::stable_sort(result.begin(),result.end(),[](const auto& a,const auto& b) {
    return a.distance<b.distance;
  });
  return result;
}
}
