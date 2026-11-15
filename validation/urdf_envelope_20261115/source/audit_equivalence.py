from pathlib import Path
import importlib.util,json,math
import numpy as np
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Float32MultiArray,MultiArrayDimension
spec=importlib.util.spec_from_file_location('audit','/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes/tools/cmu_minimal/audit_commands.py');audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)
rng=np.random.default_rng(3817);rows=cols=201;res=.04
msg=GridMap();msg.header.frame_id='map';msg.header.stamp.sec=100;msg.info.resolution=res;msg.info.length_x=msg.info.length_y=rows*res;msg.info.pose.orientation.w=1.
raw=np.zeros((rows,cols),np.float32);raw[rng.integers(15,186,180),rng.integers(15,186,180)]=1
for k in range(11):
    msg.layers.append('ht_dir_'+str(k) if k<8 else ['ht_valid','ht_observation_valid','ht_obstacle'][k-8]);a=Float32MultiArray();a.layout.dim=[MultiArrayDimension(label='column_index',size=cols,stride=rows*cols),MultiArrayDimension(label='row_index',size=rows,stride=rows)]
    data=np.full((rows,cols),.9 if k<8 else 1,np.float32) if k<10 else raw;a.data=data.flatten(order='F').tolist();msg.data.append(a)
audit.RADIUS=.8;decoded=audit.decode(msg);rr,cc=np.indices((rows,cols));gx=(rows*.5-rr-.5)*res;gy=(cols*.5-cc-.5)*res
counts={'matched':0,'allowed':0,'occupied':0}
for length,width,bx,by in [(.6,.6,0,0),(.9298609,.69959,0,0),(.8,.2,.25,-.1)]:
    margin=res/math.sqrt(2)+.01+math.hypot(abs(bx)+length/2,abs(by)+width/2)*math.pi/128
    for i in range(120):
        x,y,angle=rng.uniform(-2,2),rng.uniform(-2,2),rng.uniform(-math.pi,math.pi);dx=gx-x;dy=gy-y;cs=math.cos(angle);sn=math.sin(angle)
        dense=bool(np.any((np.abs(cs*dx+sn*dy-bx)<=length/2+margin)&(np.abs(-sn*dx+cs*dy-by)<=width/2+margin)&(raw>=.5)))
        d={'x':x,'y':y,'yaw':angle,'time':100.1,'map_stamp':100.,'linear_candidate':0.,'angular_candidate':0.,'reaction_time':.1,'linear_brake_accel':2.5,'angular_brake_accel':3.,'obstacle_footprint':'urdf_box_xy_v1','body_length':length,'body_width':width,'body_center_x':bx,'body_center_y':by,'support_radius':.8}
        ok,reason,_=audit.check(decoded,d)
        assert ok==(not dense),(ok,reason,dense)
        counts['matched']+=1;counts['allowed' if ok else 'occupied']+=1
Path('/mnt/d/HT-URDF-Compare-20261115/analysis').mkdir(exist_ok=True)
Path('/mnt/d/HT-URDF-Compare-20261115/analysis/AUDIT_SPARSE_EQUIVALENCE.json').write_text(json.dumps(counts,indent=2));print(counts)
