"""Prepare real recorded scans and calibrated poses; no CuPy workspace imports."""
from pathlib import Path
import argparse,gzip,pickle,sqlite3,json,sys,hashlib
from copy import deepcopy
import numpy as np
from scipy.spatial.transform import Rotation
from rclpy.serialization import deserialize_message,serialize_message
from sensor_msgs.msg import PointCloud2
from nav_msgs.msg import Odometry
from tf2_msgs.msg import TFMessage
from sensor_msgs_py.point_cloud2 import read_points_numpy

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'src/ht_scout_bridge'))
from ht_scout_bridge.geometry import load_calibration,self_filter_keep_mask,transform


def stamp(m):return m.header.stamp.sec*10**9+m.header.stamp.nanosec
def matrix(p):return transform([p.position.x,p.position.y,p.position.z],[p.orientation.x,p.orientation.y,p.orientation.z,p.orientation.w])


def main():
    p=argparse.ArgumentParser();p.add_argument('--bag',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
    profile,poi_base,poi_lidar=load_calibration(ROOT/'src/ht_scout_bridge/config/scout_extrinsics.yaml');base_lidar=np.linalg.inv(poi_base)@poi_lidar
    databases=sorted(a.bag.glob('*.db3'),key=lambda x:int(x.stem.split('_')[-1]));odoms=[];statics={}
    for file in databases:
        c=sqlite3.connect('file:'+str(file)+'?mode=ro&immutable=1',uri=True)
        topics={i:name for i,name in c.execute('select id,name from topics') if name in ['/state_estimation','/tf_static']}
        query=','.join('?' for _ in topics)
        for tid,data in c.execute(f'select topic_id,data from messages where topic_id in ({query}) order by timestamp',tuple(topics)):
            if topics[tid]=='/state_estimation':odoms.append(deserialize_message(data,Odometry))
            else:
                for t in deserialize_message(data,TFMessage).transforms:
                    tr,q=t.transform.translation,t.transform.rotation
                    key=(t.header.frame_id,t.child_frame_id)
                    value=transform([tr.x,tr.y,tr.z],[q.x,q.y,q.z,q.w])
                    if key in statics:np.testing.assert_allclose(statics[key],value,atol=1e-9)
                    statics[key]=value
        c.close()
    np.testing.assert_allclose(statics[('FP_POI','rslidar')],poi_lidar,atol=1e-8)
    np.testing.assert_allclose(statics[('FP_POI','scout_chassis_link')],poi_base,atol=1e-8)
    odoms.sort(key=stamp);body=[]
    for m in odoms:
        assert m.header.frame_id=='map' and m.child_frame_id=='rslidar'
        b=matrix(m.pose.pose)@np.linalg.inv(base_lidar);out=Odometry();out.header=deepcopy(m.header);out.child_frame_id='base_link'
        out.pose.pose.position.x,out.pose.pose.position.y,out.pose.pose.position.z=map(float,b[:3,3])
        out.pose.pose.orientation.x,out.pose.pose.orientation.y,out.pose.pose.orientation.z,out.pose.pose.orientation.w=map(float,Rotation.from_matrix(b[:3,:3]).as_quat())
        # Pose-only derived aid for HT height reference. No valid twist is
        # asserted; these messages are never sent to a vehicle controller.
        out.twist.twist.linear.x=out.twist.twist.linear.y=out.twist.twist.linear.z=float('nan')
        out.twist.twist.angular.x=out.twist.twist.angular.y=out.twist.twist.angular.z=float('nan')
        body.append(serialize_message(out))
    old={'enabled':True,'min_xyz':[-1,-.7,-.9],'max_xyz':[.2,.7,.2]};times=np.array([stamp(m) for m in odoms],np.int64)
    header={'format':'recorded_lidar_rebuild_v1','odometry':body,'original_lidar_odometry':[serialize_message(m) for m in odoms],
            'pose_scope':'Derived base_link poses only; NaN twist explicitly unmeasured; not control odometry',
            'source':str(a.bag),'scan_sampling_s':.5,'recorded_static_calibration_matches':True,
            'source_calibration':profile,'base_from_lidar':base_lidar.tolist()}
    frames=[];next_receipt=None;skipped=0
    with gzip.open(a.output/'selected_raw_inputs.pkl.gz','wb',compresslevel=3) as stream:
        pickle.dump(header,stream,protocol=5)
        for file in databases:
            c=sqlite3.connect('file:'+str(file)+'?mode=ro&immutable=1',uri=True);topic=c.execute("select id from topics where name='/rslidar_points'").fetchone()[0]
            start=c.execute('select timestamp from messages where topic_id=? order by timestamp limit 1',(topic,)).fetchone()[0]
            end=c.execute('select timestamp from messages where topic_id=? order by timestamp desc limit 1',(topic,)).fetchone()[0]
            if next_receipt is None:next_receipt=start
            while next_receipt<=end:
                receipt,data=c.execute('select timestamp,data from messages where topic_id=? and timestamp>=? order by timestamp limit 1',(topic,next_receipt)).fetchone();next_receipt+=500_000_000
                m=deserialize_message(data,PointCloud2);assert m.header.frame_id=='rslidar'
                j=int(np.argmin(abs(times-stamp(m))));skew=(times[j]-stamp(m))/1e9
                if abs(skew)>.05:skipped+=1;continue
                xyz=read_points_numpy(m,field_names=('x','y','z'),skip_nans=False).reshape(-1,3)
                before=self_filter_keep_mask(xyz,old);after=self_filter_keep_mask(xyz,profile['lidar_self_filter'],base_lidar)
                t=matrix(odoms[j].pose.pose)
                record={'stamp_ns':stamp(m),'receipt_ns':receipt,'raw_cdr':data,'before':before,'after':after,
                        'R':t[:3,:3].astype(np.float32),'t':t[:3,3].astype(np.float32),'pose_skew_s':skew}
                pickle.dump(record,stream,protocol=5)
                frames.append({'stamp_ns':stamp(m),'pose_skew_s':skew,'raw_cdr_sha256':hashlib.sha256(data).hexdigest()})
            c.close();print(file.name,len(frames),'prepared',flush=True)
    (a.output/'INDEX.json').write_text(json.dumps({'accepted_scans':len(frames),'skipped_pose_skew':skipped,'odometry':len(body),'recorded_static_calibration_matches':True,'frames':frames},indent=2)+'\n')


if __name__=='__main__':main()
