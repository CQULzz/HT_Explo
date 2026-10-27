#include "ht_cost/ht_cost_map.h"
#include <grid_map_ros/GridMapRosConverter.hpp>
#include <grid_map_core/iterators/GridMapIterator.hpp>
#include <opencv2/imgproc.hpp>
#include <tf2/LinearMath/Matrix3x3.h>
#include <tf2/LinearMath/Transform.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>

namespace ht_cost_ns {
namespace {
using TerrainHistory=std::map<std::pair<int,int>,HtCostMap::TerrainCell>;
bool terrainGuidanceAllowed(const TerrainHistory& history,const Map* latest,
                            bool configuration_scores,double x,double y) {
  // Coarse OR aggregation can include a nearby safe center in the same0.2m
  // cell. Do not let it admit this exact center if a known physical obstacle
  // overlaps its body. All configuration channels share this physical mask.
  if (configuration_scores && latest) {
    size_t index;int channel;
    if (latest->cellAndChannel(x,y,latest->yaw+latest->heading_offset,index,channel) &&
        latest->blocked_footprint[channel][index]) return false;
  }
  const auto it=history.find({static_cast<int>(std::floor(x/.2)),
                              static_cast<int>(std::floor(y/.2))});
  return it==history.end() || it->second.feasible;
}
}
HtCostMap::HtCostMap(rclcpp::Node::SharedPtr node,bool publish_permission)
  : clock_(node->get_clock()), logger_(node->get_logger()),
    buffer_(clock_) {
  enabled_=node->declare_parameter<bool>("ht_enabled",false);
  const auto mode=node->declare_parameter<std::string>("ht_exploration_mode","tare_waypoint");
  if (mode!="tare_waypoint" && mode!="legacy_xytheta_greedy")
    throw std::invalid_argument("Unknown HT exploration mode");
  tare_coverage_=mode=="tare_waypoint";
  collect_terrain_=publish_permission && enabled_ && tare_coverage_;
  calibrated_=node->declare_parameter<bool>("ht_directions_calibrated",false);
  min_probability_=node->declare_parameter<double>("ht_min_probability",0.5);
  timeout_=node->declare_parameter<double>("ht_map_timeout",1.0);
  step_=node->declare_parameter<double>("ht_sample_step",0.02);
  lookahead_=node->declare_parameter<double>("ht_lookahead_distance",2.0);
  reached_distance_=node->declare_parameter<double>("ht_waypoint_reached_distance",0.3);
  footprint_radius_=node->declare_parameter<double>("ht_validity_radius",0.6);
  const auto score_semantics=node->declare_parameter<std::string>("ht_score_semantics","point");
  if (score_semantics!="point" && score_semantics!="configuration")
    throw std::invalid_argument("HT score semantics must be point or configuration");
  configuration_scores_=score_semantics=="configuration";
  require_reversible_motion_=node->declare_parameter<bool>("ht_require_reversible_motion",false);
  heading_offset_=node->declare_parameter<double>("ht_heading_offset",0.0);
  const auto policy=node->declare_parameter<std::string>("ht_unknown_policy","strict");
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
  for (double v : {min_probability_,footprint_radius_})
    if (!std::isfinite(v) || v<0) throw std::invalid_argument("Negative/non-finite HT parameter");
  if (min_probability_>1) throw std::invalid_argument("ht_min_probability must be in [0,1]");
  for (double v : {timeout_,step_,lookahead_,reached_distance_})
    if (!std::isfinite(v) || v<=0) throw std::invalid_argument("Non-positive HT parameter");
  if (!std::isfinite(heading_offset_) || step_<0.001 || footprint_radius_>3)
    throw std::invalid_argument("HT sampling parameters outside supported range");
  if (reached_distance_>=lookahead_)
    throw std::invalid_argument("HT waypoint reached distance must be smaller than lookahead");
  if (enabled_) {
    // Invalid parameters must fail before creating a TF executor thread;
    // unwinding a half-constructed listener can hang node initialization.
    listener_=std::make_unique<tf2_ros::TransformListener>(buffer_);
    if (publish_permission)
      permission_=node->create_publisher<std_msgs::msg::Bool>("/ht_navigation_allowed",1);
    owns_prior_=publish_permission;
    const auto startup_topic=node->declare_parameter<std::string>("ht_startup_topic","/ht_startup_prior");
    // Retain the original start/expiry for late subscribers, not a new TTL.
    const auto startup_qos=rclcpp::QoS(1).reliable().transient_local();
    if (owns_prior_)
      startup_pub_=node->create_publisher<tare_planner::msg::StartupPrior>(startup_topic,startup_qos);
    else
      startup_sub_=node->create_subscription<tare_planner::msg::StartupPrior>(startup_topic,startup_qos,
        [this](tare_planner::msg::StartupPrior::ConstSharedPtr msg){receiveStartupPrior(*msg);});
    // Map decoding and footprint dilation must be serviced while the default
    // planner callback group is spending seconds evaluating XYtheta routes.
    map_callback_group_=node->create_callback_group(rclcpp::CallbackGroupType::MutuallyExclusive);
    rclcpp::SubscriptionOptions options;
    options.callback_group=map_callback_group_;
    subscription_=node->create_subscription<grid_map_msgs::msg::GridMap>(
      topic,rclcpp::QoS(1).reliable(),
      [this](grid_map_msgs::msg::GridMap::ConstSharedPtr msg){receive(msg);},options);
    RCLCPP_INFO(logger_,"HT hard gate: min_probability=%.3f unknown_policy=%s calibrated=%d reversible=%d scores=%s",
                min_probability_,policy.c_str(),calibrated_,require_reversible_motion_,score_semantics.c_str());
  }
}

StartupPrior HtCostMap::startupPrior() const {
  std::lock_guard<std::mutex> lock(prior_mutex_);
  auto prior=prior_;
  const double now=clock_->now().seconds();
  if (prior.initialized && (now<prior.start || now-prior.start>=prior.lifetime)) prior.retired=true;
  return prior;
}

void HtCostMap::publishStartupPrior() {
  if (!startup_pub_) return;
  const auto prior=startupPrior();
  if (!prior.initialized) return;
  tare_planner::msg::StartupPrior msg;
  msg.header.frame_id="map";
  msg.header.stamp=rclcpp::Time(static_cast<int64_t>(std::llround(prior.start*1e9)),clock_->get_clock_type());
  msg.expires_at=rclcpp::Time(static_cast<int64_t>(std::llround((prior.start+prior.lifetime)*1e9)),clock_->get_clock_type());
  msg.anchor.x=prior.anchor.x;msg.anchor.y=prior.anchor.y;msg.anchor.z=prior.anchor.z;
  msg.radius=prior.radius;msg.retired=prior.retired;
  startup_pub_->publish(msg);
}

void HtCostMap::start(Point p) {
  if (!owns_prior_ || !std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z)) return;
  {
    std::lock_guard<std::mutex> lock(prior_mutex_);
    prior_.initialize(p,clock_->now().seconds());
  }
  publishStartupPrior();
}

void HtCostMap::updateExecution(Point p,bool was_fallback) {
  const double now=clock_->now().seconds();
  bool newly_retired=false;
  {
    std::lock_guard<std::mutex> lock(prior_mutex_);
    const bool retired=prior_.retired;
    prior_.update(p,now);
    newly_retired=prior_.retired && !retired;
  }
  if (newly_retired && owns_prior_) publishStartupPrior();
  budget_.update(now,p,was_fallback);
}

void HtCostMap::receiveStartupPrior(const tare_planner::msg::StartupPrior& msg) {
  const auto& p=msg.anchor;
  if (msg.header.frame_id!="map" || msg.header.stamp.sec<0 || msg.expires_at.sec<0 ||
      msg.header.stamp.nanosec>=1000000000u || msg.expires_at.nanosec>=1000000000u ||
      !std::isfinite(p.x) || !std::isfinite(p.y) || !std::isfinite(p.z) ||
      !std::isfinite(msg.radius) || msg.radius<0 || msg.radius>3) return;
  const double start=rclcpp::Time(msg.header.stamp).seconds();
  const double expiry=rclcpp::Time(msg.expires_at).seconds();
  const double now=clock_->now().seconds();
  if (expiry<=start || start>now) return;
  std::lock_guard<std::mutex> lock(prior_mutex_);
  if (prior_.initialized && (std::abs(prior_.start-start)>1e-6 ||
      std::abs(prior_.start+prior_.lifetime-expiry)>1e-6 || prior_.radius!=msg.radius ||
      prior_.anchor.x!=p.x || prior_.anchor.y!=p.y || prior_.anchor.z!=p.z)) {
    // A follower must not silently join another mission or reset its disk.
    startup_sync_fault_=true;prior_.retired=true;return;
  }
  if (!prior_.initialized) {
    prior_.initialize({p.x,p.y,p.z},start);
    prior_.radius=msg.radius;prior_.lifetime=expiry-start;
  }
  // Even tolerated floating-point round trips cannot accumulate time/radius.
  prior_.retired=prior_.retired || msg.retired || now>=prior_.start+prior_.lifetime;
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
    if (configuration_scores_ && (!grid.exists("ht_observation_valid") || !grid.exists("ht_obstacle")))
      throw std::runtime_error("Configuration HT requires separate physical observation and obstacle layers");
    if (collect_terrain_ && !grid.exists("ht_elevation"))
      throw std::runtime_error("TARE waypoint mode requires same-source ht_elevation");
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
    std::vector<unsigned char> physical_valid(size);
    std::vector<unsigned char> occupied(size,0);
    const bool separate_observation=grid.exists("ht_observation_valid");
    struct Aggregate { double x=0,y=0,z=0; int count=0; bool feasible=false; };
    std::map<std::pair<int,int>,Aggregate> terrain;

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
      const float physical=separate_observation ? grid.at("ht_observation_valid",*it):valid;
      physical_valid[index]=std::isfinite(physical) && physical>=0.5;
      if (configuration_scores_) {
        const float obstacle=grid.at("ht_obstacle",*it);
        if (!std::isfinite(obstacle) || (obstacle!=0.f && obstacle!=1.f))
          throw std::runtime_error("Invalid HT obstacle mask");
        occupied[index]=obstacle>=.5;
      }
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
    // Physical obstacle/observation cells require a body footprint. Vehicle
    // configuration scores already describe a vehicle trial at a reference
    // position and heading; dilating them treats neighbouring *configurations*
    // as physical obstacles. Keep the legacy point-score contract explicit.
    const double radius_cells=std::ceil(footprint_radius_/out->resolution)+1;
    if (!std::isfinite(radius_cells) || radius_cells>101)
      throw std::runtime_error("HT footprint/map resolution outside supported range");
    const int radius=static_cast<int>(radius_cells);
    cv::Mat kernel(2*radius+1,2*radius+1,CV_8UC1,cv::Scalar(0));
    for (int ix=-radius;ix<=radius;++ix) for (int iy=-radius;iy<=radius;++iy)
      if (std::hypot(ix*out->resolution,iy*out->resolution) <=
          footprint_radius_+std::sqrt(2.0)*out->resolution)
        kernel.at<unsigned char>(ix+radius,iy+radius)=1;
    std::vector<unsigned char> source(size);
    cv::Mat src(out->rows,out->cols,CV_8UC1,source.data());
    cv::Mat dst;
    for (size_t i=0;i<size;++i) source[i]=physical_valid[i] ? 0 : 1;
    cv::dilate(src,dst,kernel,cv::Point(-1,-1),1,cv::BORDER_CONSTANT,cv::Scalar(1));
    out->unknown_footprint.assign(dst.datastart,dst.dataend);
    out->physical_valid=std::move(physical_valid);
    for (int k=0;k<8;++k) {
      for (size_t i=0;i<size;++i)
        source[i]=configuration_scores_ ? occupied[i] :
          (out->valid[i] && out->probabilities[k][i]<min_probability_ ? 1 : 0);
      cv::dilate(src,dst,kernel,cv::Point(-1,-1),1,cv::BORDER_CONSTANT,cv::Scalar(0));
      out->blocked_footprint[k].assign(dst.datastart,dst.dataend);
    }
    if (!out->wellFormed()) throw std::runtime_error("Invalid HT map geometry");
    // Collapse only after the execution body's known-obstacle masks exist.
    // Unknown body observations remain optimistic exploration guidance; making
    // them a new hard coarse barrier would seal off every unseen frontier at
    // the local-map rim. Execution keeps its independent strict unknown gate.
    if (collect_terrain_) for (grid_map::GridMapIterator it(grid); !it.isPastEnd(); ++it) {
      const float observed=grid.at("ht_observation_valid",*it);
      const float scored=grid.at("ht_valid",*it);
      const bool measured=std::isfinite(observed) && observed>=.5;
      const bool eligible=measured && std::isfinite(scored) && scored>=.5;
      grid_map::Position p;grid.getPosition(*it,p);
      const auto world=transform*tf2::Vector3(p.x(),p.y(),0);
      size_t index;int channel;
      if (!out->cellAndChannel(world.x(),world.y(),out->yaw+out->heading_offset,index,channel))
        throw std::runtime_error("Terrain reference outside decoded HT grid");
      const bool body_obstacle=configuration_scores_ && out->blocked_footprint[0][index];
      // A missing prediction must not hide newly observed physical rejection
      // from history. Unknown, unblocked cells retain the old guidance policy.
      if (!eligible && !body_obstacle) continue;
      auto& a=terrain[{static_cast<int>(std::floor(world.x()/.2)),static_cast<int>(std::floor(world.y()/.2))}];
      a.x=world.x();a.y=world.y();
      for(int k=0;k<8;++k) {
        const float score=out->probabilities[k][index];
        const bool known_obstacle=configuration_scores_ && out->blocked_footprint[k][index];
        a.feasible=a.feasible || (eligible && std::isfinite(score) && score>=min_probability_ && !known_obstacle);
      }
      const float z=grid.at("ht_elevation",*it);
      if (measured && grid.at("ht_obstacle",*it)<.5 && std::isfinite(z)) {a.z+=z+transform.getOrigin().z();++a.count;}
    }
    std::lock_guard<std::mutex> lock(mutex_);
    for (const auto& entry:terrain) {
      auto& cell=terrain_history_[entry.first];const auto& a=entry.second;
      if(out->stamp<cell.stamp) continue;
      cell.x=a.x;cell.y=a.y;cell.stamp=out->stamp;cell.feasible=a.feasible;
      cell.height=a.count ? a.z/a.count : std::numeric_limits<double>::quiet_NaN();
    }
    latest_=std::move(out);latest_error_.clear();
  } catch (const std::exception& e) {
    std::lock_guard<std::mutex> lock(mutex_);
    latest_.reset();latest_error_=std::string("HT_MAP_REJECTED: ")+e.what();
    RCLCPP_WARN_THROTTLE(logger_,*clock_,2000,"HT map rejected: %s",e.what());
  }
}
std::vector<HtCostMap::TerrainCell> HtCostMap::terrainWindow(double x,double y,double radius) {
  std::lock_guard<std::mutex> lock(mutex_);std::vector<TerrainCell> result;
  for(const auto& entry:terrain_history_) {
    const auto& c=entry.second;
    if(std::abs(c.x-x)<=radius && std::abs(c.y-y)<=radius && std::isfinite(c.height)) result.push_back(c);
  }
  return result;
}
bool HtCostMap::terrainAdmissible(double x,double y) {
  std::lock_guard<std::mutex> lock(mutex_);
  return terrainGuidanceAllowed(terrain_history_,latest_.get(),configuration_scores_,x,y);
}
std::vector<bool> HtCostMap::terrainAdmissible(const std::vector<Point>& points) {
  std::lock_guard<std::mutex> lock(mutex_);std::vector<bool> allowed;allowed.reserve(points.size());
  for(const auto& p:points) {
    allowed.push_back(terrainGuidanceAllowed(terrain_history_,latest_.get(),configuration_scores_,p.x,p.y));
  }
  return allowed;
}
void HtCostMap::beginCycle() {
  std::lock_guard<std::mutex> lock(mutex_);
  cycle_=latest_;cycle_error_=latest_error_;
}
bool HtCostMap::ready() const {
  std::lock_guard<std::mutex> lock(prior_mutex_);
  if (enabled_ && startup_sync_fault_) return false;
  return !enabled_ || (calibrated_ && cycle_ && cycle_->fresh(clock_->now().seconds(),timeout_));
}
std::string HtCostMap::status() const {
  std::lock_guard<std::mutex> lock(prior_mutex_);
  if (!enabled_) return "HT_DISABLED";
  if (startup_sync_fault_) return "HT_STARTUP_PRIOR_CONFLICT";
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
  // Planning and execution use exactly the same HT footprint gate. A rejected
  // edge never enters the shortest-path graph; accepted edges use distance only.
  if (!permits(support(a,b))) return std::numeric_limits<double>::infinity();
  return std::hypot(std::hypot(b.x-a.x,b.y-a.y),b.z-a.z);
}
Support HtCostMap::support(const Point& a,const Point& b) const {
  return supportDirected(a,b,std::atan2(b.y-a.y,b.x-a.x));
}
Support HtCostMap::poseSupport(double x,double y,double yaw) const {
  const Point p{x,y,0};
  return supportDirected(p,p,yaw);
}
Support HtCostMap::motionSupport(Pose2 a,Pose2 b) const {
  if (!enabled_) return Support::KNOWN;
  if (!ready() || !std::isfinite(a.yaw) || !std::isfinite(b.yaw)) return Support::FAULT;
  const double angle=wrapYaw(b.yaw-a.yaw);
  std::vector<double> cuts{0,1};
  // Split at the actual eight-channel boundaries, rather than selecting
  // headings at arbitrary angular sample offsets.
  if (std::abs(angle)>1e-10) {
    const double offset=cycle_->yaw+cycle_->heading_offset;
    const double low=std::min(a.yaw,a.yaw+angle)-offset;
    const double high=std::max(a.yaw,a.yaw+angle)-offset;
    for (int k=static_cast<int>(std::floor(low/(kPi/4)-.5));
         k<=static_cast<int>(std::ceil(high/(kPi/4)-.5));++k) {
      const double t=(offset+(k+.5)*(kPi/4)-a.yaw)/angle;
      if (t>1e-10 && t<1-1e-10) cuts.push_back(t);
    }
  }
  std::sort(cuts.begin(),cuts.end());
  auto point=[&](double t) {return Point{a.x+t*(b.x-a.x),a.y+t*(b.y-a.y),0};};
  Support result=Support::KNOWN;
  auto merge=[&](Support s) {
    if (s==Support::FAULT || s==Support::BLOCKED) {result=s;return false;}
    if (s==Support::UNKNOWN || (s==Support::STARTUP_PRIOR && result==Support::KNOWN)) result=s;
    return true;
  };
  if (!merge(poseSupport(a.x,a.y,a.yaw)) || !merge(poseSupport(b.x,b.y,b.yaw))) return result;
  for (size_t i=1;i<cuts.size();++i)
    if (!merge(supportDirected(point(cuts[i-1]),point(cuts[i]),
             a.yaw+angle*(cuts[i-1]+cuts[i])*.5))) return result;
  if (std::hypot(b.x-a.x,b.y-a.y)>1e-6) {
    if (!merge(support(point(0),point(1)))) return result;
    // Preserve the exact swept body poses when driving the same arc backward.
    // Body-heading checks above are already symmetric under path reversal;
    // the additional travel-direction gate is not. Do not average opposite
    // probabilities or assume a one-way HT edge can be retraced.
    if (require_reversible_motion_) {
      const auto reverse=support(point(1),point(0));
      if (!permits(reverse))
        RCLCPP_INFO_THROTTLE(logger_,*clock_,1000,
          "HT_RETURN_MARGIN_BLOCK map_stamp=%.9f a=(%.3f,%.3f,%.3f) b=(%.3f,%.3f,%.3f) reverse_support=%d",
          cycle_->stamp,a.x,a.y,a.yaw,b.x,b.y,b.yaw,static_cast<int>(reverse));
      merge(reverse);
    }
  }
  return result;
}
Support HtCostMap::supportDirected(const Point& a,const Point& b,double heading) const {
  if (!enabled_) return Support::KNOWN;
  if (!ready()) return Support::FAULT;
  const auto prior=startupPrior();
  size_t first,last;int channel,last_channel;
  if (!cycle_->cellAndChannel(a.x,a.y,heading,first,channel) ||
      !cycle_->cellAndChannel(b.x,b.y,heading,last,last_channel)) return Support::UNKNOWN;
  const double co=std::cos(cycle_->yaw),si=std::sin(cycle_->yaw),res=cycle_->resolution;
  auto gridPosition=[&](Point p) {
    const double dx=p.x-cycle_->center_x,dy=p.y-cycle_->center_y;
    return std::pair<double,double>{cycle_->rows*.5-(co*dx+si*dy)/res,
                                  cycle_->cols*.5-(-si*dx+co*dy)/res};
  };
  const auto start=gridPosition(a),end=gridPosition(b);
  const double dr=end.first-start.first,dc=end.second-start.second;
  int row=first/cycle_->cols,col=first%cycle_->cols;
  const int end_row=last/cycle_->cols,end_col=last%cycle_->cols;
  const int sr=(dr>0)-(dr<0),sc=(dc>0)-(dc<0);
  const double inf=std::numeric_limits<double>::infinity();
  const double delta_r=sr ? 1/std::abs(dr):inf,delta_c=sc ? 1/std::abs(dc):inf;
  double tr=sr ? ((sr>0 ? row+1:row)-start.first)/dr:inf;
  double tc=sc ? ((sc>0 ? col+1:col)-start.second)/dc:inf;
  Support result=Support::KNOWN;
  auto inspect=[&](int r,int c) {
    if (r<0 || c<0 || r>=cycle_->rows || c>=cycle_->cols) return Support::UNKNOWN;
    const size_t index=static_cast<size_t>(r)*cycle_->cols+c;
    if (cycle_->blocked_footprint[channel][index]) return Support::BLOCKED;
    if (cycle_->valid[index] && cycle_->probabilities[channel][index]<min_probability_)
      return Support::BLOCKED;
    if (cycle_->valid[index] && !cycle_->unknown_footprint[index]) return Support::KNOWN;
    // Unknown uses the same rasterized support mask as known-unsafe terrain.
    // Re-scanning at arbitrary sub-cell offsets made split edges disagree.
    if (!prior.initialized || prior.retired) return Support::UNKNOWN;
    const double mx=(cycle_->rows*.5-r-.5)*res,my=(cycle_->cols*.5-c-.5)*res;
    const double cx=cycle_->center_x+co*mx-si*my,cy=cycle_->center_y+si*mx+co*my;
    if (!cycle_->valid[index] && !prior.contains(cx,cy)) return Support::UNKNOWN;
    const int radius=static_cast<int>(std::ceil(footprint_radius_/res))+1;
    Support s=Support::STARTUP_PRIOR;
    for (int ix=-radius;ix<=radius;++ix) for (int iy=-radius;iy<=radius;++iy) {
      if (std::hypot(ix*res,iy*res)>footprint_radius_+std::sqrt(2.0)*res) continue;
      const int rr=r+ix,cc=c+iy;
      const bool observed=rr>=0 && cc>=0 && rr<cycle_->rows && cc<cycle_->cols &&
        cycle_->physical_valid[static_cast<size_t>(rr)*cycle_->cols+cc];
      const double local_x=mx-ix*res,local_y=my-iy*res;
      const double x=cycle_->center_x+co*local_x-si*local_y;
      const double y=cycle_->center_y+si*local_x+co*local_y;
      if (!observed && !prior.contains(x,y)) s=Support::UNKNOWN;
    }
    return s;
  };
  auto visit=[&](int r,int c) {
    const auto s=inspect(r,c);
    if (s==Support::BLOCKED || s==Support::FAULT) {result=s;return false;}
    if (s==Support::UNKNOWN || (s==Support::STARTUP_PRIOR && result==Support::KNOWN)) result=s;
    return true;
  };
  // Supercover DDA: every crossed cell is visited, including both neighbours
  // of an exact grid corner. Splitting a segment cannot hide a touched cell.
  for (int count=0;count<=cycle_->rows+cycle_->cols+4;++count) {
    if (!visit(row,col)) return result;
    if (row==end_row && col==end_col) return result;
    if (std::abs(tr-tc)<1e-12) {
      if (!visit(row+sr,col) || !visit(row,col+sc)) return result;
      row+=sr;col+=sc;tr+=delta_r;tc+=delta_c;
    } else if (tr<tc) {row+=sr;tr+=delta_r;}
    else {col+=sc;tc+=delta_c;}
  }
  return Support::FAULT;
}
bool HtCostMap::knownSegment(const Point& a,const Point& b) const {
  return support(a,b)==Support::KNOWN;
}
}
