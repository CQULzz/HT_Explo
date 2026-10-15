#!/usr/bin/env python3
"""Run one fresh, simulation-only original-TARE/current-XYtheta pair and rebuild PPT."""
import argparse
import csv
import datetime as dt
import json
import os
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
WORK=ROOT.parent
CMU=Path(os.environ.get('HT_SIM_WS',str(WORK/'autonomous_exploration_development_environment')))
UP=Path(os.environ.get('HT_TARE_BASELINE_WS',str(WORK/'tare_planner_upstream_baseline')))
CUPY=Path(os.environ.get('HT_CUPY_WS',str(WORK/'elevation_mapping_cupy_ws')))
BRIDGE=ROOT/'tools/ht_cupy_bridge'
RESULTS=HERE/'scheduled_results'
LATEST=HERE/'latest_current_vs_upstream.json'
CUDA_LIBS=[Path('/home/lzz/.local/lib/python3.12/site-packages/nvidia/cuda_nvrtc/lib'),
           Path('/home/lzz/.local/lib/python3.12/site-packages/nvidia/cuda_runtime/lib')]
try:
    # Only use the archived user-space 580.173 libraries while the loaded
    # kernel module is still 580.173; a later driver update makes them invalid.
    if '580.173.02' in Path('/proc/driver/nvidia/version').read_text():
        CUDA_LIBS.insert(0, BRIDGE/'vendor/nvidia_580173')
except OSError:
    pass

def q(p):return shlex.quote(str(p))
def source(*prefixes):return ' '.join(f'source {q(p)} &&' for p in prefixes)

class Trial:
    def __init__(self,name,folder,domain):
        self.name=name;self.folder=folder;self.domain=domain;self.processes=[]
        self.env=os.environ.copy()
        self.env.update(ROS_DOMAIN_ID=str(domain),GZ_PARTITION=f'ht_tare_pair_{domain}',
                        ROS_LOCALHOST_ONLY='1',PYTHONUNBUFFERED='1')
        # Keep Gazebo rendering and CuPy on a user-space driver matching the
        # loaded kernel module; CUDA runtime libraries remain independently available.
        self.env['LD_LIBRARY_PATH']=':'.join(str(x) for x in CUDA_LIBS)+':'+self.env.get('LD_LIBRARY_PATH','')
        self.folder.mkdir(parents=True,exist_ok=True)
    def start(self,label,command):
        log=(self.folder/f'{label}.log').open('w')
        proc=subprocess.Popen(['bash','-lc',command],env=self.env,stdout=log,stderr=subprocess.STDOUT,
                              start_new_session=True)
        self.processes.append((label,proc,log))
        print(f'{self.name}: started {label} pid={proc.pid}',flush=True)
        return proc
    def run(self,label,command,timeout):
        logpath=self.folder/f'{label}.log'
        with logpath.open('w') as log:
            p=subprocess.run(['bash','-lc',command],env=self.env,stdout=log,stderr=subprocess.STDOUT,timeout=timeout)
        if p.returncode:
            raise RuntimeError(f'{self.name}: {label} failed ({p.returncode}); see {logpath}')
        return logpath.read_text(errors='replace')
    def check(self):
        dead=[name for name,p,_ in self.processes if p.poll() is not None]
        if dead:raise RuntimeError(f'{self.name}: processes exited early: {dead}')
    def stop(self):
        for label,p,_ in reversed(self.processes):
            if p.poll() is None:
                try:os.killpg(p.pid,signal.SIGINT)
                except ProcessLookupError:pass
        deadline=time.monotonic()+12
        for _,p,log in reversed(self.processes):
            while p.poll() is None and time.monotonic()<deadline:time.sleep(.15)
            if p.poll() is None:
                try:os.killpg(p.pid,signal.SIGTERM)
                except ProcessLookupError:pass
            log.close()
        self.processes.clear()

def preflight():
    needed=[CMU/'install/setup.bash',UP/'install/setup.bash',ROOT/'install_standalone/setup.bash',
            CUPY/'install/setup.bash',BRIDGE/'cmu_xytheta.launch.py',BRIDGE/'cupy_to_ht.py',
            BRIDGE/'ht_trial.yaml',BRIDGE/'assets/lidar_downward.sdf',HERE/'paired_probe.py',
            HERE/'stage_garage_pose.py']
    missing=[str(p) for p in needed if not p.exists()]
    if not (Path('/opt/ros/jazzy/bin/ros2')).exists():missing.append('executable: ros2')
    if not shutil_which('colcon'):missing.append('executable: colcon')
    if missing:raise RuntimeError('preflight missing: '+', '.join(missing))
    return {'checked':[str(p) for p in needed], 'original_workspace':str(UP),
            'current_workspace':str(ROOT),'sim_workspace':str(CMU)}

def shutil_which(name):
    from shutil import which
    return which(name)

def build_current(folder):
    command=(source('/opt/ros/jazzy/setup.bash')+
        f' cd {q(ROOT)} && colcon --log-base log_standalone build --build-base build_standalone '
        f'--install-base install_standalone --packages-select tare_planner --cmake-args -DCMAKE_BUILD_TYPE=Release')
    with (folder/'build.log').open('w') as log:
        completed=subprocess.run(['bash','-lc',command],stdout=log,stderr=subprocess.STDOUT,timeout=900)
    if completed.returncode:raise RuntimeError(f'current tare_planner build failed; see {folder/"build.log"}')

def run_trial(trial,variant,duration):
    ros=Path('/opt/ros/jazzy/setup.bash')
    cmu=CMU/'install/setup.bash'
    sim=source(ros,cmu)+f' exec ros2 launch {q(BRIDGE/"cmu_xytheta.launch.py")} world_name:=garage'
    trial.start('sim',sim)
    time.sleep(10);trial.check()
    stage=source(ros,cmu)+f' python3 {q(HERE/"stage_garage_pose.py")}'
    stage_output=trial.run('stage',stage,95)
    stage_data=json.loads(stage_output.strip().splitlines()[-1])
    (trial.folder/'stage.json').write_text(json.dumps(stage_data,indent=2)+'\n')
    if variant=='original':
        local=source(ros,cmu)+ ' exec ros2 launch local_planner local_planner.launch autonomySpeed:=0.5'
        tare=source(ros,cmu,UP/'install/setup.bash')+' exec ros2 launch tare_planner explore_garage.launch rviz:=false'
    else:
        trial.env['HT_HISTORY_DUMP']=str(trial.folder/'historical_elevation.npz')
        mapper=source(ros,CUPY/'install/setup.bash')+(
            ' exec ros2 run elevation_mapping_cupy elevation_mapping_node --ros-args'
            f' -p core_param_file:={q(CUPY/"config/trial_core.yaml")}'
            f' -p setup_file:={q(CUPY/"config/trial_setup.yaml")}')
        trial.start('elevation',mapper);time.sleep(3);trial.check()
        bridge=source(ros,cmu)+f' exec python3 {q(BRIDGE/"cupy_to_ht.py")}'
        trial.start('ht_bridge',bridge);time.sleep(10);trial.check()
        follow=source(ros,ROOT/'install_standalone/setup.bash')+(
            ' exec ros2 run tare_planner xytheta_follower --ros-args'
            f' --params-file {q(BRIDGE/"ht_trial.yaml")}')
        trial.start('xytheta_follower',follow);time.sleep(2);trial.check()
        tare=source(ros,ROOT/'install_standalone/setup.bash')+(
            ' exec ros2 launch tare_planner explore_ht.launch.py scenario:=garage use_sim_time:=false'
            f' ht_config:={q(BRIDGE/"ht_trial.yaml")}')
    probe=source(ros,cmu,(UP/'install/setup.bash' if variant=='original' else ROOT/'install_standalone/setup.bash'))+(
        f' exec python3 {q(HERE/"paired_probe.py")} --output {q(trial.folder)}'
        f' --duration {duration} --warmup 120')
    probe_proc=trial.start('probe',probe)
    time.sleep(1)
    trial.start('tare',tare)
    if variant=='original':
        # Starting CMU's follower before TARE moves the staged robot toward its
        # default waypoint, corrupting the paired start pose.
        start_file=trial.folder/'measurement_started.json'
        deadline=time.monotonic()+120
        while not start_file.exists() and time.monotonic()<deadline:
            if probe_proc.poll() is not None:break
            time.sleep(.2)
        if not start_file.exists():raise RuntimeError('original: probe did not start measurement')
        trial.start('local_planner',local)
    try:
        probe_proc.wait(timeout=duration+145)
    except subprocess.TimeoutExpired:
        raise RuntimeError(f'{variant}: recorder timed out')
    if probe_proc.returncode:
        raise RuntimeError(f'{variant}: recorder failed ({probe_proc.returncode}); see {trial.folder/"probe.log"}')
    summary=json.loads((trial.folder/'summary.json').read_text())
    return summary

def validate(pair,duration):
    for name,summary in pair.items():
        if summary['sample_count']<duration*1.7:raise RuntimeError(f'{name}: too few samples')
        if summary['odom_count']<duration*25:raise RuntimeError(f'{name}: too little odometry')
        if summary['registered_scans']<duration*2:raise RuntimeError(f'{name}: too few registered scans')
        if summary['planner_runtime_count']<duration*.25:raise RuntimeError(f'{name}: too few TARE cycles')
        x,y,yaw=summary['start_pose_xyyaw']
        if ((x-.3)**2+(y-3.5)**2)**.5>.45:raise RuntimeError(f'{name}: start position mismatched')
    a=pair['original']['start_pose_xyyaw'];b=pair['current']['start_pose_xyyaw']
    if ((a[0]-b[0])**2+(a[1]-b[1])**2)**.5>.2:
        raise RuntimeError('paired starting positions differ by >0.2 m')

def report(folder,pair,duration):
    a=pair['original'];b=pair['current']
    fields=[('行驶距离 / m','distance_m'),('到访 1 m XY 栅格','visited_1m_xy_cells'),
            ('倒车指令比例','reverse_cmd_fraction'),('零速指令比例','zero_cmd_fraction'),
            ('TARE 规划中位数 / s','planner_runtime_median_s'),('探索完成','exploration_finished')]
    lines=['# 原版 TARE vs 当前 XYθ 版本：一次 Garage 配对实验','',
           f'日期：{dt.datetime.now().astimezone().isoformat()}；每组记录 {duration} 秒。',
           '两组使用独立重启的同一 CMU Garage、同一 64 线仿真雷达、同一预定位姿与 0.5 m/s 前进速度上限。',
           '这是端到端系统对比：当前版使用 CuPy/HT、Hybrid A* 和独立跟踪器；原版使用自身路径/CMU local planner。',
           '单次运行含探索随机性，不能作统计显著性或单模块因果结论。轨迹栅格不是探索体积。','',
           '| 指标 | 原版 TARE | 当前 XYθ |','|---|---:|---:|']
    for label,key in fields:
        def fmt(value):
            if key.endswith('_fraction'):return f'{100*value:.1f}%'
            if key.endswith('_s') or key=='distance_m':return f'{value:.2f}'
            if isinstance(value,bool):return '是' if value else '否'
            return str(value)
        lines.append(f'| {label} | {fmt(a[key])} | {fmt(b[key])} |')
    rows=list(csv.DictReader((folder/'current/timeseries.csv').open()))
    moving=[float(row['t_s']) for row in rows if float(row['distance_m'])<=b['distance_m']-.01]
    last_progress=max(moving) if moving else 0.0
    counts=b.get('ht_status_callbacks',{})
    lines+=['','## 当前版本停滞检查','',
            f'当前版到访栅格和行驶距离在约 {last_progress:.1f} 秒后基本不再增加，零速指令占 {100*b["zero_cmd_fraction"]:.1f}%。'+
            f'状态记录：HT_ASSISTED {counts.get("HT_ASSISTED",0)} 次、'+
            f'NO_EXECUTABLE_ROUTE {counts.get("NO_EXECUTABLE_ROUTE",0)} 次、'+
            f'HT_MAP_STALE {counts.get("HT_MAP_STALE",0)} 次。']
    if b.get('ht_map_count'):
        lines.append(f'独立记录器收到 HT 地图 {b["ht_map_count"]} 幅；最大到达间隔 '
                     f'{b["ht_map_gap_max_s"]:.2f} 秒、观测到的最大地图年龄 '
                     f'{b["ht_map_age_max_s"]:.2f} 秒。因此外部地图输入并未整体中断；'+
                     'TARE 内部出现 stale 仍需检查其订阅、回调调度和快照时间戳。')
    lines.append('TARE 日志显示反复找不到 XYθ 可执行路线，HT 边大量被拒；'
                 '停滞主要表现为路线不可用判断。单线程规划回调占用导致地图处理延迟是待验证假设，不能从这一次实验认定为根因。')
    lines+=['',f'原版原始数据：`original/timeseries.csv`、`original/summary.json`。',
            f'当前原始数据：`current/timeseries.csv`、`current/summary.json`。',
            '日志与预定位姿保留在各组目录。']
    if (folder/'current/historical_elevation.npz').exists():
        lines.append('融合后的全局历史高程图：`current/historical_elevation.npz`。')
    if (folder/'current/historical_elevation.png').exists():
        lines.append('全局历史高程图可视化：`current/historical_elevation.png`。')
    (folder/'REPORT.md').write_text('\n'.join(lines)+'\n')

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--check',action='store_true',help='read-only preflight; no simulation')
    ap.add_argument('--duration',type=int,default=180)
    ap.add_argument('--smoke',action='store_true',help='run a short integration test without updating the PPT')
    args=ap.parse_args()
    info=preflight()
    if args.check:
        print(json.dumps({'preflight':'ok',**info},ensure_ascii=False,indent=2));return
    stamp=dt.datetime.now().astimezone().strftime('%Y-%m-%d_%H-%M-%S')
    folder=RESULTS/stamp;folder.mkdir(parents=True,exist_ok=True)
    (folder/'manifest.json').write_text(json.dumps({'started_at':dt.datetime.now().astimezone().isoformat(),
      'duration_per_trial_s':args.duration,'scenario':'Garage','vehicle_speed_cap_mps':.5,
      'trial_order':['original','current'],**info},ensure_ascii=False,indent=2)+'\n')
    pair={};failure=None
    try:
        build_current(folder)
        for name,domain in (('original',207),('current',208)):
            trial=Trial(name,folder/name,domain)
            try:pair[name]=run_trial(trial,name,args.duration)
            finally:trial.stop();time.sleep(5)
        history=folder/'current/historical_elevation.npz'
        if history.exists():
            with (folder/'current/history_render.log').open('w') as log:
                subprocess.run([sys.executable,str(BRIDGE/'render_historical_elevation.py'),
                                str(history),str(folder/'current/historical_elevation.png')],
                               stdout=log,stderr=subprocess.STDOUT,timeout=60)
        validate(pair,args.duration)
        report(folder,pair,args.duration)
        if args.smoke:
            print(f'SMOKE COMPLETE {folder}; presentation unchanged',flush=True)
            return
        result={'status':'complete','run_dir':str(folder),'duration_s':args.duration,
                'scenario':'Garage','original':pair['original'],'current':pair['current'],
                'caveat':'One sequential run per version; different controllers and perception stacks; path cells are not explored volume.'}
        draft=folder/'latest_current_vs_upstream.json';draft.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        # Build the presentation against the draft first; publish comparison metadata only after success.
        env=os.environ.copy();env['HT_PPT_COMPARISON_JSON']=str(draft)
        with (folder/'ppt_build.log').open('w') as log:
            completed=subprocess.run([sys.executable,str(HERE/'build_group_meeting.py')],env=env,
                                     stdout=log,stderr=subprocess.STDOUT,timeout=90)
        if completed.returncode:raise RuntimeError(f'PPT rebuild failed; see {folder/"ppt_build.log"}')
        LATEST.write_text(draft.read_text())
        print(f'COMPLETE {folder}',flush=True)
    except Exception as exc:
        failure={'status':'failed','error':str(exc),'run_dir':str(folder),
                 'finished_at':dt.datetime.now().astimezone().isoformat()}
        (folder/'FAILURE.json').write_text(json.dumps(failure,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps(failure,ensure_ascii=False),file=sys.stderr,flush=True)
        raise

if __name__=='__main__':main()
