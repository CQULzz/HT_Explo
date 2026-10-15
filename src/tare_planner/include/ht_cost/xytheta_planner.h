#pragma once

#include "ht_cost/ht_cost_core.h"
#include <chrono>
#include <cstdint>
#include <limits>
#include <queue>
#include <unordered_map>

namespace ht_cost_ns {

struct Pose2 {
  double x=0, y=0, yaw=0;
};

inline double wrapYaw(double yaw) {
  while (yaw>kPi) yaw-=2*kPi;
  while (yaw<=-kPi) yaw+=2*kPi;
  return yaw;
}

struct XYThetaPlan {
  std::vector<Pose2> poses;
  double seconds=std::numeric_limits<double>::infinity();
  int expanded=0;
  bool reached=false;
};

struct XYThetaConfig {
  double cell=0.3;
  int headings=16;
  double drive_step=0.4;
  double forward_speed=0.5;
  double reverse_speed=0.25;
  double max_yaw_rate=0.8;
  double goal_radius=0.4;
  double max_radius=7.0;
  int max_expansions=8000;
  double max_search_seconds=0.2;
};

// Hybrid A*: the key is discrete (x,y,theta), while each stored state and
// primitive trajectory remain continuous. The primitive controls are exactly
// executable by a differential drive: constant (v,omega), including v=0 spin.
template<class Valid>
XYThetaPlan planXYTheta(Pose2 start,Point goal,const XYThetaConfig& cfg,Valid valid) {
  XYThetaPlan out;
  if (!std::isfinite(start.x) || !std::isfinite(start.y) || !std::isfinite(start.yaw) ||
      !std::isfinite(goal.x) || !std::isfinite(goal.y) || cfg.cell<=0 ||
      cfg.headings<8 || cfg.drive_step<=0 || cfg.forward_speed<=0 ||
      cfg.reverse_speed<=0 || cfg.max_yaw_rate<=0 || cfg.max_expansions<=0)
    return out;
  start.yaw=wrapYaw(start.yaw);
  if (!valid(start,start,0)) return out;
  const double yaw_step=2*kPi/cfg.headings;
  struct Key { int x,y,h; bool operator==(const Key& b) const {return x==b.x&&y==b.y&&h==b.h;} };
  struct Hash { size_t operator()(Key k) const {
    uint64_t z=(uint64_t(uint32_t(k.x))*0x9e3779b185ebca87ULL) ^
               (uint64_t(uint32_t(k.y))*0xc2b2ae3d27d4eb4fULL) ^ uint32_t(k.h);
    return static_cast<size_t>(z^(z>>32));
  }};
  auto key=[&](Pose2 p) {
    int h=static_cast<int>(std::llround(wrapYaw(p.yaw)/yaw_step));
    h=(h%cfg.headings+cfg.headings)%cfg.headings;
    return Key{static_cast<int>(std::llround((p.x-start.x)/cfg.cell)),
               static_cast<int>(std::llround((p.y-start.y)/cfg.cell)),h};
  };
  struct State {Pose2 pose;std::vector<Pose2> edge;int parent;double g;};
  std::vector<State> states;
  states.push_back({start,{},-1,0});
  std::unordered_map<Key,double,Hash> best;
  best.emplace(key(start),0);
  using QueueItem=std::pair<double,int>;
  std::priority_queue<QueueItem,std::vector<QueueItem>,std::greater<QueueItem>> open;
  auto heuristic=[&](Pose2 p) {return std::hypot(goal.x-p.x,goal.y-p.y)/cfg.forward_speed;};
  open.emplace(heuristic(start),0);
  const auto deadline=std::chrono::steady_clock::now()+
      std::chrono::duration<double>(cfg.max_search_seconds);
  while (!open.empty() && out.expanded<cfg.max_expansions) {
    if ((out.expanded&31)==0 && std::chrono::steady_clock::now()>deadline) break;
    const int index=open.top().second;open.pop();
    const State current=states[index];
    if (current.g>best[key(current.pose)]+1e-9) continue;
    ++out.expanded;
    if (std::hypot(goal.x-current.pose.x,goal.y-current.pose.y)<=cfg.goal_radius) {
      std::vector<int> chain;
      for (int i=index;i>=0;i=states[i].parent) chain.push_back(i);
      std::reverse(chain.begin(),chain.end());
      out.poses.push_back(start);
      for (size_t i=1;i<chain.size();++i)
        out.poses.insert(out.poses.end(),states[chain[i]].edge.begin(),states[chain[i]].edge.end());
      out.seconds=current.g;out.reached=true;return out;
    }
    struct Control {double v,omega,duration;};
    const double forward_time=cfg.drive_step/cfg.forward_speed;
    const double reverse_time=cfg.drive_step/cfg.reverse_speed;
    const Control controls[]={{0,cfg.max_yaw_rate,yaw_step/cfg.max_yaw_rate},
      {0,-cfg.max_yaw_rate,yaw_step/cfg.max_yaw_rate},
      {cfg.forward_speed,0,forward_time},
      {cfg.forward_speed,yaw_step/forward_time,forward_time},
      {cfg.forward_speed,-yaw_step/forward_time,forward_time},
      {-cfg.reverse_speed,0,reverse_time},
      {-cfg.reverse_speed,yaw_step/reverse_time,reverse_time},
      {-cfg.reverse_speed,-yaw_step/reverse_time,reverse_time}};
    for (const auto& control:controls) {
      if (std::abs(control.omega)>cfg.max_yaw_rate+1e-9) continue;
      const int n=std::max(2,static_cast<int>(std::ceil(std::max(
        std::abs(control.v)*control.duration/0.1,std::abs(control.omega)*control.duration/0.12))));
      const double dt=control.duration/n;
      Pose2 pose=current.pose;
      std::vector<Pose2> samples;samples.reserve(n);
      bool feasible=true;
      for (int i=0;i<n;++i) {
        Pose2 next=pose;
        const double dtheta=control.omega*dt;
        if (std::abs(control.omega)<1e-9) {
          next.x+=control.v*dt*std::cos(pose.yaw);
          next.y+=control.v*dt*std::sin(pose.yaw);
        } else {
          next.x+=control.v/control.omega*(std::sin(pose.yaw+dtheta)-std::sin(pose.yaw));
          next.y-=control.v/control.omega*(std::cos(pose.yaw+dtheta)-std::cos(pose.yaw));
        }
        next.yaw=wrapYaw(pose.yaw+dtheta);
        if (std::hypot(next.x-start.x,next.y-start.y)>cfg.max_radius ||
            !valid(pose,next,control.v)) {feasible=false;break;}
        samples.push_back(next);pose=next;
      }
      if (!feasible) continue;
      const Key next_key=key(pose);
      // Reversal is physically possible but slower and more likely to cause
      // gear oscillation. This penalty acts on maneuver time, never HT risk.
      const double cost=control.duration*(control.v<0?1.15:1.0);
      const double candidate=current.g+cost;
      auto old=best.find(next_key);
      if (old!=best.end() && candidate>=old->second-1e-9) continue;
      best[next_key]=candidate;
      const int next_index=static_cast<int>(states.size());
      states.push_back({pose,std::move(samples),index,candidate});
      open.emplace(candidate+heuristic(pose),next_index);
    }
  }
  return out;
}
}  // namespace ht_cost_ns
