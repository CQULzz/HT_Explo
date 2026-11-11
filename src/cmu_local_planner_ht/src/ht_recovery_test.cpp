#include "ht_recovery.hpp"
#include <rclcpp/serialization.hpp>
#include <rcl/time.h>
#include <fstream>
#include <cstring>
#include <iostream>

int main(int argc,char** argv) {
  rclcpp::init(argc,argv);
  auto node=std::make_shared<rclcpp::Node>("ht_recovery_fixture",rclcpp::NodeOptions().parameter_overrides({
    rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("traversability_mode","ht_only"),
    rclcpp::Parameter("ht_validity_radius",.45),rclcpp::Parameter("ht_recovery_enabled",true)}));
  cmu_ht::Gate gate(node);cmu_ht::Recovery recovery(node,gate);
  std::ifstream file("/home/lzz/ht_only_20261111/analysis/live_indoor_stop/global_local.cdr",std::ios::binary);
  std::vector<char> bytes((std::istreambuf_iterator<char>(file)),{});
  if(bytes.empty())throw std::runtime_error("Missing frozen HT fixture");
  rclcpp::SerializedMessage serialized(bytes.size());auto& buffer=serialized.get_rcl_serialized_message();
  std::memcpy(buffer.buffer,bytes.data(),bytes.size());buffer.buffer_length=bytes.size();
  grid_map_msgs::msg::GridMap map;rclcpp::Serialization<grid_map_msgs::msg::GridMap> serializer;serializer.deserialize_message(&serialized,&map);
  const double stamp=map.header.stamp.sec+map.header.stamp.nanosec*1e-9,query=stamp+.4;
  if(rcl_enable_ros_time_override(node->get_clock()->get_clock_handle())!=RCL_RET_OK ||
     rcl_set_ros_time_override(node->get_clock()->get_clock_handle(),int64_t(query*1e9))!=RCL_RET_OK)throw std::runtime_error("Clock override failed");
  gate.receive(map);cmu_ht::Pose pose{14.641681671142578,8.538067817687988,-2.497877836227417};
  const cmu_ht::Pose goal{11.849130669080782,1.0412912503302776},origin=pose;
  if(!gate.pose(pose))throw std::runtime_error("Recorded origin is not valid");
  double old_v=.05,old_w=.471234679;
  if(gate.chooseCommand(pose,old_v,old_w))throw std::runtime_error("Old rejected controller fixture unexpectedly allowed");
  std::cout<<"PASS old native command and its angular projections remain rejected"<<std::endl;
  std::ofstream trace("/home/lzz/ht_recovery_20261111/analysis/fixture_trace.csv");
  trace<<"time,x,y,yaw,linear,angular,map_stamp,query_time\n";trace<<std::setprecision(15);
  double v=0,w=0,previous_v=0,previous_w=0,max_accel=0,max_angular_accel=0;bool complete=false;
  recovery.setGoal(goal,0);bool updated_goal=false;
  for(int tick=0;tick<2250;++tick) {
    const double t=tick*.02;
    if(!updated_goal && t>=5.6){recovery.setGoal({goal.x+(goal.x-origin.x)*.2,goal.y+(goal.y-origin.y)*.2,0},t);updated_goal=true;}
    recovery.select(pose,t,t,true,.5,false,0,0,v,w);
    trace<<t<<","<<pose.x<<","<<pose.y<<","<<pose.yaw<<","<<v<<","<<w<<","<<stamp<<","<<query<<"\n";
    max_accel=std::max(max_accel,std::abs(v-previous_v)/.02);max_angular_accel=std::max(max_angular_accel,std::abs(w-previous_w)/.02);
    previous_v=v;previous_w=w;
    if(recovery.completed){complete=true;break;}
    // Match CMU vehicleSimulator's 200Hz yaw-first velocity integration.
    for(int substep=0;substep<4;++substep){pose.yaw=cmu_ht::wrap(pose.yaw+w*.005);pose.x+=v*.005*std::cos(pose.yaw);pose.y+=v*.005*std::sin(pose.yaw);}
  }
  trace.close();const double movement=std::hypot(pose.x-origin.x,pose.y-origin.y);
  const double progress=std::hypot(origin.x-goal.x,origin.y-goal.y)-std::hypot(pose.x-goal.x,pose.y-goal.y);
  std::cout<<"fixture state="<<recovery.state<<" plans="<<recovery.plans<<" completed="<<recovery.completed<<" invalidated="<<recovery.invalidated
           <<" movement="<<movement<<" goal_progress="<<progress<<" search_ms="<<recovery.last_search_ms<<" accel="<<max_accel<<" angular_accel="<<max_angular_accel<<std::endl;
  if(!complete || progress<.5 || recovery.invalidated || max_accel>2.50001 || max_angular_accel>3.00001)throw std::runtime_error("Recovery fixture failed");
  std::cout<<"PASS recorded blocked pose executed continuous recovery with progress and limits"<<std::endl;
  if(recovery.compatible_goal_updates!=1 || recovery.plans!=1)throw std::runtime_error("Compatible waypoint update restarted recovery");
  std::cout<<"PASS retained waypoint survives publication gap and compatible update preserves recovery"<<std::endl;
  const auto plans=recovery.plans;double rejected_v=1,rejected_w=1;
  recovery.select(pose,100,99,true,.5,false,0,0,rejected_v,rejected_w);
  if(rejected_v || rejected_w || recovery.plans!=plans)throw std::runtime_error("Stale odometry bypassed");
  std::cout<<"PASS stale odometry stops recovery"<<std::endl;
  map.header.stamp.sec-=2;gate.receive(map);recovery.setGoal(goal,101);rejected_v=rejected_w=0;
  recovery.select(pose,101,101,true,.5,false,0,0,rejected_v,rejected_w);
  recovery.select(pose,102,102,true,.5,false,0,0,rejected_v,rejected_w);
  if(recovery.plans!=plans || rejected_v || rejected_w)throw std::runtime_error("Stale map bypassed");
  std::cout<<"PASS stale map cannot be bypassed by recovery"<<std::endl;
  auto reverse_node=std::make_shared<rclcpp::Node>("ht_recovery_reverse",rclcpp::NodeOptions().parameter_overrides({
    rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("traversability_mode","ht_only"),
    rclcpp::Parameter("ht_validity_radius",.45),rclcpp::Parameter("ht_recovery_enabled",true)}));
  cmu_ht::Gate reverse_gate(reverse_node);cmu_ht::Recovery reverse_recovery(reverse_node,reverse_gate);
  grid_map_msgs::msg::GridMap synthetic;synthetic.header.frame_id="map";synthetic.header.stamp=reverse_node->now();
  synthetic.info.resolution=.04;synthetic.info.length_x=synthetic.info.length_y=81*.04;synthetic.info.pose.orientation.w=1;
  for(int k=0;k<11;++k){synthetic.layers.push_back(k<8?"ht_dir_"+std::to_string(k):k==8?"ht_valid":k==9?"ht_observation_valid":"ht_obstacle");
    std_msgs::msg::Float32MultiArray array;array.layout.dim.resize(2);array.layout.dim[0].label="column_index";array.layout.dim[1].label="row_index";
    array.layout.dim[0].size=array.layout.dim[1].size=81;array.layout.dim[0].stride=81*81;array.layout.dim[1].stride=81;
    array.data.assign(81*81,k==4?.1:k<8?.9:k<10?1:0);synthetic.data.push_back(array);}
  reverse_gate.receive(synthetic);cmu_ht::Pose reverse_pose{0,0,0};double min_v=0,max_yaw=0;
  double reverse_time=0,rv_before=0,rw_before=0,previous_control=0;
  for(int tick=0;tick<2000 && !reverse_recovery.completed;++tick){double rv=0,rw=0;
    reverse_recovery.setGoal({-1,0,0},reverse_time);
    reverse_recovery.select(reverse_pose,reverse_time,reverse_time,true,.5,false,0,0,rv,rw);
    if(tick>0 && (std::abs(rv-rv_before)>2.5*(reverse_time-previous_control)+1e-7 || std::abs(rw-rw_before)>3.*(reverse_time-previous_control)+1e-7))throw std::runtime_error("Jittered recovery output exceeded acceleration limit");
    rv_before=rv;rw_before=rw;previous_control=reverse_time;min_v=std::min(min_v,rv);max_yaw=std::max(max_yaw,std::abs(reverse_pose.yaw));
    const double timing[3]={.02,.001,.019};const double dt=timing[tick%3];
    for(double remaining=dt;remaining>1e-10;){double sub=std::min(.005,remaining);reverse_pose.yaw=cmu_ht::wrap(reverse_pose.yaw+rw*sub);reverse_pose.x+=rv*sub*std::cos(reverse_pose.yaw);reverse_pose.y+=rv*sub*std::sin(reverse_pose.yaw);remaining-=sub;}
    reverse_time+=dt;
  }
  std::cout<<"reverse state="<<reverse_recovery.state<<" x="<<reverse_pose.x<<" min_v="<<min_v<<" max_yaw="<<max_yaw<<" completed="<<reverse_recovery.completed<<std::endl;
  if(!reverse_recovery.completed || reverse_pose.x>-.5 || min_v>-.1 || max_yaw>.03)throw std::runtime_error("Reverse execution did not preserve actual allowed body yaw");
  std::cout<<"PASS recovery executes reverse while opposite travel-direction channel is forbidden"<<std::endl;
  double cancel_v=0,cancel_w=0;reverse_recovery.setGoal({-1,0,0},100);
  reverse_recovery.select({0,0,0},100,100,true,.5,false,0,0,cancel_v,cancel_w);
  reverse_recovery.select({0,0,0},100.5,100.5,true,.5,false,0,0,cancel_v,cancel_w);
  if(!reverse_recovery.active())throw std::runtime_error("Cancellation fixture failed to start");
  reverse_recovery.setGoal({1,0,0},100.52);
  reverse_recovery.select({0,0,0},100.52,100.52,true,.5,false,0,0,cancel_v,cancel_w);
  if(reverse_recovery.active() || reverse_recovery.state!="GOAL_CHANGED" || cancel_v || cancel_w || reverse_recovery.goal_cancellations!=1)throw std::runtime_error("Opposite target failed to cancel recovery");
  std::cout<<"PASS incompatible waypoint update cancels and stops recovery"<<std::endl;
  synthetic.data[9].data[40+40*81]=0;reverse_gate.receive(synthetic);
  if(reverse_recovery.plan({0,0,0},{-1,0,0}))throw std::runtime_error("Recovery search bypassed unknown origin");
  std::cout<<"PASS recovery search rejects unknown footprint at its origin"<<std::endl;
  synthetic.data[9].data[40+40*81]=1;synthetic.data[10].data[40+40*81]=1;reverse_gate.receive(synthetic);
  if(reverse_recovery.plan({0,0,0},{-1,0,0}))throw std::runtime_error("Recovery search bypassed occupied origin");
  std::cout<<"PASS recovery search rejects occupied footprint at its origin"<<std::endl;
  rclcpp::shutdown();return 0;
}
