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
}
