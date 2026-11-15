#include <gazebo/gazebo.hh>
#include <gazebo/sensors/RaySensor.hh>
#include <gazebo/physics/MultiRayShape.hh>
#include <gazebo/physics/RayShape.hh>
#include <gazebo_ros/node.hpp>
#include <sensor_msgs/msg/point_cloud2.hpp>
#include <std_msgs/msg/string.hpp>
#include <cmath>
#include <cstring>
#include <limits>
#include <sstream>
#include <iomanip>
#include <vector>

namespace gazebo {
// Nominal channel angles are explicit. Changing just <vertical> min/max would
// give a fictitious uniform 32-beam sensor and wrong ground visibility.
class Helios32Ray final : public SensorPlugin {
 public:
  void Load(sensors::SensorPtr sensor,sdf::ElementPtr config) override {
    sensor_=std::dynamic_pointer_cast<sensors::RaySensor>(sensor);
    if(!sensor_)throw std::runtime_error("Helios32 requires a CPU ray sensor");
    node_=gazebo_ros::Node::Get(config);
    auto parse=[](std::string s){std::istringstream in(s);std::vector<double> out;double x;while(in>>x)out.push_back(x);return out;};
    angles_=parse(config->Get<std::string>("vertical_angles_deg"));
    maxima_=parse(config->Get<std::string>("channel_max_ranges_m"));
    if(angles_.size()!=32 || maxima_.size()!=32 || sensor_->VerticalRayCount()!=32 || sensor_->RangeCount()!=sensor_->RayCount())
      throw std::runtime_error("Helios32 channel/sample contract mismatch");
    horizontal_=sensor_->RayCount();window_=config->Get<double>("optical_window_radius_m");
    min_=config->Get<double>("output_min_range_m");frame_=config->Get<std::string>("frame_name");
    mode_=config->HasElement("self_filter_mode")?config->Get<std::string>("self_filter_mode"):"collision_identity";
    if(mode_!="crop_box" && mode_!="collision_identity")throw std::runtime_error("Invalid self_filter_mode");
    if(mode_=="crop_box"){
      const auto lo=parse(config->Get<std::string>("crop_min_xyz")),hi=parse(config->Get<std::string>("crop_max_xyz"));
      if(lo.size()!=3 || hi.size()!=3)throw std::runtime_error("Crop bounds require XYZ");
      for(size_t j=0;j<3;++j){
        if(!std::isfinite(lo[j]) || !std::isfinite(hi[j]) || lo[j]>=hi[j])throw std::runtime_error("Invalid crop bounds");
        crop_min_[j]=lo[j];crop_max_[j]=hi[j];
      }
    }
    if(horizontal_<4 || window_<0 || window_>.2 || min_<0 || min_>1)throw std::runtime_error("Invalid Helios32 geometry");
    shape_=sensor_->LaserShape();const auto offset=sensor_->Pose();
    if(shape_->RayCount()!=32*horizontal_ || shape_->GetMinRange()!=0)throw std::runtime_error("Ray trace must start at optical window, not blind-range boundary");
    starts_.reserve(32*horizontal_);directions_.reserve(32*horizontal_);
    for(size_t ring=0;ring<32;++ring)for(unsigned i=0;i<horizontal_;++i){
      if(!std::isfinite(angles_[ring]) || !std::isfinite(maxima_[ring]) || maxima_[ring]<=min_)throw std::runtime_error("Invalid channel calibration");
      const double a=-M_PI+2*M_PI*i/horizontal_,v=angles_[ring]*M_PI/180;
      const ignition::math::Vector3d start(window_*std::cos(a),window_*std::sin(a),0);
      const ignition::math::Vector3d direction(std::cos(v)*std::cos(a),std::cos(v)*std::sin(a),std::sin(v));
      starts_.push_back(start);directions_.push_back(direction);
      if(!shape_->SetRay(ring*horizontal_+i,offset.Pos()+offset.Rot()*start,offset.Pos()+offset.Rot()*(start+direction*sensor_->RangeMax())))
        throw std::runtime_error("Unable to configure nonuniform ray");
    }
    raw_=node_->create_publisher<sensor_msgs::msg::PointCloud2>("/rslidar_points",rclcpp::QoS(2).reliable());
    filtered_=node_->create_publisher<sensor_msgs::msg::PointCloud2>("/velodyne_points",rclcpp::QoS(2).reliable());
    status_=node_->create_publisher<std_msgs::msg::String>("/helios_sim/scan_status",10);
    connection_=sensor_->ConnectUpdated(std::bind(&Helios32Ray::scan,this));sensor_->SetActive(true);
    RCLCPP_INFO(node_->get_logger(),"Helios32: 32 explicit beams, %u azimuths, %.1fHz simulated, filter=%s",horizontal_,sensor_->UpdateRate(),mode_.c_str());
  }
 private:
  void scan(){
    std::vector<double> ranges;sensor_->Ranges(ranges);if(ranges.size()!=starts_.size())return;
    sensor_msgs::msg::PointCloud2 raw;raw.header.stamp=node_->now();raw.header.frame_id=frame_;raw.height=32;raw.width=horizontal_;raw.is_dense=false;
    const char* names[]={"x","y","z","intensity","ring","azimuth_index","time","range"};
    const unsigned offsets[]={0,4,8,12,16,18,20,24};
    for(int k=0;k<8;++k){sensor_msgs::msg::PointField f;f.name=names[k];f.offset=offsets[k];f.count=1;f.datatype=(k==4||k==5)?sensor_msgs::msg::PointField::UINT16:sensor_msgs::msg::PointField::FLOAT32;raw.fields.push_back(f);}
    raw.point_step=28;raw.row_step=raw.width*raw.point_step;raw.data.resize(raw.row_step*raw.height);auto filtered=raw;
    size_t self_hits=0,cropped=0,blind_hits=0,hits=0,forwarded=0;const float nan=std::numeric_limits<float>::quiet_NaN();
    for(size_t k=0;k<ranges.size();++k){
      const auto ring=uint16_t(k/horizontal_),az=uint16_t(k%horizontal_);const double range=ranges[k];
      const bool self=mode_=="collision_identity" && shape_->Ray(k)->CollisionName().find("robot::")!=std::string::npos;
      const bool hit=std::isfinite(range)&&range<sensor_->RangeMax()-1e-5;
      if(hit){++hits;if(self)++self_hits;if(range<min_)++blind_hits;}
      const bool valid=hit&&range>=min_&&range<=maxima_[ring];
      const auto point=starts_[k]+directions_[k]*range;
      const bool inside=mode_=="crop_box" && valid &&
        point.X()>=crop_min_[0] && point.X()<=crop_max_[0] &&
        point.Y()>=crop_min_[1] && point.Y()<=crop_max_[1] &&
        point.Z()>=crop_min_[2] && point.Z()<=crop_max_[2];
      if(inside)++cropped;
      float values[4]={valid?float(point.X()):nan,valid?float(point.Y()):nan,valid?float(point.Z()):nan,valid?1.f:0.f};
      const size_t offset=k*28;std::memcpy(raw.data.data()+offset,values,16);std::memcpy(raw.data.data()+offset+16,&ring,2);std::memcpy(raw.data.data()+offset+18,&az,2);
      // Frame is instantaneous: no fabricated per-point motion compensation.
      const float time=0,measured=valid?float(range):nan;std::memcpy(raw.data.data()+offset+20,&time,4);std::memcpy(raw.data.data()+offset+24,&measured,4);
      std::memcpy(filtered.data.data()+offset,raw.data.data()+offset,28);
      if(self || inside){for(int j=0;j<3;++j)std::memcpy(filtered.data.data()+offset+j*4,&nan,4);}else if(valid)++forwarded;
    }
    raw_->publish(raw);filtered_->publish(filtered);
    std::ostringstream s;s<<std::setprecision(17)<<"{\"time\":"<<node_->now().seconds()<<",\"rays\":"<<ranges.size()<<",\"hits\":"<<hits<<",\"self_hits\":"<<self_hits<<",\"cropped_points\":"<<cropped<<",\"self_filter_mode\":\""<<mode_<<"\",\"blind_hits\":"<<blind_hits<<",\"forwarded\":"<<forwarded<<",\"recast_self_hits\":false}";
    std_msgs::msg::String message;message.data=s.str();status_->publish(message);
  }
  sensors::RaySensorPtr sensor_;physics::MultiRayShapePtr shape_;gazebo_ros::Node::SharedPtr node_;event::ConnectionPtr connection_;
  rclcpp::Publisher<sensor_msgs::msg::PointCloud2>::SharedPtr raw_,filtered_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr status_;
  std::vector<double> angles_,maxima_;std::vector<ignition::math::Vector3d> starts_,directions_;
  unsigned horizontal_=0;double window_=0,min_=0;std::string frame_;
  std::string mode_;double crop_min_[3]{},crop_max_[3]{};
};
GZ_REGISTER_SENSOR_PLUGIN(Helios32Ray)
}
