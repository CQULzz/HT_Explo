from pathlib import Path
import importlib.util,json,collections,math,csv
import numpy as np
import rosbag2_py
from grid_map_msgs.msg import GridMap
from rclpy.serialization import deserialize_message
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.font_manager import FontProperties
spec=importlib.util.spec_from_file_location('audit','/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/tools/cmu_minimal/audit_commands.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
root=Path('/home/lzz/ht_urdf_compare_20261115');out=Path('/mnt/d/HT-URDF-Compare-20261115/analysis');env=json.loads((root/'setup/URDF_ENVELOPE.json').read_text());results=[];example=None
def pose(m,x,y,yaw,length,width,bx,by):
    r=int(math.floor(m['rows']*.5-(x-m['cx'])/m['res']));c=int(math.floor(m['cols']*.5-(y-m['cy'])/m['res']))
    if not(0<=r<m['rows'] and 0<=c<m['cols']):return False,'OUTSIDE'
    reach=math.hypot(abs(bx)+length/2,abs(by)+width/2);margin=m['res']/math.sqrt(2)+.01+reach*math.pi/128
    dx=m['obstacle_x']-x;dy=m['obstacle_y']-y;cs,sn=math.cos(yaw),math.sin(yaw)
    if np.any((np.abs(cs*dx+sn*dy-bx)<=length/2+margin)&(np.abs(-sn*dx+cs*dy-by)<=width/2+margin)):return False,'OCCUPIED'
    if m['missing'][r,c]:return False,'MISSING_SUPPORT'
    if not np.isfinite(m['valid'][r,c]) or m['valid'][r,c]<.5:return False,'CONTEXT'
    k=int(math.floor((math.atan2(math.sin(yaw),math.cos(yaw))+2*math.pi)/(math.pi/4)+.5))%8
    s=m['scores'][k,r,c]
    if not np.isfinite(s) or not .5<=s<=1:return False,'SCORE'
    return True,'ALLOWED'
for variant in ['baseline','urdf']:
    run=root/'runs'/f'{variant}_campus_600s_01';start=json.loads((run/'observations/START.json').read_text())['clock'];rows=list(csv.DictReader((run/'observations/metrics.csv').open()));t=np.array([float(r['time']) for r in rows]);xy=np.array([[float(r['x']),float(r['y'])] for r in rows]);seen=set();counts=collections.Counter()
    reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(run/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local']))
    while reader.has_next():
        _,data,receipt=reader.read_next();msg=deserialize_message(data,GridMap);clock=msg.header.stamp.sec+msg.header.stamp.nanosec/1e9;elapsed=clock-start
        if not 0<=elapsed<600:continue
        bucket=int(elapsed/10)
        if bucket in seen:continue
        seen.add(bucket);counts['maps']+=1
        audit.RADIUS=.45;old=audit.decode(msg);audit.RADIUS=env['required_support_radius'];new=audit.decode(msg)
        base=xy[np.argmin(abs(t-clock))]
        for dx in np.arange(-2,2.001,.5):
            for dy in np.arange(-2,2.001,.5):
                x,y=base+[dx,dy]
                for k in range(8):
                    yaw=k*math.pi/4;a,ar=pose(old,x,y,yaw,.6,.6,0,0);b,br=pose(new,x,y,yaw,*env['size_xyz'][:2],*env['center_xyz'][:2]);counts['poses']+=1;counts[f'old_{a}_urdf_{b}']+=1
                    if a and not b:
                        counts['new_rejection_'+br]+=1
                        if br=='OCCUPIED' and example is None:
                            example={'recording':variant,'map_elapsed_s':elapsed,'x':x,'y':y,'yaw':yaw,'scope':'Hypothetical nearby pose on recorded map, not an executed vehicle pose or command.'}
                            np.savez_compressed(out/'nearby_pose_example.npz',obstacle_x=new['obstacle_x'],obstacle_y=new['obstacle_y'],resolution=new['res'])
    results.append({'recording':variant,'scope':'First map each 10s, hypothetical XY offsets -2..2m at 0.5m intervals and 8 body headings. Same fresh map and HT thresholds, old/new body and corresponding support circles. Not a motion-planning or collision-truth test.','counts':dict(counts)})
(out/'NEARBY_POSE_COMPARISON.json').write_text(json.dumps({'results':results,'example':example},indent=2))
if example:
    a=np.load(out/'nearby_pose_example.npz');px,py,yaw=example['x'],example['y'],example['yaw'];font=FontProperties(fname='/mnt/c/Windows/Fonts/msyh.ttc');fig,ax=plt.subplots(figsize=(7,6));near=(abs(a['obstacle_x']-px)<1)&(abs(a['obstacle_y']-py)<1);ax.scatter(a['obstacle_x'][near],a['obstacle_y'][near],s=35,marker='s',c='black',label='原图硬占用格中心')
    for lo,hi,color,label in [(np.array([-.3,-.3]),np.array([.3,.3]),'tab:blue','旧包络'),(np.array(env['min_xyz'][:2]),np.array(env['max_xyz'][:2]),'tab:orange','URDF包络')]:
        pts=np.array([[lo[0],lo[1]],[hi[0],lo[1]],[hi[0],hi[1]],[lo[0],hi[1]]]);cs,sn=math.cos(yaw),math.sin(yaw);rot=np.array([[cs,-sn],[sn,cs]]);pts=pts@rot.T+[px,py];ax.add_patch(Polygon(pts,fill=False,lw=2,color=color,label=label))
    ax.scatter(px,py,marker='+',c='red');ax.set_xlim(px-1,px+1);ax.set_ylim(py-1,py+1);ax.set_aspect('equal');ax.grid(alpha=.2);ax.legend(prop=font);ax.set_title('实测地图的附近假设姿态：旧框允许，新框占用拒绝',fontproperties=font);ax.set_xlabel('X / m');ax.set_ylabel('Y / m');fig.tight_layout();fig.savefig(out/'nearby_pose_example.png',dpi=160);plt.close(fig)
print(json.dumps(results,indent=2))
