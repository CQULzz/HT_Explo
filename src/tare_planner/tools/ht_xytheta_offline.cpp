// Offline snapshot queries only: no navigation, permission or velocity output.
// Example: ht_xytheta_offline --map ht.cdr --start 0 0 0 --goal -1 0 --output result.json
#include "ht_cost/ht_cost_map.h"
#include <rcl/time.h>
#include <rclcpp/serialization.hpp>
#include <rclcpp/serialized_message.hpp>
#include <algorithm>
#include <chrono>
#include <cstdint>
#include <cstring>
#include <cstdlib>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <iterator>
#include <sstream>
#include <stdexcept>
#include <thread>
#include <unistd.h>

namespace {
using ht_cost_ns::Pose2;
using ht_cost_ns::Support;
using Bytes=std::vector<uint8_t>;

std::string quoted(const std::string& value) {
  std::ostringstream out;out<<'"';
  for(unsigned char c:value) {
    if(c=='"' || c=='\\')out<<'\\'<<c;
    else if(c<32)out<<"\\u"<<std::hex<<std::setw(4)<<std::setfill('0')<<int(c)<<std::dec;
    else out<<c;
  }
  out<<'"';return out.str();
}
void number(std::ostream& out,double value) {
  if(std::isfinite(value))out<<std::setprecision(17)<<value;else out<<"null";
}
Bytes readFile(const std::string& path) {
  std::ifstream input(path,std::ios::binary|std::ios::ate);
  if(!input)throw std::runtime_error("Cannot open file: "+path);
  const auto size=input.tellg();
  if(size<0 || size>512*1024*1024)throw std::runtime_error("Invalid or excessive file length: "+path);
  input.seekg(0);Bytes bytes(static_cast<size_t>(size));
  if(!bytes.empty() && !input.read(reinterpret_cast<char*>(bytes.data()),size))
    throw std::runtime_error("Cannot read file: "+path);
  return bytes;
}
// Self-contained SHA-256 keeps the offline tool independent of a new crypto
// package. Hash both the exact CDR input and the canonical parameter JSON.
uint32_t rotate(uint32_t n,unsigned s) {return (n>>s)|(n<<(32-s));}
std::string sha256(Bytes input) {
  static constexpr uint32_t k[64]={
    0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,
    0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,
    0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,
    0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,
    0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,
    0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,
    0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,
    0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
  uint32_t hash[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};
  const uint64_t bits=uint64_t(input.size())*8;input.push_back(0x80);
  while(input.size()%64!=56)input.push_back(0);
  for(int s=56;s>=0;s-=8)input.push_back(static_cast<uint8_t>(bits>>s));
  for(size_t pos=0;pos<input.size();pos+=64) {
    uint32_t w[64];
    for(int i=0;i<16;++i)w[i]=(uint32_t(input[pos+4*i])<<24)|(uint32_t(input[pos+4*i+1])<<16)|
      (uint32_t(input[pos+4*i+2])<<8)|input[pos+4*i+3];
    for(int i=16;i<64;++i)w[i]=w[i-16]+(rotate(w[i-15],7)^rotate(w[i-15],18)^(w[i-15]>>3))+
      w[i-7]+(rotate(w[i-2],17)^rotate(w[i-2],19)^(w[i-2]>>10));
    uint32_t a=hash[0],b=hash[1],c=hash[2],d=hash[3],e=hash[4],f=hash[5],g=hash[6],h=hash[7];
    for(int i=0;i<64;++i) {
      const uint32_t t1=h+(rotate(e,6)^rotate(e,11)^rotate(e,25))+((e&f)^(~e&g))+k[i]+w[i];
      const uint32_t t2=(rotate(a,2)^rotate(a,13)^rotate(a,22))+((a&b)^(a&c)^(b&c));
      h=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;
    }
    hash[0]+=a;hash[1]+=b;hash[2]+=c;hash[3]+=d;hash[4]+=e;hash[5]+=f;hash[6]+=g;hash[7]+=h;
  }
  std::ostringstream out;out<<std::hex<<std::setfill('0');
  for(uint32_t part:hash)out<<std::setw(8)<<part;
  return out.str();
}
std::string sha256(const std::string& value) {return sha256(Bytes(value.begin(),value.end()));}
const char* supportName(Support s) {
  switch(s) {
    case Support::KNOWN:return "KNOWN";case Support::STARTUP_PRIOR:return "STARTUP_PRIOR";
    case Support::UNKNOWN:return "UNKNOWN";case Support::BLOCKED:return "BLOCKED";
    default:return "FAULT";
  }
}
double numeric(const std::string& value) {
  size_t used=0;const double n=std::stod(value,&used);
  if(used!=value.size() || !std::isfinite(n))throw std::runtime_error("Invalid finite number: "+value);
  return n;
}
struct Query {std::string map,label;Pose2 start;ht_cost_ns::Point goal;};
struct Options {std::vector<Query> queries;std::string output,semantics="configuration";double search=.15;};
Options parse(int argc,char** argv) {
  Options result;Query single;bool have_start=false,have_goal=false;std::string batch;
  auto next=[&](int& i){if(++i>=argc)throw std::runtime_error("Missing option value");return std::string(argv[i]);};
  for(int i=1;i<argc;++i) {
    const std::string key=argv[i];
    if(key=="--map")single.map=next(i);
    else if(key=="--output")result.output=next(i);
    else if(key=="--label")single.label=next(i);
    else if(key=="--semantics")result.semantics=next(i);
    else if(key=="--search-seconds")result.search=numeric(next(i));
    else if(key=="--batch")batch=next(i);
    else if(key=="--start") {single.start.x=numeric(next(i));single.start.y=numeric(next(i));single.start.yaw=numeric(next(i));have_start=true;}
    else if(key=="--goal") {single.goal.x=numeric(next(i));single.goal.y=numeric(next(i));have_goal=true;}
    else throw std::runtime_error("Unknown option: "+key);
  }
  if(result.output.empty())throw std::runtime_error("Require --output FILE");
  if(result.semantics!="configuration" && result.semantics!="point")throw std::runtime_error("Invalid --semantics");
  if(result.search<=0 || result.search>60)throw std::runtime_error("Search budget must be in (0,60] seconds");
  if(!batch.empty()) {
    if(!single.map.empty() || have_start || have_goal)throw std::runtime_error("--batch cannot be mixed with --map/--start/--goal");
    std::ifstream input(batch);if(!input)throw std::runtime_error("Cannot open batch TSV");
    std::string line;int row=0;
    while(std::getline(input,line)) {
      ++row;if(!line.empty() && line.back()=='\r')line.pop_back();
      if(line.empty() || line.front()=='#')continue;
      std::vector<std::string> fields;std::istringstream stream(line);std::string field;
      while(std::getline(stream,field,'\t'))fields.push_back(field);
      if(fields.size()!=7)throw std::runtime_error("Batch row "+std::to_string(row)+" must have 7 TAB-separated fields: map sx sy yaw gx gy label");
      Query q;q.map=fields[0];q.start={numeric(fields[1]),numeric(fields[2]),numeric(fields[3])};
      q.goal={numeric(fields[4]),numeric(fields[5]),0};q.label=fields[6];result.queries.push_back(q);
    }
  } else {
    if(single.map.empty() || !have_start || !have_goal)throw std::runtime_error("Require --map FILE --start x y yaw --goal x y");
    result.queries.push_back(single);
  }
  if(result.queries.empty())throw std::runtime_error("No queries");
  return result;
}
ht_cost_ns::XYThetaConfig plannerConfig(double search) {
  ht_cost_ns::XYThetaConfig c;c.cell=.3;c.headings=32;c.turn_angles={ht_cost_ns::kPi/16,ht_cost_ns::kPi/8};
  // Match LocalCoveragePlanner's current XYThetaConfig defaults exactly.
  // Its nominal planning speed is .5 m/s; the real follower separately caps
  // execution at .4 m/s. This tool estimates planner cost, not actual timing.
  c.drive_step=.4;c.forward_speed=.5;c.reverse_speed=.25;c.max_yaw_rate=.8;
  c.goal_radius=.35;c.max_radius=7;c.max_search_seconds=search;c.max_expansions=8000;
  c.try_direct_connection=true;return c;
}
std::string parameters(const Options& opt) {
  std::ostringstream out;out<<std::setprecision(17);
  out<<"{\"ht_enabled\":true,\"ht_directions_calibrated\":true,\"ht_exploration_mode\":\"tare_waypoint\","
       "\"ht_score_semantics\":"<<quoted(opt.semantics)<<",\"ht_unknown_policy\":\"strict\","
       "\"ht_min_probability\":0.5,\"ht_validity_radius\":0.6,\"ht_map_timeout\":1,"
       "\"ht_startup_radius\":0,\"ht_startup_duration\":30,\"ht_require_reversible_motion\":false,"
       "\"ht_heading_offset\":0,\"ht_channel_order\":[0,1,2,3,4,5,6,7],\"ht_sample_step\":0.02,"
       "\"ht_lookahead_distance\":2,\"ht_waypoint_reached_distance\":0.3,"
       "\"xytheta_cell\":0.3,\"xytheta_headings\":32,\"xytheta_turn_angles_deg\":[11.25,22.5],"
       "\"xytheta_drive_step\":0.4,\"forward_speed\":0.5,\"reverse_speed\":0.25,\"max_yaw_rate\":0.8,"
       "\"xytheta_goal_radius\":0.35,\"xytheta_max_radius\":7,\"xytheta_max_expansions\":8000,"
       "\"xytheta_search_seconds\":"<<opt.search<<",\"try_direct_connection\":true,"
       "\"startup_prior_initialized\":false,\"publish_permission\":false}";return out.str();
}
std::string query(const Query& q,const Options& opt,size_t index) {
  const Bytes bytes=readFile(q.map);if(bytes.empty())throw std::runtime_error("Empty CDR map");
  rclcpp::SerializedMessage serialized(bytes.size());auto& wire=serialized.get_rcl_serialized_message();
  std::memcpy(wire.buffer,bytes.data(),bytes.size());wire.buffer_length=bytes.size();
  grid_map_msgs::msg::GridMap map;rclcpp::Serialization<grid_map_msgs::msg::GridMap> codec;
  codec.deserialize_message(&serialized,&map);
  if(map.header.frame_id!="map")throw std::runtime_error("Offline runner requires frame_id=map; no external TF is assumed");
  if(map.header.stamp.sec<0 || map.header.stamp.nanosec>=1000000000u)
    throw std::runtime_error("Invalid original map stamp");
  const int64_t stamp=int64_t(map.header.stamp.sec)*1000000000LL+map.header.stamp.nanosec;
  if(stamp<=0)throw std::runtime_error("Require positive original map stamp");
  const std::string topic="/ht_offline_"+std::to_string(getpid())+"_"+std::to_string(index)+"/grid";
  rclcpp::NodeOptions settings;settings.use_global_arguments(false);
  settings.arguments({"--ros-args","-r","/ht_startup_prior:="+topic+"_unused_startup_prior"});
  settings.parameter_overrides({
    rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("ht_directions_calibrated",true),
    rclcpp::Parameter("ht_exploration_mode","tare_waypoint"),rclcpp::Parameter("ht_topic",topic),
    rclcpp::Parameter("ht_score_semantics",opt.semantics),rclcpp::Parameter("ht_unknown_policy","strict"),
    rclcpp::Parameter("ht_min_probability",.5),rclcpp::Parameter("ht_validity_radius",.6),
    rclcpp::Parameter("ht_map_timeout",1.),rclcpp::Parameter("ht_startup_radius",0.),
    rclcpp::Parameter("ht_require_reversible_motion",false)});
  auto node=std::make_shared<rclcpp::Node>("ht_offline_"+std::to_string(index),settings);
  auto* clock=node->get_clock()->get_clock_handle();
  if(rcl_enable_ros_time_override(clock)!=RCL_RET_OK || rcl_set_ros_time_override(clock,stamp)!=RCL_RET_OK)
    throw std::runtime_error("Cannot freeze ROS time at the original source stamp");
  // false suppresses all navigation permission publication and no start() is
  // called. The only publisher created by this tool carries this input map.
  ht_cost_ns::HtCostMap ht(node,false);
  auto pub=node->create_publisher<grid_map_msgs::msg::GridMap>(topic,rclcpp::QoS(1).reliable());
  const auto load_started=std::chrono::steady_clock::now();
  while(true) {
    pub->publish(map);rclcpp::spin_some(node);ht.beginCycle();
    if(ht.ready())break;
    if(std::chrono::steady_clock::now()-load_started>std::chrono::seconds(3))
      throw std::runtime_error("Snapshot not accepted: "+ht.status());
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  if(ht.startupPrior().initialized)throw std::runtime_error("Unexpected external startup prior in isolated offline query");
  const auto start_support=ht.poseSupport(q.start.x,q.start.y,q.start.yaw);
  auto valid=[&](Pose2 a,Pose2 b,double) {return ht.permits(ht.motionSupport(a,b));};
  const auto begun=std::chrono::steady_clock::now();
  const auto plan=ht_cost_ns::planXYTheta(q.start,q.goal,plannerConfig(opt.search),valid);
  const double elapsed=std::chrono::duration<double>(std::chrono::steady_clock::now()-begun).count();
  // Re-evaluate every returned segment after search, independently of the
  // validity calls made during expansion. This uses the same frozen snapshot.
  std::vector<Support> checked;bool all_permitted=!plan.poses.empty();double length=0,rotation=0;
  for(size_t i=1;i<plan.poses.size();++i) {
    const auto support=ht.motionSupport(plan.poses[i-1],plan.poses[i]);checked.push_back(support);
    all_permitted=all_permitted&&ht.permits(support);
    length+=std::hypot(plan.poses[i].x-plan.poses[i-1].x,plan.poses[i].y-plan.poses[i-1].y);
    rotation+=std::abs(ht_cost_ns::wrapYaw(plan.poses[i].yaw-plan.poses[i-1].yaw));
  }
  if(!plan.poses.empty())all_permitted=all_permitted&&ht.permits(ht.poseSupport(plan.poses.front().x,plan.poses.front().y,plan.poses.front().yaw));
  const bool source_unchanged=stamp==int64_t(map.header.stamp.sec)*1000000000LL+map.header.stamp.nanosec;
  const bool verified=plan.reached&&all_permitted&&source_unchanged&&
    !plan.poses.empty()&&std::hypot(plan.poses.back().x-q.goal.x,plan.poses.back().y-q.goal.y)<=.35+1e-9;
  std::ostringstream out;out<<std::setprecision(17);
  out<<"{\"label\":"<<quoted(q.label)<<",\"map_file\":"<<quoted(q.map)<<",\"map_sha256\":"<<quoted(sha256(bytes));
  out<<",\"source_stamp\":{\"sec\":"<<map.header.stamp.sec<<",\"nanosec\":"<<map.header.stamp.nanosec<<"},\"map_stamp_ns\":"<<stamp<<",\"clock_ns\":"<<node->now().nanoseconds();
  out<<",\"map_frame\":"<<quoted(map.header.frame_id)<<",\"map_status\":"<<quoted(ht.status())<<",\"map_resolution\":";
  number(out,map.info.resolution);out<<",\"start\":["<<q.start.x<<','<<q.start.y<<','<<q.start.yaw<<"],\"goal\":["<<q.goal.x<<','<<q.goal.y<<']';
  out<<",\"start_support\":"<<quoted(supportName(start_support))<<",\"reached\":"<<(plan.reached?"true":"false");
  out<<",\"termination\":"<<quoted(ht_cost_ns::terminationName(plan.termination))<<",\"expanded\":"<<plan.expanded;
  out<<",\"dominated_edges_pruned\":"<<plan.dominated_edges_pruned<<",\"direct_connection\":"<<(plan.direct_connection?"true":"false");
  out<<",\"seconds\":";number(out,plan.seconds);out<<",\"search_wall_ms\":"<<elapsed*1000<<",\"path_length_m\":"<<length<<",\"rotation_rad\":"<<rotation;
  out<<",\"source_stamp_unchanged\":"<<(source_unchanged?"true":"false")<<",\"independent_recheck_passed\":"<<(verified?"true":"false")
     <<",\"all_segments_permitted\":"<<(all_permitted?"true":"false")<<",\"poses\":[";
  for(size_t i=0;i<plan.poses.size();++i){if(i)out<<',';const auto& p=plan.poses[i];out<<'['<<p.x<<','<<p.y<<','<<p.yaw<<']';}
  out<<"],\"segment_support\":[";for(size_t i=0;i<checked.size();++i){if(i)out<<',';out<<quoted(supportName(checked[i]));}
  out<<"]}";return out.str();
}
} // namespace

int main(int argc,char** argv) {
  try {
    const auto opt=parse(argc,argv);
    if(!std::getenv("ROS_DOMAIN_ID"))setenv("ROS_DOMAIN_ID","182",0);
    if(!std::getenv("ROS_LOCALHOST_ONLY"))setenv("ROS_LOCALHOST_ONLY","1",0);
    rclcpp::init(0,nullptr);
    const auto canonical=parameters(opt);std::ostringstream out;bool failed=false;
    out<<"{\"schema\":\"ht_xytheta_offline_v1\",\"scope\":\"Frozen HT snapshot + actual C++ HtCostMap/Hybrid A*. Excludes TARE goal selection, independent collision_cloud, live freshness, tracking and physical execution.\","
       "\"clock_policy\":\"ROS time frozen at each unmodified input map stamp; no stamp refresh\","
       "\"ros_domain_id\":"<<quoted(std::getenv("ROS_DOMAIN_ID"))<<",\"ros_localhost_only\":"<<quoted(std::getenv("ROS_LOCALHOST_ONLY"))
       <<",\"parameters\":"<<canonical<<",\"parameters_sha256\":"<<quoted(sha256(canonical));
    out<<",\"executable_sha256\":"<<quoted(sha256(readFile("/proc/self/exe")))<<",\"queries\":[";
    for(size_t i=0;i<opt.queries.size();++i) {
      if(i)out<<',';
      try {out<<query(opt.queries[i],opt,i);}
      catch(const std::exception& e){failed=true;out<<"{\"label\":"<<quoted(opt.queries[i].label)<<",\"map_file\":"<<quoted(opt.queries[i].map)<<",\"error\":"<<quoted(e.what())<<'}';}
    }
    out<<"]}\n";std::ofstream output(opt.output,std::ios::binary);
    if(!output || !(output<<out.str()))throw std::runtime_error("Cannot write output: "+opt.output);
    rclcpp::shutdown();return failed?2:0;
  } catch(const std::exception& e) {
    std::cerr<<"ht_xytheta_offline: "<<e.what()<<'\n';if(rclcpp::ok())rclcpp::shutdown();return 2;
  }
}
