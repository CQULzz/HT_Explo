"""Read recorded candidate clouds; no navigation nodes or parameter changes."""
import argparse,csv,json,re
from collections import deque
from pathlib import Path
import numpy as np
import cv2
import rosbag2_py
from rclpy.serialization import deserialize_message
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points
from nav_msgs.msg import Odometry,Path as RosPath
from std_msgs.msg import String
from grid_map_msgs.msg import GridMap

def extract(trial,output,until):
    origin=json.loads((trial/'current/measurement_started.json').read_text())['wall_time']
    profiles=[]
    for line in (trial/'current/tare.log').read_text().splitlines():
        m=re.search(r'\[(\d+\.\d+)\].*HT_REPRESENTATION_PROFILE global_ms=([\d.]+) viewpoints_ms=([\d.]+) keypose_ms=([\d.]+) coverage_ms=([\d.]+) covered_areas_ms=([\d.]+)',line)
        if m:
            profiles.append((float(m[1])-origin,float(m[1])-origin-sum(float(m[j]) for j in (4,5,6))/1000))
    types={'/viewpoint_vis_cloud':PointCloud2,'/viewpoint_in_collision_cloud_':PointCloud2,
           '/collision_cloud':PointCloud2,'/state_estimation_at_scan':Odometry,
           '/tare_tsp_order':String,'/tare_coverage_route':RosPath,
           '/ht_traversability/global_local':GridMap}
    r=rosbag2_py.SequentialReader()
    r.open(rosbag2_py.StorageOptions(uri=str(trial/'evidence_bag'),storage_id='mcap'),rosbag2_py.ConverterOptions('',''))
    r.set_filter(rosbag2_py.StorageFilter(topics=list(types)))
    rows=[];pose={};clouds={};last={};route=[];global_route=[];latest_map=None;terrain={};maps=deque(maxlen=50)
    while r.has_next():
        topic,raw,t=r.read_next();sec=t/1e9-origin
        if sec>until:break
        msg=deserialize_message(raw,types[topic])
        if isinstance(msg,GridMap):
            n=round(msg.info.length_x/msg.info.resolution);m=round(msg.info.length_y/msg.info.resolution)
            layers={name:np.roll(np.asarray(msg.data[i].data,np.float32).reshape((n,m),order='F'),
                      (-msg.outer_start_index,-msg.inner_start_index),(0,1)) for i,name in enumerate(msg.layers)}
            res=msg.info.resolution;rad=int(np.ceil(.6/res)+1)
            di,dj=np.mgrid[-rad:rad+1,-rad:rad+1]
            kernel=(np.hypot(di,dj)*res<=.6+np.sqrt(2)*res).astype(np.uint8)
            body=cv2.dilate((layers['ht_obstacle']>=.5).astype(np.uint8),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=0).astype(bool)
            layers['computed_body_blocked']=body
            eligible=(layers['ht_observation_valid']>=.5)&(layers['ht_valid']>=.5)
            considered=eligible|body
            ii,jj=np.indices((n,m));xx=msg.info.pose.position.x+(n*.5-ii-.5)*res;yy=msg.info.pose.position.y+(m*.5-jj-.5)*res
            keys=np.column_stack((np.floor(xx[considered]/.2),np.floor(yy[considered]/.2))).astype(np.int32)
            unique,inv=np.unique(keys,axis=0,return_inverse=True)
            good=eligible & ~body & (np.max(np.stack([layers[f'ht_dir_{k}'] for k in range(8)]),axis=0)>=.5)
            values=np.zeros(len(unique),dtype=np.uint8);np.maximum.at(values,inv,good[considered].astype(np.uint8))
            for k,v in zip(unique,values):terrain[tuple(k)]=int(v)
            latest_map=(sec,layers,np.array([msg.info.pose.position.x,msg.info.pose.position.y,msg.info.resolution]))
            maps.append((*latest_map,np.asarray([[*k,v] for k,v in sorted(terrain.items())],dtype=np.int32)))
        elif isinstance(msg,Odometry):
            pose=dict(x=msg.pose.pose.position.x,y=msg.pose.pose.position.y,z=msg.pose.pose.position.z,odom_bag_t_s=sec)
        elif isinstance(msg,String):
            global_route=msg.data
        elif isinstance(msg,RosPath):
            value=[[p.pose.position.x,p.pose.position.y,p.pose.position.z] for p in msg.poses]
            if topic=='/tare_tsp_order':global_route=value
            else:route=value
        else:
            pts=read_points(msg,field_names=('x','y','z','intensity'),skip_nans=True)
            a=np.column_stack([pts[n] for n in ('x','y','z','intensity')]).astype(float)
            last[topic]=(sec,a)
            if topic!='/viewpoint_vis_cloud' or sec<0:continue
            unvisited=a[:,3]>=0
            gain=np.floor(a[unvisited,3]).astype(int)
            row={'t_s':sec,**pose,'candidates':len(a),'unvisited':int(unvisited.sum()),
                 'visited':int((~unvisited).sum()),'gain_gt40':int((gain>40).sum()),
                 'max_unvisited_gain':int(gain.max()) if len(gain) else 0,
                 'published_tsp_order_latest':global_route,'local_route_nodes_latest':len(route)}
            for i,n in enumerate('xyz'):
                row[n+'_min']=float(a[:,i].min()) if len(a) else None
                row[n+'_max']=float(a[:,i].max()) if len(a) else None
            for k,(s,c) in last.items():row[k.strip('/')+'_latest_count']=len(c)
            rows.append(row)
            key=f'frame_{len(rows):04d}'
            clouds[key]=a.astype(np.float32)
            if '/collision_cloud' in last:clouds[key+'_collision']=last['/collision_cloud'][1].astype(np.float32)
            if '/viewpoint_in_collision_cloud_' in last:clouds[key+'_collision_viewpoints']=last['/viewpoint_in_collision_cloud_'][1].astype(np.float32)
            if latest_map:
                s,layers,geometry=latest_map
                row['latest_ht_bag_t_s']=s
                clouds[key+'_ht_geometry']=geometry
                for name in ['ht_valid','ht_obstacle','ht_observation_valid','computed_body_blocked']+[f'ht_dir_{i}' for i in range(8)]:
                    clouds[key+'_'+name]=layers[name]
                clouds[key+'_computed_terrain_history']=np.asarray([[*k,v] for k,v in sorted(terrain.items())],dtype=np.int32)
                profile=min(profiles,key=lambda v:abs(v[0]-sec)) if profiles else None
                if profile and 0<=sec-profile[0]<.3:
                    row['estimated_viewpoint_end_t_s']=profile[1]
                    prior=[v for v in maps if v[0]<=profile[1]]
                    if prior:
                        s,ls,g,h=prior[-1]
                        row['gate_ht_bag_t_s']=s
                        clouds[key+'_gate_ht_geometry']=g
                        clouds[key+'_gate_computed_terrain_history']=h
                        for name in ['computed_body_blocked','ht_valid']+[f'ht_dir_{k}' for k in range(8)]:clouds[key+'_gate_'+name]=ls[name]
    output.mkdir(parents=True,exist_ok=True)
    fields=list(dict.fromkeys(k for row in rows for k in row))
    with (output/'candidates.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
    np.savez_compressed(output/'candidate_frames.npz',**clouds)
    (output/'metadata.json').write_text(json.dumps({'trial':str(trial.resolve()),'origin_wall_time':origin,
        'until_s':until,'rows':len(rows),'scope':'Published candidate cloud only; intensity>=0 encodes raw surface gain+array_index/10000, -1 visited. Does not expose frontier gain, preselected virtual coverage or exploring-cell membership. Counts do not reconstruct the actual selection queue. Latest collision/route timestamps may precede cloud. Fields prefixed gate use the latest bag map before viewpoint-phase end estimated from phase timing logs; computed terrain history/footprint mirror the map-frame configuration-score protocol with threshold0.5/radius0.6m. They are not an exact capture of the internal map pointer or all graph state.'},indent=2)+'\n')
    print(json.dumps(rows[:2]+rows[-4:],indent=2))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('trial',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--until',type=float,default=40)
    a=p.parse_args();extract(a.trial,a.output,a.until)
