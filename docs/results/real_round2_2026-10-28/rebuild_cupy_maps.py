"""Independent CuPy producer: reads serialized inputs, writes native GridMaps.

Run with the separate CuPy package installed/on PYTHONPATH. Imports no HT code.
"""
from pathlib import Path
from types import SimpleNamespace
import argparse,gzip,pickle,json,threading,time
import numpy as np
import cupy as cp
from rclpy.serialization import deserialize_message,serialize_message
from rclpy.time import Time
from sensor_msgs.msg import PointCloud2
from sensor_msgs_py.point_cloud2 import read_points_numpy
from elevation_mapping_cupy import ElevationMap,Parameter
from elevation_mapping_cupy.elevation_mapping_ros import ElevationMappingNode


def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True);p.add_argument('--package-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();a.output.mkdir(exist_ok=False,parents=True)
    plugins=a.output/'plugins.yaml';plugins.write_text('min_filter:\n  enable: false\n')
    states={};streams={};summary=[]
    with gzip.open(a.input,'rb') as reader:
        header=pickle.load(reader)
        for key in ['before','after']:
            param=Parameter(use_chainer=False,resolution=.04,map_length=11.64,
                weight_file=str(a.package_dir/'config/core/weights.dat'),plugin_config_file=str(plugins),
                enable_drift_compensation=False,enable_overlap_clearance=False)
            param.subscriber_cfg={'scan':{'data_type':'pointcloud'}};param.update();mapping=ElevationMap(param)
            n=mapping.cell_n-2;assert n==291
            result=[]
            node=SimpleNamespace(map_translation=True,map=mapping,last_integrated_stamp=None,
                map_access_lock=threading.RLock(),map_data=np.empty((n,n),np.float32),map_frame='map',
                publisher_configs={'raw':{'layers':['elevation','variance','observation_age'],'basic_layers':['elevation']}},
                map_publishers={'raw':SimpleNamespace(publish=result.append)})
            states[key]=(mapping,node,result);streams[key]=[]
            scalar_parameters={k:v for k,v in vars(param).items() if isinstance(v,(str,int,float,bool))}
            (a.output/(key+'_parameters.json')).write_text(json.dumps(scalar_parameters,indent=2)+'\n')
        index=0;first=None;last=None
        while True:
            try:r=pickle.load(reader)
            except EOFError:break
            source=deserialize_message(r['raw_cdr'],PointCloud2);xyz=read_points_numpy(source,field_names=('x','y','z'),skip_nans=False).reshape(-1,3)
            stamp=r['stamp_ns']/1e9;first=stamp if first is None else first
            row={'index':index,'source_stamp_ns':r['stamp_ns'],'pose_skew_s':r['pose_skew_s']}
            for key,(mapping,node,results) in states.items():
                started=time.perf_counter();mapping.move_to(r['t'].copy(),r['R'].copy())
                if last is not None:
                    mapping.param.time_interval=stamp-last;mapping.update_time();mapping.update_variance()
                mapping.input_pointcloud(xyz[r[key]],['x','y','z'],r['R'].copy(),r['t'].copy(),0.,0.,observation_stamp=stamp)
                if index%2==0:
                    node.last_integrated_stamp=Time(nanoseconds=r['stamp_ns']);ElevationMappingNode.publish_map(node,'raw')
                    msg=results.pop();assert msg.layers==['elevation','variance','observation_age']
                    streams[key].append(serialize_message(msg))
                cp.cuda.get_current_stream().synchronize()
                row[key+'_s']=time.perf_counter()-started
            summary.append(row);last=stamp;index+=1
            if index%20==0:print('CuPy real scans',index,flush=True)
    for key,maps in streams.items():
        (a.output/(key+'_native_maps.pkl')).write_bytes(pickle.dumps({'maps':maps,'odometry':header['odometry']},protocol=5))
    (a.output/'SUMMARY.json').write_text(json.dumps({'scope':'Independent GPU CuPy rebuild from original sampled scans; not simulation or vehicle driving','scans':index,'maps_per_variant':{k:len(v) for k,v in streams.items()},'duration_s':last-first,'resolution':.04,'published_shape':[291,291],'source_time_age':True,'pose_scope':header['pose_scope'],'drift_compensation':False,'overlap_clearance':False,'rows':summary},indent=2)+'\n')


if __name__=='__main__':main()
