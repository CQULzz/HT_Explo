#pragma once
#include "ht_gate.hpp"
#include <geometry_msgs/msg/point_stamped.hpp>
#include <nav_msgs/msg/path.hpp>
#include <std_msgs/msg/bool.hpp>
#include <queue>
#include <limits>

namespace cmu_ht {
// Pose search and its explicit turn/forward/reverse executor use one Gate and
// one unicycle model. Recovery never edits TARE goals or HT evidence.
class Recovery {
 public:
  Recovery(rclcpp::Node::SharedPtr node,Gate& gate):node_(node),gate_(gate) {
    enabled=node_->declare_parameter("ht_recovery_enabled",false);
    speed_=node_->declare_parameter("ht_recovery_speed",.15);
    angular_=node_->declare_parameter("ht_recovery_angular_speed",.5);
    accel_=node_->declare_parameter("ht_recovery_linear_accel",2.5);
    angular_accel_=node_->declare_parameter("ht_recovery_angular_accel",3.);
    progress_=node_->declare_parameter("ht_recovery_progress",.75);
    search_ms_=node_->declare_parameter("ht_recovery_search_ms",20.);
    odom_timeout_=node_->declare_parameter("ht_odometry_timeout",.2);
    if(speed_<=0 || angular_<=0 || accel_<=0 || angular_accel_<=0 || progress_<=0 || search_ms_<=0 || odom_timeout_<=0)
      throw std::invalid_argument("Invalid HT recovery parameters");
    if(enabled && (!gate_.enabled || gate_.mode!="ht_only"))throw std::invalid_argument("Recovery requires the HT-only gate");
    if(enabled) {
      goal_sub_=node_->create_subscription<geometry_msgs::msg::PointStamped>("/way_point",5,[this](geometry_msgs::msg::PointStamped::ConstSharedPtr m){
        if(m->header.frame_id!="map" && !m->header.frame_id.empty())return;
        setGoal({m->point.x,m->point.y,0},node_->now().seconds());
      });
      finish_sub_=node_->create_subscription<std_msgs::msg::Bool>("/exploration_finish",5,[this](std_msgs::msg::Bool::ConstSharedPtr m){finished_=m->data;});
      diagnostics_=node_->create_publisher<std_msgs::msg::String>("/ht_minimal/recovery",20);
      path_pub_=node_->create_publisher<nav_msgs::msg::Path>("/ht_minimal/recovery_path",5);
    }
  }
  bool enabled=false;
  bool active() const {return active_;}
  uint64_t plans=0,completed=0,invalidated=0,search_failures=0,goal_cancellations=0,compatible_goal_updates=0;
  std::string state="IDLE";
  double last_search_ms=0;
  const std::vector<Pose>& route() const {return route_;}
  void setGoal(Pose goal,double now) {if(std::isfinite(goal.x)&&std::isfinite(goal.y)){goal_=goal;goal_at_=now;have_goal_=true;}}

  // Returns true when recovery (including its stop states) owns this output.
  bool select(Pose pose,double now,double odom_stamp,bool permitted,double speed_limit,
              bool native_allowed,double native_v,double native_w,double& v,double& w) {
    if(!enabled)return false;
    if(permitted && (now-odom_stamp<-.01 || now-odom_stamp>odom_timeout_)) {
      reset("ODOMETRY_STALE");v=w=0;report(now,pose,v,w);return true;
    }
    // A TARE waypoint is a retained target, not a fixed-frequency heartbeat.
    if(!permitted || finished_ || !have_goal_ || (!active_ && distance(pose,goal_)<.25)) {
      const bool was_active=active_;
      reset(finished_?"EXPLORATION_FINISHED":!permitted?"PAUSED":"IDLE");last_tick_=now;
      if(was_active){v=w=0;report(now,pose,v,w);return true;}
      return false;
    }
    if(active_ && distance(goal_,planned_goal_)>.05) {
      // TARE's extended waypoint often shifts along the same route. Retain an
      // executing prefix if its endpoint still advances toward the new target.
      if(distance(pose,goal_)<.25 || distance(route_.back(),goal_)>distance(pose,goal_)+.01) {
        ++goal_cancellations;reset("GOAL_CHANGED");v=w=0;report(now,pose,v,w);return true;
      }
      planned_goal_=goal_;++compatible_goal_updates;
    }
    if(!std::isfinite(speed_limit)||speed_limit<=0) {
      reset("SPEED_LIMIT");v=w=0;report(now,pose,v,w);return true;
    }
    execution_speed_=std::min(speed_,speed_limit);
    if(active_)return execute(pose,now,v,w);
    const bool moving=native_allowed&&(std::abs(native_v)+std::abs(native_w)>1e-8);
    if(!moving){if(blocked_at_<0)blocked_at_=now;}else blocked_at_=-1;
    // Take over only after the native output has remained zero/rejected for
    // 0.4s. The validated recovery starts at rest, never in mid-turn.
    const bool stalled=blocked_at_>=0 && now-blocked_at_>=.4;
    if(!stalled || now<next_plan_){last_tick_=now;return false;}
    next_plan_=now+.25;
    if(!gate_.pose(pose)){state="START_INVALID:"+gate_.last_reason;report(now,pose,0,0);return false;}
    execution_speed_=std::min(speed_,std::max(0.,speed_limit));
    if(execution_speed_<.01)return false;
    if(!plan(pose,goal_)){++search_failures;state="SEARCH_FAILED";report(now,pose,0,0);return false;}
    origin_=pose;planned_goal_=goal_;index_=1;progress_index_=0;progress_at_=now;best_error_=std::numeric_limits<double>::infinity();active_=true;previous_v_=previous_w_=0;last_tick_=now;
    state="EXECUTING";publishPath();report(now,pose,0,0);return execute(pose,now,v,w);
  }

  bool plan(Pose start,Pose goal) {
    const auto began=std::chrono::steady_clock::now();
    if(!gate_.pose(start))return false;
    const double step=gate_.resolution();
    if(step<.01 || step>.2)return false;
    const int half=int(std::ceil(3./step)),side=2*half+1,total=side*side*8;
    const double requested=std::min(progress_,distance(start,goal)-.2);
    if(requested<.1)return false;
    auto id=[&](int x,int y,int k){return ((x+half)*side+y+half)*8+k;};
    auto decode=[&](int i){const int k=i%8,cell=i/8;return Pose{start.x+(cell/side-half)*step,start.y+(cell%side-half)*step,k*pi/4};};
    auto heuristic=[&](Pose p){return std::max(0.,distance(p,goal)-(distance(start,goal)-requested))/execution_speed_;};
    std::vector<double> cost(total,std::numeric_limits<double>::infinity());std::vector<int> parent(total,-2);
    using Item=std::pair<double,int>;std::priority_queue<Item,std::vector<Item>,std::greater<Item>> queue;
    for(int k=0;k<8;++k){Pose p{start.x,start.y,k*pi/4};if(gate_.segment(start,p)){
      const int i=id(0,0,k);cost[i]=std::abs(wrap(p.yaw-start.yaw))/angular_;parent[i]=-1;queue.push({cost[i]+heuristic(p),i});}}
    const int dx[8]={1,1,0,-1,-1,-1,0,1},dy[8]={0,1,1,1,0,-1,-1,-1};
    int expanded=0;
    while(!queue.empty()) {
      const double elapsed=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count();
      if(elapsed>search_ms_ || expanded>30000)break;
      const auto item=queue.top();queue.pop();const int u=item.second;const Pose p=decode(u);
      if(item.first>cost[u]+heuristic(p)+1e-7)continue;
      ++expanded;
      if(distance(start,goal)-distance(p,goal)>=requested) {
        std::vector<Pose> candidate;int i=u;
        while(i>=0){candidate.push_back(decode(i));i=parent[i];}
        candidate.push_back(start);std::reverse(candidate.begin(),candidate.end());compress(candidate);
        if(gate_.path(candidate) && simulate(candidate)) {
          route_=std::move(candidate);++plans;last_search_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count();return true;
        }
      }
      const int k=u%8,cell=u/8,x=cell/side-half,y=cell%side-half;
      auto edge=[&](int xx,int yy,int kk,double seconds) {
        if(std::abs(xx)>half || std::abs(yy)>half)return;
        const int v=id(xx,yy,kk);const double next=cost[u]+seconds;
        if(next>=cost[v]-1e-9)return;
        const Pose q=decode(v);if(!gate_.segment(p,q))return;
        cost[v]=next;parent[v]=u;queue.push({next+heuristic(q),v});
      };
      edge(x,y,(k+1)%8,(pi/4)/angular_);edge(x,y,(k+7)%8,(pi/4)/angular_);
      for(int gear:{-1,1})edge(x+gear*dx[k],y+gear*dy[k],k,step*std::hypot(dx[k],dy[k])/execution_speed_);
    }
    last_search_ms=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-began).count();return false;
  }

 private:
  static double distance(Pose a,Pose b){return std::hypot(a.x-b.x,a.y-b.y);}
  static double approach(double a,double b,double amount){return a+std::max(-amount,std::min(amount,b-a));}
  static void compress(std::vector<Pose>& p) {
    std::vector<Pose> q;
    for(const Pose& c:p) {
      if(!q.empty() && distance(q.back(),c)<1e-8 && std::abs(wrap(q.back().yaw-c.yaw))<1e-8)continue;
      if(q.size()>1) {
        const Pose a=q[q.size()-2],b=q.back();
        const double ux=b.x-a.x,uy=b.y-a.y,vx=c.x-b.x,vy=c.y-b.y;
        if(std::hypot(ux,uy)>1e-8 && std::hypot(vx,vy)>1e-8 &&
           std::abs(wrap(a.yaw-b.yaw))<1e-8 && std::abs(wrap(b.yaw-c.yaw))<1e-8 &&
           std::abs(ux*vy-uy*vx)<1e-8 && ux*vx+uy*vy>0) {q.back()=c;continue;}
      }
      q.push_back(c);
    }
    p=std::move(q);
  }
  bool follow(const std::vector<Pose>& path,size_t& index,Pose current,double dt,
              double& pv,double& pw,double& v,double& w) const {
    if(index>=path.size()){v=approach(pv,0,accel_*dt);w=approach(pw,0,angular_accel_*dt);pv=v;pw=w;return false;}
    const Pose from=path[index-1],target=path[index];const bool turn=distance(from,target)<1e-7;
    const double angle=wrap(target.yaw-current.yaw);double desired_v=0,desired_w=0;
    bool reached=false;
    if(turn) {
      reached=std::abs(angle)<.02;
      if(!reached)desired_w=std::copysign(std::min(angular_,std::sqrt(2.*angular_accel_*std::max(0.,std::abs(angle)-.01))),angle);
    } else {
      // Completion uses along/cross errors; a small overshoot must not deadlock.
      const double ux=std::cos(target.yaw),uy=std::sin(target.yaw);
      const double gear=((target.x-from.x)*ux+(target.y-from.y)*uy)>=0?1.:-1.;
      const double along=gear*((target.x-current.x)*ux+(target.y-current.y)*uy);
      const double cross=ux*(target.y-current.y)-uy*(target.x-current.x);
      reached=along<=.01 && along>=-.02 && std::abs(cross)<=.015 && std::abs(angle)<.04;
      if(!reached) {
        desired_w=std::max(-angular_,std::min(angular_,3.*angle+2.*gear*cross));
        if(std::abs(angle)<.1)desired_v=gear*std::min(execution_speed_,std::sqrt(2.*accel_*std::max(0.,along-.005)));
      }
    }
    v=approach(pv,desired_v,accel_*dt);w=approach(pw,desired_w,angular_accel_*dt);pv=v;pw=w;
    if(reached && std::abs(v)+std::abs(w)<1e-7)++index;
    return true;
  }
  bool simulate(const std::vector<Pose>& path) {
    if(path.size()<2)return false;
    Pose p=path.front();size_t i=1;double pv=0,pw=0,v=0,w=0;
    for(int tick=0;tick<2000;++tick) {
      follow(path,i,p,.02,pv,pw,v,w);
      if(!gate_.command(p,v,w,false))return false;
      if(i>=path.size() && std::abs(v)+std::abs(w)<1e-7)return true;
      p.x+=v*.02*std::cos(p.yaw+w*.01);p.y+=v*.02*std::sin(p.yaw+w*.01);p.yaw=wrap(p.yaw+w*.02);
    }
    return false;
  }
  bool execute(Pose pose,double now,double& v,double& w) {
    if(!gate_.pose(pose)){++invalidated;reset("START_INVALID:"+gate_.last_reason);v=w=0;next_plan_=now+.25;report(now,pose,v,w);return true;}
    // Bounded no-progress recovery: a lateral miss or estimator jump cannot
    // retain ownership forever, even when all map checks still pass.
    if(index_<route_.size()) {
      const Pose target=route_[index_];
      const double error=distance(pose,target)+.25*std::abs(wrap(target.yaw-pose.yaw));
      if(progress_index_!=index_ || error<best_error_-.001) {
        progress_index_=index_;best_error_=error;progress_at_=now;
      } else if(now-progress_at_>2.) {
        reset("NO_PROGRESS");v=w=0;next_plan_=now+.5;report(now,pose,v,w);return true;
      }
    }
    const double dt=std::max(0.,std::min(.05,now-last_tick_));last_tick_=now;
    follow(route_,index_,pose,dt,previous_v_,previous_w_,v,w);
    if(!gate_.command(pose,v,w)){++invalidated;reset("COMMAND_REJECTED:"+gate_.last_reason);v=w=0;next_plan_=now+.25;report(now,pose,v,w);return true;}
    if(index_>=route_.size() && std::abs(v)+std::abs(w)<1e-7) {
      ++completed;state="COMPLETED";active_=false;blocked_at_=-1;next_plan_=now+.5;
    }
    report(now,pose,v,w);return true;
  }
  void reset(const std::string& reason){active_=false;state=reason;blocked_at_=-1;previous_v_=previous_w_=0;}
  void publishPath() {
    nav_msgs::msg::Path msg;msg.header.frame_id="map";msg.header.stamp=node_->now();
    for(Pose p:route_){geometry_msgs::msg::PoseStamped s;s.header=msg.header;s.pose.position.x=p.x;s.pose.position.y=p.y;s.pose.orientation.z=std::sin(p.yaw/2);s.pose.orientation.w=std::cos(p.yaw/2);msg.poses.push_back(s);}
    if(path_pub_)path_pub_->publish(msg);
  }
  void report(double now,Pose pose,double v,double w) {
    if(!diagnostics_ || (state==last_report_state_ && now-last_report_at_<.2))return;
    last_report_at_=now;last_report_state_=state;std::ostringstream out;out<<std::fixed<<std::setprecision(9)
      <<"{\"time\":"<<now<<",\"map_stamp\":"<<gate_.mapStamp()<<",\"state\":\""<<state<<"\",\"active\":"<<(active_?"true":"false")
      <<",\"plans\":"<<plans<<",\"completed\":"<<completed<<",\"invalidated\":"<<invalidated<<",\"search_failures\":"<<search_failures
      <<",\"goal_cancellations\":"<<goal_cancellations<<",\"compatible_goal_updates\":"<<compatible_goal_updates<<",\"goal_age_s\":"<<(now-goal_at_)
      <<",\"search_ms\":"<<last_search_ms<<",\"x\":"<<pose.x<<",\"y\":"<<pose.y<<",\"yaw\":"<<pose.yaw
      <<",\"goal_x\":"<<goal_.x<<",\"goal_y\":"<<goal_.y<<",\"segment\":"<<index_<<",\"segments\":"<<route_.size()
      <<",\"progress_m\":"<<distance(origin_,pose)<<",\"linear\":"<<v<<",\"angular\":"<<w<<"}";
    std_msgs::msg::String msg;msg.data=out.str();diagnostics_->publish(msg);
  }
  rclcpp::Node::SharedPtr node_;Gate& gate_;
  double speed_=.15,execution_speed_=.15,angular_=.5,accel_=2.5,angular_accel_=3.,progress_=.75,search_ms_=20.,odom_timeout_=.2;
  bool have_goal_=false,finished_=false,active_=false;
  Pose goal_,planned_goal_,origin_;
  double goal_at_=0,blocked_at_=-1,next_plan_=0,last_tick_=0,previous_v_=0,previous_w_=0,last_report_at_=-1;
  size_t progress_index_=0;double best_error_=std::numeric_limits<double>::infinity(),progress_at_=0;
  size_t index_=0;std::vector<Pose> route_;std::string last_report_state_;
  rclcpp::Subscription<geometry_msgs::msg::PointStamped>::SharedPtr goal_sub_;
  rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr finish_sub_;
  rclcpp::Publisher<std_msgs::msg::String>::SharedPtr diagnostics_;
  rclcpp::Publisher<nav_msgs::msg::Path>::SharedPtr path_pub_;
};
}
