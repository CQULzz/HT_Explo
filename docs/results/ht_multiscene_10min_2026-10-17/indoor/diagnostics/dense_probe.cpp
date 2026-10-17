#include "ht_cost/xytheta_planner.h"
#include <fstream>
#include <iostream>
#include <iterator>
#include <array>
using namespace ht_cost_ns;
int main(int argc,char**argv) {
 if(argc!=2)return 2;
 std::ifstream file(argv[1],std::ios::binary);std::vector<unsigned char> free((std::istreambuf_iterator<char>(file)),{});
 const int n=241;const double res=.04093567251461988,cx=3.070175438596491,cy=.24561403508771928;
 Pose2 robot{3.0886306762695312,.2650969922542572,.16400225460529327};
 auto pose_valid=[&](Pose2 p,double heading){int r=int(std::floor(n*.5-(p.x-cx)/res)),c=int(std::floor(n*.5-(p.y-cy)/res));int k=int(std::llround(wrapYaw(heading)/(kPi/4)));k=(k%8+8)%8;return r>=0&&c>=0&&r<n&&c<n&&free[k*n*n+r*n+c];};
 auto valid=[&](Pose2 a,Pose2 b,double v){double turn=wrapYaw(b.yaw-a.yaw);int count=std::max(2,int(std::ceil(std::max(std::hypot(b.x-a.x,b.y-a.y)/.005,std::abs(turn)/.01))));for(int i=0;i<=count;++i){double t=double(i)/count;Pose2 p{a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),wrapYaw(a.yaw+t*turn)};if(!pose_valid(p,p.yaw))return false;if(std::hypot(b.x-a.x,b.y-a.y)>1e-6&&!pose_valid(p,std::atan2(b.y-a.y,b.x-a.x)))return false;}return true;};
 XYThetaConfig cfg;cfg.goal_radius=.35;cfg.max_search_seconds=.15;
 for (Point goal:std::vector<Point>{{4.8,0,0},{4.2,0,0},{4.2,.1,0},{1.2,0,0},{1.8,.1,0}}){auto plan=planXYTheta(robot,goal,cfg,valid);std::cout<<goal.x<<","<<goal.y<<" reached="<<plan.reached<<" states="<<plan.poses.size()<<" expanded="<<plan.expanded<<" seconds="<<plan.seconds<<"\n";if(plan.reached){std::ofstream p(std::string(argv[1])+".path.csv");p<<"x,y,yaw\n";for(auto q:plan.poses)p<<q.x<<","<<q.y<<","<<q.yaw<<"\n";}}
}
