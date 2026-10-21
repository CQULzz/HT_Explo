"""Compare old/new bridge on identical real source frames after the trial ends."""
from array import array
import importlib.util
import json
from pathlib import Path
import sys
import numpy as np
import rclpy
import torch
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/ht_cupy_bridge'))
import cupy_to_ht
from test_source_contract import source_map
folder=Path(sys.argv[1]);files=sorted((folder/'current/inference_context').glob('*.npz'))
spec=importlib.util.spec_from_file_location('old_bridge',Path(__file__).with_name('cupy_to_ht_before.py'))
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old);old.__file__=cupy_to_ht.__file__
rclpy.init();a=old.CupyToHt();b=cupy_to_ht.CupyToHt();results=[]
try:
    for path in [files[0],files[len(files)//2],files[-1]]:
        messages=[[],[]]
        with np.load(path) as sample:
            m=source_map();stamp=float(sample['source_stamp']);m.header.stamp.sec=int(stamp)
            m.header.stamp.nanosec=round((stamp-int(stamp))*1e9)
            cx,cy,res=map(float,sample['source_geometry'])
            m.info.pose.position.x=cx;m.info.pose.position.y=cy
            m.info.resolution=res;m.info.length_x=m.info.length_y=291*res
            for layer,key in zip(m.data,('source_elevation','source_variance','source_observation_age')):
                layer.data=array('f',sample[key].flatten(order='F').tobytes())
            for i,n in enumerate((a,b)):
                n.pub=type('P',(),{'publish':lambda _,msg,i=i:messages[i].append(msg)})()
                n.on_map(m)
            assert len(messages[0])==len(messages[1])==1
            x,y=messages[0][0],messages[1][0]
            assert x.info==y.info and x.layers==y.layers
            for xx,yy in zip(x.data,y.data):
                assert xx.layout==yy.layout
                np.testing.assert_array_equal(np.asarray(xx.data),np.asarray(yy.data))
            # Also recompute the actual recorded network context; history replay
            # above compares two bridges, not a full recorded odometry replay.
            with torch.inference_mode():
                tensor=torch.from_numpy(sample['height'][None,None]).contiguous(memory_format=torch.channels_last)
                p=torch.softmax(b.model(tensor),dim=2)[0,:,1].numpy()
            p[:,sample['occupied']]=0.
            difference=float(np.max(np.abs(p-sample['probabilities'])))
            np.testing.assert_allclose(p,sample['probabilities'],atol=1e-6,rtol=0)
            results.append(dict(source=str(path),published_layers=len(x.layers),
                                old_new_layers_exact=True,recorded_model_max_abs_difference=difference))
finally:a.destroy_node();b.destroy_node();rclpy.try_shutdown()
Path(__file__).with_name('recorded_input_checks.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
