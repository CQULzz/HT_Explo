from pathlib import Path
import hashlib, json, os, signal, subprocess, tarfile, time, shutil

ROOT=Path('/home/lzz/tare_native_campus_20261118')
CASE='native_campus_01'
PACKAGES=['local_planner','terrain_analysis','terrain_analysis_ext','sensor_scan_generation','vehicle_simulator','tare_planner']
TOPICS=['/tf','/tf_static','/clock','/state_estimation','/state_estimation_at_scan','/registered_scan','/velodyne_points','/terrain_map','/terrain_map_ext','/way_point','/path','/cmd_vel','/exploration_finish','/start_exploration','/global_path','/local_path','/exploration_path','/filtered_frontier_cloud','/uncovered_cloud','/coverage_cloud','/exploring_cell_vis_cloud','/runtime','/runtime_breakdown']

def freeze():
    files=[]
    for package in PACKAGES:
        base=ROOT/'project/src'/package
        files += [p for p in base.rglob('*') if p.is_file() and p.suffix in ['.cpp','.h','.hpp','.yaml','.launch','.xacro','.sdf','.world','.txt','.xml'] and 'or-tools' not in p.parts]
        files += [p for p in (ROOT/'project/install'/package/'lib').rglob('*') if p.is_file()]
    files += [p for p in (ROOT/'project/src/tare_planner/or-tools/lib').glob('*.so*') if p.is_file()]
    files += [ROOT/n for n in ['env.sh','simulation.launch.py','run.py','observer.py','mission_stop.py','campus.world','recording_qos.yaml','mcap.yaml','PLAN.json']]
    files += [p for p in Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus').rglob('*') if p.is_file()]
    return {str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}

def main():
    for pkg in ['local_planner','vehicle_simulator','tare_planner']:
        prefix=subprocess.check_output(['ros2','pkg','prefix',pkg],text=True).strip()
        assert Path(prefix).resolve()==(ROOT/'project/install'/pkg).resolve(),prefix
    ledger=json.loads((ROOT/'BUDGET.json').read_text())
    assert len(ledger['attempts'])<ledger['maximum_formal_launch_attempts']
    assert shutil.disk_usage(ROOT).free>80*1024**3
    ledger['attempts'].append({'case':CASE,'started_wall':time.time()});(ROOT/'BUDGET.json').write_text(json.dumps(ledger,indent=2))
    out=ROOT/'runs'/CASE;out.mkdir(exist_ok=False);before=freeze()
    (out/'FREEZE.json').write_text(json.dumps(before,indent=2))
    with tarfile.open(out/'frozen_runtime.tar.gz','w:gz',compresslevel=1) as archive:
        for name in before:archive.add(name,arcname=name.lstrip('/'),recursive=False)
    env=os.environ.copy();env.update(DISPLAY=':109');children={};logs={};commands={};codes={}
    def spawn(key,args):
        commands[key]=list(map(str,args));logs[key]=(out/(key+'.log')).open('w');children[key]=subprocess.Popen(commands[key],env=env,stdout=logs[key],stderr=subprocess.STDOUT,start_new_session=True);(out/'COMMANDS.json').write_text(json.dumps(commands,indent=2))
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
    result={'case':CASE,'mode':'upstream_tare_native_aede','started_wall':time.time(),'requested_duration_s':None,'navigation_source_commit':'b6760adb4280b379567c76f4e684ce628e28ef71','cmu_source_commit':'158e67b31b644ed1e8b06eb1d7f70e183cc62591','ht_enabled':False,'reference_config':'native VLP16/0.6m body/2.0mps/campus.yaml; one ROS2 frontier declaration compatibility line; no HT/mapper/model'}
    try:
        spawn('simulation',['ros2','launch',ROOT/'simulation.launch.py'])
        spawn('bag',['ros2','bag','record','-s','mcap','--storage-config-file',ROOT/'mcap.yaml','--qos-profile-overrides-path',ROOT/'recording_qos.yaml','--max-cache-size','268435456','-b','500000000','-o',out/'bag',*TOPICS])
        spawn('observer',['python3',ROOT/'observer.py','--output',out/'observations','--duration','0'])
        started=time.monotonic();dumped=False
        while children['observer'].poll() is None:
            for key in ['simulation','bag']:
                if children[key].poll() is not None:raise RuntimeError(key+' exited early')
            if 'process has died' in (out/'simulation.log').read_text(errors='replace'):raise RuntimeError('Simulation child exited during collection')
            if not dumped and (out/'observations/START.json').exists():
                expected={'localPlanner':'local_planner','pathFollower':'local_planner','tare_planner_node':'tare_planner','vehicleSimulator':'vehicle_simulator'};actual=[]
                for proc in Path('/proc').iterdir():
                    if not proc.name.isdigit():continue
                    try:
                        exe=(proc/'exe').resolve()
                        if exe.name not in expected or b'ROS_DOMAIN_ID=205' not in (proc/'environ').read_bytes().split(b'\0'):continue
                        path=ROOT/'project/install'/expected[exe.name]/'lib'/expected[exe.name]/exe.name
                        assert exe==path.resolve(),str(exe)
                        actual.append({'pid':int(proc.name),'executable':str(exe),'sha256':hashlib.sha256(exe.read_bytes()).hexdigest()})
                    except (FileNotFoundError,ProcessLookupError,PermissionError):continue
                assert {Path(e['executable']).name for e in actual}==set(expected),actual
                (out/'ACTUAL_NAVIGATION.json').write_text(json.dumps(actual,indent=2))
                nodes=subprocess.check_output(['ros2','node','list','--no-daemon','--spin-time','2'],text=True)
                assert 'cupy_to_ht' not in nodes and 'elevation_mapping' not in nodes,nodes
                (out/'NODES.txt').write_text(nodes)
                for node in ['/tare_planner_node','/localPlanner','/pathFollower','/vehicleSimulator','/terrainAnalysis','/terrainAnalysisExt','/robot_state_publisher']:
                    with (out/(node[1:]+'.yaml')).open('w') as file:subprocess.run(['ros2','param','dump','--no-daemon','--spin-time','3',node],stdout=file,stderr=subprocess.STDOUT,env=env,timeout=20)
                dumped=True
            if not (out/'observations/START.json').exists() and time.monotonic()-started>420:raise RuntimeError('Startup readiness deadline')
            if shutil.disk_usage(ROOT).free<40*1024**3:raise RuntimeError('Evidence disk reserve')
            time.sleep(1)
        if children['observer'].returncode:raise RuntimeError('Observer failed')
        summary=json.loads((out/'observations/SUMMARY.json').read_text());result.update(summary=summary,collection_complete=True,mission_complete=summary['mission_complete'],mission_outcome=summary['mission_outcome'])
        stop('bag');stop('simulation');codes['observer']=children['observer'].returncode
    except BaseException as error:
        result.update(error=repr(error),collection_complete=False)
        for key in ['observer','bag','simulation']:stop(key)
    finally:
        result.update(ended_wall=time.time(),exit_codes=codes,freeze_unchanged=before==freeze());(out/'RESULT.json').write_text(json.dumps(result,indent=2))
        for file in logs.values():file.close()
        print(json.dumps(result,indent=2),flush=True)
    if not result['collection_complete'] or not result['freeze_unchanged']:raise RuntimeError('Native attempt failed; data retained')

if __name__=='__main__':
    main()
