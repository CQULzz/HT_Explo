#pragma once
#include "ht_cost/target_commitment.h"
#include <map>
#include <functional>

namespace ht_cost_ns {
// Independent of short local-goal commitments. Completing a local goal must
// never renew the deadline of an unreachable world-space global destination.
struct GuideProgress {
  enum class Event { None, Reached, Stalled };
  Point goal{};
  int task_id=-1;
  bool active=false, previous_healthy=false;
  double best_distance=0, idle_seconds=0, last_observed=0;
  double stall_seconds=60, cooldown_seconds=180, identity_radius=2;
  double stationary_stall_seconds=12,stationary_seconds=0;
  Point stationary_anchor{};
  struct Cooldown {Point goal; double until;};
  std::vector<Cooldown> cooldowns;
  struct History {Point goal;double best_distance,idle_seconds,last_seen;};
  std::vector<History> history;
  void remember(double now) {
    for (auto& h:history) if (TargetCommitment::distance(h.goal,goal)<identity_radius) {
      h={goal,best_distance,idle_seconds,now};return;
    }
    history.push_back({goal,best_distance,idle_seconds,now});
  }
  void forget() {
    history.erase(std::remove_if(history.begin(),history.end(),
      [&](const History& h){return TargetCommitment::distance(h.goal,goal)<identity_radius;}),history.end());
  }
  bool cooling(Point p,double now) const {
    for (const auto& c:cooldowns)
      if (now<c.until && TargetCommitment::distance(p,c.goal)<identity_radius) return true;
    return false;
  }
  // The tour omits tasks delegated to the local horizon. Its membership is
  // not coverage evidence. Prefer the owning world's task state when known.
  bool taskStillPending(bool in_tour,const std::function<bool(int)>& pending) const {
    return task_id>=0 && pending ? pending(task_id):in_tour;
  }
  bool select(Point p,Point robot,double now,int selected_task=-1) {
    if (cooling(p,now)) return false;
    if (active && TargetCommitment::distance(p,goal)<identity_radius) {
      if (selected_task>=0) task_id=selected_task;
      return true;
    }
    if (active) remember(now);
    history.erase(std::remove_if(history.begin(),history.end(),
      [&](const History& h){return now<h.last_seen || now-h.last_seen>=4*cooldown_seconds;}),history.end());
    goal=p;task_id=selected_task;active=true;best_distance=TargetCommitment::distance(robot,p);
    idle_seconds=0;last_observed=now;previous_healthy=false;
    stationary_seconds=0;stationary_anchor=robot;
    // Changing A -> B -> A must not erase A's failed attempts. Only time
    // actually spent tracking A counts; a new best approach still renews it.
    for (const auto& h:history) if (TargetCommitment::distance(h.goal,p)<identity_radius) {
      goal=h.goal;best_distance=h.best_distance;idle_seconds=h.idle_seconds;break;
    }
    return true;
  }
  Event observe(Point robot,double now,bool healthy) {
    cooldowns.erase(std::remove_if(cooldowns.begin(),cooldowns.end(),
      [&](const Cooldown& c){return now>=c.until;}),cooldowns.end());
    if (!active) return Event::None;
    const double dt=now-last_observed;
    last_observed=now;
    // Missing planning callbacks and stale maps are not evidence of an
    // unreachable destination. Ignore gaps, and require two healthy samples.
    const bool continuous=healthy && previous_healthy && dt>=0 && dt<=5;
    if (continuous) idle_seconds+=dt;
    previous_healthy=healthy;
    if (!continuous) {stationary_seconds=0;stationary_anchor=robot;}
    else if (TargetCommitment::distance(robot,stationary_anchor)>.1) {
      stationary_seconds=0;stationary_anchor=robot;
    } else if (dt>=0 && dt<=5) stationary_seconds+=dt;
    if (!healthy) return Event::None;
    const double d=TargetCommitment::distance(robot,goal);
    if (d<=1) {
      // The global tour can briefly retain an already reached destination.
      // Cool guidance only; useful local sensing targets remain eligible.
      cooldowns.push_back({goal,now+cooldown_seconds});
      forget();active=false;return Event::Reached;
    }
    if (d<best_distance-0.5) {best_distance=d;idle_seconds=0;}
    remember(now);
    if (idle_seconds<stall_seconds &&
        (stationary_stall_seconds<=0 || stationary_seconds<stationary_stall_seconds)) return Event::None;
    cooldowns.push_back({goal,now+cooldown_seconds});forget();active=false;
    return Event::Stalled;
  }
};

// Count world-cell entries, not planner invocations. Revisits remain possible
// for necessary backtracking, but repeated circuits become less attractive.
struct ExplorationVisits {
  std::map<std::pair<int,int>,unsigned> entries;
  Point last{};
  bool initialized=false;
  static std::pair<int,int> cell(Point p) {
    return {static_cast<int>(std::floor(p.x)),static_cast<int>(std::floor(p.y))};
  }
  void observe(Point robot) {
    if (initialized && (cell(robot)==cell(last) || TargetCommitment::distance(robot,last)<0.5)) return;
    ++entries[cell(robot)];last=robot;initialized=true;
  }
  double penalty(Point p) const {
    const auto found=entries.find(cell(p));
    return found==entries.end()?0:std::log1p(found->second);
  }
};

// Subtract time separately: dividing a negative utility by travel time would
// favor longer detours to an equally unproductive recovery goal.
inline double transitScore(double progress,double revisit_penalty,double seconds) {
  return -8+progress-2*revisit_penalty-0.15*seconds;
}
} // namespace ht_cost_ns
