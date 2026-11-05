from pathlib import Path
import os,sys,subprocess,time,signal,json,hashlib,datetime,argparse,shutil,re
ap=argparse.ArgumentParser();ap.add_argument('--label',required=True);ap.add_argument('--duration',type=float,default=120);ap.add_argument('--domain',type=int,default=228);ap.add_argument('--runtime',type=Path,default=Path(__file__).parent);ap.add_argument('--project',type=Path,default=Path('/home/lzz/HT_stop_fix_20261104/project'));ap.add_argument('--mapper-workspace',type=Path,default=Path('/home/lzz/my test/ht_cupy_gpu_ws_20261028'));ap.add_argument('--output-root',type=Path);ap.add_argument('--seed',type=int,default=-1);ap.add_argument('--ht-processing-mode',choices=['executor','worker'],default='executor');ap.add_argument('--render-backend',choices=['egl','wsl-d3d12'],default='egl');args=ap.parse_args()
if args.seed < -1 or args.seed > 4294967295:ap.error('seed must be -1 or uint32')
R=args.runtime.resolve();P=args.project.resolve();W=args.mapper_workspace.resolve();out=(args.output_root or R.parent)/args.label;out.mkdir(exist_ok=False)
def hashes():
 files=[]
 for d in [P/'install_real',W/'install_stable/elevation_mapping_cupy',Path('/home/lzz/HT_pcd_sim_20261105/assets')]:files.extend(p for p in d.rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix!='.pyc')
 files.extend(p for p in R.glob('*') if p.is_file())
 return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
frozen=hashes();env=os.environ.copy();env.update(ROS_DOMAIN_ID=str(args.domain),GZ_PARTITION='ht_navfix_'+args.label,HT_SIM_DURATION=str(args.duration))
gazebo_home=out/'gazebo-home';gazebo_home.mkdir();gazebo_env=env.copy();gazebo_env['HOME']=str(gazebo_home)
if args.render_backend=='wsl-d3d12':
 if not env.get('DISPLAY'):raise RuntimeError('wsl-d3d12 requires the WSLg X display')
 gazebo_env.update(GALLIUM_DRIVER='d3d12',MESA_LOADER_DRIVER_OVERRIDE='d3d12',MESA_D3D12_DEFAULT_ADAPTER_NAME='NVIDIA',LD_LIBRARY_PATH='/usr/lib/wsl/lib:'+env.get('LD_LIBRARY_PATH',''))
ogre_log=gazebo_home/'.gz/rendering/ogre2.log'
manifest={'seed':args.seed,'seed_scope':'TARE greedy stream and Gazebo; ROS/GPU scheduling remains nondeterministic','ht_processing_mode':args.ht_processing_mode,'render_backend':args.render_backend,'gazebo_display':env.get('DISPLAY'),'variant':args.label,'requested_duration_sim_s':args.duration,'isolated_ros_domain':args.domain,'wall_start':datetime.datetime.now().astimezone().isoformat(),'project_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=P,text=True).strip(),'frozen_hashes':frozen};(out/'manifest.json').write_text(json.dumps(manifest,indent=2));subprocess.run(['git','diff','HEAD','--binary'],cwd=P,stdout=open(out/'working_tree.patch','wb'),check=True)
cmds={'record':f'ros2 bag record -s mcap --storage-preset-profile zstd_fast --max-cache-size 134217728 --max-bag-duration 300 --disable-keyboard-controls -o {out}/bag /clock /tf /tf_static /sim/ground_truth /sim/cmd_vel /sim/fixposition_odom /sim_evidence/scan /ht_real/odometry /ht_real/traversability /ht_real/ht_reasons /ht_real/ht_evidence /ht_real/ht_runtime /ht_real/ht_performance /ht_real/input_performance /ht_real/input_status /ht_real/runtime_status /ht_real/ht_input_status /ht_real/ht_execution_status /ht_real/ht_follower_status /ht_real/ht_navigation_allowed /ht_real/ht_startup_prior /ht_real/mission_state /ht_real/mission_completed /ht_real/way_point /ht_real/ht_xytheta_path /ht_real/ht_route_goal /ht_real/tare_native_waypoint /ht_real/tare_route_branch /ht_real/tare_coverage_route /ht_real/cmd_vel_stamped /ht_real/stop /ht_real/collision_cloud /ht_real/ht_execution_rejected_edge /ht_real/tare_tsp_order',
'observer':f'/usr/bin/python3 {R}/observe.py {out}','bridge':'ros2 run ros_gz_bridge parameter_bridge /clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock /sim/ground_truth@nav_msgs/msg/Odometry[gz.msgs.Odometry /sim/raw_points/points@sensor_msgs/msg/PointCloud2[gz.msgs.PointCloudPacked /sim/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist','adapter':f'/usr/bin/python3 {R}/sim_adapter.py','mapper':f'python {R}/mapper_strict.py --ros-args -r __node:=elevation_mapping_node -p use_sim_time:=true -p core_param_file:={R}/mapper_core.yaml -p setup_file:={R}/mapper_setup.yaml','navigation':f'ros2 launch ht_scout_bridge scout_real.launch.py use_sim_time:=true run_mode:=drive chassis_command_topic:=/sim/cmd_vel cloud_topic:=/sim/raw_cloud odometry_topic:=/sim/fixposition_odom calibration_file:={R}/candidate_extrinsics.yaml tare_sampling_seed:={args.seed}','gazebo':f'gz sim -s -r {"--headless-rendering" if args.render_backend=="egl" else ""} {('--seed '+str(args.seed)) if args.seed>=0 else ''} -v 2 {R}/scene.sdf'}
ps=[];error=None;started=time.monotonic();resources=open(out/'resources.jsonl','w')
try:
 for label,cmd in cmds.items():
  f=open(out/(label+'.log'),'w');child_env=gazebo_env if label=='gazebo' else env.copy()
  if label=='navigation':child_env['HT_PROCESSING_MODE']=args.ht_processing_mode
  if label=='mapper':child_env['CUPY_STATS_DUMP']=str(out/'mapper_stats.json')
  p=subprocess.Popen(cmd,shell=True,executable='/bin/bash',env=child_env,stdout=f,stderr=subprocess.STDOUT,start_new_session=True);ps.append((label,p))
 (out/'pids.json').write_text(json.dumps({k:p.pid for k,p in ps}));print('Started',args.label,flush=True)
 while not (out/'DONE.json').exists():
  time.sleep(5)
  if (out/'DONE.json').exists():break
  navigation_log=(out/'navigation.log').read_text(errors='replace')
  if '[ERROR]' in navigation_log and 'process has died' in navigation_log:
   raise RuntimeError('ROS launch child exited before collection completed; see navigation.log')
  if args.render_backend=='wsl-d3d12' and ogre_log.exists():
   renderers=re.findall(r'GL_RENDERER = (.+)',ogre_log.read_text(errors='replace'))
   if renderers and not all('D3D12' in x and 'NVIDIA' in x for x in renderers):
    raise RuntimeError('Requested NVIDIA D3D12 renderer was not selected: '+repr(renderers))
  dead=[(k,p.poll()) for k,p in ps if p.poll() is not None]
  if dead:raise RuntimeError(str(dead))
  if time.monotonic()-started>max(300,args.duration*2.2+60):raise RuntimeError('Wall guard reached')
  ids=','.join(str(p.pid) for _,p in ps);resources.write(json.dumps({'wall':time.monotonic()-started,'ps':subprocess.check_output(['ps','-o','pid,pcpu,pmem,rss,args','-p',ids,'--ppid',ids],text=True)})+'\n');resources.flush()
except BaseException as e:error=repr(e)
finally:
 for sig,timeout in [(signal.SIGINT,8),(signal.SIGTERM,3),(signal.SIGKILL,3)]:
  for k,p in reversed(ps):
   if p.poll() is None:
    try:os.killpg(p.pid,sig)
    except ProcessLookupError:pass
  deadline=time.monotonic()+timeout
  for k,p in ps:
   try:p.wait(timeout=max(.01,deadline-time.monotonic()))
   except subprocess.TimeoutExpired:pass
 if ogre_log.exists():shutil.copy2(ogre_log,out/'ogre2.log')
 renderer_text=(out/'ogre2.log').read_text(errors='replace') if (out/'ogre2.log').exists() else ''
 renderers=re.findall(r'GL_RENDERER = (.+)',renderer_text)
 renderer_verified=bool(renderers) and (args.render_backend!='wsl-d3d12' or all('D3D12' in x and 'NVIDIA' in x for x in renderers))
 if not renderer_verified and error is None:error='Renderer log missing or requested backend not verified'
 shutdown_nonzero={k:p.poll() for k,p in ps if p.poll()!=0}
 resources.close();completion=json.loads((out/'DONE.json').read_text()) if (out/'DONE.json').exists() else {};actual_duration=completion.get('elapsed_sim',-1.);full_duration=actual_duration>=args.duration;now=hashes();changed=[k for k,v in frozen.items() if now.get(k)!=v];result={'render_backend':args.render_backend,'actual_gl_renderers':renderers,'renderer_verified':renderer_verified,'managed_shutdown_nonzero':shutdown_nonzero,'error':error,'requested_duration_sim_s':args.duration,'actual_duration_sim_s':actual_duration,'full_requested_duration':full_duration,'full_600_sim_s':args.duration>=600 and full_duration,'failure_stage':None if full_duration else ('startup' if not (out/'READY.json').exists() else 'collection'),'frozen_files_changed':changed,'wall_elapsed':time.monotonic()-started,'exit_codes':{k:p.poll() for k,p in ps}};(out/'RUN_RESULT.json').write_text(json.dumps(result,indent=2));print(result,flush=True)
if error or changed or not full_duration or shutdown_nonzero:sys.exit(1)
