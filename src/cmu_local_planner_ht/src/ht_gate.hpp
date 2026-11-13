#pragma once
// A local execution constraint only. TARE's exploration objectives and CMU's
// collision scores, motion primitives and controller remain upstream code.
#include <rclcpp/rclcpp.hpp>
#include <grid_map_msgs/msg/grid_map.hpp>
#include <geometry_msgs/msg/polygon_stamped.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <std_msgs/msg/string.hpp>
#include <opencv2/imgproc.hpp>
#include <array>
#include <algorithm>
#include <cmath>
#include <map>
#include <memory>
#include <sstream>
#include <iomanip>
#include <stdexcept>
#include <vector>

namespace cmu_ht {
constexpr double pi=3.14159265358979323846;
inline double wrap(double a) {return std::atan2(std::sin(a),std::cos(a));}
struct Pose {double x=0,y=0,yaw=0;};
class Gate {
 public:
  explicit Gate(rclcpp::Node::SharedPtr node):node_(node) {
    enabled=node_->declare_parameter("ht_enabled",false);
    mode=node_->declare_parameter<std::string>("traversability_mode","geometry_and_ht");
    if(mode!="geometry_only" && mode!="geometry_and_ht" && mode!="ht_only")
      throw std::invalid_argument("Invalid traversability_mode");
    if(mode=="geometry_only")enabled=false;
    if(mode=="ht_only" && !enabled)throw std::invalid_argument("ht_only requires ht_enabled");
    require_boundary_=node_->declare_parameter("require_navigation_boundary",false);
    threshold_=node_->declare_parameter("ht_min_probability",.5);
    timeout_=node_->declare_parameter("ht_map_timeout",1.);
    radius_=node_->declare_parameter("ht_validity_radius",.6);
    reaction_=node_->declare_parameter("ht_reaction_time",.1);
    brake_linear_=node_->declare_parameter("ht_linear_brake_accel",2.5);
    brake_angular_=node_->declare_parameter("ht_angular_brake_accel",3.);
    topic_=node_->declare_parameter<std::string>("ht_topic","/ht_traversability/global_local");
    if(threshold_<0 || threshold_>1 || timeout_<=0 || radius_<0 ||
       !std::isfinite(reaction_) || reaction_<0 || reaction_>1 ||
       !std::isfinite(brake_linear_) || brake_linear_<=0 ||
       !std::isfinite(brake_angular_) || brake_angular_<=0)
      throw std::invalid_argument("Invalid HT gate parameters");
    boundary_sub_=node_->create_subscription<geometry_msgs::msg::PolygonStamped>("/navigation_boundary",5,
      [this](geometry_msgs::msg::PolygonStamped::ConstSharedPtr m){receiveBoundary(*m);});
    if(mode=="ht_only")external_sub_=node_->create_subscription<sensor_msgs::msg::PointCloud2>("/added_obstacles",5,
      [this](sensor_msgs::msg::PointCloud2::ConstSharedPtr m){external_obstacles_=size_t(m->width)*m->height;});
    if(enabled) {
      sub_=node_->create_subscription<grid_map_msgs::msg::GridMap>(topic_,rclcpp::QoS(1).reliable(),
        [this](grid_map_msgs::msg::GridMap::ConstSharedPtr msg){receive(*msg);});
      diagnostics_=node_->create_publisher<std_msgs::msg::String>("/ht_minimal/"+std::string(node_->get_name()),1);
      path_rejection_=node_->create_publisher<std_msgs::msg::String>("/ht_minimal/path_rejection",10);
      if(std::string(node_->get_name())=="pathFollower")
        command_audit_=node_->create_publisher<std_msgs::msg::String>("/ht_minimal/command_audit",100);
      if(std::string(node_->get_name())=="pathFollower")
        projection_=node_->create_publisher<std_msgs::msg::String>("/ht_minimal/command_projection",10);
      timer_=node_->create_wall_timer(std::chrono::seconds(1),[this](){report();});
    }
  }
  bool enabled=false;
  std::string mode;
  bool usesGeometry() const {return mode!="ht_only";}
  // CMU supplies its configured full body envelope in the vehicle frame.
  // Keep support, HT scores, boundary and TTL independent of this refinement.
  void setBodyEnvelope(double length,double width) {
    if(!std::isfinite(length)||!std::isfinite(width)||length<=0||width<=0||length>6||width>6)
      throw std::invalid_argument("Invalid HT body envelope");
    if(std::hypot(length/2,width/2)>radius_+1e-9)
      throw std::invalid_argument("Body envelope exceeds HT support/boundary radius");
    body_half_length_=length/2;body_half_width_=width/2;
  }
  bool bodyOccupied(Pose p) const {
    if(body_half_length_<=0 || body_half_width_<=0)return true;
    // Cell extent plus the maximum translation/rotation between sweep samples.
    const double reach=std::hypot(body_half_length_,body_half_width_);
    const double margin=res_/std::sqrt(2.)+.01+reach*pi/128;
    const int n=std::ceil((reach+margin)/res_)+1;
    const int rr=std::floor(rows_*.5-(p.x-cx_)/res_),cc=std::floor(cols_*.5-(p.y-cy_)/res_);
    if(rr-n>=0&&cc-n>=0&&rr+n<rows_&&cc+n<cols_) {
      const int a=rr-n,b=cc-n,z=rr+n+1,w=cc+n+1;
      if(occupied_sum_.at<int>(z,w)-occupied_sum_.at<int>(a,w)-occupied_sum_.at<int>(z,b)+occupied_sum_.at<int>(a,b)==0)return false;
    }
    const double cosine=std::cos(p.yaw),sine=std::sin(p.yaw);
    for(int r=rr-n;r<=rr+n;++r)for(int c=cc-n;c<=cc+n;++c) {
      const double dx=cx_+(rows_*.5-r-.5)*res_-p.x,dy=cy_+(cols_*.5-c-.5)*res_-p.y;
      const double x=cosine*dx+sine*dy,y=-sine*dx+cosine*dy;
      if(std::abs(x)>body_half_length_+margin||std::abs(y)>body_half_width_+margin)continue;
      if(r<0||c<0||r>=rows_||c>=cols_||raw_occupied_.at<unsigned char>(r,c))return true;
    }
    return false;
  }
  void receiveBoundary(const geometry_msgs::msg::PolygonStamped& msg) {
    boundary_received_=true;boundary_.clear();boundary_valid_=msg.header.frame_id=="map" && msg.polygon.points.size()>=3;
    for(const auto& p:msg.polygon.points) {
      if(!std::isfinite(p.x)||!std::isfinite(p.y))boundary_valid_=false;
      boundary_.push_back({p.x,p.y,0});
    }
    double area=0;
    for(size_t i=0;i<boundary_.size();++i){const auto& a=boundary_[i];const auto& b=boundary_[(i+1)%boundary_.size()];area+=a.x*b.y-b.x*a.y;}
    if(std::abs(area)<1e-8)boundary_valid_=false;
  }
  bool withinBoundary(Pose p) {
    if(!boundary_received_) {
      if(require_boundary_){last_reason="NAVIGATION_BOUNDARY_MISSING";return false;}
      return true;
    }
    if(!boundary_valid_){last_reason="NAVIGATION_BOUNDARY_INVALID";return false;}
    bool inside=false;
    const double margin=radius_+std::sqrt(2.)*res_;
    for(size_t i=0,j=boundary_.size()-1;i<boundary_.size();j=i++) {
      const auto& a=boundary_[j];const auto& b=boundary_[i];
      if((a.y>p.y)!=(b.y>p.y) && p.x<(b.x-a.x)*(p.y-a.y)/(b.y-a.y)+a.x)inside=!inside;
      const double dx=b.x-a.x,dy=b.y-a.y,l2=dx*dx+dy*dy;
      const double t=l2>0?std::max(0.,std::min(1.,((p.x-a.x)*dx+(p.y-a.y)*dy)/l2)):0;
      if(std::hypot(p.x-a.x-t*dx,p.y-a.y-t*dy)<margin){last_reason="NAVIGATION_BOUNDARY_FOOTPRINT";return false;}
    }
    if(!inside)last_reason="NAVIGATION_BOUNDARY_OUTSIDE";
    return inside;
  }
  std::string last_reason="HT_MAP_MISSING";
  uint64_t allowed=0,rejected=0;
  double mapStamp() const {return stamp_;}
  double resolution() const {return res_;}
  void receive(const grid_map_msgs::msg::GridMap& msg) {
    try {
      if(msg.header.frame_id!="map" || msg.layers.size()!=msg.data.size() || msg.data.empty())
        throw std::runtime_error("frame/layer count");
      const auto& q=msg.info.pose.orientation;
      if(std::abs(q.x)>1e-6 || std::abs(q.y)>1e-6 || std::abs(q.z)>1e-6 || std::abs(std::abs(q.w)-1)>1e-6)
        throw std::runtime_error("axis-aligned map required");
      const double resolution=msg.info.resolution;
      if(!std::isfinite(resolution) || resolution<.01 || resolution>.2 ||
         !std::isfinite(msg.info.length_x) || !std::isfinite(msg.info.length_y))throw std::runtime_error("resolution");
      const int rows=std::lround(msg.info.length_x/resolution),cols=std::lround(msg.info.length_y/resolution);
      if(!std::isfinite(resolution) || resolution<.01 || resolution>.2 || rows<1 || cols<1 || rows>1000 || cols>1000 ||
         !std::isfinite(msg.info.pose.position.x) || !std::isfinite(msg.info.pose.position.y) ||
         msg.outer_start_index>=unsigned(rows) || msg.inner_start_index>=unsigned(cols))
        throw std::runtime_error("geometry");
      auto layer=[&](const std::string& name) {
        auto it=std::find(msg.layers.begin(),msg.layers.end(),name);
        if(it==msg.layers.end())throw std::runtime_error("missing "+name);
        const auto& a=msg.data[it-msg.layers.begin()];
        if(a.layout.dim.size()!=2 || a.layout.dim[0].label!="column_index" ||
           a.layout.dim[1].label!="row_index" || a.layout.dim[0].size!=unsigned(cols) ||
           a.layout.dim[1].size!=unsigned(rows) || a.layout.dim[0].stride!=unsigned(rows*cols) ||
           a.layout.dim[1].stride!=unsigned(rows) || a.layout.data_offset!=0 || a.data.size()!=size_t(rows*cols))
          throw std::runtime_error("layout "+name);
        std::vector<float> out(rows*cols);
        for(int r=0;r<rows;++r)for(int c=0;c<cols;++c)
          out[r*cols+c]=a.data[(r+msg.outer_start_index)%rows+((c+msg.inner_start_index)%cols)*rows];
        return out;
      };
      std::array<std::vector<float>,8> scores;
      for(int k=0;k<8;++k)scores[k]=layer("ht_dir_"+std::to_string(k));
      auto valid=layer("ht_valid"),physical=layer("ht_observation_valid"),obstacle=layer("ht_obstacle");
      cv::Mat unknown(rows,cols,CV_8U),occupied(rows,cols,CV_8U);
      for(int i=0;i<rows*cols;++i) {
        unknown.data[i]=!std::isfinite(physical[i]) || physical[i]<.5;
        occupied.data[i]=std::isfinite(obstacle[i]) && obstacle[i]>=.5;
      }
      const double inflated=radius_+std::sqrt(2.)*resolution;
      const int n=std::ceil(inflated/resolution);
      cv::Mat kernel(2*n+1,2*n+1,CV_8U,cv::Scalar(0));
      for(int x=-n;x<=n;++x)for(int y=-n;y<=n;++y)
        if(std::hypot(x*resolution,y*resolution)<=inflated)kernel.at<unsigned char>(x+n,y+n)=1;
      cv::Mat unsafe,missing;
      cv::dilate(unknown,missing,kernel,cv::Point(-1,-1),1,cv::BORDER_CONSTANT,cv::Scalar(1));
      cv::dilate(occupied,unsafe,kernel,cv::Point(-1,-1),1,cv::BORDER_CONSTANT,cv::Scalar(0));
      probabilities_=std::move(scores);valid_=std::move(valid);
      raw_occupied_=occupied;cv::integral(occupied,occupied_sum_,CV_32S);
      missing_=missing;occupied_=unsafe;rows_=rows;cols_=cols;res_=resolution;
      cx_=msg.info.pose.position.x;cy_=msg.info.pose.position.y;
      stamp_=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9;
      have_map_=true;++maps_;last_reason="MAP_RECEIVED";
    } catch(const std::exception& e) {
      have_map_=false;last_reason="HT_MAP_INVALID";++invalid_maps_;
      RCLCPP_WARN_THROTTLE(node_->get_logger(),*node_->get_clock(),3000,"HT map rejected: %s",e.what());
    }
  }
  bool pose(Pose p) {
    if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.yaw)){last_reason="INVALID_POSE";return false;}
    if(!withinBoundary(p))return false;
    if(external_obstacles_){last_reason="EXTERNAL_NO_GO_UNSUPPORTED";return false;}
    if(!enabled)return true;
    const double age=node_->now().seconds()-stamp_;
    if(!have_map_){last_reason="HT_MAP_MISSING_OR_INVALID";return false;}
    if(age<0 || age>timeout_){last_reason="HT_MAP_STALE";return false;}
    if(!std::isfinite(p.x)||!std::isfinite(p.y)||!std::isfinite(p.yaw)) {last_reason="INVALID_POSE";return false;}
    const int r=std::floor(rows_*.5-(p.x-cx_)/res_),c=std::floor(cols_*.5-(p.y-cy_)/res_);
    if(r<0||c<0||r>=rows_||c>=cols_){last_reason="HT_OUTSIDE_MAP";return false;}
    const int index=r*cols_+c;
    const int channel=int(std::floor((wrap(p.yaw)+2*pi)/(pi/4)+.5))%8;
    if((body_half_length_>0 ? bodyOccupied(p) : occupied_.data[index]!=0)){last_reason="HT_OCCUPIED";return false;}
    if(missing_.data[index]){last_reason="HT_MISSING_SUPPORT";return false;}
    if(!std::isfinite(valid_[index])||valid_[index]<.5){last_reason="HT_CONTEXT_INVALID";return false;}
    const float score=probabilities_[channel][index];
    if(!std::isfinite(score)||score<0||score>1){last_reason="HT_SCORE_INVALID";return false;}
    if(score<threshold_){
      last_reason="HT_DIRECTION_LOW";
      const double now=node_->now().seconds();
      if(now-last_rejection_report_>=.2) {
        last_rejection_report_=now;float best=0;
        for(const auto& scores:probabilities_)if(std::isfinite(scores[index]))best=std::max(best,scores[index]);
        std::ostringstream out;out<<std::fixed<<std::setprecision(9)
          <<"{\"time\":"<<now<<",\"map_stamp\":"<<stamp_<<",\"x\":"<<p.x<<",\"y\":"<<p.y
          <<",\"yaw\":"<<p.yaw<<",\"channel\":"<<channel<<",\"score\":"<<score
          <<",\"best_direction_score\":"<<best<<",\"consumer\":\""<<node_->get_name()<<"\"}";
        std_msgs::msg::String msg;msg.data=out.str();path_rejection_->publish(msg);
      }
      return false;
    }
    last_reason="HT_ALLOWED";return true;
  }
  bool segment(Pose a,Pose b) {
    const double angle=wrap(b.yaw-a.yaw);
    const int n=std::max(1,int(std::ceil(std::max(std::hypot(b.x-a.x,b.y-a.y)/.02,std::abs(angle)/(pi/64)))));
    for(int i=0;i<=n;++i) {
      const double t=double(i)/n;
      if(!pose({a.x+(b.x-a.x)*t,a.y+(b.y-a.y)*t,a.yaw+angle*t}))return false;
    }
    return true;
  }
  bool path(const std::vector<Pose>& poses) {
    bool ok=!poses.empty();
    if(ok)ok=pose(poses.front());
    for(size_t i=1;ok&&i<poses.size();++i)ok=segment(poses[i-1],poses[i]);
    count(ok);
    return ok;
  }
  bool chooseCommand(Pose start,double& linear,double& angular) {
    const double native_linear=linear,native_angular=angular;
    if(command(start,linear,angular))return true;
    const auto original_reason=last_reason;
    // A valid primitive does not imply that the proportional tracker's
    // startup turn is valid: it can rotate across a bad heading before its
    // linear acceleration carries the body along that primitive. Keep native
    // translation and project only angular velocity onto checked candidates.
    // No motion is permitted from an invalid current pose.
    if(std::abs(linear)>1e-8 && pose(start)) {
      for(double scale:{.5,.25,.125,0.}) {
        angular=native_angular*scale;
        if(command(start,linear,angular)) {
          if(projection_) {
            std::ostringstream out;out<<std::fixed<<std::setprecision(9)
              <<"{\"time\":"<<node_->now().seconds()<<",\"map_stamp\":"<<stamp_
              <<",\"native_linear\":"<<native_linear<<",\"native_angular\":"<<native_angular
              <<",\"selected_linear\":"<<linear<<",\"selected_angular\":"<<angular
              <<",\"angular_scale\":"<<scale<<",\"original_rejection\":\""<<original_reason<<"\"}";
            std_msgs::msg::String msg;msg.data=out.str();projection_->publish(msg);
          }
          return true;
        }
      }
    }
    linear=0;angular=0;return false;
  }
  bool command(Pose start,double linear,double angular,bool emit_audit=true) {
    bool ok=pose(start);Pose previous=start;
    // CMU applies Twist velocities directly. On rejection this adapter sends
    // zero immediately; this reaction+deceleration envelope is conservative
    // for that simulated actuator, and must be calibrated before hardware use.
    // A constant 1s turn incorrectly overshot the proportional controller's
    // target and prevented safe turns next to direction-dependent terrain.
    const double horizon=reaction_+std::max(std::abs(linear)/brake_linear_,std::abs(angular)/brake_angular_);
    auto velocity=[&](double initial,double accel,double t) {
      return std::copysign(std::max(0.,std::abs(initial)-accel*std::max(0.,t-reaction_)),initial);
    };
    for(double t=0;ok&&t<horizon-1e-10;) {
      const double dt=std::min(.02,horizon-t),mid=t+dt*.5;
      const double v=velocity(linear,brake_linear_,mid),w=velocity(angular,brake_angular_,mid);
      Pose next=previous;
      next.x+=v*dt*std::cos(previous.yaw+w*dt*.5);
      next.y+=v*dt*std::sin(previous.yaw+w*dt*.5);next.yaw+=w*dt;
      ok=segment(previous,next);previous=next;
      t+=dt;
    }
    if(emit_audit)count(ok);
    if(emit_audit && command_audit_) {
      std::ostringstream out;out<<std::fixed<<std::setprecision(9)
        <<"{\"time\":"<<node_->now().seconds()<<",\"map_stamp\":"<<stamp_
        <<",\"x\":"<<start.x<<",\"y\":"<<start.y<<",\"yaw\":"<<start.yaw
        <<",\"linear_candidate\":"<<linear<<",\"angular_candidate\":"<<angular
        <<",\"reaction_time\":"<<reaction_<<",\"linear_brake_accel\":"<<brake_linear_
        <<",\"obstacle_footprint\":\""<<(body_half_length_>0?"oriented_box_v1":"circle_v1")<<"\""
        <<",\"body_length\":"<<2*body_half_length_<<",\"body_width\":"<<2*body_half_width_
        <<",\"support_radius\":"<<radius_
        <<",\"angular_brake_accel\":"<<brake_angular_<<",\"horizon_s\":"<<horizon
        <<",\"allowed\":"<<(ok?"true":"false")<<",\"reason\":\""<<last_reason<<"\"}";
      std_msgs::msg::String msg;msg.data=out.str();command_audit_->publish(msg);
    }
    return ok;
  }
 private:
  void count(bool ok){if(ok)++allowed;else {++rejected;++reasons_[last_reason];}}
  void report() {
    std::ostringstream s;s<<"{\"enabled\":true,\"map_stamp\":"<<std::fixed<<std::setprecision(9)<<stamp_
      <<",\"map_age_s\":"<<node_->now().seconds()-stamp_<<",\"accepted_maps\":"<<maps_
      <<",\"invalid_maps\":"<<invalid_maps_<<",\"allowed\":"<<allowed<<",\"rejected\":"<<rejected
      <<",\"last_reason\":\""<<last_reason<<"\",\"reasons\":{";
    bool first=true;for(const auto& p:reasons_){if(!first)s<<",";first=false;s<<"\""<<p.first<<"\":"<<p.second;}
    s<<"}}";std_msgs::msg::String msg;msg.data=s.str();diagnostics_->publish(msg);
  }
  rclcpp::Node::SharedPtr node_;
  rclcpp::Subscription<grid_map_msgs::msg::GridMap>::SharedPtr sub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr diagnostics_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr command_audit_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr path_rejection_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr projection_;
  rclcpp::TimerBase::SharedPtr timer_;
  std::string topic_;
  double threshold_=.5,timeout_=1,radius_=.6,res_=.04,cx_=0,cy_=0,stamp_=0;
  double last_rejection_report_=-1;
  double reaction_=.1,brake_linear_=2.5,brake_angular_=3.;
  int rows_=0,cols_=0;bool have_map_=false;
  uint64_t maps_=0,invalid_maps_=0;
  std::map<std::string,uint64_t> reasons_;
  std::array<std::vector<float>,8> probabilities_;
  std::vector<float> valid_;cv::Mat occupied_,missing_,raw_occupied_,occupied_sum_;
  double body_half_length_=0,body_half_width_=0;
  bool require_boundary_=false,boundary_received_=false,boundary_valid_=false;
  size_t external_obstacles_=0;
  std::vector<Pose> boundary_;
  rclcpp::Subscription<geometry_msgs::msg::PolygonStamped>::SharedPtr boundary_sub_;
  rclcpp::Subscription<sensor_msgs::msg::PointCloud2>::SharedPtr external_sub_;
};
} // namespace cmu_ht
