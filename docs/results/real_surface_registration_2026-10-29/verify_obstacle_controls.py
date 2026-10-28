import torch
exec(open('verify_mapper_registration.py').read().split('for height in [0.')[0])
# Existing features are explicitly present from initialization. New features
# have separate latency traces, so perfect-pose equivalence cannot hide them.
rows=[];latencies=[]
for height in [.02,.05,.10,.20,.50]:
 pts=ground.copy();feature=((pts[:,0]>.65)&(pts[:,0]<.95)&(abs(pts[:,1])<.2));pts[feature,2]+=height
 a=create(False);b=create(True)
 for scan in range(4):
  for m in [a,b]:m.input_pointcloud(pts.copy(),['x','y','z'],np.eye(3),np.zeros(3),0.,0.,observation_stamp=100.+scan*.1)
 a.input_pointcloud(pts.copy(),['x','y','z'],np.eye(3),np.zeros(3),0.,0.,observation_stamp=101.)
 b.input_pointcloud(pts.copy(),['x','y','z'],R.copy(),t.copy(),0.,0.,observation_stamp=101.)
 ga=cp.asnumpy(a.elevation_map);gb=cp.asnumpy(b.elevation_map);use=(ga[2]>.5)&(gb[2]>.5);err=gb[0,use]-ga[0,use]
 row={'height_m':height,'existing_feature_peak_m':float(np.max(gb[0,use]+.75)),'perfect_peak_m':float(np.max(ga[0,use]+.75)),'p99_error_m':float(np.quantile(abs(err),.99)),'status':b.last_surface_registration['status']};rows.append(row);print('existing',row,flush=True);assert abs(row['existing_feature_peak_m']-height)<.003 and row['p99_error_m']<.003
 # Same scan stream/cadence with a sudden new feature, explicitly report
 # baseline latency, rather than assert that rigid geometry solves old gating.
 maps=[create(False),create(True)]
 for scan in range(4):
  for m in maps:m.input_pointcloud(ground.copy(),['x','y','z'],np.eye(3),np.zeros(3),0.,0.,observation_stamp=100.+scan*.1)
 traces=[[],[]]
 for scan in range(18):
  for k,m in enumerate(maps):
   m.param.time_interval=.1;m.update_time();m.update_variance()
   m.input_pointcloud(pts.copy(),['x','y','z'],(np.eye(3) if k==0 else R.copy()),(np.zeros(3) if k==0 else t.copy()),0.,0.,observation_stamp=101.+scan*.1)
   z=cp.asnumpy(m.elevation_map);valid=z[2]>.5;traces[k].append(float(np.max(z[0,valid]+.75)))
 first=[next((i for i,h in enumerate(v) if h>=height*.5),None) for v in traces];latencies.append({'height_m':height,'scan_interval_s':.1,'perfect_pose_peak_by_scan':traces[0],'registered_peak_by_scan':traces[1],'first_half_height_scan_zero_based':first});print('new feature',height,'first half-height',first,flush=True)
(O/'OBSTACLE_CONTROL_REGRESSION.json').write_text(json.dumps({'scope':'Synthetic actual CUDA fusion, not real terrain traversability labels. Existing-feature preservation and sudden-new-feature latency reported separately.','existing_feature_cases':rows,'new_feature_cases':latencies,'existing_feature_preservation_passed':True,'new_feature_latency_remaining':'Legacy variance gate can delay insertion even with perfect pose; not repaired by pose registration. Existing registered-point execution collision checks are outside this offline study.'},indent=2)+'\n')
