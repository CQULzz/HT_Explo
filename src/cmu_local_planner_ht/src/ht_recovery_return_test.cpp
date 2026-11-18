#include "ht_gate.hpp"
#include <geometry_msgs/msg/point_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <std_msgs/msg/bool.hpp>
#include <queue>
#include <limits>
// Inspect the same retained phase flag set by the ROS finish subscription.
#define private public
#include "ht_recovery.hpp"
#undef private
#include <rcl/time.h>
#include <iostream>

void require(bool value,const char* message) {
  if(!value)throw std::runtime_error(message);
  std::cout<<"PASS "<<message<<std::endl;
}
grid_map_msgs::msg::GridMap mapFixture(rclcpp::Node::SharedPtr node) {
  grid_map_msgs::msg::GridMap m;m.header.frame_id="map";m.header.stamp=node->now();
  m.info.resolution=.04;m.info.length_x=m.info.length_y=101*.04;m.info.pose.orientation.w=1;
  for(int k=0;k<11;++k) {
    m.layers.push_back(k<8?"ht_dir_"+std::to_string(k):k==8?"ht_valid":k==9?"ht_observation_valid":"ht_obstacle");
    std_msgs::msg::Float32MultiArray a;a.layout.dim.resize(2);
    a.layout.dim[0].label="column_index";a.layout.dim[1].label="row_index";
    a.layout.dim[0].size=a.layout.dim[1].size=101;
    a.layout.dim[0].stride=101*101;a.layout.dim[1].stride=101;
    a.data.assign(101*101,k<8?.9:k<10?1:0);m.data.push_back(a);
  }
  return m;
}
int main(int argc,char**argv) {
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("recovery_return_test",rclcpp::NodeOptions().parameter_overrides({
    rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("traversability_mode","ht_only"),
    rclcpp::Parameter("ht_validity_radius",.45),rclcpp::Parameter("ht_recovery_enabled",true)}));
  cmu_ht::Gate gate(node);gate.setBodyEnvelope(.6,.6);cmu_ht::Recovery recovery(node,gate);
  auto original=mapFixture(node);const double query=node->now().seconds()+.1;
  require(rcl_enable_ros_time_override(node->get_clock()->get_clock_handle())==RCL_RET_OK &&
    rcl_set_ros_time_override(node->get_clock()->get_clock_handle(),int64_t(query*1e9))==RCL_RET_OK,"fixture clock is frozen for static-map execution only");
  gate.receive(original);
  auto finish=node->create_publisher<std_msgs::msg::Bool>("/exploration_finish",5);
  std_msgs::msg::Bool message;message.data=true;
  for(int i=0;i<100 && !recovery.finished_;++i) {
    finish->publish(message);rclcpp::spin_some(node);
    if(!recovery.finished_)rclcpp::sleep_for(std::chrono::milliseconds(2));
  }
  require(recovery.finished_,"real exploration_finish subscription sets the return phase");
  recovery.setGoal({1,0,0},query);
  cmu_ht::Pose p{0,0,0};double v=0,w=0,pv=0,pw=0;bool moved=false;
  for(int tick=0;tick<1000 && !recovery.completed;++tick) {
    const double now=query+tick*.02;
    // The native zero command can be HT_ALLOWED despite no local path.
    recovery.select(p,now,now,true,.5,true,0,0,v,w);
    if(std::abs(v-pv)>.050001 || std::abs(w-pw)>.060001)throw std::runtime_error("return acceleration limit");
    if(std::abs(v)+std::abs(w)>1e-8) {
      moved=true;if(!gate.command(p,v,w,false))throw std::runtime_error("unsafe return command");
    }
    pv=v;pw=w;
    for(int j=0;j<4;++j){p.yaw=cmu_ht::wrap(p.yaw+w*.005);p.x+=v*.005*std::cos(p.yaw);p.y+=v*.005*std::sin(p.yaw);}
  }
  require(moved && recovery.completed && p.x>.5,"exploration finish still permits checked return recovery from an allowed zero command");
  const auto completed=recovery.completed;
  recovery.select({1,0,0},query+30,query+30,true,.5,true,0,0,v,w);
  require(!recovery.active() && recovery.state=="RETURN_GOAL_REACHED" && recovery.completed==completed,"arrival at retained return goal does not restart recovery");

  // The context frontier is only0.4m away: the old fixed0.75m objective
  // rejected every reachable prefix even though a shorter checked one exists.
  auto pocket=original;
  for(int r=0;r<101;++r)for(int c=0;c<101;++c) {
    const double x=(50-r)*.04;
    if(x>.4)pocket.data[8].data[r+c*101]=0;
  }
  gate.receive(pocket);recovery.reset("IDLE");recovery.next_plan_=0;recovery.setGoal({1,0,0},query+40);
  require(recovery.plan({0,0,0},{1,0,0}),"short safe HT pocket produces an executable prefix");
  const auto route=recovery.route();
  require(route.back().x>=.25 && route.back().x<=.4 && gate.path(route),"partial prefix stops before invalid context");
  require(recovery.last_search_outcome=="PARTIAL_PROGRESS" && recovery.last_search_progress>=.25,"partial progress is explicitly diagnosed");
  require(!gate.pose({.48,0,0}) && gate.last_reason=="HT_CONTEXT_INVALID","forward context veto remains enforced");
  auto tiny=original;
  for(int r=0;r<101;++r)for(int c=0;c<101;++c)
    if((50-r)*.04>.12)tiny.data[8].data[r+c*101]=0;
  gate.receive(tiny);
  require(!recovery.plan({0,0,0},{1,0,0}),"tiny progress cannot create repeated recovery ownership");

  auto refuses=[&](grid_map_msgs::msg::GridMap m,const char* reason) {
    gate.receive(m);recovery.reset("IDLE");recovery.next_plan_=0;
    recovery.setGoal({1,0,0},query+50);const auto plans=recovery.plans;
    recovery.select({0,0,0},query+50,query+50,true,.5,true,0,0,v,w);
    recovery.select({0,0,0},query+50.5,query+50.5,true,.5,true,0,0,v,w);
    require(!recovery.active() && recovery.plans==plans && v==0 && w==0,"return recovery cannot bypass invalid origin");
    require(recovery.state==std::string("START_INVALID:")+reason,"invalid return origin reports its actual gate reason");
  };
  auto invalid=original;invalid.data[8].data[50+50*101]=0;refuses(invalid,"HT_CONTEXT_INVALID");
  invalid=original;invalid.data[9].data[50+50*101]=0;refuses(invalid,"HT_MISSING_SUPPORT");
  invalid=original;invalid.data[10].data[50+50*101]=1;refuses(invalid,"HT_OCCUPIED");
  invalid=original;invalid.data[0].data[50+50*101]=.1;refuses(invalid,"HT_DIRECTION_LOW");
  invalid=original;invalid.header.stamp.sec-=2;refuses(invalid,"HT_MAP_STALE");
  gate.receive(original);recovery.reset("IDLE");recovery.setGoal({1,0,0},query+60);
  recovery.select({0,0,0},query+60,query+59,true,.5,true,0,0,v,w);
  require(v==0 && w==0 && recovery.state=="ODOMETRY_STALE","finished exploration does not bypass odometry TTL");
  recovery.select({0,0,0},query+61,query+61,false,.5,true,0,0,v,w);
  require(!recovery.active() && recovery.state=="PAUSED","pause still inhibits return recovery");
  recovery.select({0,0,0},query+62,query+62,true,0,true,0,0,v,w);
  require(v==0 && w==0 && recovery.state=="SPEED_LIMIT","zero speed limit still inhibits return recovery");
  rclcpp::shutdown();return 0;
}
