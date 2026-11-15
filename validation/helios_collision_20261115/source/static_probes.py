from pathlib import Path
import copy,json,os,signal,subprocess,time,xml.etree.ElementTree as ET
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String

root=Path('/home/lzz/ht_helios_collision_20261115');assets=root/'common_sensor_optical';out=root/'static_probes_optical';out.mkdir(exist_ok=True)
manifest=json.loads((assets/'MANIFEST.json').read_text());window=manifest['optical_window_radius_m'];height=manifest['lidar_height_above_ground_m'];angles=np.array(manifest['profile']['vertical_angles_deg'])
def sub(p,t,value=None,**attrs):
    e=ET.SubElement(p,t,attrs)
    if value is not None:e.text=str(value)
    return e
def box(world,name,xyz,size):
    m=sub(world,'model',name=name);sub(m,'static','true');sub(m,'pose',' '.join(map(str,[*xyz,0,0,0])));l=sub(m,'link',name='link');g=sub(sub(l,'collision',name='collision'),'geometry');sub(sub(g,'box'),'size',' '.join(map(str,size)))
def world(case):
    sdf=ET.Element('sdf',version='1.7');w=sub(sdf,'world',name='default');physics=sub(w,'physics',name='ode',type='ode');sub(physics,'max_step_size','.001');sub(physics,'real_time_update_rate','1000')
    box(w,'floor',(0,0,-.05),(100,100,.1));box(w,'wall',(5.1725,0,3),(.1,30,6))
    if case=='blind':box(w,'near_obstruction',(.1725+.15,0,height),(.06,.06,.06))
    robot=copy.deepcopy(ET.parse(assets/'robot.sdf').getroot().find('model'));robot.set('name','robot');sub(robot,'pose',f'.1725 0 {height} 0 0 0')
    if case in ('transparent','blind'):
        for l in robot.findall('link'):
            for c in list(l.findall('collision')):l.remove(c)
    w.append(robot);lidar=copy.deepcopy(ET.parse(assets/'lidar.sdf').getroot().find('model'));sub(lidar,'pose',f'.1725 0 {height} 0 0 0');w.append(lidar)
    path=out/(case+'.world');ET.ElementTree(sdf).write(path,encoding='unicode');return path

rclpy.init();results=[]
for case in ['transparent','opaque','blind']:
    path=world(case);node=Node('helios_static_'+case);messages={};counts={'raw':0,'filtered':0,'status':0};times=[]
    def receive(key,m):
        messages[key]=m;counts[key]+=1
        if key=='raw':times.append(time.monotonic())
    subscriptions=[node.create_subscription(PointCloud2,'/rslidar_points',lambda m:receive('raw',m),10),node.create_subscription(PointCloud2,'/velodyne_points',lambda m:receive('filtered',m),10),node.create_subscription(String,'/helios_sim/scan_status',lambda m:receive('status',m),10)]
    log=(out/(case+'.log')).open('w');p=subprocess.Popen(['gzserver','--verbose',str(path),'-s','libgazebo_ros_init.so'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            if p.poll() is not None:raise RuntimeError(case+' gazebo exited')
            if min(counts.values())>=20:break
        else:raise RuntimeError(case+' sensor deadline exceeded: '+str(counts))
        def data(m):
            dt=np.dtype({'names':['x','y','z','ring','azimuth_index','range'],'formats':['<f4','<f4','<f4','<u2','<u2','<f4'],'offsets':[0,4,8,16,18,24],'itemsize':28})
            return np.frombuffer(m.data,dtype=dt).copy()
        a=data(messages['raw']);b=data(messages['filtered']);finite=np.isfinite(a['x']);valid=np.isfinite(b['x'])
        worldx=b['x']+.1725;worldz=b['z']+height
        under=valid&(abs(worldz)<.015)&(abs(worldx)<.44)&(abs(b['y'])<.15)
        ring10=b[(b['ring']==9)&(b['azimuth_index']==900)]
        inferred=np.degrees(np.arctan2(a['z'],np.hypot(a['x'],a['y'])-window));angle_errors=[]
        for k in range(32):
            subset=(a['ring']==k)&finite
            if subset.any():angle_errors.append(float(np.max(abs(inferred[subset]-angles[k]))))
        status=json.loads(messages['status'].data);result={'case':case,'counts':counts,'valid_raw_points':int(finite.sum()),'valid_filtered_points':int(valid.sum()),'ground_points_under_solid_chassis':int(under.sum()),'all_channel_angles_max_error_deg':max(angle_errors),'represented_rings':len(angle_errors),'front_horizontal_range_m':None if not np.isfinite(ring10['range'][0]) else float(ring10['range'][0]),'wall_rate_hz':(len(times)-1)/(times[-1]-times[0]),'scan_status':status}
        np.savez_compressed(out/(case+'.npz'),raw=a,filtered=b);results.append(result);(out/'RESULTS.json').write_text(json.dumps(results,indent=2));print(json.dumps(result,indent=2),flush=True)
    finally:
        if p.poll() is None:
            os.killpg(p.pid,signal.SIGINT)
            try:p.wait(timeout=12)
            except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGTERM);p.wait(timeout=10)
        log.close();node.destroy_node();time.sleep(2)
rclpy.shutdown()
by={r['case']:r for r in results}
# At the corrected optical height even the transparent -55deg nominal scanner
# does not reach the solid chassis footprint. Test actual shadows instead of
# requiring fictitious ground returns underneath it.
assert by['opaque']['valid_filtered_points'] < by['transparent']['valid_filtered_points']
assert by['opaque']['scan_status']['self_hits']==by['opaque']['valid_raw_points']-by['opaque']['valid_filtered_points']
assert by['opaque']['ground_points_under_solid_chassis']==0 and by['opaque']['scan_status']['self_hits']>0 and by['opaque']['valid_filtered_points']>0
assert by['transparent']['front_horizontal_range_m']>4 and by['blind']['front_horizontal_range_m'] is None and by['blind']['scan_status']['blind_hits']>0
assert all(r['all_channel_angles_max_error_deg']<.001 and r['represented_rings']==32 for r in results)
(out/'PASSED.json').write_text(json.dumps({'passed':True,'scope':'Gazebo ray intersections, full 1800x32 nominal pattern; body shadow, nonuniform angles and near-blind obstruction checks.'},indent=2))
print('STATIC_OCCLUSION_PROBES_PASSED')
