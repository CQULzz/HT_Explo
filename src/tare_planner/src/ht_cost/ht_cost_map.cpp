#include "ht_cost/ht_cost_map.h"
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_core/iterators/GridMapIterator.hpp>
#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Transform.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

namespace ht_cost_ns {
HtCostMap::HtCostMap(rclcpp::Node::SharedPtr node)
  : clock_(node->get_clock()), logger_(node->get_logger()),
    buffer_(clock_), listener_(buffer_) {
  enabled_=node->declare_parameter<bool>("ht_enabled",false);
  calibrated_=node->declare_parameter<bool>("ht_directions_calibrated",false);
  weight_=node->declare_parameter<double>("ht_weight",1.0);
  unknown_penalty_=node->declare_parameter<double>("ht_unknown_penalty",2.0);
  timeout_=node->declare_parameter<double>("ht_map_timeout",1.0);
  step_=node->declare_parameter<double>("ht_sample_step",0.02);
  lookahead_=node->declare_parameter<double>("ht_lookahead_distance",2.0);
  reached_distance_=node->declare_parameter<double>("ht_waypoint_reached_distance",0.3);
  footprint_radius_=node->declare_parameter<double>("ht_validity_radius",0.6);
  heading_offset_=node->declare_parameter<double>("ht_heading_offset",0.0);
  const auto policy=node->declare_parameter<std::string>("ht_unknown_policy","geometric_fallback");
  if (policy!="strict" && policy!="geometric_fallback") throw std::invalid_argument("Invalid ht_unknown_policy");
  geometric_fallback_=policy=="geometric_fallback";
  prior_.radius=node->declare_parameter<double>("ht_startup_radius",1.2);
  prior_.lifetime=node->declare_parameter<double>("ht_startup_duration",30.0);
  fallback_lookahead_=node->declare_parameter<double>("ht_fallback_lookahead",0.5);
  fallback_speed_=node->declare_parameter<double>("ht_fallback_speed",0.2);
  budget_.max_seconds=node->declare_parameter<double>("ht_fallback_max_seconds",60.0);
  budget_.max_distance=node->declare_parameter<double>("ht_fallback_max_distance",10.0);
  for (double v : {prior_.lifetime,fallback_lookahead_,fallback_speed_,budget_.max_seconds,budget_.max_distance})
    if (!std::isfinite(v) || v<=0) throw std::invalid_argument("Invalid HT execution parameter");
  if (!std::isfinite(prior_.radius) || prior_.radius<0 || prior_.radius>3 ||
      fallback_lookahead_<=reached_distance_ || fallback_lookahead_>lookahead_)
    throw std::invalid_argument("Invalid HT startup radius/fallback lookahead");
  frame_="map";  // TARE's existing world frame.
  const auto order=node->declare_parameter<std::vector<int64_t>>(
    "ht_channel_order",{0,1,2,3,4,5,6,7});
  const auto topic=node->declare_parameter<std::string>(
    "ht_topic","/ht_traversability/global_local");
  auto sorted=order;
  std::sort(sorted.begin(),sorted.end());
  if (sorted != std::vector<int64_t>({0,1,2,3,4,5,6,7}))
    throw std::invalid_argument("ht_channel_order must be a permutation of 0..7");
  for (int i=0;i<8;++i) channel_order_[i]=static_cast<int>(order[i]);
  for (double v : {weight_,unknown_penalty_,footprint_radius_})
    if (!std::isfinite(v) || v<0) throw std::invalid_argument("Negative/non-finite HT parameter");
  for (double v : {timeout_,step_,lookahead_,reached_distance_})
    if (!std::isfinite(v) || v<=0) throw std::invalid_argument("Non-positive HT parameter");
  if (!std::isfinite(heading_offset_) || step_<0.001 || footprint_radius_>3)
    throw std::invalid_argument("HT sampling parameters outside supported range");
  if (reached_distance_>=lookahead_)
    throw std::invalid_argument("HT waypoint reached distance must be smaller than lookahead");
  if (enabled_) {
    permission_=node->create_publisher<std_msgs::msg::Bool>("/ht_navigation_allowed",1);
    subscription_=node->create_subscription<grid_map_msgs::msg::GridMap>(
      topic,rclcpp::QoS(1).best_effort(),
      [this](grid_map_msgs::msg::GridMap::ConstSharedPtr msg){receive(msg);});
    RCLCPP_INFO(logger_,"HT enabled: weight=%.3f unknown=%.3f calibrated=%d",
                weight_,unknown_penalty_,calibrated_);
  }
}

void HtCostMap::receive(grid_map_msgs::msg::GridMap::ConstSharedPtr msg) {
  try {
    // The upstream converter indexes layout.dim and maps the raw buffer
    // without checking its length. Validate before entering Eigen/GridMap.
    const auto& info=msg->info;
    for (double v : {info.resolution,info.length_x,info.length_y})
      if (!std::isfinite(v) || v<=0) throw std::runtime_error("Invalid GridMap geometry");
    for (double v : {info.pose.position.x,info.pose.position.y,info.pose.position.z})
      if (!std::isfinite(v)) throw std::runtime_error("Invalid GridMap position");
    const double rows=std::round(info.length_x/info.resolution);
    const double cols=std::round(info.length_y/info.resolution);
    if (!std::isfinite(rows) || !std::isfinite(cols) || rows<1 || cols<1 ||
        rows>std::numeric_limits<int>::max() || cols>std::numeric_limits<int>::max() ||
        msg->header.frame_id.empty() || msg->layers.size()!=msg->data.size() ||
        msg->data.empty() || msg->outer_start_index>=rows || msg->inner_start_index>=cols)
      throw std::runtime_error("Invalid GridMap dimensions/frame/buffer index");
    for (const auto& data : msg->data) {
      const auto& dim=data.layout.dim;
      if (dim.size()!=2 || dim[0].label!="column_index" || dim[1].label!="row_index" ||
          dim[0].size!=cols || dim[1].size!=rows || data.layout.data_offset!=0 ||
          data.data.size()!=static_cast<size_t>(rows)*static_cast<size_t>(cols) ||
          dim[0].stride!=data.data.size() || dim[1].stride!=rows)
        throw std::runtime_error("Invalid GridMap array layout/data length");
    }
    // grid_map's geometry is axis-aligned within its frame; reject tilted/rotated
    // message poses rather than silently dropping an unsupported orientation.
    const auto& q=msg->info.pose.orientation;
    if (!std::isfinite(q.x) || !std::isfinite(q.y) || !std::isfinite(q.z) || !std::isfinite(q.w) ||
        std::abs(q.x)>1e-6 || std::abs(q.y)>1e-6 || std::abs(q.z)>1e-6 ||
        std::abs(std::abs(q.w)-1)>1e-6)
      throw std::runtime_error("Unsupported GridMap pose orientation");
    grid_map::GridMap grid;
    if (!grid_map::GridMapRosConverter::fromMessage(*msg,grid))
      throw std::runtime_error("Cannot decode GridMap");
    for (int k=0;k<8;++k)
      if (!grid.exists("ht_dir_"+std::to_string(k)))
        throw std::runtime_error("Missing ht_dir layers; set aggregate_only=false");
    if (!grid.exists("ht_valid")) throw std::runtime_error("Missing ht_valid");
    tf2::Transform transform;
    transform.setIdentity();
    if (msg->header.frame_id != frame_) {
      auto tf=buffer_.lookupTransform(frame_,msg->header.frame_id,
          rclcpp::Time(msg->header.stamp),rclcpp::Duration::from_seconds(0.0));
      tf2::fromMsg(tf.transform,transform);
    }
    double roll,pitch,yaw;
    tf2::Matrix3x3(transform.getRotation()).getRPY(roll,pitch,yaw);
    if (std::abs(roll)>1e-3 || std::abs(pitch)>1e-3)
      throw std::runtime_error("HT requires gravity-aligned map frames");
    auto out=std::make_shared<Map>();
    out->rows=grid.getSize()(0); out->cols=grid.getSize()(1);
    out->resolution=grid.getResolution();
    out->stamp=rclcpp::Time(msg->header.stamp).seconds();
    out->yaw=yaw; out->heading_offset=heading_offset_;
    out->channel_order=channel_order_;
    auto center=transform*tf2::Vector3(grid.getPosition().x(),grid.getPosition().y(),0);
    out->center_x=center.x(); out->center_y=center.y();
    const size_t size=static_cast<size_t>(out->rows)*out->cols;
    out->valid.assign(size,0);
    for (auto& layer : out->probabilities)
      layer.assign(size,std::numeric_limits<float>::quiet_NaN());
    for (grid_map::GridMapIterator it(grid); !it.isPastEnd(); ++it) {
      grid_map::Position pos;
      grid.getPosition(*it,pos);
      const int row=static_cast<int>(std::floor(out->rows*0.5-
                       (pos.x()-grid.getPosition().x())/out->resolution));
      const int col=static_cast<int>(std::floor(out->cols*0.5-
                       (pos.y()-grid.getPosition().y())/out->resolution));
      if (row<0 || col<0 || row>=out->rows || col>=out->cols)
        throw std::runtime_error("Invalid GridMap index");
      const size_t index=static_cast<size_t>(row)*out->cols+col;
      const float valid=grid.at("ht_valid",*it);
      out->valid[index]=std::isfinite(valid) && valid>=0.5;
      for (int k=0;k<8;++k) {
        const float p=grid.at("ht_dir_"+std::to_string(k),*it);
        out->probabilities[k][index]=p;
        if (!std::isfinite(p) || p<0 || p>1) {
          if (std::isfinite(valid) && valid>=0.5)
            throw std::runtime_error("Invalid probability in claimed-valid HT cell");
          out->valid[index]=0;
        }
      }
    }
    if (!out->wellFormed()) throw std::runtime_error("Invalid HT map geometry");
    std::lock_guard<std::mutex> lock(mutex_);
    latest_=std::move(out);latest_error_.clear();
  } catch (const std::exception& e) {
    std::lock_guard<std::mutex> lock(mutex_);
    latest_.reset();latest_error_=std::string("HT_MAP_REJECTED: ")+e.what();
    RCLCPP_WARN_THROTTLE(logger_,*clock_,2000,"HT map rejected: %s",e.what());
  }
}
void HtCostMap::beginCycle() {
  std::lock_guard<std::mutex> lock(mutex_);
  cycle_=latest_;cycle_error_=latest_error_;
}
bool HtCostMap::ready() const {
  return !enabled_ || (calibrated_ && cycle_ && cycle_->fresh(clock_->now().seconds(),timeout_));
}
std::string HtCostMap::status() const {
  if (!enabled_) return "HT_DISABLED";
  if (!calibrated_) return "HT_UNCALIBRATED";
  if (!cycle_) return cycle_error_;
  const double now=clock_->now().seconds();
  if (now<cycle_->stamp) return "HT_MAP_FUTURE_STAMP";
  if (!cycle_->fresh(now,timeout_)) return "HT_MAP_STALE";
  return "HT_MAP_FRESH";
}
void HtCostMap::publishPermission(bool allowed) {
  if (!permission_) return;
  std_msgs::msg::Bool msg;
  msg.data=allowed && ready();
  permission_->publish(msg);
  if (!msg.data)
    RCLCPP_WARN_THROTTLE(logger_,*clock_,3000,
      "HT waypoint held: check calibration, fresh map/TF, sensor updates and valid local route");
}
double HtCostMap::cost(const Point& a,const Point& b) const {
  if (!enabled_) return std::hypot(std::hypot(b.x-a.x,b.y-a.y),b.z-a.z);
  if (!ready()) return std::numeric_limits<double>::infinity();
  auto result=segment(cycle_.get(),a,b,step_);
  if (result.unknown_length>0 && prior_.initialized && !prior_.retired) {
    const int n=std::max(1,static_cast<int>(std::ceil(result.length/std::min(step_,cycle_->resolution/2))));
    const double heading=std::atan2(b.y-a.y,b.x-a.x),ds=result.length/n;
    for (int i=0;i<n;++i) {
      const double t=(i+0.5)/n,x=a.x+t*(b.x-a.x),y=a.y+t*(b.y-a.y);
      if (!std::isfinite(cycle_->sample(x,y,heading)) && prior_.contains(x,y))
        result.unknown_length=std::max(0.0,result.unknown_length-ds);
    }
  }
  return result.total(weight_,unknown_penalty_);
}
Support HtCostMap::support(const Point& a,const Point& b) const {
  if (!enabled_) return Support::KNOWN;
  if (!ready()) return Support::FAULT;
  const double length=std::hypot(b.x-a.x,b.y-a.y);
  const double count=std::ceil(length/std::min(step_,cycle_->resolution/2));
  if (!std::isfinite(count) || count>10000) return Support::FAULT;
  const int n=std::max(1,static_cast<int>(count));
  const double heading=std::atan2(b.y-a.y,b.x-a.x);
  // This checks HT support, NOT physical footprint collision or stopping safety.
  const double cells=std::ceil(footprint_radius_/cycle_->resolution);
  if (!std::isfinite(cells) || cells>100) return Support::FAULT;
  const int radius=static_cast<int>(cells);
  Support result=Support::KNOWN;
  for (int i=0;i<=n;++i) {
    const double t=static_cast<double>(i)/n;
    for (int ix=-radius;ix<=radius;++ix) for (int iy=-radius;iy<=radius;++iy) {
      const double dx=ix*cycle_->resolution,dy=iy*cycle_->resolution;
      if (std::hypot(dx,dy)>footprint_radius_+cycle_->resolution/2) continue;
      const double x=a.x+t*(b.x-a.x)+dx,y=a.y+t*(b.y-a.y)+dy;
      if (!std::isfinite(cycle_->sample(x,y,heading))) {
        if (!prior_.contains(x,y)) return Support::UNKNOWN;
        result=Support::STARTUP_PRIOR;
      }
    }
  }
  return result;
}
bool HtCostMap::knownSegment(const Point& a,const Point& b) const {
  return support(a,b)==Support::KNOWN;
}
}
