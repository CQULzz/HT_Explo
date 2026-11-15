#include "ht_gate.hpp"
#include <iostream>
void check(bool v,const char* s){if(!v)throw std::runtime_error(s);std::cout<<"PASS "<<s<<std::endl;}
grid_map_msgs::msg::GridMap fixture(rclcpp::Node::SharedPtr n,double x,double y){
 grid_map_msgs::msg::GridMap m;m.header.frame_id="map";m.header.stamp=n->now();m.info.resolution=.02;m.info.length_x=m.info.length_y=201*.02;m.info.pose.orientation.w=1;
 for(int k=0;k<11;++k){m.layers.push_back(k<8?"ht_dir_"+std::to_string(k):k==8?"ht_valid":k==9?"ht_observation_valid":"ht_obstacle");
 std_msgs::msg::Float32MultiArray a;a.layout.dim.resize(2);a.layout.dim[0].label="column_index";a.layout.dim[1].label="row_index";
 a.layout.dim[0].size=a.layout.dim[1].size=201;a.layout.dim[0].stride=201*201;a.layout.dim[1].stride=201;a.data.assign(201*201,k<8?.9:k<10?1:0);m.data.push_back(a);}
 int r=std::floor(201*.5-x/.02),c=std::floor(201*.5-y/.02);m.data[10].data[r+c*201]=1;return m;
}
int main(int argc,char**argv){rclcpp::init(argc,argv);
 auto make=[](const char* name,bool box,std::vector<double> lo,std::vector<double> hi,double radius){return std::make_shared<rclcpp::Node>(name,rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("traversability_mode","ht_only"),rclcpp::Parameter("ht_validity_radius",radius),rclcpp::Parameter("ht_use_urdf_envelope",box),rclcpp::Parameter("ht_body_min_xyz",lo),rclcpp::Parameter("ht_body_max_xyz",hi)}));};
 auto old=make("old_box",false,{-.3,-.3,-.3},{.3,.3,.3},.6);cmu_ht::Gate a(old);a.setBodyEnvelope(.6,.6);
 auto n=make("urdf_box",true,{-.465,-.35,-.235},{.465,.35,.651},.6);cmu_ht::Gate b(n);b.setBodyEnvelope(.6,.6);
 auto m=fixture(n,.44,0);a.receive(m);b.receive(m);check(a.pose({0,0,0})&&!b.pose({0,0,0}),"URDF nose rejects obstacle missed by old square");
 m=fixture(n,.4,.4);b.receive(m);check(b.pose({0,0,0})&&b.pose({0,0,cmu_ht::pi/2})&&!b.segment({0,0,0},{0,0,cmu_ht::pi/2}),"rotation sweep catches corner despite clear endpoints");
 check(!b.command({0,0,0},0,1),"braking command checks rotating URDF corner");
 m=fixture(n,.55,0);b.receive(m);check(b.pose({0,0,0})&&!b.segment({0,0,0},{.5,0,0}),"translation sweep rejects obstacle crossed before endpoint");
 auto o=make("offset_box",true,{0,-.1,-.2},{.8,.1,.5},.81);cmu_ht::Gate c(o);c.setBodyEnvelope(.6,.6);m=fixture(o,.7,0);c.receive(m);check(!c.pose({0,0,0}),"asymmetric URDF center retained");m=fixture(o,-.4,0);c.receive(m);check(c.pose({0,0,0}),"offset does not invent a rear overhang");
 m=fixture(n,1.5,1.5);int center=100+100*201;m.data[9].data[center]=0;b.receive(m);check(!b.pose({0,0,0})&&b.last_reason=="HT_MISSING_SUPPORT","URDF mode preserves missing-ground rejection");
 m=fixture(n,1.5,1.5);m.data[0].data[center]=.1;b.receive(m);check(!b.pose({0,0,0})&&b.last_reason=="HT_DIRECTION_LOW","URDF mode preserves probability threshold");
 auto pn=std::make_shared<rclcpp::Node>("initial_prior",rclcpp::NodeOptions().parameter_overrides({rclcpp::Parameter("ht_enabled",true),rclcpp::Parameter("traversability_mode","ht_only"),rclcpp::Parameter("ht_validity_radius",.6),rclcpp::Parameter("ht_initial_support_prior_enabled",true),rclcpp::Parameter("ht_initial_support_prior_radius",.65)}));
 cmu_ht::Gate prior(pn);prior.setBodyEnvelope(.6,.6);
 m=fixture(pn,1.5,1.5);m.data[9].data[center]=0;prior.receive(m);
 check(!prior.pose({0,0,0}),"prior waits for actual initial odometry, not candidate pose");
 prior.anchorInitialSupportPrior({0,0,0});prior.receive(m);
 check(prior.pose({0,0,0}),"initial prior supplies absent support inside fixed patch");
 prior.anchorInitialSupportPrior({.7,0,0});
 m=fixture(pn,1.5,1.5);int outside_r=std::floor(201*.5-.7/.02);m.data[9].data[outside_r+100*201]=0;prior.receive(m);
 check(!prior.pose({.1,0,0})&&prior.last_reason=="HT_MISSING_SUPPORT","prior stays fixed and outside unknown still rejects");
 m=fixture(pn,.1,0);m.data[9].data[center]=0;prior.receive(m);
 check(!prior.pose({0,0,0})&&prior.last_reason=="HT_OCCUPIED","initial prior cannot override measured obstacle");
 m=fixture(pn,1.5,1.5);m.data[9].data[center]=0;m.data[0].data[center]=.1;prior.receive(m);
 check(!prior.pose({0,0,0})&&prior.last_reason=="HT_DIRECTION_LOW","initial prior cannot override low neural score");
 m=fixture(pn,1.5,1.5);m.data[9].data[center]=0;m.data[8].data[center]=0;prior.receive(m);
 check(!prior.pose({0,0,0})&&prior.last_reason=="HT_CONTEXT_INVALID","initial prior cannot override invalid neural context");
 m=fixture(pn,1.5,1.5);m.data[9].data[center]=0;m.header.stamp=pn->now()-rclcpp::Duration::from_seconds(2);prior.receive(m);
 check(!prior.pose({0,0,0})&&prior.last_reason=="HT_MAP_STALE","initial prior cannot override stale map");
 rclcpp::shutdown();return 0;}
