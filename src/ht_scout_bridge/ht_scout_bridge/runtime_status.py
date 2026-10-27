"""Read-only runtime diagnosis and RViz overlays. Never sends control messages."""
import json,math,time
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data,QoSProfile,DurabilityPolicy
from nav_msgs.msg import Odometry
from grid_map_msgs.msg import GridMap
from tare_planner.msg import StartupPrior
from std_msgs.msg import String,ColorRGBA
from geometry_msgs.msg import Point,TwistStamped
from visualization_msgs.msg import Marker,MarkerArray
from sensor_msgs.msg import PointCloud2,PointField
from builtin_interfaces.msg import Duration

GOOD_PLAN={'HT_ASSISTED','STARTUP_PRIOR','GEOMETRIC_FALLBACK','GEOMETRIC'}

def diagnose(mode,odom_age,map_age,direction_accepted,planner,follower,bridge,
             output_publishers=0,output_subscribers=0):
    if odom_age is None or not 0<=odom_age<=.5:return 'ODOMETRY_MISSING_OR_STALE'
    if map_age is None or not 0<=map_age<=1.:return 'HT_MAP_MISSING_OR_STALE'
    if not direction_accepted:return 'DIRECTION_EVIDENCE_NOT_ACCEPTED'
    if planner not in GOOD_PLAN:return planner or 'PLANNER_STATUS_MISSING'
    if mode=='inspect':return 'INSPECT_NO_MOTOR_OUTPUT'
    if follower not in ('DRIVING','TURNING','ALIGNING'):return follower or 'FOLLOWER_STATUS_MISSING'
    if mode=='preview':return 'PREVIEW_NO_MOTOR_OUTPUT'
    if bridge!='FORWARDING':return bridge or 'COMMAND_BRIDGE_STATUS_MISSING'
    if output_publishers!=1:return 'COMMAND_OWNERSHIP_CONFLICT'
    if output_subscribers==0:return 'NO_CHASSIS_COMMAND_SUBSCRIBER'
    return 'COMMAND_SENT_NOT_WHEEL_CONFIRMED'


def decode_grid(m):
    nx=round(m.info.length_x/m.info.resolution);ny=round(m.info.length_y/m.info.resolution)
    if nx<1 or ny<1 or nx>1024 or ny>1024:raise ValueError('Invalid grid size')
    a={k:np.roll(np.asarray(v.data,np.float32).reshape(nx,ny,order='F'),
          (-m.outer_start_index,-m.inner_start_index),(0,1)) for k,v in zip(m.layers,m.data)}
    rr,cc=np.indices((nx,ny));r=m.info.resolution
    x=m.info.pose.position.x+((nx-1)/2-rr)*r;y=m.info.pose.position.y+((ny-1)/2-cc)*r
    return a,x,y

class RuntimeStatus(Node):
    def __init__(self):
        super().__init__('scout_runtime_status')
        self.mode=self.declare_parameter('run_mode','inspect').value
        self.mapping=self.declare_parameter('mapping_verified',False).value
        self.terrain=self.declare_parameter('terrain_validated',False).value
        self.acceptance=self.declare_parameter('direction_acceptance','mapping').value
        self.command_topic=self.declare_parameter('command_topic','/ht_real/cmd_vel_stamped').value
        self.output_topic=self.declare_parameter('chassis_command_topic','/cmd_vel').value
        self.latest={};self.grid=None;self.decoded=None;self.odom=None;self.prior=None;self.command=None;self.last_reason=None
        self.statuspub=self.create_publisher(String,'/ht_real/runtime_status',1)
        self.markpub=self.create_publisher(MarkerArray,'/ht_real/runtime_markers',1)
        self.bestpub=self.create_publisher(PointCloud2,'/ht_real/visualization/best_probability',1)
        self.rawpub=self.create_publisher(PointCloud2,'/ht_real/visualization/measured_height',1)
        for key,topic in [('planner','/ht_real/ht_execution_status'),('follower','/ht_real/ht_follower_status'),
            ('bridge','/ht_real/command_bridge_status'),('input','/ht_real/input_status'),('ht_input','/ht_real/ht_input_status')]:
            self.create_subscription(String,topic,lambda m,k=key:self.receive(k,m.data),5)
        self.create_subscription(GridMap,'/ht_real/traversability',self.map_received,1)
        self.create_subscription(GridMap,'/ht_real/elevation_raw',self.raw_received,1)
        self.create_subscription(Odometry,'/ht_real/odometry',self.odom_received,qos_profile_sensor_data)
        self.create_subscription(StartupPrior,'/ht_real/ht_startup_prior',self.prior_received,
            QoSProfile(depth=1,durability=DurabilityPolicy.TRANSIENT_LOCAL))
        self.create_subscription(TwistStamped,self.command_topic,self.command_received,1)
        self.raw=None;self.create_timer(.5,self.tick)
    def receive(self,key,text):self.latest[key]=(text,time.monotonic())
    def odom_received(self,m):self.odom=m
    def map_received(self,m):
        self.grid=m
        try:self.decoded=decode_grid(m)
        except (ValueError,KeyError,IndexError):self.decoded=None
    def raw_received(self,m):self.raw=m
    def prior_received(self,m):self.prior=m
    def command_received(self,m):self.command=m
    def current(self,key,timeout):
        x=self.latest.get(key);return x[0] if x and time.monotonic()-x[1]<=timeout else None
    @staticmethod
    def stamp(m):return m.header.stamp.sec+m.header.stamp.nanosec*1e-9
    def marker(self,i,kind):
        m=Marker();m.header.frame_id='map';m.header.stamp=self.get_clock().now().to_msg();m.ns='runtime_readonly';m.id=i;m.type=kind;m.action=Marker.ADD;m.pose.orientation.w=1.;m.lifetime=Duration(sec=2);return m
    def tick(self):
        now=self.get_clock().now().nanoseconds/1e9
        odom_age=now-self.stamp(self.odom) if self.odom else None
        map_age=now-self.stamp(self.grid) if self.grid else None
        direction=self.mapping and (self.acceptance=='mapping' or self.terrain)
        p=self.current('planner',3.);f=self.current('follower',1.);b=self.current('bridge',1.)
        reason=diagnose(self.mode,odom_age,map_age,direction,p,f,b,
            self.count_publishers(self.output_topic),self.count_subscribers(self.output_topic))
        remaining=None;active=False
        if self.prior:
            end=self.prior.expires_at.sec+self.prior.expires_at.nanosec*1e-9
            remaining=max(0.,end-now);active=not self.prior.retired and self.stamp(self.prior)<=now<end
        result={'mode':self.mode,'reason':reason,'planner':p,'follower':f,'command_bridge':b,
            'input':self.current('input',3.),'ht_input':self.current('ht_input',3.),'odometry_age_s':odom_age,
            'ht_map_age_s':map_age,'mapping_verified':self.mapping,'terrain_response_validated':self.terrain,
            'direction_acceptance':self.acceptance,'startup_prior_active':active,'startup_remaining_s':remaining,
            'motor_output_enabled':self.mode=='drive','wheel_motion_confirmed':False}
        if self.command:
            result['command']={'topic':self.command_topic,'age_s':now-self.stamp(self.command),
                'linear_x':self.command.twist.linear.x,'angular_z':self.command.twist.angular.z}
        if self.decoded is not None and self.odom and map_age is not None and 0<=map_age<=1.:
            a,x,y=self.decoded;pos=self.odom.pose.pose.position
            inside=(x-pos.x)**2+(y-pos.y)**2<=.6**2
            result['body']={'cells':int(inside.sum()),'unknown':int((inside&(a['ht_observation_valid']<.5)).sum()),
                'context_invalid':int((inside&(a['ht_valid']<.5)).sum()),'obstacle':int((inside&(a['ht_obstacle']>=.5)).sum()),
                'interpolated':int((inside&(a.get('ht_interpolated',np.zeros_like(x))>=.5)).sum())}
        if self.markpub.get_subscription_count() or self.bestpub.get_subscription_count() or self.rawpub.get_subscription_count():
            try:self.visualize(result,active,remaining)
            except (ValueError,KeyError,IndexError) as e:result['display_error']=str(e)
        self.statuspub.publish(String(data=json.dumps(result,ensure_ascii=False)))
        if reason!=self.last_reason:
            self.get_logger().info(f'mode={self.mode} reason={reason}; mapping={self.mapping}, physical_response={self.terrain}')
            self.last_reason=reason
    def cloud(self,m,x,y,z,mask,rgb):
        a=np.empty(int(mask.sum()),dtype=[('x','<f4'),('y','<f4'),('z','<f4'),('rgb','<u4')])
        a['x']=x[mask];a['y']=y[mask];a['z']=z[mask];a['rgb']=rgb[mask] if isinstance(rgb,np.ndarray) else rgb
        c=PointCloud2();c.header=m.header;c.height=1;c.width=len(a);c.point_step=16;c.row_step=c.width*16;c.is_dense=True
        c.fields=[PointField(name=n,offset=i*4,datatype=PointField.UINT32 if n=='rgb' else PointField.FLOAT32,count=1) for i,n in enumerate(['x','y','z','rgb'])];c.data=a.tobytes();return c
    def visualize(self,result,active,remaining):
        pos=self.odom.pose.pose.position if self.odom else Point()
        ground=pos.z-.23479;markers=[]
        text=self.marker(0,Marker.TEXT_VIEW_FACING);text.pose.position=Point(x=pos.x,y=pos.y,z=pos.z+1.3)
        text.scale.z=.10;text.color=ColorRGBA(r=1.,g=1.,b=1.,a=1.)
        text.text=f'{self.mode}: {result["reason"]}\nMapping={self.mapping} terrain_test={self.terrain}\nPrior={active} remaining={remaining or 0:.1f}s\nWhite=body; cyan=HT; green ring=start prior'
        markers.append(text)
        def ring(i,x,y,r,color):
            m=self.marker(i,Marker.LINE_STRIP);m.scale.x=.025;m.color=color
            m.points=[Point(x=float(x+r*math.cos(t)),y=float(y+r*math.sin(t)),z=float(ground+.07)) for t in np.linspace(0,2*math.pi,65)];return m
        markers.append(ring(1,pos.x,pos.y,.6,ColorRGBA(r=1.,g=1.,b=1.,a=1.)))
        if self.prior:
            markers.append(ring(2,self.prior.anchor.x,self.prior.anchor.y,self.prior.radius,
                ColorRGBA(r=.1 if active else .5,g=1. if active else .5,b=.1 if active else .5,a=1.)))
        if self.grid and self.decoded is not None and result['ht_map_age_s'] is not None and 0<=result['ht_map_age_s']<=1.:
            m=self.grid;a,x,y=self.decoded;valid=a['ht_valid']>=.5;physical=a['ht_observation_valid']>=.5;blocked=a['ht_obstacle']>=.5
            inside=(x-pos.x)**2+(y-pos.y)**2<=.6**2
            result['body']={'cells':int(inside.sum()),'unknown':int((inside&~physical).sum()),
                'context_invalid':int((inside&~valid).sum()),'obstacle':int((inside&blocked).sum()),
                'interpolated':int((inside&(a.get('ht_interpolated',np.zeros_like(x))>=.5)).sum())}
            body=self.marker(3,Marker.CUBE_LIST);body.scale.x=body.scale.y=m.info.resolution*.9;body.scale.z=.015
            for i,j in zip(*np.nonzero(inside)):
                body.points.append(Point(x=float(x[i,j]),y=float(y[i,j]),z=float(ground+.04)))
                rgb=(1.,.05,1.) if blocked[i,j] else (1.,.1,.05) if not physical[i,j] else (1.,.75,.05) if not valid[i,j] else (.1,.8,.2)
                body.colors.append(ColorRGBA(r=rgb[0],g=rgb[1],b=rgb[2],a=1.))
            markers.append(body)
            edge=self.marker(4,Marker.LINE_STRIP);edge.scale.x=.025;edge.color=ColorRGBA(r=.1,g=.8,b=1.,a=1.)
            cx=m.info.pose.position.x;cy=m.info.pose.position.y;hx=m.info.length_x/2;hy=m.info.length_y/2
            edge.points=[Point(x=cx+dx*hx,y=cy+dy*hy,z=ground) for dx,dy in [(-1,-1),(-1,1),(1,1),(1,-1),(-1,-1)]];markers.append(edge)
            if self.bestpub.get_subscription_count():
                prob=np.max(np.nan_to_num(np.stack([a[f'ht_dir_{k}'] for k in range(8)]),nan=0),axis=0);v=np.clip(prob,0,1)
                rgb=(((1-v)*255).astype(np.uint32)<<16)|((v*255).astype(np.uint32)<<8)
                self.bestpub.publish(self.cloud(m,x,y,a['ht_elevation']+.025,valid&np.isfinite(a['ht_elevation']),rgb))
        self.markpub.publish(MarkerArray(markers=markers))
        if self.raw and self.rawpub.get_subscription_count() and 0<=self.get_clock().now().nanoseconds/1e9-self.stamp(self.raw)<=1.:
            a,x,y=decode_grid(self.raw);self.rawpub.publish(self.cloud(self.raw,x,y,a['elevation'],np.isfinite(a['elevation']),0x909090))

def main():
    rclpy.init();n=RuntimeStatus()
    try:rclpy.spin(n)
    except KeyboardInterrupt:pass
    finally:n.destroy_node();rclpy.try_shutdown()
