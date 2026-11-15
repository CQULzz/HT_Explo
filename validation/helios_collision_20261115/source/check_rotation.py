"""Verify real Gazebo scan registration before/after a 90-degree carrier turn.
Run only after the navigation test, in a separate ROS/Gazebo domain.
"""
from pathlib import Path
import copy,json,math,os,signal,subprocess,time,xml.etree.ElementTree as ET
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped
root=Path('/home/lzz/ht_helios_collision_20261115');out=root/'rotation_probe_optical';out.mkdir(exist_ok=True)
world=ET.parse(root/'static_probes_optical/opaque.world');w=world.getroot().find('world');plugin=ET.SubElement(w,'plugin',name='state',filename='libgazebo_ros_state.so');ET.SubElement(plugin,'update_rate').text='50'
camera=copy.deepcopy(ET.parse(root/'common_sensor_optical/camera.sdf').getroot().find('model'));ET.SubElement(camera,'pose').text='.1725 0 .84849 0 0 0';w.append(camera);world.write(out/'test.world',encoding='unicode')
rclpy.init();n=Node('helios_heading_check');last={};count={'scan':0}
def scan(m):last['scan']=m;count['scan']+=1
subs=[n.create_subscription(PointCloud2,'/registered_scan',scan,10),n.create_subscription(Odometry,'/state_estimation',lambda m:last.update(odom=m),10)]
pub=n.create_publisher(TwistStamped,'/cmd_vel',10);processes=[];logs=[]
def spawn(name,args):
    f=(out/(name+'.log')).open('w');logs.append(f);p=subprocess.Popen(args,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);processes.append(p)
def spin(seconds):
    end=time.monotonic()+seconds
    while time.monotonic()<end:rclpy.spin_once(n,timeout_sec=.02)
def command(w):
    m=TwistStamped();m.header.stamp=n.get_clock().now().to_msg();m.header.frame_id='vehicle';m.twist.angular.z=float(w);pub.publish(m)
def stats():
    m=last['scan'];fields={f.name:f.offset for f in m.fields};dt=np.dtype({'names':['x','y','z'],'formats':['<f4']*3,'offsets':[fields[k] for k in ['x','y','z']],'itemsize':m.point_step});a=np.frombuffer(m.data,dtype=dt)
    mask=np.isfinite(a['x'])&(a['z']>.2)&(a['z']<4.5)&(np.hypot(a['x'],a['y'])>1)
    x=a['x'][mask];q=last['odom'].pose.pose.orientation;yaw=math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z));p=last['odom'].pose.pose.position
    return {'yaw_rad':yaw,'wall_points':len(x),'wall_x_error_p95_m':float(np.quantile(abs(x-5.1225),.95)) if len(x) else None,'base_xy':[p.x-.1725*math.cos(yaw),p.y-.1725*math.sin(yaw)]}
try:
    spawn('gazebo',['gzserver','--verbose',str(out/'test.world'),'-s','libgazebo_ros_init.so'])
    spawn('carrier',['ros2','run','helios32_sim','vehicleSimulator','--ros-args','-p','vehicleHeight:=0.84849','-p','vehicleX:=0.1725','-p','sensorOffsetX:=0.1725','-p','adjustZ:=false','-p','adjustIncl:=false'])
    deadline=time.monotonic()+90
    while time.monotonic()<deadline and (count['scan']<8 or 'odom' not in last):spin(.1)
    if count['scan']<8:raise RuntimeError('Carrier scan startup timeout')
    command(0);spin(3);before=stats();deadline=time.monotonic()+12
    while time.monotonic()<deadline:
        value=stats()['yaw_rad']
        if value>=1.55:break
        command(.5);spin(.04)
    command(0);spin(5);after=stats()
    result={'before':before,'after':after,'scope':'Same opaque Scout/Helios model, flat floor and wall. Gazebo rotates body/scanner; actual compiled carrier registers scans. No HT or hardware controller.'}
    (out/'RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    assert before['wall_points']>100 and after['wall_points']>100
    assert before['wall_x_error_p95_m']<.03 and after['wall_x_error_p95_m']<.03
    assert after['yaw_rad']>1.4 and np.linalg.norm(after['base_xy'])<.02
    (out/'PASSED.json').write_text(json.dumps({'passed':True,'scope':'Scan registration only; cleanup is recorded separately.'},indent=2))
finally:
    command(0)
    for p in reversed(processes):
        if p.poll() is None:
            os.killpg(p.pid,signal.SIGINT)
            try:p.wait(timeout=12)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
    for f in logs:f.close()
    (out/'CLEANUP.json').write_text(json.dumps({'exit_codes':[p.returncode for p in processes],'clean':all(p.returncode==0 for p in processes)},indent=2))
    n.destroy_node();rclpy.shutdown()
