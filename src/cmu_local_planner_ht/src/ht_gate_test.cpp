#include "ht_gate.hpp"
#include <iostream>
void require(bool condition,const char* name){if(!condition)throw std::runtime_error(name);std::cout<<"PASS "<<name<<std::endl;}
grid_map_msgs::msg::GridMap map(rclcpp::Node::SharedPtr n) {
 grid_map_msgs::msg::GridMap m;m.header.frame_id="map";m.header.stamp=n->now();
 m.info.resolution=.04;m.info.length_x=m.info.length_y=81*.04;m.info.pose.orientation.w=1;
 for(int k=0;k<11;++k){m.layers.push_back(k<8?"ht_dir_"+std::to_string(k):k==8?"ht_valid":k==9?"ht_observation_valid":"ht_obstacle");
 std_msgs::msg::Float32MultiArray a;a.layout.dim.resize(2);a.layout.dim[0].label="column_index";a.layout.dim[1].label="row_index";
 a.layout.dim[0].size=a.layout.dim[1].size=81;a.layout.dim[0].stride=81*81;a.layout.dim[1].stride=81;
 a.data.assign(81*81,k<8?.9:k<10?1:0);m.data.push_back(a);}
 return m;
}
int main(int argc,char** argv){rclcpp::init(argc,argv);
 auto node=std::make_shared<rclcpp::Node>("ht_gate_test",rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("ht_enabled",true)}));
 cmu_ht::Gate g(node);auto m=map(node);g.receive(m);
 require(g.command({0,0,0},.2,0),"all-high forward accepted");
 require(g.command({0,0,0},-.2,0),"all-high reverse accepted");
 std::fill(m.data[0].data.begin(),m.data[0].data.end(),.1);g.receive(m);
 require(!g.pose({0,0,0})&&g.pose({0,0,cmu_ht::pi/2}),"same XY different body yaw selects different channel");
 require(!g.command({0,0,0},-.2,0),"reverse keeps actual low body yaw");
 m=map(node);std::fill(m.data[4].data.begin(),m.data[4].data.end(),.1);g.receive(m);
 require(g.command({0,0,0},-.2,0),"reverse does not demand opposite travel channel");
 m=map(node);std::fill(m.data[1].data.begin(),m.data[1].data.end(),.1);g.receive(m);
 require(g.command({0,0,-1.143677235},0,cmu_ht::pi/2),"recorded turn avoids false constant-1s overshoot rejection");
 require(!g.command({0,0,.3},0,cmu_ht::pi/2),"braking turn still rejects genuinely crossed low direction");
 m=map(node);std::fill(m.data[3].data.begin(),m.data[3].data.end(),.1);g.receive(m);
 double linear=-.05,angular=-.471232653;
 require(!g.command({0,0,2.783087969},linear,angular),"recorded reverse startup native command rejected");
 require(g.chooseCommand({0,0,2.783087969},linear,angular)&&linear==-.05&&std::abs(angular)<.471232653,
   "reverse startup projects steering through the same hard gate");
 m=map(node);std::fill(m.data[1].data.begin(),m.data[1].data.end(),.1);g.receive(m);
 require(g.pose({0,0,0})&&g.pose({0,0,cmu_ht::pi/2})&&!g.segment({0,0,0},{0,0,cmu_ht::pi/2}),"turn checks intermediate direction");
 m=map(node);m.data[9].data[40+40*81]=0;g.receive(m);
 require(!g.pose({0,0,0})&&g.last_reason=="HT_MISSING_SUPPORT","unknown footprint rejected");
 linear=.1;angular=.3;
 require(!g.chooseCommand({0,0,0},linear,angular)&&linear==0&&angular==0,"command projection cannot bypass unknown support");
 m=map(node);m.data[10].data[40+40*81]=1;g.receive(m);
 require(!g.pose({.2,0,0})&&g.last_reason=="HT_OCCUPIED","measured obstacle footprint rejected");
 m=map(node);m.header.stamp=rclcpp::Time(node->now().nanoseconds()-2000000000LL);g.receive(m);
 require(!g.pose({0,0,0})&&g.last_reason=="HT_MAP_STALE","stale map rejected");
 m=map(node);m.data[0].data.clear();g.receive(m);
 require(!g.pose({0,0,0}),"malformed map rejected");
 auto cmu=std::make_shared<rclcpp::Node>("ht_gate_cmu_test",rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("ht_validity_radius",.45)}));
 cmu_ht::Gate cmuGate(cmu);m=map(cmu);m.data[10].data[26+40*81]=1;cmuGate.receive(m);
 require(cmuGate.pose({0,0,0}),"CMU geometry accepts obstacle outside native .45m envelope plus grid margin");
 m.data[10].data[30+40*81]=1;cmuGate.receive(m);
 require(!cmuGate.pose({0,0,0}),"CMU geometry still blocks obstacle inside native body envelope");
 rclcpp::shutdown();return 0;}
