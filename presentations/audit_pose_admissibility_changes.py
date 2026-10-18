#!/usr/bin/env python3
"""Separate HT field changes from pose crossings using recorded full-rate HT maps."""
import argparse
import json
from pathlib import Path

import cv2
import numpy as np
import rosbag2_py
from rclpy.serialization import deserialize_message
from nav_msgs.msg import Odometry
from geometry_msgs.msg import TwistStamped
from std_msgs.msg import String
from grid_map_msgs.msg import GridMap


class Field:
    def __init__(self,m):
        self.stamp=m.header.stamp.sec+m.header.stamp.nanosec*1e-9
        self.res=float(m.info.resolution);self.cx=m.info.pose.position.x;self.cy=m.info.pose.position.y
        n=round(m.info.length_x/self.res);self.n=n
        def layer(name):
            a=np.asarray(m.data[m.layers.index(name)].data,np.float32).reshape((n,n),order='F')
            return np.roll(a,(-m.outer_start_index,-m.inner_start_index),(0,1))
        self.valid=layer('ht_valid')>=.5
        self.p=np.stack([layer(f'ht_dir_{k}') for k in range(8)])
        physical=layer('ht_observation_valid')>=.5 if 'ht_observation_valid' in m.layers else self.valid
        self.physical=physical
        radius=int(np.ceil(.6/self.res)+1);i,j=np.mgrid[-radius:radius+1,-radius:radius+1]
        kernel=(np.hypot(i,j)*self.res<=.6+np.sqrt(2)*self.res).astype('uint8')
        self.unknown=cv2.dilate((~physical).astype('uint8'),kernel,borderType=cv2.BORDER_CONSTANT,borderValue=1)>0
        self.blocked=np.stack([cv2.dilate((self.valid&(p<.5)).astype('uint8'),kernel)>0 for p in self.p])
        self.bi,self.bj=np.nonzero(kernel);self.bi-=radius;self.bj-=radius

    def inspect(self,pose):
        x,y,yaw=pose;k=int(np.floor(yaw/(np.pi/4)+.5))%8
        r=int(np.floor(self.n*.5-(x-self.cx)/self.res));c=int(np.floor(self.n*.5-(y-self.cy)/self.res))
        result=dict(map_stamp=self.stamp,heading_bin=k,row=r,col=c)
        if not(0<=r<self.n and 0<=c<self.n):return dict(result,status='OUTSIDE')
        status='BLOCKED' if self.blocked[k,r,c] else 'UNKNOWN' if self.unknown[r,c] or not self.valid[r,c] else 'KNOWN'
        ii,jj=r+self.bi,c+self.bj;inside=(ii>=0)&(ii<self.n)&(jj>=0)&(jj<self.n)
        result.update(status=status,min_body_p=float(np.nanmin(self.p[k,ii[inside],jj[inside]])))
        reverse_status='BLOCKED' if self.blocked[(k+4)%8,r,c] else 'UNKNOWN' if self.unknown[r,c] or not self.valid[r,c] else 'KNOWN'
        result.update(reverse_status=reverse_status,reversible_pose=status=='KNOWN' and reverse_status=='KNOWN',
                      reversible_heading_pairs=int(sum(not self.blocked[d,r,c] and not self.blocked[d+4,r,c] for d in range(4)))
                      if self.valid[r,c] and not self.unknown[r,c] else 0)
        return result


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('trial',type=Path);ap.add_argument('--bag-file',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--capture-transition',type=Path,help='Save the first same-map heading-bin crossing as a regression fixture')
    ap.add_argument('--capture-map-update',type=Path,help='Save both fields at the first same-world-pose admission change')
    args=ap.parse_args();cv2.setNumThreads(1)
    origin=json.loads((args.trial/'current/measurement_started.json').read_text())['wall_time']
    reader=rosbag2_py.SequentialReader()
    reader.open(rosbag2_py.StorageOptions(uri=str(args.bag_file or args.trial/'evidence_bag'),storage_id='mcap'),
                rosbag2_py.ConverterOptions('',''))
    reader.set_filter(rosbag2_py.StorageFilter(topics=['/ht_traversability/global_local','/state_estimation','/cmd_vel','/ht_follower_status']))
    field=None;pose=None;last_cmd=None;changes=[];return_changes=[];statuses=[];last_status=None;map_count=0
    while reader.has_next():
        topic,data,ns=reader.read_next();time_s=ns/1e9-origin
        if time_s>=600:break
        if topic=='/ht_traversability/global_local':
            new=Field(deserialize_message(data,GridMap));map_count+=1
            if field is not None and pose is not None and time_s>=0:
                a,b=field.inspect(pose),new.inspect(pose)
                if a['status']=='KNOWN' and b['status']=='BLOCKED':
                    changes.append(dict(time_s=time_s,cause='map_update_at_same_pose',pose=pose,before=a,after=b,last_cmd=last_cmd))
                    if args.capture_map_update and not args.capture_map_update.exists():
                        args.capture_map_update.mkdir(parents=True)
                        for label,f in [('before',field),('after',new)]:
                            np.savez_compressed(args.capture_map_update/(label+'.npz'),
                                **{f'ht_ht_dir_{k}':f.p[k] for k in range(8)},
                                ht_ht_valid=f.valid.astype(np.float32),
                                ht_ht_observation_valid=f.physical.astype(np.float32),
                                ht_geometry=[f.cx,f.cy,f.res],ht_stamp=f.stamp,robot=pose)
                        (args.capture_map_update/'transition.json').write_text(json.dumps(changes[-1],indent=2)+'\n')
                if a.get('reversible_pose') and not b.get('reversible_pose'):
                    return_changes.append(dict(time_s=time_s,cause='map_update_at_same_pose',pose=pose,before=a,after=b,last_cmd=last_cmd))
            field=new
        elif topic=='/state_estimation':
            m=deserialize_message(data,Odometry);p=m.pose.pose.position;q=m.pose.pose.orientation
            new=[p.x,p.y,float(np.arctan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z)))]
            if field is not None and pose is not None and time_s>=0:
                a,b=field.inspect(pose),field.inspect(new)
                if a['status']=='KNOWN' and b['status']=='BLOCKED':
                    changes.append(dict(time_s=time_s,cause='pose_update_on_same_map',before_pose=pose,pose=new,before=a,after=b,last_cmd=last_cmd))
                    if args.capture_transition and not args.capture_transition.exists() and a['heading_bin']!=b['heading_bin']:
                        args.capture_transition.parent.mkdir(parents=True,exist_ok=True)
                        np.savez_compressed(args.capture_transition,
                            **{f'ht_ht_dir_{k}':field.p[k] for k in range(8)},
                            ht_ht_valid=field.valid.astype(np.float32),
                            ht_ht_observation_valid=field.physical.astype(np.float32),
                            ht_geometry=[field.cx,field.cy,field.res],ht_stamp=field.stamp,
                            robot=pose,crossed_pose=new,transition_time_s=time_s)
                if a.get('reversible_pose') and not b.get('reversible_pose'):
                    return_changes.append(dict(time_s=time_s,cause='pose_update_on_same_map',before_pose=pose,pose=new,before=a,after=b,last_cmd=last_cmd))
            pose=new
        elif topic=='/cmd_vel':
            m=deserialize_message(data,TwistStamped)
            last_cmd=dict(time_s=time_s,v=m.twist.linear.x,w=m.twist.angular.z)
            if field is not None and pose is not None:
                horizon=max(.2,abs(last_cmd['v'])/.5+.1,abs(last_cmd['w'])/1.2+.1)
                projected=[pose[0]+last_cmd['v']*horizon*np.cos(pose[2]+last_cmd['w']*horizon*.5),
                    pose[1]+last_cmd['v']*horizon*np.sin(pose[2]+last_cmd['w']*horizon*.5),
                    pose[2]+last_cmd['w']*horizon]
                last_cmd.update(recorded_pose=pose,recorded_field_now=field.inspect(pose),
                                constant_command_preview=field.inspect(projected),preview_horizon_s=horizon)
        else:
            s=deserialize_message(data,String).data
            if s!=last_status and time_s>=0:
                statuses.append(dict(time_s=time_s,status=s,pose=pose,field=field.inspect(pose) if field is not None and pose is not None else None))
            last_status=s
    result=dict(source=str(args.trial.resolve()),bag_file=str(args.bag_file) if args.bag_file else None,
        ht_map_messages=map_count,known_to_blocked_changes=changes,return_margin_losses=return_changes,follower_status_changes=statuses,
        caveat='Uses bag reception ordering, not the exact subscriber callback ordering. Raw pose admissibility excludes map freshness/startup prior; reported snapshot rules are the deployed0.5/0.6m/map-frame identity-channel settings. Pose changes and field changes are separated on identical inputs to that comparison.')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(ht_maps=map_count,known_to_blocked=len(changes),changes=changes[-6:],
        blocked_status_events=[r for r in statuses if r['status']=='HT_CURRENT_POSE_BLOCKED'][-4:]),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
