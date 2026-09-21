#!/usr/bin/env python3
import argparse,json,os,signal,subprocess,sys,time,hashlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(HERE.parent));from run_exploration_suite import shutdown

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True);ap.add_argument('--duration',type=float,default=120);ap.add_argument('--condition',choices=['both','baseline','ht'],default='both');ap.add_argument('--pairs',type=int,default=2);ap.add_argument('--policy',choices=['strict','geometric_fallback'],default='geometric_fallback');ap.add_argument('--weight',type=float,default=1.0);ap.add_argument('--startup-radius',type=float,default=1.2);ap.add_argument('--map-outage-at',type=float);ap.add_argument('--map-outage-duration',type=float,default=5.0);a=ap.parse_args();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 order=[(c,i+1) for i in range(a.pairs) for c in (['baseline','ht'] if i%2==0 else ['ht','baseline'])]
 if a.condition!='both':order=[(c,r) for c,r in order if c==a.condition]
 protocol={'map_outage':{'at_s':a.map_outage_at,'duration_s':a.map_outage_duration} if a.map_outage_at is not None else None,'downward_lidar':os.environ.get('HT_DOWNWARD_LIDAR')=='1','duration_s':a.duration,'order':order,'ht_weight':a.weight,'ht_unknown_policy':a.policy,'ht_startup_radius_m':a.startup_radius,'ht_startup_duration_s':30,'fallback_speed_m_s':.2,'fallback_lookahead_m':.5,'fallback_max_seconds':60,'fallback_max_distance_m':10,'ht_map_timeout_s':3,'student_weights_sha256':hashlib.sha256(Path('/home/lzz/下载/original_scout/mini_25_training/runs/formal/student/best_epoch_weights.pth').read_bytes()).hexdigest(),'lidar_profile':{'vertical_degrees':[-75,15],'vertical_samples':64,'robot_visuals_hidden_from_lidar':True} if os.environ.get('HT_DOWNWARD_LIDAR')=='1' else {'vertical_degrees':[-15,15],'vertical_samples':16},'elevation':{'bin_m':.1,'nearest_support_m':.25,'patch_observed_ratio':.9,'resolution_m':21/513,'rows':291,'columns':291},'speed_m_s':.5,'clock':'wall','ht_elevation_source':'online registered lidar only, no ground-truth elevation input','terrain':json.loads((HERE/'assets/terrain.json').read_text()),'working_tree_diff':subprocess.check_output(['git','diff','HEAD'],cwd=ROOT,text=True),'git_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'scripts_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in HERE.glob('*.py')},'note':'Pilot; simplified kinematic vehicle, geometric exposure proxy, no collision or roll-over truth. Both arms run identical HT inference load.'};(out/'protocol.json').write_text(json.dumps(protocol,indent=2))
 for condition,rep in order:
  case=out/f'{condition}_{rep}';case.mkdir();params={'/**':{'ros__parameters':{'ht_enabled':condition=='ht','ht_directions_calibrated':True,'ht_heading_offset':0.,'ht_channel_order':list(range(8)),'ht_weight':a.weight,'ht_unknown_policy':a.policy,'ht_startup_radius':a.startup_radius,'ht_map_timeout':3.,'kAutoStart':False,'kUseTerrainHeight':True}}};(case/'params.json').write_text(json.dumps(params));env=dict(os.environ,ROS_DOMAIN_ID='86',HT_SNAPSHOT=str(case/'ht_snapshot.npz'),GZ_PARTITION=f'ht_mountain_{os.getpid()}_{condition}_{rep}');ps=[];logs=[];ht=None;paused=False;outage_started=False;outage_events=[]
  def start(cmd,name):
   f=(case/f'{name}.log').open('w');logs.append(f);p=subprocess.Popen(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);ps.append(p);return p
  print('START',condition,rep,flush=True)
  try:
   sim=start(['ros2','launch',str(HERE/'sim.launch.py')],'sim');time.sleep(12)
   ht=start([sys.executable,str(HERE/'live_ht.py')],'ht')
   probe=start([sys.executable,str(HERE/'probe.py'),'--output',str(case),'--duration',str(a.duration)],'probe')
   measurement_start=time.monotonic()+15
   planner_cmd=['ros2','launch','tare_planner','explore_ht.launch.py','scenario:=forest',f'ht_config:={case/"params.json"}']
   if os.environ.get('HT_DEBUG'):
    planner_cmd=['gdb','-batch','-ex','run','-ex','thread apply all bt','--args',str(ROOT/'install/tare_planner/lib/tare_planner/tare_planner_node'),'--ros-args','--params-file',str(ROOT/'install/tare_planner/share/tare_planner/forest.yaml'),'--params-file',str(case/'params.json')]
   planner=start(planner_cmd,'planner')
   deadline=time.monotonic()+a.duration+50
   while probe.poll() is None:
    if any(p.poll() is not None for p in [sim,ht,planner]):raise RuntimeError(f'Required process exited: {case}')
    if time.monotonic()>deadline:raise RuntimeError('Probe timed out')
    elapsed=time.monotonic()-measurement_start
    if condition=='ht' and a.map_outage_at is not None:
     if not outage_started and elapsed>=a.map_outage_at:
      ht.send_signal(signal.SIGSTOP);paused=True;outage_started=True;outage_events.append({'t':elapsed,'event':'pause_ht'})
     if paused and elapsed>=a.map_outage_at+a.map_outage_duration:
      ht.send_signal(signal.SIGCONT);paused=False;outage_events.append({'t':elapsed,'event':'resume_ht'})
    time.sleep(.2)
   if probe.returncode:raise RuntimeError('Probe failed')
   data=json.loads((case/'metrics.json').read_text())
   if not data['final'] or data['samples'][-1]['t']<a.duration-.5 or data['samples'][-1]['scans']<a.duration*3:raise RuntimeError('Incomplete run or insufficient sensor frames')
   print('COMPLETE',condition,rep,data['samples'][-1],flush=True)
  finally:
   if paused and ht is not None and ht.poll() is None:ht.send_signal(signal.SIGCONT)
   if outage_events:(case/'fault_injection.json').write_text(json.dumps(outage_events,indent=2))
   shutdown(ps)
   for f in logs:f.close()
if __name__=='__main__':main()
