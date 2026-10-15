#include "ht_cost/xytheta_planner.h"
#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <nav_msgs/msg/path.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/int8.hpp>
#include <algorithm>
#include <chrono>

namespace {
using ht_cost_ns::Pose2;
using ht_cost_ns::wrapYaw;
double clamp(double value,double limit) {return std::clamp(value,-limit,limit);}
Pose2 poseOf(const geometry_msgs::msg::Pose& pose) {
  const auto& q=pose.orientation;
  return {pose.position.x,pose.position.y,
    wrapYaw(std::atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))};
}
int gear(Pose2 a,Pose2 b) {
  const double dx=b.x-a.x,dy=b.y-a.y;
  if (std::hypot(dx,dy)<1e-4) return 0;
  return dx*std::cos(a.yaw)+dy*std::sin(a.yaw)>=0 ? 1 : -1;
}
}

class XYThetaFollower : public rclcpp::Node {
 public:
  XYThetaFollower() : Node("xytheta_follower") {
    max_speed_=declare_parameter<double>("max_speed",0.5);
    max_reverse_=declare_parameter<double>("max_reverse",0.25);
    max_yaw_rate_=declare_parameter<double>("max_yaw_rate",0.8);
    max_accel_=declare_parameter<double>("max_accel",0.5);
    max_yaw_accel_=declare_parameter<double>("max_yaw_accel",1.2);
    path_timeout_=declare_parameter<double>("path_timeout",3.0);
    odom_timeout_=declare_parameter<double>("odom_timeout",0.5);
    // TARE publishes this permission in its 1 Hz planning callback. A 0.5 s
    // timeout makes the vehicle stop for half of every healthy cycle.
    permission_timeout_=declare_parameter<double>("permission_timeout",1.5);
    path_sub_=create_subscription<nav_msgs::msg::Path>("/ht_xytheta_path",rclcpp::QoS(1).reliable(),
      [this](nav_msgs::msg::Path::ConstSharedPtr msg) {
        path_.clear();index_=1;
        if (msg->header.frame_id!="map") return;
        for (const auto& stamped:msg->poses) {
          const auto pose=poseOf(stamped.pose);
          if (!std::isfinite(pose.x) || !std::isfinite(pose.y) || !std::isfinite(pose.yaw)) {
            path_.clear();return;
          }
          path_.push_back(pose);
        }
        path_received_=now().seconds();
      });
    odom_sub_=create_subscription<nav_msgs::msg::Odometry>("/state_estimation",5,
      [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) {
        robot_=poseOf(msg->pose.pose);odom_received_=now().seconds();
      });
    permission_sub_=create_subscription<std_msgs::msg::Bool>("/ht_navigation_allowed",5,
      [this](std_msgs::msg::Bool::ConstSharedPtr msg) {
        permitted_=msg->data;permission_received_=now().seconds();
      });
    stop_sub_=create_subscription<std_msgs::msg::Int8>("/stop",5,
      [this](std_msgs::msg::Int8::ConstSharedPtr msg) {stop_=msg->data;});
    cmd_pub_=create_publisher<geometry_msgs::msg::TwistStamped>("/cmd_vel",5);
    timer_=create_wall_timer(std::chrono::milliseconds(50),[this]() {tick();});
  }
 private:
  void tick() {
    const double now_s=now().seconds();
    geometry_msgs::msg::TwistStamped cmd;
    cmd.header.stamp=now();cmd.header.frame_id="vehicle";
    const bool fresh=odom_received_>0 && now_s-odom_received_<odom_timeout_ &&
      path_received_>0 && now_s-path_received_<path_timeout_ &&
      permission_received_>0 && now_s-permission_received_<permission_timeout_;
    if (!fresh || !permitted_ || stop_>=1 || path_.size()<2) {
      linear_=0;angular_=0;cmd_pub_->publish(cmd);return;
    }
    while (index_<path_.size()) {
      const auto& p=path_[index_];
      const double distance=std::hypot(p.x-robot_.x,p.y-robot_.y);
      const double yaw_error=std::abs(wrapYaw(p.yaw-robot_.yaw));
      if (distance>0.12 || (gear(path_[index_-1],p)==0 && yaw_error>0.14)) break;
      ++index_;
    }
    if (index_>=path_.size()) {
      linear_=0;angular_=0;cmd_pub_->publish(cmd);return;
    }
    const int direction=gear(path_[index_-1],path_[index_]);
    size_t target_index=index_;
    if (direction!=0) {
      double ahead=0;
      while (target_index+1<path_.size() && ahead<0.35) {
        const auto& a=path_[target_index];const auto& b=path_[target_index+1];
        if (gear(a,b)!=direction || std::abs(wrapYaw(b.yaw-a.yaw))>0.25) break;
        ahead+=std::hypot(b.x-a.x,b.y-a.y);
        ++target_index;
      }
    }
    const auto& target=path_[target_index];
    double wanted_v=0,wanted_w=0;
    if (direction==0) {
      wanted_w=clamp(2.5*wrapYaw(target.yaw-robot_.yaw),max_yaw_rate_);
    } else {
      const double bearing=std::atan2(target.y-robot_.y,target.x-robot_.x);
      const double travel_yaw=robot_.yaw+(direction<0?ht_cost_ns::kPi:0);
      const double bearing_error=wrapYaw(bearing-travel_yaw);
      const double pose_error=wrapYaw(target.yaw-robot_.yaw);
      wanted_w=clamp(2.2*bearing_error+0.8*pose_error,max_yaw_rate_);
      if (std::abs(bearing_error)<0.65 && std::abs(pose_error)<0.8)
        wanted_v=direction*(direction>0?max_speed_:max_reverse_);
    }
    const double dt=0.05;
    linear_+=clamp(wanted_v-linear_,max_accel_*dt);
    angular_+=clamp(wanted_w-angular_,max_yaw_accel_*dt);
    cmd.twist.linear.x=linear_;cmd.twist.angular.z=angular_;
    cmd_pub_->publish(cmd);
  }
  std::vector<Pose2> path_;
  size_t index_=1;
  Pose2 robot_{};
  double path_received_=-1,odom_received_=-1,permission_received_=-1;
  double max_speed_,max_reverse_,max_yaw_rate_,max_accel_,max_yaw_accel_;
  double path_timeout_,odom_timeout_,permission_timeout_;
  double linear_=0,angular_=0;
  bool permitted_=false;
  int stop_=0;
  rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr permission_sub_;
  rclcpp::Subscription<std_msgs::msg::Int8>::SharedPtr stop_sub_;
  rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr cmd_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc,char** argv) {
  rclcpp::init(argc,argv);
  rclcpp::spin(std::make_shared<XYThetaFollower>());
  rclcpp::shutdown();
}
