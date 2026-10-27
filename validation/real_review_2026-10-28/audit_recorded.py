"""Replay trusted stationary evidence, with no devices or navigation nodes."""
from pathlib import Path
import argparse,copy,hashlib,json,pickle,sys,time
from types import SimpleNamespace
import numpy as np
import rclpy
from rclpy.time import Time
from rclpy.serialization import deserialize_message
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/ht_cupy_bridge'))
from cupy_to_ht import CupyToHt

def ns(m):return m.header.stamp.sec*10**9+m.header.stamp.nanosec
def decode(m):return {k:np.asarray(v.data,np.float32).reshape(241,241,order='F') for k,v in zip(m.layers,m.data)}

def main():
    p=argparse.ArgumentParser();p.add_argument('input',type=Path);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    a.output.mkdir(parents=True,exist_ok=False)
    raw=pickle.loads(a.input.read_bytes())
    maps=[deserialize_message(b,GridMap) for b in raw['maps']]
    odoms=[deserialize_message(b,Odometry) for b in raw['odometry']]
    selected=[maps[i] for i in np.linspace(5,len(maps)-2,8,dtype=int)]
    runs=[];outputs=[];last=None
    for enabled in (False,True):
        rclpy.init(args=['--ros-args','-p','ht_device:=cpu','-p','ht_quality_backend:=numpy',
            '-p','surface_sensor_ground_offset_m:=0.23479','-p','odometry_child_frame:=base_link',
            '-p','ht_small_hole_repair:='+str(enabled).lower()])
        n=CupyToHt();received=[];clock=[ns(selected[0])]
        n.get_clock=lambda:SimpleNamespace(now=lambda:Time(nanoseconds=clock[0]))
        class Capture:
            def publish(self,m):received.append(m)
            def get_subscription_count(self):return 0
        n.pub=Capture();n.history_pub=Capture();idx=0;timings=[];frames=[]
        try:
            for m in selected:
                clock[0]=ns(m)+30_000_000
                while idx<len(odoms) and ns(odoms[idx])<=clock[0]:n.on_odometry(odoms[idx]);idx+=1
                t=time.perf_counter();n.on_map(copy.deepcopy(m));timings.append(time.perf_counter()-t)
            assert len(received)==8
            for result in received:
                h=decode(result);pose=min(odoms,key=lambda x:abs(ns(x)-ns(result)))
                r=result.info.resolution;ii,jj=np.indices((241,241))
                x=result.info.pose.position.x+(120-ii)*r;y=result.info.pose.position.y+(120-jj)*r
                body=(x-pose.pose.pose.position.x)**2+(y-pose.pose.pose.position.y)**2<=.6**2
                physical=h['ht_observation_valid']>=.5;context=h['ht_valid']>=.5;obstacle=h['ht_obstacle']>=.5
                frames.append(dict(stamp_ns=ns(result),body_cells=int(body.sum()),physical_unknown=int((body&~physical).sum()),
                    context_invalid=int((body&~context).sum()),obstacle_cells=int((body&obstacle).sum()),
                    finite_terrain=int(np.isfinite(h['ht_elevation']).sum()),eligible_terrain=int((physical&context&np.isfinite(h['ht_elevation'])).sum()),
                    interpolated=int((h.get('ht_interpolated',np.zeros_like(x))>=.5).sum()),
                    pose_delta_s=(ns(pose)-ns(result))/1e9))
                last=(h,x,y,pose)
            runs.append(dict(interpolation=enabled,frames=frames,callback_mean_s=float(np.mean(timings))))
            outputs.append(received)
        finally:n.destroy_node();rclpy.try_shutdown()
    for before,after in zip(*outputs):
        assert before.header==after.header and before.info==after.info
        u,v=decode(before),decode(after)
        for k in ['ht_valid','ht_observation_valid','ht_obstacle']:np.testing.assert_array_equal(u[k],v[k])
        mask=np.isfinite(u['ht_elevation']);np.testing.assert_array_equal(u['ht_elevation'][mask],v['ht_elevation'][mask])
    source_hash=hashlib.sha256(a.input.read_bytes()).hexdigest()
    report=dict(scope='Eight identical saved stationary frames. CPU/NumPy replay on review host, controlled recorded clock; not a Jetson timing or vehicle-motion acceptance.',
        source=str(a.input),source_sha256=source_hash,source_maps=len(maps),source_odometry=len(odoms),runs=runs,
        support_and_obstacle_masks_equal=True,existing_finite_heights_equal=True,
        weights_sha256=hashlib.sha256((ROOT/'tools/ht_cupy_bridge/student_best_epoch_weights.pth').read_bytes()).hexdigest())
    (a.output/'audit.json').write_text(json.dumps(report,indent=2)+'\n')
    h,x,y,pose=last;np.savez_compressed(a.output/'last_snapshot.npz',x=x,y=y,robot=[pose.pose.pose.position.x,pose.pose.pose.position.y],**h)
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Circle
    fig,axes=plt.subplots(1,3,figsize=(13,4.5))
    fields=[('Physical support',h['ht_observation_valid']),('HT context validity',h['ht_valid']),('Finite terrain height',np.isfinite(h['ht_elevation']).astype(float))]
    for ax,(label,values) in zip(axes,fields):
        ax.pcolormesh(x,y,values,cmap='RdYlGn',vmin=0,vmax=1,shading='nearest')
        ax.add_patch(Circle((pose.pose.pose.position.x,pose.pose.pose.position.y),.6,fill=False,color='white',linewidth=2))
        ax.plot(pose.pose.pose.position.x,pose.pose.pose.position.y,'bo',markersize=4);ax.set(title=label,xlabel='map X / m',ylabel='map Y / m',aspect='equal')
    fig.suptitle('Saved real-input frame: white circle = 0.6 m body check; interpolation does not expand support')
    fig.tight_layout();fig.savefig(a.output/'support_audit.png',dpi=160);plt.close(fig)
    print(json.dumps({'source_maps':len(maps),'runs':[{'interpolation':v['interpolation'],'last_frame':v['frames'][-1]} for v in runs]},indent=2))

if __name__=='__main__':main()
