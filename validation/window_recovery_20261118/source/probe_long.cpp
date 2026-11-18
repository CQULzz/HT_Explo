#include "ht_gate.hpp"
#include <geometry_msgs/msg/point_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <std_msgs/msg/bool.hpp>
#include <queue>
#include <limits>
#define private public
#include "ht_recovery.hpp"
#undef private
#include <rclcpp/serialization.hpp>
#include <rcl/time.h>
#include <fstream>
#include <iostream>
#include <cstring>
int main(int argc,char**argv){
 rclcpp::init(argc,argv);
 auto n=std::make_shared<rclcpp::Node>("pathFollower",rclcpp::NodeOptions().parameter_overrides({
  rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("traversability_mode","ht_only"),
  rclcpp::Parameter("ht_validity_radius",.58182230175),rclcpp::Parameter("ht_use_urdf_envelope",true),
  rclcpp::Parameter("ht_body_min_xyz",std::vector<double>{-.4649301,-.3497950000007719,-.2351843}),
  rclcpp::Parameter("ht_body_max_xyz",std::vector<double>{.4649308,.34979500000080593,.6502000536441803}),
  rclcpp::Parameter("ht_recovery_enabled",true),rclcpp::Parameter("ht_recovery_search_ms",2000.)}));
 cmu_ht::Gate g(n);g.setBodyEnvelope(.6,.6);cmu_ht::Recovery rec(n,g);
 std::ifstream in("/home/lzz/ht_window_recovery_20261118/analysis/campus_stop.cdr",std::ios::binary);
 std::vector<char> b((std::istreambuf_iterator<char>(in)),{});if(b.empty())throw std::runtime_error("Missing recorded map");
 rclcpp::SerializedMessage s(b.size());auto& z=s.get_rcl_serialized_message();std::memcpy(z.buffer,b.data(),b.size());z.buffer_length=b.size();
 grid_map_msgs::msg::GridMap m;rclcpp::Serialization<grid_map_msgs::msg::GridMap>().deserialize_message(&s,&m);
 const double query=m.header.stamp.sec+m.header.stamp.nanosec*1e-9+.4;
 rcl_enable_ros_time_override(n->get_clock()->get_clock_handle());rcl_set_ros_time_override(n->get_clock()->get_clock_handle(),int64_t(query*1e9));g.receive(m);
 cmu_ht::Pose p{-4.210022449,-1.912616372,.973024487},goal{.172499999,0,0},origin=p;
 std::cout<<"origin_allowed="<<g.pose(p)<<std::endl;
 bool planned=rec.plan(p,goal);std::cout<<"direct_plan="<<planned<<" search_ms="<<rec.last_search_ms<<" reason="<<g.last_reason<<" nodes="<<rec.route().size()<<std::endl;
 for(auto q:rec.route())std::cout<<"route,"<<q.x<<","<<q.y<<","<<q.yaw<<std::endl;
 rec.setGoal(goal,query);rec.finished_=true;double v=0,w=0;
 std::ofstream out("/home/lzz/ht_window_recovery_20261118/analysis/probe_trace.csv");out<<"elapsed_s,x,y,yaw,v,w,state\n";out<<std::setprecision(15);
 bool ever_active=false;int moving=0;double minscore=1.;
 for(int tick=0;tick<3000;++tick){double t=query+tick*.02;
  rec.select(p,t,t,true,.5,true,0,0,v,w);ever_active|=rec.active();
  if(std::abs(v)+std::abs(w)>1e-8){++moving;if(!g.command(p,v,w,false))throw std::runtime_error("unsafe output");}
  out<<tick*.02<<","<<p.x<<","<<p.y<<","<<p.yaw<<","<<v<<","<<w<<","<<rec.state<<"\n";
  if(rec.completed)break;
  for(int j=0;j<4;++j){p.yaw=cmu_ht::wrap(p.yaw+w*.005);p.x+=v*.005*std::cos(p.yaw);p.y+=v*.005*std::sin(p.yaw);}
 }
 std::cout<<"finished_flag="<<rec.finished_<<" active_seen="<<ever_active<<" completed="<<rec.completed<<" moving_ticks="<<moving<<" progress="<<std::hypot(origin.x-goal.x,origin.y-goal.y)-std::hypot(p.x-goal.x,p.y-goal.y)<<" state="<<rec.state<<" invalidated="<<rec.invalidated<<std::endl;
 rclcpp::shutdown();
}
