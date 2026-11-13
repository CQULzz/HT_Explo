#!/usr/bin/env python3
import os,signal,subprocess,json,time,hashlib,argparse,tarfile
from pathlib import Path
ROOT=Path('/home/lzz/ht_execution_300s_20261113');PROJECT=Path('/home/lzz/HT_Explo_execution_20261113');PY=ROOT/'venv/bin/python'
TOPICS=['/tf','/tf_static','/clock','/state_estimation','/state_estimation_at_scan','/registered_scan','/sensor_scan','/terrain_map','/terrain_map_ext','/way_point','/path','/cmd_vel','/exploration_finish','/start_exploration','/global_path','/local_path','/exploration_path','/elevation_mapping/elevation_map_raw','/ht_traversability/global_local','/ht_performance','/ht_runtime','/ht_reasons','/ht_minimal/localPlanner','/ht_minimal/pathFollower','/ht_minimal/command_audit','/ht_minimal/path_rejection','/ht_minimal/command_projection','/navigation_boundary','/sensor_coverage_planner/coverage_boundary','/ht_minimal/local_selection','/free_paths','/ht_minimal/recovery','/ht_minimal/recovery_path']

def freeze():
 files=[]
 for base in [PROJECT/'src/cmu_local_planner_ht',PROJECT/'tools/ht_cupy_bridge',PROJECT/'tools/ht_height_quality',PROJECT/'tools/cmu_minimal']:
  files += [p for p in base.rglob('*') if p.is_file() and p.suffix in ('.py','.cpp','.hpp','.json','.patch') and '__pycache__' not in p.parts]
 files += [PROJECT/'tools/ht_cupy_bridge/student_best_epoch_weights.pth']
 for base in [ROOT/'runtime',ROOT/'config',ROOT/'common_sensor',ROOT/'mapper_source/elevation_mapping_cupy_2204/elevation_mapping_cupy/script/elevation_mapping_cupy',ROOT/'install_mapper/elevation_mapping_cupy/local/lib/python3.10/dist-packages/elevation_mapping_cupy']:
  files += [p for p in base.rglob('*') if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.nbi','.nbc')]
 for base in [ROOT/'install_native/tare_planner',Path('/home/lzz/ht_execution_300s_20261113/install_gate/cmu_local_planner_ht')]:
  files += [p for p in (base/'lib').rglob('*') if p.is_file() and os.access(p,os.X_OK)]
 files += [ROOT/'install_native/tare_planner/share/tare_planner/indoor.yaml',ROOT/'env.sh',ROOT/'mcap.yaml',ROOT/'mapper_setup_4hz.yaml',ROOT/'source/MAPPER_BASE.json',ROOT/'mapper_source/elevation_mapping_cupy_2204/elevation_mapping_cupy/config/core/weights.dat']
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}

def case(name,scene,duration):
 preflight = "import elevation_mapping_cupy,torch,cupy,grid_map_msgs.msg,rosbag2_py; assert torch.cuda.is_available(); assert '/ht_execution_300s_20261113/install_mapper/' in elevation_mapping_cupy.__file__; print('Isolated mapper preflight passed')"
 subprocess.run([str(PY),'-c',preflight],check=True)
 ledger=json.loads((ROOT/'BUDGET.json').read_text())
 if len(ledger['attempts'])>=ledger['maximum_formal_launch_attempts']:raise RuntimeError('Formal attempt budget exhausted')
 if __import__('shutil').disk_usage(ROOT).free<12*1024**3:raise RuntimeError('Insufficient disk before launch; no attempt consumed')
 ledger['attempts'].append({'name':name,'scene':scene,'wall_time':time.time()});(ROOT/'BUDGET.json').write_text(json.dumps(ledger,indent=2))
 out=ROOT/'runs'/name;out.mkdir(parents=True,exist_ok=False);children={};logs={};commands={};codes={};before=freeze()
 (out/'ENVIRONMENT.json').write_text(json.dumps({key:os.environ.get(key) for key in ['ROS_DOMAIN_ID','ROS_LOCALHOST_ONLY','RMW_IMPLEMENTATION','AMENT_PREFIX_PATH','PYTHONPATH','LD_LIBRARY_PATH','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS']},indent=2))
 (out/'FREEZE.json').write_text(json.dumps(before,indent=2));env=os.environ.copy();env.update(DISPLAY=':88',GAZEBO_MODEL_DATABASE_URI='',GAZEBO_MASTER_URI='http://127.0.0.1:'+str(11516),ROS_LOG_DIR=str(ROOT/'ros_logs'),CUPY_STATS_DUMP=str(out/'mapper_stats.json'),HT_DIAGNOSTICS_DUMP=str(out/'ht_diagnostics.json'),HT_HISTORY_DUMP=str(out/'ht_history.npz'))
 with tarfile.open(out/'frozen_runtime.tar.gz','w:gz') as archive:
  for path in before:archive.add(path,arcname=path.lstrip('/'),recursive=False)
 def spawn(key,args):
  commands[key]=list(map(str,args));logs[key]=(out/(key+'.log')).open('w');children[key]=subprocess.Popen(commands[key],stdout=logs[key],stderr=subprocess.STDOUT,env=env,start_new_session=True)
  (out/'COMMANDS.json').write_text(json.dumps(commands,indent=2))
 def stop(key):
  p=children.get(key)
  if p is None:return
  if p.poll() is None:
   os.killpg(p.pid,signal.SIGINT)
   try:p.wait(timeout=25)
   except subprocess.TimeoutExpired:
    os.killpg(p.pid,signal.SIGTERM)
    try:p.wait(timeout=5)
    except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
  codes[key]=p.returncode
 result={'case':name,'mode':'ht_only','scene':scene,'requested_duration_s':duration,'started_wall':time.time(),
  'project_commit':'7957e72f8e8b921912d6064cfb02eac22c1d9ec3',
  'cmu_commit':'158e67b31b644ed1e8b06eb1d7f70e183cc62591','native_tare_commit':'b6760adb4280b379567c76f4e684ce628e28ef71',
  'scene_manifest':json.loads(Path('/home/lzz/pcd_test_20261110/runtime/SCENE_MANIFEST.json').read_text()) if scene=='user_pcd' else {'scene':'official CMU indoor'}}
 try:
  spawn('simulation',['ros2','launch',str(ROOT/'simulation.launch.py'),'scene:='+scene])
  if scene=='user_pcd':spawn('boundary',['python3',PROJECT/'tools/user_pcd/boundary.py'])
  spawn('bag',['ros2','bag','record','-s','mcap','--storage-config-file',str(ROOT/'mcap.yaml'),'-b','500000000','-o',str(out/'bag'),*TOPICS])
  spawn('mapper',[PY,ROOT/'install_mapper/elevation_mapping_cupy/lib/elevation_mapping_cupy/elevation_mapping_node','--ros-args','-p','core_param_file:=/home/lzz/ht_execution_300s_20261113/config/trial_core.yaml','-p','setup_file:='+str(ROOT/'mapper_setup_4hz.yaml')])
  spawn('model',[PY,PROJECT/'tools/ht_cupy_bridge/cupy_to_ht.py','--ros-args','-p','ht_device:=cuda','-p','ht_torch_threads:=2','-p','ht_processing_mode:=worker','-p','ht_context_backend:=numpy','-p','surface_sensor_ground_offset_m:=0.75','-p','ht_require_observation_variance:=true'])
  spawn('observer',['python3',PROJECT/'tools/cmu_minimal/collect.py','--output',out/'observations','--duration',str(duration),'--require-ht'])
  started=time.monotonic();dumped=False
  while children['observer'].poll() is None:
   for key in (['simulation','bag','mapper','model']+(['boundary'] if scene=='user_pcd' else [])):
    if children[key].poll() is not None:raise RuntimeError(key+' exited early '+str(children[key].returncode))
   text=(out/'simulation.log').read_text(errors='replace')
   if 'process has died' in text:raise RuntimeError('Simulation child exited before collection finished')
   if not dumped and (out/'observations/START.json').exists():
    for node in ['/tare_planner_node','/localPlanner','/pathFollower','/cupy_to_ht_bridge']:
     with (out/(node[1:]+'.yaml')).open('w') as f:
      subprocess.run(['ros2','param','dump','--no-daemon','--spin-time','3',node],stdout=f,stderr=subprocess.STDOUT,env=env,timeout=20)
    dumped=True
   if time.monotonic()-started>duration+150:raise RuntimeError('Observer deadline exceeded')
   time.sleep(1)
  if children['observer'].returncode:raise RuntimeError('Observer failed')
  result['summary']=json.loads((out/'observations/SUMMARY.json').read_text());result['collection_complete']=result['summary']['elapsed_s']>=duration
  result['phase_ended_wall']=time.time()
  # Stop evidence writer before teardown; preserve cleanup errors separately.
  stop('bag');stop('model');stop('mapper');stop('boundary');stop('simulation');codes['observer']=children['observer'].returncode
 except BaseException as exc:
  result['error']=repr(exc);result['collection_complete']=False
  for key in ['observer','bag','model','mapper','boundary','simulation']:stop(key)
 finally:
  result['exit_codes']=codes;result['ended_wall']=time.time();result['freeze_unchanged']=before==freeze()
  (out/'RESULT.json').write_text(json.dumps(result,indent=2));
  for f in logs.values():f.close()
  print(json.dumps(result,indent=2),flush=True)
 if not result.get('collection_complete') or not result['freeze_unchanged']:raise RuntimeError(name+' failed; evidence retained')
 return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--duration',type=float,default=300);p.add_argument('--name',required=True);p.add_argument('--scene',choices=['user_pcd','indoor'],default='user_pcd');a=p.parse_args()
 case(a.name,a.scene,a.duration)
