#include <gtest/gtest.h>
#include "viewpoint_manager/viewpoint_manager.h"
#include <rclcpp/serialization.hpp>
#include <fstream>
#include <sstream>
#include <cstring>
#include <thread>
#include <iostream>
using namespace ht_cost_ns;
TEST(SnapshotSearch, RecordedStoppedEnvironment){
 if(!rclcpp::ok())rclcpp::init(0,nullptr);
 const std::string dir="/tmp/ht_stopped_search_fixture_195/";
 const char* params=std::getenv("HT_PROBE_PARAMETERS");ASSERT_NE(params,nullptr);
 rclcpp::NodeOptions options;options.arguments({"--ros-args","--params-file",params});options.automatically_declare_parameters_from_overrides(false);
 auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);for(const auto& entry:node->get_node_parameters_interface()->get_parameter_overrides())if(entry.first.rfind("ht_",0)!=0 && !node->has_parameter(entry.first))node->declare_parameter(entry.first,entry.second);viewpoint_manager_ns::ViewPointManager manager(node);
 const Eigen::Vector3d robot(13.107903480529785,5.560585975646973,.7473725080490112);const Pose2 start{robot.x(),robot.y(),1.813777685165405};
 manager.UpdateRobotPosition({0,0,.75});manager.UpdateRobotPosition(robot);
 auto cloudFrom=[&](std::string file){auto cloud=std::make_shared<pcl::PointCloud<pcl::PointXYZI>>();std::ifstream f(dir+file+".csv");std::string l;std::getline(f,l);while(std::getline(f,l)){std::replace(l.begin(),l.end(),',',' ');std::istringstream s(l);pcl::PointXYZI p;if(s>>p.x>>p.y>>p.z>>p.intensity)cloud->push_back(p);}return cloud;};
 manager.CheckViewPointCollision(cloudFrom("collision_cloud"));
 // Reconstruct horizon membership/heights from recorded public visualizations.
 // This is a frozen public-message approximation, not exact internal state.
 for(int i=0;i<manager.GetViewPointNum();++i){manager.SetViewPointCandidate(i,false);manager.SetViewPointCollision(i,false);}
 for(auto name:{"viewpoint_vis_cloud","viewpoint_in_collision_cloud_"})for(const auto& p:cloudFrom(name)->points){int id=manager.GetViewPointInd(Eigen::Vector3d(p.x,p.y,p.z));if(!manager.InRange(id))continue;manager.SetViewPointHeight(id,p.z);if(std::string(name)=="viewpoint_vis_cloud")manager.SetViewPointCandidate(id,true);else manager.SetViewPointCollision(id,true);}
 std::ifstream in(dir+"ht_map.cdr",std::ios::binary);std::vector<char> bytes((std::istreambuf_iterator<char>(in)),{});ASSERT_FALSE(bytes.empty());rclcpp::SerializedMessage serialized(bytes.size());auto& raw=serialized.get_rcl_serialized_message();std::memcpy(raw.buffer,bytes.data(),bytes.size());raw.buffer_length=bytes.size();grid_map_msgs::msg::GridMap msg;rclcpp::Serialization<grid_map_msgs::msg::GridMap> codec;codec.deserialize_message(&serialized,&msg);
 auto pub=node->create_publisher<grid_map_msgs::msg::GridMap>(node->get_parameter("ht_topic").as_string(),rclcpp::QoS(1).reliable());
 for(int k=0;k<30;++k){msg.header.stamp=node->now();pub->publish(msg);rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(20));}auto ht=manager.HT();ht->beginCycle();ASSERT_TRUE(ht->ready());
 size_t calls=0,geom_reject=0,ht_reject=0;
 auto valid=[&](Pose2 a,Pose2 b,double v){++calls;if(manager.InCollisionAtPose({b.x,b.y,robot.z()},std::abs(v)>1e-9?.12:0)){++geom_reject;return false;}if(!ht->permits(ht->motionSupport(a,b))){++ht_reject;return false;}return true;};
 ASSERT_TRUE(valid(start,start,0));XYThetaConfig cfg;cfg.headings=32;cfg.turn_angles={kPi/16,kPi/8};cfg.goal_radius=.35;
 for(Point goal:std::vector<Point>{{12.75,2.85,0},{13.05,2.25,0},{12.45,6.15,0}}){
  for(bool reverse:{false,true}){
   calls=geom_reject=ht_reject=0;Pose2 p=start;const double distance=std::hypot(goal.x-p.x,goal.y-p.y);const double angle=wrapYaw(std::atan2(goal.y-p.y,goal.x-p.x)+(reverse?kPi:0));const double delta=wrapYaw(angle-p.yaw);bool ok=true;
   int n=std::max(1,int(std::ceil(std::abs(delta)/.05)));for(int i=1;i<=n&&ok;++i){Pose2 q=start;q.yaw=wrapYaw(start.yaw+delta*i/n);ok=valid(p,q,0);p=q;}
   const Pose2 turn_end=p;n=std::max(1,int(std::ceil(distance/.05)));for(int i=1;i<=n&&ok;++i){Pose2 q=turn_end;q.x=turn_end.x+(goal.x-turn_end.x)*i/n;q.y=turn_end.y+(goal.y-turn_end.y)*i/n;ok=valid(p,q,reverse?-cfg.reverse_speed:cfg.forward_speed);p=q;}
   std::cout<<"DIRECT goal="<<goal.x<<","<<goal.y<<" reverse="<<reverse<<" allowed="<<ok<<" queries="<<calls<<" geometry_reject="<<geom_reject<<" ht_reject="<<ht_reject<<std::endl;
  }
  for(double budget:{.075,.15,1.0}){calls=geom_reject=ht_reject=0;cfg.max_search_seconds=budget;auto b=std::chrono::steady_clock::now();auto plan=planXYTheta(start,goal,cfg,valid);std::cout<<"SEARCH goal="<<goal.x<<","<<goal.y<<" budget="<<budget<<" term="<<terminationName(plan.termination)<<" expanded="<<plan.expanded<<" queries="<<calls<<" geometry_reject="<<geom_reject<<" ht_reject="<<ht_reject<<" wall_s="<<std::chrono::duration<double>(std::chrono::steady_clock::now()-b).count()<<std::endl;}
 }
}
