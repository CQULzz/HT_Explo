"""Bounded static Gazebo probe: compare output against an independent XYZ mask."""
import argparse,copy,json,os,signal,subprocess,time
from pathlib import Path
import xml.etree.ElementTree as ET
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import PointCloud2
from std_msgs.msg import String

def main():
    p=argparse.ArgumentParser();p.add_argument('--assets',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(exist_ok=False,parents=True)
    manifest=json.loads((a.assets/'MANIFEST.json').read_text())
    assert manifest['self_filter_mode']=='crop_box' and manifest['collision_count']==0
    sdf=ET.Element('sdf',version='1.7');world=ET.SubElement(sdf,'world',name='default')
    def box(name,pose,size):
        m=ET.SubElement(world,'model',name=name);ET.SubElement(m,'static').text='true';ET.SubElement(m,'pose').text=pose
        g=ET.SubElement(ET.SubElement(ET.SubElement(m,'link',name='link'),'collision',name='collision'),'geometry')
        ET.SubElement(ET.SubElement(g,'box'),'size').text=size
    h=manifest['lidar_height_above_ground_m']
    box('floor','0 0 -.05 0 0 0','30 30 .1')
    box('wall','5 0 3 0 0 0','.1 20 6')
    # Endpoint inside the body box; this stand-in exercises the actual filter.
    box('inside_box_target',f'.25 0 {h-.1} 0 0 0','.06 .08 .06')
    for filename in ['robot.sdf','lidar.sdf']:
        m=copy.deepcopy(ET.parse(a.assets/filename).getroot().find('model'))
        ET.SubElement(m,'pose').text=f'0 0 {h} 0 0 0';world.append(m)
    path=a.output/'probe.world';ET.ElementTree(sdf).write(path,encoding='unicode')
    rclpy.init();node=Node('crop_box_probe');received={};counts={};times=[];samples={}
    def receive(key,m):
        counts[key]=counts.get(key,0)+1
        if key=='raw':times.append(time.monotonic())
        if key=='status':received[key]=json.loads(m.data);return
        stamp=(m.header.stamp.sec,m.header.stamp.nanosec)
        samples.setdefault(stamp,{})[key]=m
    subscriptions=[node.create_subscription(PointCloud2,t,lambda m,k=k:receive(k,m),10) for k,t in [('raw','/rslidar_points'),('filtered','/velodyne_points')]]
    subscriptions.append(node.create_subscription(String,'/helios_sim/scan_status',lambda m:receive('status',m),10))
    result={};log=(a.output/'gazebo.log').open('w')
    proc=subprocess.Popen(['gzserver','--verbose',str(path),'-s','libgazebo_ros_init.so'],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    try:
        deadline=time.monotonic()+90
        while time.monotonic()<deadline:
            rclpy.spin_once(node,timeout_sec=.1)
            if proc.poll() is not None:raise RuntimeError('Gazebo exited before probe')
            if min(counts.get(k,0) for k in ['raw','filtered','status'])>=20:break
        else:raise RuntimeError('Probe input timeout')
        pair=next(v for v in reversed(list(samples.values())) if 'raw' in v and 'filtered' in v)
        def xyz(m):
            dt=np.dtype({'names':['x','y','z'],'formats':['<f4']*3,'offsets':[0,4,8],'itemsize':m.point_step})
            v=np.frombuffer(m.data,dtype=dt);return np.column_stack([v[k] for k in ['x','y','z']])
        raw=xyz(pair['raw']);filtered=xyz(pair['filtered']);finite=np.isfinite(raw).all(1)
        inside=finite&(raw>=manifest['crop_min_xyz']).all(1)&(raw<=manifest['crop_max_xyz']).all(1)
        assert inside.sum()>0,'Fixture did not exercise removal'
        assert np.isnan(filtered[inside]).all(),'Box endpoints survived'
        assert np.array_equal(raw[finite&~inside],filtered[finite&~inside]),'Outside points changed'
        assert np.isnan(filtered[~finite]).all(),'No-return points became returns'
        assert pair['raw'].height==pair['filtered'].height==32
        assert pair['raw'].header==pair['filtered'].header
        np.savez_compressed(a.output/'clouds.npz',raw=raw,filtered=filtered)
        result.update(passed=True,removed_points=int(inside.sum()),preserved_outside_points=int((finite&~inside).sum()),wall_rate_hz=(len(times)-1)/(times[-1]-times[0]),status=received['status'],scope='Static endpoint crop check only; no body shadow, navigation or real-time acceptance.')
    finally:
        if proc.poll() is None:
            os.killpg(proc.pid,signal.SIGINT)
            try:proc.wait(timeout=15)
            except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGTERM);proc.wait(timeout=10)
        result['gazebo_exit_code']=proc.returncode
        log.close();node.destroy_node();rclpy.shutdown()
        (a.output/'RESULT.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

if __name__=='__main__':main()
