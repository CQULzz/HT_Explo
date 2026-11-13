#include "ht_gate.hpp"
#include <geometry_msgs/msg/point_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <std_msgs/msg/bool.hpp>
#include <queue>
#include <limits>
// Isolate tracking from graph search with fixed-path fixtures.
#define private public
#include "ht_recovery.hpp"
#undef private
#include <iostream>
void check(bool ok,const char* text){if(!ok)throw std::runtime_error(text);std::cout<<"PASS "<<text<<std::endl;}
grid_map_msgs::msg::GridMap fixture(rclcpp::Node::SharedPtr n){
 grid_map_msgs::msg::GridMap m;m.header.frame_id="map";m.header.stamp=n->now();
 m.info.resolution=.04;m.info.length_x=m.info.length_y=81*.04;m.info.pose.orientation.w=1;
 for(int k=0;k<11;k++){m.layers.push_back(k<8?"ht_dir_"+std::to_string(k):k==8?"ht_valid":k==9?"ht_observation_valid":"ht_obstacle");
 std_msgs::msg::Float32MultiArray a;a.layout.dim.resize(2);a.layout.dim[0].label="column_index";a.layout.dim[1].label="row_index";
 a.layout.dim[0].size=a.layout.dim[1].size=81;a.layout.dim[0].stride=81*81;a.layout.dim[1].stride=81;
 a.data.assign(81*81,k<8?.9:k<10?1:0);m.data.push_back(a);}return m;
}
int main(int argc,char**argv){
 rclcpp::init(argc,argv);
 auto n=std::make_shared<rclcpp::Node>("execution_test",rclcpp::NodeOptions().parameter_overrides({
 rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("traversability_mode","ht_only"),rclcpp::Parameter("ht_validity_radius",.45),
 rclcpp::Parameter("ht_map_timeout",1000.),rclcpp::Parameter("ht_recovery_enabled",true)}));
 cmu_ht::Gate g(n);auto m=fixture(n);
 for(int r=0;r<81;r++)m.data[10].data[r+29*81]=1;
 g.receive(m);check(!g.pose({0,0,0}),"baseline circle rejects wall beside body");g.setBodyEnvelope(.6,.6);
 check(g.pose({0,0,0})&&g.command({0,0,0},.15,0)&&g.command({0,0,0},-.15,0),"body envelope permits forward and reverse along wall");
 check(g.pose({0,0,cmu_ht::pi/2})&&!g.segment({0,0,0},{0,0,cmu_ht::pi/2}),"clear turn endpoints cannot hide intermediate corner collision");
 check(!g.command({0,0,.45},0,1.),"braking sweep rejects corner hitting wall");
 check(!g.pose({0,.2,0}),"real body obstacle is rejected");
 auto blocked=m;blocked.data[9].data[40+40*81]=0;g.receive(blocked);check(!g.pose({0,0,0})&&g.last_reason=="HT_MISSING_SUPPORT","unknown support still rejected");
 blocked=m;blocked.data[0].data[40+40*81]=.1;g.receive(blocked);check(!g.pose({0,0,0})&&g.last_reason=="HT_DIRECTION_LOW","low HT score still rejected");
 blocked=m;blocked.data[10].data[40+40*81]=1;g.receive(blocked);check(!g.pose({0,0,0}),"arrival cannot erase new obstacle inside body");
 bool invalid=false;try{g.setBodyEnvelope(2,2);}catch(const std::invalid_argument&){invalid=true;}check(invalid,"oversized body rejected");
 m=fixture(n);g.receive(m);cmu_ht::Recovery rec(n,g);
 auto run=[&](const std::vector<cmu_ht::Pose>& path){
   size_t index=1;auto p=path.front();double pv=0,pw=0,v=0,w=0;
   for(int tick=0;tick<2000;tick++){
     const double oldv=pv,oldw=pw;rec.follow(path,index,p,.02,pv,pw,v,w);
     if(std::abs(v-oldv)>.050001||std::abs(w-oldw)>.060001)throw std::runtime_error("acceleration bound");
     if(!g.command(p,v,w,false))throw std::runtime_error("sweep rejected");
     if(index==path.size()){std::cout<<"route time="<<tick*.02<<" endpoint="<<p.x<<","<<p.y<<std::endl;return tick*.02;}
     for(int j=0;j<4;j++){p.yaw=cmu_ht::wrap(p.yaw+w*.005);p.x+=v*.005*std::cos(p.yaw);p.y+=v*.005*std::sin(p.yaw);}
   }throw std::runtime_error("route did not finish");
 };
 double t1=run({{0,0,-.261188596},{0,0,0},{.81871345,0,0}});
 double t2=run({{0,0,.52910769},{0,0,cmu_ht::pi/4},{-.04093567,-.04093567,cmu_ht::pi/4},{-.04093567,-.04093567,0},{.81871345,-.04093567,0}});
 check(t1<7. && t2<10.,"braking controller shortens both recorded-shape routes");
 size_t idx=1;double pv=0,pw=0,v=0,w=0;std::vector<cmu_ht::Pose> route={{0,0,0},{1,0,0}};
 rec.follow(route,idx,{1.004,0,0},.02,pv,pw,v,w);check(idx==2&&v==0&&w==0,"4mm overshoot completes without deadlock");
 idx=1;rec.follow(route,idx,{1.004,.05,0},.02,pv,pw,v,w);check(idx==1,"lateral miss is not accepted");
 rec.active_=true;rec.have_goal_=true;rec.goal_={3,0,0};rec.planned_goal_=rec.goal_;rec.route_=route;rec.index_=1;rec.previous_v_=.15;rec.last_tick_=1;
 for(int i=1;i<=5;i++)rec.select({.1,0,0},1+i*.02,1+i*.02,true,.03,false,0,0,v,w);
 check(std::abs(v)<=.030001,"active recovery follows new speed limit after braking");
 rec.select({.1,0,0},2,2,true,0,false,0,0,v,w);check(!rec.active()&&v==0&&w==0,"zero limit stops recovery");
 rec.active_=true;rec.route_=route;rec.index_=1;rec.progress_index_=0;rec.last_tick_=3;
 rec.select({.1,0,0},3,3,true,.15,false,0,0,v,w);rec.select({.1,0,0},5.1,5.1,true,.15,false,0,0,v,w);
 check(!rec.active()&&rec.state=="NO_PROGRESS"&&v==0&&w==0,"stuck pose releases recovery ownership");
 cmu_ht::Pose p{0,0,0};rec.setGoal({-.9,0,0},10);rec.next_plan_=0;
 for(int i=0;i<1000&&!rec.completed;i++){double t=10+i*.02;rec.select(p,t,t,true,.5,false,0,0,v,w);for(int j=0;j<4;j++){p.yaw=cmu_ht::wrap(p.yaw+w*.005);p.x+=v*.005*cos(p.yaw);p.y+=v*.005*sin(p.yaw);}}
 check(rec.completed&&p.x<-.5,"graph search and execution finish reverse recovery");
 rclcpp::shutdown();return 0;
}
