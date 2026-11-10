#!/usr/bin/env python3
import os,signal,subprocess,json,time,hashlib,argparse,tarfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=Path('/home/lzz/cmu_real_compare_20261110')
SHARED=Path('/home/lzz/cmu_test_20261110')
OLD=Path('/home/lzz/HT_Explo_review');PY=SHARED/'venv/bin/python'
TOPICS=['/tf','/tf_static','/clock','/state_estimation','/state_estimation_at_scan',
 '/registered_scan','/terrain_map','/terrain_map_ext','/cmd_vel',
 '/elevation_mapping/elevation_map_raw','/ht_real/odometry','/ht_real/exploration_start',
 '/ht_real/traversability','/ht_real/historical_elevation','/ht_real/collision_cloud',
 '/ht_real/way_point','/ht_real/ht_xytheta_path','/ht_real/ht_execution_rejected_edge',
 '/ht_real/ht_navigation_allowed','/ht_real/ht_execution_status','/ht_real/ht_follower_status',
 '/ht_real/mission_state','/ht_real/mission_completed','/ht_real/exploration_finish',
 '/ht_real/ht_startup_prior','/ht_real/ht_runtime','/ht_real/ht_performance','/ht_real/ht_reasons',
 '/ht_real/ht_evidence','/ht_real/tare_native_waypoint','/ht_real/tare_route_branch',
 '/ht_real/tare_coverage_route','/ht_real/tare_tsp_order','/ht_real/global_path',
 '/ht_real/local_path','/ht_real/exploration_path']

def freeze():
 files=list(HERE.glob('*.py'))+list((OLD/'tools/ht_cupy_bridge').glob('*'))
 files+=list((HERE.parent/'cmu_minimal').glob('*.py'))
 files+=list((OLD/'src/tare_planner/src').rglob('*.cpp'))+list((OLD/'src/tare_planner/include').rglob('*.h'))
 files+=list((OLD/'src/ht_scout_bridge/config').glob('*'))+list((SHARED/'common_sensor').glob('*'))
 files += [SHARED/'mapper_setup_4hz.yaml',Path('/home/lzz/cmu_mapper_20261110/config/trial_core.yaml')]
 files+=list((ROOT/'install_old/tare_planner/lib').rglob('*'))
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}

def main():
 p=argparse.ArgumentParser();p.add_argument('--name',required=True);p.add_argument('--duration',type=float,default=600);a=p.parse_args()
 out=ROOT/'runs'/a.name;out.mkdir(parents=True,exist_ok=False)
 children={};logs={};commands={};codes={};before=freeze()
 (out/'FREEZE.json').write_text(json.dumps(before,indent=2))
 with tarfile.open(out/'frozen_runtime.tar.gz','w:gz') as archive:
  for f in before:archive.add(f,arcname=f.lstrip('/'),recursive=False)
 env=os.environ.copy();env.update(DISPLAY=':88',GAZEBO_MODEL_DATABASE_URI='',
  GAZEBO_MASTER_URI='http://127.0.0.1:11503',CUPY_STATS_DUMP=str(out/'mapper_stats.json'),
  HT_DIAGNOSTICS_DUMP=str(out/'ht_diagnostics.json'),HT_HISTORY_DUMP=str(out/'ht_history.npz'))
 def spawn(key,args):
  commands[key]=list(map(str,args));logs[key]=(out/(key+'.log')).open('w')
  children[key]=subprocess.Popen(commands[key],stdout=logs[key],stderr=subprocess.STDOUT,env=env,start_new_session=True)
  (out/'COMMANDS.json').write_text(json.dumps(commands,indent=2))
 def stop(key):
  proc=children.get(key)
  if proc is None:return
  if proc.poll() is None:
   os.killpg(proc.pid,signal.SIGINT)
   try:proc.wait(timeout=25)
   except subprocess.TimeoutExpired:
    os.killpg(proc.pid,signal.SIGTERM)
    try:proc.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(proc.pid,signal.SIGKILL);proc.wait()
  codes[key]=proc.returncode
 result={'old_commit':subprocess.check_output(['git','-C',str(OLD),'rev-parse','HEAD'],text=True).strip(),
  'case':a.name,'requested_duration_s':a.duration,'started_wall':time.time(),
  'adaptations':['sensor pose to base_link: local z=-0.51521m; preserve stamps',
   'sensor_origin_offset=[0,0,0.51521]; surface_ground_offset=0.23479m',
   'CMU shared downward sensor; shared 4Hz elevation mapper; no physical input/command bridge',
   'old follower TwistStamped connects directly to CMU /cmd_vel; no second local controller']}
 try:
  spawn('simulation',['ros2','launch',HERE/'simulation.launch.py'])
  spawn('adapter',['python3',HERE/'adapter.py'])
  spawn('bag',['ros2','bag','record','-s','mcap','--storage-config-file',SHARED/'mcap.yaml','-b','500000000','-o',out/'bag',*TOPICS])
  spawn('mapper',[PY,SHARED/'install_mapper/elevation_mapping_cupy/lib/elevation_mapping_cupy/elevation_mapping_node',
   '--ros-args','-p','core_param_file:=/home/lzz/cmu_mapper_20261110/config/trial_core.yaml',
   '-p','setup_file:='+str(SHARED/'mapper_setup_4hz.yaml')])
  spawn('model',[PY,OLD/'tools/ht_cupy_bridge/cupy_to_ht.py','--ros-args','-r','__ns:=/ht_real',
   '-r','/ht_runtime:=/ht_real/ht_runtime','-r','/ht_performance:=/ht_real/ht_performance',
   '-r','/ht_reasons:=/ht_real/ht_reasons','-r','/ht_evidence:=/ht_real/ht_evidence',
   '-r','/ht_input_status:=/ht_real/ht_input_status',
   '-r','/elevation_mapping/historical_local:=/ht_real/historical_elevation',
   '-p','ht_topic:=/ht_real/traversability','-p','ht_device:=cuda',
   '-p','surface_odometry_topic:=/ht_real/odometry','-p','surface_sensor_ground_offset_m:=0.23479',
   '-p','ht_qualify_evidence:=true','-p','ht_small_hole_repair:=true','-p','ht_small_hole_profile:=moderate'])
  spawn('observer',['python3',HERE/'collect.py','--output',out/'observations','--duration',str(a.duration),'--require-ht',
   '--ros-args','-r','/start_exploration:=/ht_real/exploration_start',
   '-r','/exploration_finish:=/ht_real/exploration_finish','-r','/path:=/ht_real/ht_xytheta_path',
   '-r','/way_point:=/ht_real/way_point','-r','/ht_traversability/global_local:=/ht_real/traversability'])
  started=time.monotonic();dumped=False
  while children['observer'].poll() is None:
   for key in ['simulation','adapter','bag','mapper','model']:
    if children[key].poll() is not None:raise RuntimeError(key+' exited early '+str(children[key].returncode))
   if 'process has died' in (out/'simulation.log').read_text(errors='replace'):raise RuntimeError('Simulation child died before observer finished')
   if not dumped and (out/'observations/START.json').exists():
    for node in ['/ht_real/tare_planner_node','/ht_real/xytheta_follower','/ht_real/cupy_to_ht_bridge']:
     with (out/(node.rsplit('/',1)[-1]+'.yaml')).open('w') as f:
      subprocess.run(['ros2','param','dump',node],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=20)
    dumped=True
   if time.monotonic()-started>a.duration+150:raise RuntimeError('Observer deadline exceeded')
   time.sleep(1)
  if children['observer'].returncode:raise RuntimeError('Observer failed')
  result['summary']=json.loads((out/'observations/SUMMARY.json').read_text())
  result['collection_complete']=result['summary']['elapsed_s']>=a.duration;result['phase_ended_wall']=time.time()
  for key in ['bag','model','mapper','adapter','simulation','observer']:stop(key)
 except BaseException as exc:
  result['error']=repr(exc);result['collection_complete']=False
  for key in ['observer','bag','model','mapper','adapter','simulation']:stop(key)
 finally:
  result.update(exit_codes=codes,ended_wall=time.time(),freeze_unchanged=before==freeze())
  (out/'RESULT.json').write_text(json.dumps(result,indent=2))
  for f in logs.values():f.close()
  print(json.dumps(result,indent=2),flush=True)
 if not result.get('collection_complete') or not result['freeze_unchanged']:raise RuntimeError('Trial failed; all evidence retained')
if __name__=='__main__':main()
