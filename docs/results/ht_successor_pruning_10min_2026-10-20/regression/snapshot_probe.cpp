#include <gtest/gtest.h>
#include "/home/lzz/my test/HT_Explo-fixposition/docs/fixes/evidence/2026-10-20_successor_pruning/baseline_search.h"
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
 const char* fixture=std::getenv("HT_SEARCH_FIXTURE");ASSERT_NE(fixture,nullptr);const std::string dir=std::string(fixture)+"/";
 const char* params=std::getenv("HT_PROBE_PARAMETERS");ASSERT_NE(params,nullptr);
 rclcpp::NodeOptions options;options.arguments({"--ros-args","--params-file",params});options.automatically_declare_parameters_from_overrides(false);
 auto node=std::make_shared<rclcpp::Node>("tare_planner_node",options);for(const auto& entry:node->get_node_parameters_interface()->get_parameter_overrides())if(entry.first.rfind("ht_",0)!=0 && !node->has_parameter(entry.first))node->declare_parameter(entry.first,entry.second);viewpoint_manager_ns::ViewPointManager manager(node);
 const Eigen::Vector3d robot(15.596904754638672,25.37972068786621,0.8770562410354614);const Pose2 start{robot.x(),robot.y(),-3.0564918518066406};
 manager.UpdateRobotPosition({.370797723531723,3.1604135036468506,0.8770562410354614});manager.UpdateRobotPosition(robot);
 auto cloudFrom=[&](std::string file){auto cloud=std::make_shared<pcl::PointCloud<pcl::PointXYZI>>();std::ifstream f(dir+file+".csv");std::string l;std::getline(f,l);while(std::getline(f,l)){std::replace(l.begin(),l.end(),',',' ');std::istringstream s(l);pcl::PointXYZI p;if(s>>p.x>>p.y>>p.z>>p.intensity)cloud->push_back(p);}return cloud;};
 manager.CheckViewPointCollision(cloudFrom("collision_cloud"));
 // Reconstruct horizon membership/heights from recorded public visualizations.
 // This is a frozen public-message approximation, not exact internal state.
 for(int i=0;i<manager.GetViewPointNum();++i){manager.SetViewPointCandidate(i,false);manager.SetViewPointCollision(i,false);}
 for(auto name:{"viewpoint_vis_cloud","viewpoint_in_collision_cloud_"})for(const auto& p:cloudFrom(name)->points){int id=manager.GetViewPointInd(Eigen::Vector3d(p.x,p.y,p.z));if(!manager.InRange(id))continue;manager.SetViewPointHeight(id,p.z);if(std::string(name)=="viewpoint_vis_cloud")manager.SetViewPointCandidate(id,true);else manager.SetViewPointCollision(id,true);}
 std::ifstream in(dir+"ht_map.cdr",std::ios::binary);std::vector<char> bytes((std::istreambuf_iterator<char>(in)),{});ASSERT_FALSE(bytes.empty());rclcpp::SerializedMessage serialized(bytes.size());auto& raw=serialized.get_rcl_serialized_message();std::memcpy(raw.buffer,bytes.data(),bytes.size());raw.buffer_length=bytes.size();grid_map_msgs::msg::GridMap msg;rclcpp::Serialization<grid_map_msgs::msg::GridMap> codec;codec.deserialize_message(&serialized,&msg);
 auto pub=node->create_publisher<grid_map_msgs::msg::GridMap>(node->get_parameter("ht_topic").as_string(),rclcpp::QoS(1).reliable());
 for(int k=0;k<30;++k){msg.header.stamp=node->now();pub->publish(msg);rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(20));}auto ht=manager.HT();ht->beginCycle();ASSERT_TRUE(ht->ready());

 auto refresh=[&](){for(int k=0;k<3;++k){msg.header.stamp=node->now();pub->publish(msg);rclcpp::spin_some(node);std::this_thread::sleep_for(std::chrono::milliseconds(5));}ht->beginCycle();ASSERT_TRUE(ht->ready());};
 XYThetaConfig cfg;cfg.headings=32;cfg.turn_angles={kPi/16,kPi/8};cfg.goal_radius=.35;cfg.try_direct_connection=true;
 struct Run{XYThetaPlan plan;size_t calls;double wall;};
 auto run=[&](Point goal,bool optimized,int limit,double budget){refresh();cfg.max_expansions=limit;cfg.max_search_seconds=budget;size_t calls=0;
  auto valid=[&](Pose2 a,Pose2 b,double v){++calls;if(manager.InCollisionAtPose({b.x,b.y,robot.z()},std::abs(v)>1e-9?.12:0))return false;return ht->permits(ht->motionSupport(a,b));};
  auto begin=std::chrono::steady_clock::now();auto result=optimized?planXYTheta(start,goal,cfg,valid):planXYThetaBaseline(start,goal,cfg,valid);double wall=std::chrono::duration<double>(std::chrono::steady_clock::now()-begin).count();
  std::cout<<"MEASURE goal="<<goal.x<<","<<goal.y<<" optimized="<<optimized<<" limit="<<limit<<" budget="<<budget<<" term="<<terminationName(result.termination)<<" expanded="<<result.expanded<<" queries="<<calls<<" pruned="<<result.dominated_edges_pruned<<" poses="<<result.poses.size()<<" seconds="<<result.seconds<<" wall="<<wall<<std::endl;return Run{result,calls,wall};};
 for(Point goal:std::vector<Point>{{16.570798,21.760414,0},{15.370798,21.760414,0},{12.970798,25.360414,0},{17.770798,21.760414,0}}){
  auto old=run(goal,false,256,2);auto current=run(goal,true,256,2);
  ASSERT_EQ(old.plan.termination,current.plan.termination);ASSERT_EQ(old.plan.expanded,current.plan.expanded);ASSERT_EQ(old.plan.poses.size(),current.plan.poses.size());
  if(old.plan.reached){ASSERT_DOUBLE_EQ(old.plan.seconds,current.plan.seconds);for(size_t i=0;i<old.plan.poses.size();++i){ASSERT_DOUBLE_EQ(old.plan.poses[i].x,current.plan.poses[i].x);ASSERT_DOUBLE_EQ(old.plan.poses[i].y,current.plan.poses[i].y);ASSERT_DOUBLE_EQ(old.plan.poses[i].yaw,current.plan.poses[i].yaw);}}
  for(int repeat=0;repeat<3;++repeat)for(double budget:{.075,.15})for(bool optimized:{false,true})run(goal,optimized,8000,budget);
 }
}
