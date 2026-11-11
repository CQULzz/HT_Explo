from pathlib import Path
import sys,json,math,ast
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
ROOT=Path('/home/lzz/ht_only_20261111');out=ROOT/'analysis/source_rejections';out.mkdir(exist_ok=False);project=Path('/home/lzz/HT_Explo_ht_only_20261111/tools/ht_cupy_bridge');sys.path.insert(0,str(project))
from elevation_quality import preprocess_elevation
source=ast.parse((project/'cupy_to_ht.py').read_text());function=next(n for n in source.body if isinstance(n,ast.FunctionDef) and n.name=='decode_elevation_source');ns={'np':np,'math':math};exec(compile(ast.Module(body=[function],type_ignores=[]),'exact_decode','exec'),ns)
points=json.loads((ROOT/'analysis/live_a_stop/HISTORY_CELLS.json').read_text());target=points[0]['rejected_time'];reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(ROOT/'runs/a_user_pcd_600s_02/bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/elevation_mapping/elevation_map_raw']));reader.seek(int((target-1.2)*1e9));results=[]
while reader.has_next():
 _,data,received=reader.read_next()
 if received/1e9>target+2:break
 grid=deserialize_message(data,GridMap);stamp=grid.header.stamp.sec+grid.header.stamp.nanosec*1e-9;res,z,v,age=ns['decode_elevation_source'](grid);quality=preprocess_elevation(z,v,res,backend='numpy',denoise=False);frame=[]
 for point in points:
  x,y=point['xy'];gx,gy=round(x/res),round(y/res);ii=round(grid.info.pose.position.x/res)+145-gx;jj=round(grid.info.pose.position.y/res)+145-gy
  if not(1<=ii<290 and 1<=jj<290):continue
  frame.append({'xy':[x,y],'source_elevation_m':float(z[ii,jj]),'variance_m2':float(v[ii,jj]),'observation_age_s':float(age[ii,jj]),'source_observation_time':stamp-float(age[ii,jj]),'quality_rejected':bool(quality.rejected_mask[ii,jj]),'observed_quality':bool(quality.observed_quality[ii,jj]),'height_3x3':z[ii-1:ii+2,jj-1:jj+2].tolist(),'variance_3x3':v[ii-1:ii+2,jj-1:jj+2].tolist()})
 results.append({'stamp':stamp,'cells':frame});(out/f'frame_{len(results):02d}.cdr').write_bytes(data)
(out/'RESULT.json').write_text(json.dumps({'rejection_observation_time':target,'frames':results,'scope':'Exact raw elevation source snapshots around the saved rejection time; unchanged source decoder and NumPy reference quality filter. No inference, no navigation or changes to thresholds.'},indent=2));print('frames',len(results))
for frame in results:
 print(frame['stamp']-target,[(round(c['source_elevation_m'],3),round(c['variance_m2'],3),round(c['observation_age_s'],3),c['quality_rejected']) for c in frame['cells']])
