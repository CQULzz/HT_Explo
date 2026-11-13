// Extracted follow functions: baseline 5e5eef and current candidate; fixed routes, not a recorded replay.
#include <cmath>
#include <algorithm>
#include <vector>
#include <iostream>
struct Pose{double x,y,yaw;};
double wrap(double a){return atan2(sin(a),cos(a));}
struct Baseline {
 double execution_speed_=.15,angular_=.5,accel_=2.5,angular_accel_=3.;
 static double distance(Pose a,Pose b){return hypot(a.x-b.x,a.y-b.y);}
 static double approach(double a,double b,double d){return a+std::max(-d,std::min(d,b-a));}
  bool follow(const std::vector<Pose>& path,size_t& index,Pose current,double dt,
              double& pv,double& pw,double& v,double& w) const {
    if(index>=path.size()){v=approach(pv,0,accel_*dt);w=approach(pw,0,angular_accel_*dt);pv=v;pw=w;return false;}
    const Pose from=path[index-1],target=path[index];const bool turn=distance(from,target)<1e-7;
    const double angle=wrap(target.yaw-current.yaw);double desired_v=0,desired_w=0;
    bool reached=false;
    if(turn) {
      reached=std::abs(angle)<.012;
      if(!reached)desired_w=std::copysign(std::min(angular_,3.*std::abs(angle)),angle);
    } else {
      reached=distance(current,target)<.0025;
      const double ux=std::cos(target.yaw),uy=std::sin(target.yaw);
      const double gear=((target.x-from.x)*ux+(target.y-from.y)*uy)>=0?1.:-1.;
      const double along=gear*((target.x-current.x)*ux+(target.y-current.y)*uy);
      const double cross=ux*(target.y-current.y)-uy*(target.x-current.x);
      if(!reached) {
        desired_w=std::max(-angular_,std::min(angular_,3.*angle+2.*gear*cross));
        if(std::abs(angle)<.1)desired_v=gear*std::min(execution_speed_,std::max(0.,2.*along));
      }
    }
    v=approach(pv,desired_v,accel_*dt);w=approach(pw,desired_w,angular_accel_*dt);pv=v;pw=w;
    if(reached && std::abs(v)+std::abs(w)<1e-7)++index;
    return true;
  }
};
struct Fixed {
 double execution_speed_=.15,angular_=.5,accel_=2.5,angular_accel_=3.;
 static double distance(Pose a,Pose b){return hypot(a.x-b.x,a.y-b.y);}
 static double approach(double a,double b,double d){return a+std::max(-d,std::min(d,b-a));}
  bool follow(const std::vector<Pose>& path,size_t& index,Pose current,double dt,
              double& pv,double& pw,double& v,double& w) const {
    if(index>=path.size()){v=approach(pv,0,accel_*dt);w=approach(pw,0,angular_accel_*dt);pv=v;pw=w;return false;}
    const Pose from=path[index-1],target=path[index];const bool turn=distance(from,target)<1e-7;
    const double angle=wrap(target.yaw-current.yaw);double desired_v=0,desired_w=0;
    bool reached=false;
    if(turn) {
      reached=std::abs(angle)<.02;
      if(!reached)desired_w=std::copysign(std::min(angular_,std::sqrt(2.*angular_accel_*std::max(0.,std::abs(angle)-.01))),angle);
    } else {
      // Completion uses along/cross errors; a small overshoot must not deadlock.
      const double ux=std::cos(target.yaw),uy=std::sin(target.yaw);
      const double gear=((target.x-from.x)*ux+(target.y-from.y)*uy)>=0?1.:-1.;
      const double along=gear*((target.x-current.x)*ux+(target.y-current.y)*uy);
      const double cross=ux*(target.y-current.y)-uy*(target.x-current.x);
      reached=along<=.01 && along>=-.02 && std::abs(cross)<=.015 && std::abs(angle)<.04;
      if(!reached) {
        desired_w=std::max(-angular_,std::min(angular_,3.*angle+2.*gear*cross));
        if(std::abs(angle)<.1)desired_v=gear*std::min(execution_speed_,std::sqrt(2.*accel_*std::max(0.,along-.005)));
      }
    }
    v=approach(pv,desired_v,accel_*dt);w=approach(pw,desired_w,angular_accel_*dt);pv=v;pw=w;
    if(reached && std::abs(v)+std::abs(w)<1e-7)++index;
    return true;
  }
};
template<class T> double run(const std::vector<Pose>& route){T c;Pose p=route.front();size_t i=1;double pv=0,pw=0,v=0,w=0;
for(int tick=0;tick<2000;tick++){c.follow(route,i,p,.02,pv,pw,v,w);if(i==route.size())return tick*.02;for(int j=0;j<4;j++){p.yaw=wrap(p.yaw+w*.005);p.x+=v*.005*cos(p.yaw);p.y+=v*.005*sin(p.yaw);}}return -1;}
int main(){double pi=acos(-1.);std::vector<Pose>a={{0,0,-.261188596},{0,0,0},{.81871345,0,0}};
std::vector<Pose>b={{0,0,.52910769},{0,0,pi/4},{-.04093567,-.04093567,pi/4},{-.04093567,-.04093567,0},{.81871345,-.04093567,0}};
std::cout<<"route1 baseline="<<run<Baseline>(a)<<" fixed="<<run<Fixed>(a)<<"\nroute2 baseline="<<run<Baseline>(b)<<" fixed="<<run<Fixed>(b)<<"\n";}
