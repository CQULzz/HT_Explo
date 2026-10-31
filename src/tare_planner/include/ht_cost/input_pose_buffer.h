#pragma once

#include <algorithm>
#include <array>
#include <cmath>
#include <deque>
#include <iterator>
#include <optional>
#include <string>

namespace ht_cost_ns {
// Pure input contract shared by the planner and follower. A child reference
// transform must be done upstream; accepting a map header does not perform it.
struct InputPose {
  double stamp=0;
  std::array<double,3> xyz{};
  std::array<double,4> q{0,0,0,1}; // x,y,z,w
};
inline bool mapFrame(const std::string& frame) {return frame=="map" || frame=="/map";}
inline bool validInputPose(const InputPose& p) {
  if (!std::isfinite(p.stamp) || p.stamp<=0) return false;
  double norm=0;
  for(double v:p.xyz)if(!std::isfinite(v))return false;
  for(double v:p.q) {if(!std::isfinite(v))return false;norm+=v*v;}
  return std::isfinite(norm) && std::abs(norm-1)<=.01;
}

// A sensor lever arm is expressed in the odometry child frame. Rotate it
// with the full measured attitude; adding its Z component in map coordinates
// is incorrect on a slope. This changes the observation origin, not the
// vehicle pose used by routing, collision checks, or the startup assumption.
inline std::optional<std::array<double,3>> observationOrigin(
    const InputPose& p,const std::array<double,3>& offset) {
  if(!validInputPose(p)) return {};
  for(double v:offset) if(!std::isfinite(v)) return {};
  double norm=0;for(double v:p.q) norm+=v*v;
  const double scale=1/std::sqrt(norm);
  const double x=p.q[0]*scale,y=p.q[1]*scale,z=p.q[2]*scale,w=p.q[3]*scale;
  const std::array<double,3> t{2*(y*offset[2]-z*offset[1]),
    2*(z*offset[0]-x*offset[2]),2*(x*offset[1]-y*offset[0])};
  return std::array<double,3>{p.xyz[0]+offset[0]+w*t[0]+y*t[2]-z*t[1],
    p.xyz[1]+offset[1]+w*t[1]+z*t[0]-x*t[2],
    p.xyz[2]+offset[2]+w*t[2]+x*t[1]-y*t[0]};
}

class InputPoseBuffer {
 public:
  // Duplicates and out-of-order packets are dropped. A clock reset is a
  // separate event, never inferred from one delayed packet.
  bool add(const InputPose& p) {
    if (!validInputPose(p) || (!poses_.empty() && p.stamp<=poses_.back().stamp))return false;
    poses_.push_back(p);
    while(poses_.size()>4000 || (!poses_.empty() && p.stamp-poses_.front().stamp>10))poses_.pop_front();
    return true;
  }
  std::optional<InputPose> at(double stamp,double max_skew) const {
    if(poses_.empty() || !std::isfinite(stamp) || !std::isfinite(max_skew) || max_skew<=0)return {};
    auto b=std::lower_bound(poses_.begin(),poses_.end(),stamp,
      [](const InputPose& p,double t){return p.stamp<t;});
    if(b==poses_.begin())return std::abs(b->stamp-stamp)<=max_skew ? std::optional<InputPose>(*b):std::nullopt;
    if(b==poses_.end())return std::abs(poses_.back().stamp-stamp)<=max_skew ? std::optional<InputPose>(poses_.back()):std::nullopt;
    if(b->stamp==stamp)return *b;
    const auto& a=*std::prev(b);
    if(b->stamp-a.stamp>2*max_skew+1e-6) {
      const auto& nearest=stamp-a.stamp<=b->stamp-stamp ? a:*b;
      return std::abs(nearest.stamp-stamp)<=max_skew ? std::optional<InputPose>(nearest):std::nullopt;
    }
    const double t=(stamp-a.stamp)/(b->stamp-a.stamp);
    InputPose p;p.stamp=stamp;
    for(int i=0;i<3;++i)p.xyz[i]=a.xyz[i]+t*(b->xyz[i]-a.xyz[i]);
    double dot=0,an=0,bn=0;
    for(int i=0;i<4;++i){an+=a.q[i]*a.q[i];bn+=b->q[i]*b->q[i];}
    const double scale=std::sqrt(an*bn);
    for(int i=0;i<4;++i)dot+=a.q[i]*b->q[i]/scale;
    const double sign=dot<0 ? -1:1;dot=std::clamp(std::abs(dot),0.,1.);
    const double angle=std::acos(dot),s=std::sin(angle);
    const double u=s>1e-6 ? std::sin((1-t)*angle)/s:1-t;
    const double v=s>1e-6 ? std::sin(t*angle)/s:t;
    double norm=0;
    for(int i=0;i<4;++i){p.q[i]=u*a.q[i]/std::sqrt(an)+v*sign*b->q[i]/std::sqrt(bn);norm+=p.q[i]*p.q[i];}
    for(double& value:p.q)value/=std::sqrt(norm);
    return p;
  }
  bool jump(const InputPose& p) const {
    if(poses_.empty())return false;
    const auto& a=poses_.back();const double dt=p.stamp-a.stamp;
    if(dt<=0)return false;
    double distance2=0,dot=0,an=0,bn=0;
    for(int i=0;i<3;++i)distance2+=(p.xyz[i]-a.xyz[i])*(p.xyz[i]-a.xyz[i]);
    for(int i=0;i<4;++i){dot+=a.q[i]*p.q[i];an+=a.q[i]*a.q[i];bn+=p.q[i]*p.q[i];}
    const double angle=2*std::acos(std::clamp(std::abs(dot)/std::sqrt(an*bn),0.,1.));
    // Conservative discontinuity detector, not a guarantee that smaller
    // localization corrections are harmless. Fixed thresholds are documented.
    return std::sqrt(distance2)>.75+3*dt || angle>.5+4*dt;
  }
  double latestStamp() const {return poses_.empty() ? -1:poses_.back().stamp;}
 private:
  std::deque<InputPose> poses_;
};

// Called with steady-clock time at each command tick. Cap long gaps to avoid
// a sudden catch-up command; the cap only makes the acceleration smaller.
class CommandInterval {
 public:
  double elapsed(double now) const {return last_>=0 && now>last_ ? std::min(now-last_,.05):0;}
  void published(double now) {last_=now;}
 private:
  double last_=-1;
};
} // namespace ht_cost_ns
