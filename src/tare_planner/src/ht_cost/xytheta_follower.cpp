#include "ht_cost/xytheta_planner.h"
#include "ht_cost/ht_cost_map.h"
#include "ht_cost/measured_collision_field.h"
#include "ht_cost/input_pose_buffer.h"
#include <sensor_msgs/point_cloud2_iterator.hpp>
#include <rclcpp/rclcpp.hpp>
#include <nav_msgs/msg/odometry.hpp>
#include <nav_msgs/msg/path.hpp>
#include <geometry_msgs/msg/twist_stamped.hpp>
#include <std_msgs/msg/bool.hpp>
#include <std_msgs/msg/int8.hpp>
#include <std_msgs/msg/string.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
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
  explicit XYThetaFollower(const rclcpp::NodeOptions& options=rclcpp::NodeOptions()) : Node("xytheta_follower",options) {
    const auto odometry_topic=declare_parameter<std::string>("odometry_topic","/state_estimation");
    const auto registered_scan_topic=declare_parameter<std::string>("registered_scan_topic","/registered_scan");
    const auto command_topic=declare_parameter<std::string>("command_topic","/cmd_vel");
    command_frame_=declare_parameter<std::string>("command_frame","vehicle");
    if(command_frame_.empty())throw std::invalid_argument("Empty command frame");
    expected_child_=declare_parameter<std::string>("odometry_child_frame","");
    max_speed_=declare_parameter<double>("max_speed",0.5);
    max_reverse_=declare_parameter<double>("max_reverse",0.25);
    max_yaw_rate_=declare_parameter<double>("max_yaw_rate",0.8);
    max_accel_=declare_parameter<double>("max_accel",0.5);
    max_yaw_accel_=declare_parameter<double>("max_yaw_accel",1.2);
    rotation_tolerance_=declare_parameter<double>("rotation_tolerance",0.04);
    rotation_stop_rate_=declare_parameter<double>("rotation_stop_rate",0.06);
    path_timeout_=declare_parameter<double>("path_timeout",3.0);
    odom_timeout_=declare_parameter<double>("odom_timeout",0.5);
    // TARE publishes this permission in its 1 Hz planning callback. A 0.5 s
    // timeout makes the vehicle stop for half of every healthy cycle.
    permission_timeout_=declare_parameter<double>("permission_timeout",1.5);
    scan_timeout_=declare_parameter<double>("mission_sensor_timeout",3.0);
    geometry_timeout_=declare_parameter<double>("geometry_timeout",3.0);
    const double margin=declare_parameter<double>("kViewPointCollisionMargin",0.5);
    const double cell_x=declare_parameter<double>("kCollisionGridResolutionX",0.2);
    const double cell_y=declare_parameter<double>("kCollisionGridResolutionY",0.2);
    geometry_z_plus_=declare_parameter<double>("kViewPointCollisionMarginZPlus",0.5);
    geometry_z_minus_=declare_parameter<double>("kViewPointCollisionMarginZMinus",0.5);
    geometry_radius_=margin+.5*std::hypot(cell_x,cell_y);
    for(double value:{geometry_timeout_,margin,cell_x,cell_y,geometry_z_plus_,geometry_z_minus_})
      if (!std::isfinite(value)||value<=0)throw std::invalid_argument("Invalid execution geometry envelope");
    geometry_sub_=create_subscription<sensor_msgs::msg::PointCloud2>("/collision_cloud",rclcpp::QoS(1).reliable(),
      [this](sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
        geometry_received_=-1;
        if(msg->header.frame_id!="map" || msg->is_bigendian)return;
        auto cloud=std::make_shared<ht_cost_ns::MeasuredCollisionField::Cloud>();
        try {
          if(msg->width && msg->height) {
            if(msg->point_step==0 || msg->row_step<msg->point_step*msg->width ||
               msg->data.size()<size_t(msg->row_step)*msg->height)return;
            for(const char* name:{"x","y","z"}) {
              bool found=false;
              for(const auto& field:msg->fields)if(field.name==name &&
                field.datatype==sensor_msgs::msg::PointField::FLOAT32 && field.count==1 &&
                field.offset+sizeof(float)<=msg->point_step)found=true;
              if(!found)return;
            }
            sensor_msgs::PointCloud2ConstIterator<float> x(*msg,"x"),y(*msg,"y"),z(*msg,"z");
            for(;x!=x.end();++x,++y,++z)if(std::isfinite(*x)&&std::isfinite(*y)&&std::isfinite(*z)) {
              pcl::PointXYZ p;p.x=*x;p.y=*y;p.z=*z;cloud->push_back(p);
            }
          }
        }catch(const std::exception&) {return;}
        geometry_.update(cloud);geometry_received_=now().seconds();
        geometry_stamp_=rclcpp::Time(msg->header.stamp).seconds();
      });
    for (double v:{max_speed_,max_reverse_,max_yaw_rate_,max_accel_,max_yaw_accel_,
                   path_timeout_,odom_timeout_,permission_timeout_,scan_timeout_,
                   rotation_tolerance_,rotation_stop_rate_})
      if (!std::isfinite(v) || v<=0) throw std::invalid_argument("Invalid follower limit or timeout");
    if (rotation_tolerance_>=ht_cost_ns::kPi/32)
      throw std::invalid_argument("Rotation tolerance must be smaller than half an11.25degree turn");
    path_sub_=create_subscription<nav_msgs::msg::Path>("/ht_xytheta_path",rclcpp::QoS(1).reliable(),
      [this](nav_msgs::msg::Path::ConstSharedPtr msg) {
        std::vector<Pose2> incoming;
        if (msg->header.frame_id!="map") {path_.clear();return;}
        for (const auto& stamped:msg->poses) {
          if ((!stamped.header.frame_id.empty() && !ht_cost_ns::mapFrame(stamped.header.frame_id)) ||
              !validPose(stamped.pose,1)) {path_.clear();return;}
          const auto pose=poseOf(stamped.pose);
          if (!std::isfinite(pose.x) || !std::isfinite(pose.y) || !std::isfinite(pose.yaw)) {
            path_.clear();return;
          }
          incoming.push_back(pose);
        }
        bool identical=incoming.size()==path_.size();
        for (size_t i=0;identical && i<incoming.size();++i)
          identical=std::hypot(incoming[i].x-path_[i].x,incoming[i].y-path_[i].y)<1e-5 &&
            std::abs(wrapYaw(incoming[i].yaw-path_[i].yaw))<1e-5;
        if (!identical) {
          path_=std::move(incoming);index_=1;
          // Project onto the beginning of a new plan using both position and
          // heading. A path can arrive after the car has already progressed.
          double best=std::numeric_limits<double>::infinity(),arc=0;
          for (size_t i=0;i<path_.size();++i) {
            if (i) arc+=std::hypot(path_[i].x-path_[i-1].x,path_[i].y-path_[i-1].y);
            if (arc>1.0) break;
            const double score=std::hypot(path_[i].x-robot_.x,path_[i].y-robot_.y)+
              0.25*std::abs(wrapYaw(path_[i].yaw-robot_.yaw));
            if (score<best) {best=score;index_=std::max<size_t>(1,i);}
          }
        }
        rotation_goal_index_=0;
        path_received_=now().seconds();
        path_stamp_=rclcpp::Time(msg->header.stamp).seconds();
        path_header_=msg->header;
      });
    odom_sub_=create_subscription<nav_msgs::msg::Odometry>(odometry_topic,rclcpp::SensorDataQoS().keep_last(100),
      [this](nav_msgs::msg::Odometry::ConstSharedPtr msg) {
        const double stamp=rclcpp::Time(msg->header.stamp).seconds(),now_s=now().seconds();
        if (!ht_cost_ns::mapFrame(msg->header.frame_id) || !validPose(msg->pose.pose,stamp) ||
            (!expected_child_.empty() && msg->child_frame_id!=expected_child_) ||
            stamp>now_s+.1 || now_s-stamp>odom_timeout_ || !std::isfinite(msg->twist.twist.angular.z)) {
          odom_received_=-1;return;
        }
        const auto input=inputPose(msg->pose.pose,stamp);
        if (stamp<=odom_history_.latestStamp())return;
        if (odom_history_.jump(input)) {
          input_fault_="ODOM_JUMP_RESTART_REQUIRED";odom_received_=-1;path_.clear();permitted_=false;return;
        }
        odom_history_.add(input);
        robot_=poseOf(msg->pose.pose);robot_z_=msg->pose.pose.position.z;
        measured_yaw_rate_=msg->twist.twist.angular.z;
        if (!std::isfinite(robot_z_) || !std::isfinite(robot_.x) || !std::isfinite(robot_.y) || !std::isfinite(robot_.yaw) ||
            !std::isfinite(measured_yaw_rate_)) {
          odom_received_=-1;return;
        }
        odom_received_=now().seconds();
        odom_stamp_=rclcpp::Time(msg->header.stamp).seconds();
      });
    scan_sub_=create_subscription<sensor_msgs::msg::PointCloud2>(registered_scan_topic,rclcpp::SensorDataQoS(),
      [this](sensor_msgs::msg::PointCloud2::ConstSharedPtr msg) {
        if(!ht_cost_ns::mapFrame(msg->header.frame_id)){scan_received_=-1;return;}
        scan_received_=now().seconds();scan_stamp_=rclcpp::Time(msg->header.stamp).seconds();
      });
    permission_sub_=create_subscription<std_msgs::msg::Bool>("/ht_navigation_allowed",5,
      [this](std_msgs::msg::Bool::ConstSharedPtr msg) {
        permitted_=msg->data;permission_received_=now().seconds();
      });
    stop_sub_=create_subscription<std_msgs::msg::Int8>("/stop",5,
      [this](std_msgs::msg::Int8::ConstSharedPtr msg) {stop_=msg->data;});
    completed_sub_=create_subscription<std_msgs::msg::Bool>("/mission_completed",5,
      [this](std_msgs::msg::Bool::ConstSharedPtr msg) {
        completed_=msg->data;completed_received_=now().seconds();
      });
    cmd_pub_=create_publisher<geometry_msgs::msg::TwistStamped>(command_topic,5);
    status_pub_=create_publisher<std_msgs::msg::String>("/ht_follower_status",5);
    rejection_pub_=create_publisher<nav_msgs::msg::Path>("/ht_execution_rejected_edge",5);
    timer_=create_wall_timer(std::chrono::milliseconds(50),[this]() {tick();});
  }
  void initialize() {ht_=std::make_unique<ht_cost_ns::HtCostMap>(shared_from_this(),false);}
 private:
  static ht_cost_ns::InputPose inputPose(const geometry_msgs::msg::Pose& p,double stamp) {
    return {stamp,{p.position.x,p.position.y,p.position.z},
                  {p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w}};
  }
  static bool validPose(const geometry_msgs::msg::Pose& p,double stamp) {
    return ht_cost_ns::validInputPose(inputPose(p,stamp));
  }
  static double steadySeconds() {
    return std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
  }
  void publishCommand(geometry_msgs::msg::TwistStamped& cmd) {
    cmd.header.stamp=now();
    cmd_pub_->publish(cmd);
    // Use the end of the previous publish call as a conservative reference.
    // Timing from tick starts would include variable validation work and can
    // overestimate the interval between actual consecutive publications.
    command_interval_.published(steadySeconds());
  }
  void tick() {
    const double now_s=now().seconds();
    if(last_ros_tick_>=0 && now_s<last_ros_tick_-1e-6)input_fault_="CLOCK_RESET_RESTART_REQUIRED";
    last_ros_tick_=now_s;
    geometry_msgs::msg::TwistStamped cmd;
    cmd.header.stamp=now();cmd.header.frame_id=command_frame_;
    auto fresh=[&](double stamp,double limit) {return stamp>0 && now_s>=stamp && now_s-stamp<limit;};
    auto status=[&](const std::string& reason) {
      std_msgs::msg::String s;s.data=reason;status_pub_->publish(s);
    };
    auto hold=[&](const std::string& reason) {
      if (reason!="HT_COMMAND_BLOCKED") command_blocked_since_=-1;
      linear_=0;angular_=0;
      // Late command-arc rejection happens after cmd contains the candidate.
      // Clear the outgoing message too; resetting controller state alone
      // would publish the very motion that HT just rejected.
      cmd.twist=geometry_msgs::msg::Twist();
      publishCommand(cmd);status(reason);
    };
    if(!input_fault_.empty()){hold(input_fault_);return;}
    // A current terminal heartbeat is an explicit stop, even after the final
    // path expires. An old completion flag cannot mask subsequent failures.
    if (completed_ && fresh(completed_received_,permission_timeout_)) {hold("COMPLETED");return;}
    if (!fresh(odom_received_,odom_timeout_) || !fresh(odom_stamp_,odom_timeout_)) {hold("ODOM_STALE");return;}
    if (!fresh(path_received_,path_timeout_) || !fresh(path_stamp_,path_timeout_)) {hold("PATH_STALE");return;}
    if (!permitted_ || permission_received_<=0 || stop_>=1) {hold("PLANNER_HOLD");return;}
    if (path_.size()<2) {hold("EMPTY_PATH");return;}
    if (ht_ && ht_->enabled()) {
      if (!fresh(scan_received_,scan_timeout_) || !fresh(scan_stamp_,scan_timeout_)) {hold("SCAN_STALE");return;}
      if (!prior_started_) {ht_->start({robot_.x,robot_.y,0});prior_started_=true;}
      ht_->updateExecution({robot_.x,robot_.y,0},false);ht_->beginCycle();
      if (!ht_->ready()) {hold(ht_->status());return;}
      // A fresh map and a bounded-age plan are checked here independently of
      // TARE's expensive planning callback. Never renew a stale Bool blindly.
      if (!ht_->permits(ht_->poseSupport(robot_.x,robot_.y,robot_.yaw))) {hold("HT_CURRENT_POSE_BLOCKED");return;}
      if (!fresh(geometry_received_,geometry_timeout_) || !fresh(geometry_stamp_,geometry_timeout_)) {hold("GEOMETRY_STALE");return;}
      if (geometryBlocked(robot_)) {hold("GEOMETRY_CURRENT_POSE_BLOCKED");return;}
    } else if (!fresh(permission_received_,permission_timeout_)) {hold("PERMISSION_STALE");return;}
    while (index_<path_.size()) {
      const bool rotating=gear(path_[index_-1],path_[index_])==0;
      // Intermediate angular samples are for swept validation. Track a whole
      // monotonic spin, so the position tolerance cannot consume its last
      // heading before the car has aligned and stopped rotating.
      if (rotating) {
        if (!rotation_goal_index_) rotation_goal_index_=rotationEnd(index_);
        index_=rotation_goal_index_;
      }
      const auto& p=path_[index_];
      const double distance=std::hypot(p.x-robot_.x,p.y-robot_.y);
      const double yaw_error=std::abs(wrapYaw(p.yaw-robot_.yaw));
      if (distance>0.12 || (rotating && (yaw_error>rotation_tolerance_ ||
          std::abs(angular_)>rotation_stop_rate_ || std::abs(measured_yaw_rate_)>rotation_stop_rate_))) break;
      ++index_;rotation_goal_index_=0;
    }
    if (index_>=path_.size()) {
      hold("GOAL_REACHED");return;
    }
    if (ht_ && ht_->enabled()) {
      Pose2 previous=robot_;double distance=0;
      for (size_t i=index_;i<path_.size();++i) {
        const auto& p=path_[i];
        const double length=std::hypot(p.x-previous.x,p.y-previous.y);
        const double angle=wrapYaw(p.yaw-previous.yaw);
        const int samples=std::max(1,static_cast<int>(std::ceil(std::max(length/.05,std::abs(angle)/.1))));
        if (length>1.0 || samples>100) {hold("PATH_DISCONTINUITY");return;}
        for(int sample=1;sample<=samples;++sample) {
          const double fraction=double(sample)/samples;
          Pose2 q{previous.x+(p.x-previous.x)*fraction,previous.y+(p.y-previous.y)*fraction,
                  wrapYaw(previous.yaw+angle*fraction)};
          if(geometryBlocked(q)) {rejectEdge(previous,p);hold("GEOMETRY_PATH_BLOCKED");return;}
        }
        if (!ht_->permits(ht_->motionSupport(previous,p))) {
          rejectEdge(previous,p);hold("HT_PATH_BLOCKED");return;
        }
        distance+=length;previous=p;
        if (distance>=1.0) break;
      }
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
      const double error=wrapYaw(target.yaw-robot_.yaw);
      wanted_w=std::abs(error)<=rotation_tolerance_ ? 0:clamp(2.5*error,max_yaw_rate_);
    } else {
      const double bearing=std::atan2(target.y-robot_.y,target.x-robot_.x);
      const double travel_yaw=robot_.yaw+(direction<0?ht_cost_ns::kPi:0);
      const double bearing_error=wrapYaw(bearing-travel_yaw);
      const double pose_error=wrapYaw(target.yaw-robot_.yaw);
      wanted_w=clamp(2.2*bearing_error+0.8*pose_error,max_yaw_rate_);
      if (std::abs(bearing_error)<0.65 && std::abs(pose_error)<0.8)
        wanted_v=direction*(direction>0?max_speed_:max_reverse_);
    }
    const double dt=command_interval_.elapsed(steadySeconds());
    linear_+=clamp(wanted_v-linear_,max_accel_*dt);
    angular_+=clamp(wanted_w-angular_,max_yaw_accel_*dt);
    cmd.twist.linear.x=linear_;cmd.twist.angular.z=angular_;
    if (ht_ && ht_->enabled()) {
      // Check the commanded unicycle arc too: tracking can depart from the
      // nominal route. Cover reaction plus braking distance, including yaw.
      Pose2 p=robot_;
      const double horizon=std::max(.2,std::max(std::abs(linear_)/max_accel_,std::abs(angular_)/max_yaw_accel_)+.1);
      for (double t=0;t<horizon;t+=.05) {
        Pose2 next=p;
        next.x+=linear_*.05*std::cos(p.yaw+angular_*.025);
        next.y+=linear_*.05*std::sin(p.yaw+angular_*.025);next.yaw=wrapYaw(p.yaw+angular_*.05);
        if (geometryBlocked(next)) {
          rejectEdge(p,next);hold("GEOMETRY_COMMAND_BLOCKED");return;
        }
        if (!ht_->permits(ht_->motionSupport(p,next))) {
          if (command_blocked_since_<0) command_blocked_since_=now_s;
          if (now_s-command_blocked_since_>=.5) rejectEdge(p,next);
          hold("HT_COMMAND_BLOCKED");return;
        }
        p=next;
      }
    }
    command_blocked_since_=-1;
    status(std::abs(linear_)>.01 ? "DRIVING" : std::abs(angular_)>.05 ? "TURNING" : "ALIGNING");
    publishCommand(cmd);
  }
  size_t rotationEnd(size_t index) const {
    double angle=wrapYaw(path_[index].yaw-path_[index-1].yaw);
    if (std::abs(angle)<1e-9) return index;
    const double sign=std::copysign(1.0,angle);
    double total=std::abs(angle);
    while (index+1<path_.size() && gear(path_[index],path_[index+1])==0) {
      const double next=wrapYaw(path_[index+1].yaw-path_[index].yaw);
      if (next*sign<0 || total+std::abs(next)>ht_cost_ns::kPi/2+1e-9) break;
      total+=std::abs(next);++index;
    }
    return index;
  }
  bool geometryBlocked(Pose2 p) {
    return geometry_.blocked(p.x,p.y,robot_z_,geometry_radius_,geometry_z_plus_,geometry_z_minus_);
  }
  void rejectEdge(Pose2 a,Pose2 b) {
    // Header identifies the rejected plan, not the observation time. Delayed
    // feedback must never invalidate a newer plan. Emit once per publication.
    if (last_rejected_stamp_==path_stamp_) return;
    last_rejected_stamp_=path_stamp_;
    nav_msgs::msg::Path edge;edge.header=path_header_;
    for (const auto p:{a,b}) {
      geometry_msgs::msg::PoseStamped pose;pose.header=edge.header;
      pose.pose.position.x=p.x;pose.pose.position.y=p.y;
      pose.pose.orientation.z=std::sin(p.yaw/2);pose.pose.orientation.w=std::cos(p.yaw/2);
      edge.poses.push_back(pose);
    }
    rejection_pub_->publish(edge);
  }
  ht_cost_ns::MeasuredCollisionField geometry_;
  double robot_z_=0,geometry_received_=-1,geometry_stamp_=-1;
  double geometry_timeout_,geometry_radius_,geometry_z_plus_,geometry_z_minus_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr geometry_sub_;
  std::vector<Pose2> path_;
  size_t index_=1;
  size_t rotation_goal_index_=0;
  Pose2 robot_{};
  double path_received_=-1,odom_received_=-1,permission_received_=-1;
  double path_stamp_=-1,odom_stamp_=-1,scan_received_=-1,scan_stamp_=-1,scan_timeout_;
  double max_speed_,max_reverse_,max_yaw_rate_,max_accel_,max_yaw_accel_;
  double rotation_tolerance_,rotation_stop_rate_,measured_yaw_rate_=0;
  double path_timeout_,odom_timeout_,permission_timeout_;
  double linear_=0,angular_=0;
  double last_rejected_stamp_=-1;
  double command_blocked_since_=-1;
  ht_cost_ns::InputPoseBuffer odom_history_;
  ht_cost_ns::CommandInterval command_interval_;
  std::string expected_child_,input_fault_,command_frame_;
  double last_ros_tick_=-1;
  std_msgs::msg::Header path_header_;
  bool permitted_=false;
  bool completed_=false;
  double completed_received_=-1;
  bool prior_started_=false;
  std::unique_ptr<ht_cost_ns::HtCostMap> ht_;
  int stop_=0;
  rclcpp::Subscription<nav_msgs::msg::Path>::SharedPtr path_sub_;
  rclcpp::Subscription<nav_msgs::msg::Odometry>::SharedPtr odom_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr permission_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr completed_sub_;
  rclcpp::Subscription<std_msgs::msg::Int8>::SharedPtr stop_sub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr scan_sub_;
  rclcpp::Publisher<geometry_msgs::msg::TwistStamped>::SharedPtr cmd_pub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_pub_;
  rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr rejection_pub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

#ifndef HT_FOLLOWER_NO_MAIN
int main(int argc,char** argv) {
  rclcpp::init(argc,argv);
  auto node=std::make_shared<XYThetaFollower>();node->initialize();
  rclcpp::executors::MultiThreadedExecutor executor(rclcpp::ExecutorOptions(),2);
  executor.add_node(node);executor.spin();
  rclcpp::shutdown();
}
#endif
