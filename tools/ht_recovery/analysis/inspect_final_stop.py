from pathlib import Path
import json,math,sys,collections,csv
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from std_msgs.msg import String
ROOT=Path('/home/lzz/ht_recovery_20261111');RUN=ROOT/'runs/cmu_recovery_300s_02';OUT=ROOT/'analysis/final_stop';OUT.mkdir(exist_ok=False)
sys.path.insert(0,'/home/lzz/HT_Explo_recovery_20261111/tools/cmu_minimal');from audit_commands import decode
sys.path.insert(0,'/home/lzz/HT_Explo_recovery_20261111/tools/ht_cupy_bridge');from elevation_quality import preprocess_elevation
rows=list(csv.DictReader((RUN/'observations/metrics.csv').open()));end=float(rows[-1]['time']);reader=rosbag2_py.SequentialReader();reader.open(rosbag2_py.StorageOptions(uri=str(RUN/'bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''));reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/elevation_mapping/elevation_map_raw','/ht_minimal/command_audit']));reader.seek(int((end-3)*1e9));maps=collections.OrderedDict();sources=collections.OrderedDict();chosen=None
while reader.has_next():
 topic,data,received=reader.read_next()
 if topic=='/ht_minimal/command_audit':
  d=json.loads(deserialize_message(data,String).data)
  if d['time']<=end and d['reason']=='HT_OCCUPIED':chosen=d
 else:
  m=deserialize_message(data,GridMap);k=round(m.header.stamp.sec+m.header.stamp.nanosec*1e-9,6);table=maps if topic=='/ht_traversability/global_local' else sources;table[k]=(m,data)
assert chosen is not None
msg,cdr=maps[round(chosen['map_stamp'],6)];(OUT/'global_local.cdr').write_bytes(cdr);m=decode(msg);r=int(math.floor(m['rows']/2-(chosen['x']-m['cx'])/m['res']));c=int(math.floor(m['cols']/2-(chosen['y']-m['cy'])/m['res']));channel=int(math.floor((math.atan2(math.sin(chosen['yaw']),math.cos(chosen['yaw']))+2*math.pi)/(math.pi/4)+.5))%8
layers={name:np.roll(np.asarray(a.data).reshape((m['rows'],m['cols']),order='F'),(-msg.outer_start_index,-msg.inner_start_index),(0,1)) for name,a in zip(msg.layers,msg.data)}
rr,cc=np.where(layers['ht_obstacle']>=.5);use=np.hypot((rr-r)*m['res'],(cc-c)*m['res'])<=.45+math.sqrt(2)*m['res'];rr,cc=rr[use],cc[use];xx=m['cx']+(m['rows']/2-rr-.5)*m['res'];yy=m['cy']+(m['cols']/2-cc-.5)*m['res'];cells=[];source=sources.get(round(chosen['map_stamp'],6))
if source:
 raw,rawcdr=source;(OUT/'elevation_source.cdr').write_bytes(rawcdr);nx=round(raw.info.length_x/raw.info.resolution);ny=round(raw.info.length_y/raw.info.resolution);arr={name:np.roll(np.asarray(a.data).reshape((nx,ny),order='F'),(-raw.outer_start_index,-raw.inner_start_index),(0,1)) for name,a in zip(raw.layers,raw.data)};quality=preprocess_elevation(arr['elevation'],arr['variance'],raw.info.resolution,backend='numpy',denoise=False)
 for x,y in zip(xx,yy):
  ii=round(raw.info.pose.position.x/raw.info.resolution)+nx//2-round(x/raw.info.resolution);jj=round(raw.info.pose.position.y/raw.info.resolution)+ny//2-round(y/raw.info.resolution)
  if 0<=ii<nx and 0<=jj<ny:cells.append({'xy':[x,y],'height':float(arr['elevation'][ii,jj]),'variance_m2':float(arr['variance'][ii,jj]),'observation_age_s':float(arr['observation_age'][ii,jj]),'source_quality_rejected':bool(quality.rejected_mask[ii,jj])})
record={'audit':chosen,'selected_channel':channel,'eight_scores':m['scores'][:,r,c].astype(float).tolist(),'inflated_occupied':bool(m['occupied'][r,c]),'missing':bool(m['missing'][r,c]),'context':float(m['valid'][r,c]),'raw_occupied_cells_influencing_pose':len(rr),'source_map_exact_stamp_matched':source is not None,'source_cells':cells,'source_cells_variance_gt_025':sum(x['variance_m2']>.25 for x in cells),'source_cells_quality_rejected':sum(x['source_quality_rejected'] for x in cells),'scope':'Exact final rejected command map and matching raw elevation source, NumPy reference quality filter. Explains map rejection evidence, not physical obstacle truth.'}
(OUT/'RESULT.json').write_text(json.dumps(record,indent=2));print(json.dumps(record,indent=2))
