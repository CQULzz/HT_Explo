#pragma once
#include "ht_cost/ht_cost_core.h"
#include <algorithm>

namespace ht_cost_ns {
// Goals live in world coordinates: rolling-grid indices are not identities.
// Only progress toward the committed goal renews its stall deadline.
struct TargetCommitment {
  Point goal{};
  bool active=false;
  bool productive=true;
  double best_distance=0,last_progress=0;
  double reached=0.6,stall_seconds=12,cooldown_seconds=20;
  struct Cooldown {Point goal;double until;bool recovery_only=false;};
  std::vector<Cooldown> cooldowns;
  static double distance(Point a,Point b) {return std::hypot(a.x-b.x,a.y-b.y);}
  bool cooling(Point p,double now,bool has_gain=false) const {
    for (const auto& c:cooldowns)
      if (now<c.until && !(has_gain && c.recovery_only) && distance(p,c.goal)<0.8) return true;
    return false;
  }
  bool failureCooling(Point p,double now) const {
    for (const auto& c:cooldowns)
      if (!c.recovery_only && now<c.until && distance(p,c.goal)<0.8) return true;
    return false;
  }
  void reject(double now) {
    if (active) cooldowns.push_back({goal,now+cooldown_seconds});
    active=false;
  }
  void observe(Point robot,double now) {
    cooldowns.erase(std::remove_if(cooldowns.begin(),cooldowns.end(),
      [&](const Cooldown& c){return now>=c.until;}),cooldowns.end());
    if (!active) return;
    const double d=distance(robot,goal);
    if (d<=reached) {
      if (!productive) cooldowns.push_back({goal,now+60,true});
      active=false;return;
    }
    if (d<best_distance-0.2) {best_distance=d;last_progress=now;}
    if (now<last_progress || now-last_progress>=stall_seconds) reject(now);
  }
  void commit(Point p,Point robot,double now,bool has_gain=true) {
    productive=has_gain;
    if (active && distance(p,goal)<0.8) return;
    goal=p;active=true;best_distance=distance(robot,p);last_progress=now;
  }
};
} // namespace ht_cost_ns
