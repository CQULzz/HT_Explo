#!/usr/bin/env python3
"""Run independent ten-minute HT scenes in sequence, validate and collect their videos."""
import argparse
import csv
import datetime as dt
import hashlib
import json
from pathlib import Path
import signal
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

import psutil

from run_scheduled_comparison import ROOT,CMU,BRIDGE,source,q

SCENES=('garage','campus','indoor','forest','tunnel')
NAMES=dict(garage='车库',campus='校园',indoor='室内',forest='森林',tunnel='隧道')


def read_json(path):return json.loads(path.read_text())


def write_json(path,value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n')
    temp.replace(path)


def preflight(scenes):
    missing=[]
    for scene in scenes:
        world=CMU/f'src/vehicle_simulator/world/{scene}.world'
        if not world.exists():missing.append(str(world));continue
        for uri in ET.parse(world).iter('uri'):
            name=(uri.text or '').strip()
            if name.startswith('model://'):
                asset=CMU/'src/vehicle_simulator/mesh'/name[len('model://'):]
                if not asset.exists():missing.append(str(asset))
        for path in [ROOT/f'src/tare_planner/config/{scene}.yaml',
                     ROOT/f'install_standalone/tare_planner/share/tare_planner/{scene}.yaml']:
            if not path.exists():missing.append(str(path))
    if missing:raise RuntimeError('Missing scene assets/configuration: '+str(sorted(set(missing))))


def save_report(job,state):
    title='HT 五环境各10分钟实验' if len(state['runs'])==5 else 'HT '+ '、'.join(NAMES[r['scenario']] for r in state['runs'])+'10分钟补测'
    lines=['# '+title, '',
           f'每组测量 {state["duration_s"]} 秒，从首个具备里程计和激光输入的TARE运行周期开始计时；初始化不计入。',
           '每个场景独立启动、独立高程历史，上一组完全退出且视频处理结束后再启动下一组。车速上限均为0.5m/s，HT硬约束与3秒时效保护相同。',
           '采用对应场景TARE参数；车库沿用历史配对起点，其余使用各自仿真原生起点。因此这不是相同场景的算法优劣对照。',
           '相机原生960×540、15fps，视频含状态条并裁去初始化；重复帧代表真实图像更新间隔，不做插帧。', '',
           '| 环境 | 状态 | 实际里程(m) | 近似观测体积(m³) | 末尾任务状态 | 视频 |',
           '|---|---|---:|---:|---|---|']
    playlist=['#EXTM3U','#EXTENC:UTF-8']
    for row in state['runs']:
        metrics=row.get('metrics',{})
        distance=f'{metrics["distance_m"]:.2f}' if 'distance_m' in metrics else '—'
        volume=metrics.get('observed_free_volume_m3')
        volume=f'{volume:.2f}' if volume is not None else '—'
        movie=f'{row["scenario"]}/camera_h264.mp4'
        available=(job/movie).exists() and row.get('video_ok',False)
        link=f'[播放/下载]({movie})' if available else '待生成'
        lines.append(f'| {NAMES[row["scenario"]]} | {row["state"]} | {distance} | {volume} | {metrics.get("mission","—")} | {link} |')
        if available:
            playlist += [f'#EXTINF:{state["duration_s"]},{NAMES[row["scenario"]]} HT探索',movie]
        if row.get('error'):lines += ['',f'> {row["scenario"]}：{row["error"]}', '']
    lines += ['', '[全部视频播放列表](videos.m3u) · [实时状态与校验](suite.json)', '',
              '每个场景仅一次10分钟测试，不能据此证明更长时间、所有环境或实车稳定。定时记录完成不等于探索完成。观测体积是抽样激光射线的自由体素并集近似，不是真值覆盖率；跨场景体积不可直接作为算法优劣排名。']
    (job/'REPORT.md').write_text('\n'.join(lines)+'\n')
    (job/'videos.m3u').write_text('\n'.join(playlist)+'\n')
    write_json(job/'suite.json',state)


def overview(job,state):
    import cv2
    import numpy as np
    panels=[]
    for row in state['runs']:
        image=cv2.imread(str(job/row['scenario']/'preview.jpg'))
        if image is None:continue
        panel=np.zeros((335,1440,3),np.uint8)
        panel[35:]=image
        cv2.putText(panel,row['scenario'].upper()+' | early / middle / late',
                    (15,25),cv2.FONT_HERSHEY_SIMPLEX,.65,(240,240,240),1)
        panels.append(panel)
    if panels:cv2.imwrite(str(job/'overview.jpg'),np.vstack(panels))


def audit_run(folder,duration):
    manifest=read_json(folder/'manifest.json')
    summary=read_json(folder/'summary.json')
    hashes={p:Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==value
            for p,value in manifest['source_hashes'].items()}
    shutdown=read_json(folder/'current/shutdown.json')
    video=read_json(folder/'video_validation.json')
    checks=dict(timer_completed=(folder/'COMPLETED.json').exists(),
                measured_duration_matches=summary['duration_s']==duration,
                source_hashes_unchanged=all(hashes.values()),
                enough_samples=summary['sample_count']>=duration*1.7,
                no_runtime_parent_failure=not (folder/'runtime_failures.json').exists(),
                no_live_descendants=shutdown[-1].get('remaining_live_descendants')==[],
                no_forced_shutdown=not any(x.get('signal') in ('SIGTERM','SIGKILL') for x in shutdown),
                video_full_decode_passed=video.get('full_decode_returncode')==0,
                video_duration_matches=video.get('duration_matches',False),
                video_fps_matches=video.get('fps')==15,
                analysis_passed=read_json(folder/'ANALYSIS_COMPLETED.json').get('analysis_returncode',0)==0)
    errors={}
    pattern=re.compile(r'terminate called|Traceback \(most recent call last\)|The following exception was never retrieved|exit code -(?:6|11)\b')
    for path in (folder/'current').glob('*.log'):
        matched=[line for line in path.read_text(errors='replace').splitlines() if pattern.search(line)]
        if matched:errors[path.name]=matched
    checks['no_child_or_cleanup_exception']=not errors
    pools=read_json(folder/'current/ht_cpu_threads.json')
    checks['blas_workers_bounded']=bool(pools['blas_pools']) and all(p['num_threads']==1 for p in pools['blas_pools'])
    write_json(folder/'suite_validation.json',dict(checks=checks,source_hashes_unchanged=hashes,video=video,lifecycle_errors=errors))
    return checks


def preview(folder,encoder,duration):
    import cv2
    import numpy as np
    frames=[]
    for index,second in enumerate([min(30,duration/10),duration/2,max(0,duration-10)]):
        path=folder/f'preview_{index}.jpg'
        result=subprocess.run([str(encoder),'-nostdin','-v','error','-y','-ss',str(second),
            '-i',str(folder/'camera_h264.mp4'),'-frames:v','1',str(path)],capture_output=True,timeout=45)
        if result.returncode:raise RuntimeError(result.stderr.decode(errors='replace'))
        frame=cv2.imread(str(path))
        if frame is None:raise RuntimeError('Unreadable video preview')
        frames.append(cv2.resize(frame,(480,300)))
    cv2.imwrite(str(folder/'preview.jpg'),np.hstack(frames))


def wait_process(proc,state,job,row,phase,timeout):
    deadline=time.monotonic()+timeout
    row['state']=phase;save_report(job,state)
    while proc.poll() is None:
        if time.monotonic()>deadline:raise TimeoutError(f'{row["scenario"]}: {phase} timed out')
        try:
            origin=read_json(job/row['scenario']/'current/measurement_started.json')['wall_time']
            if phase=='RECORDING':row['elapsed_measurement_s']=min(state['duration_s'],round(time.time()-origin,1))
        except (OSError,ValueError,KeyError):pass
        state['updated_at']=dt.datetime.now().astimezone().isoformat()
        save_report(job,state)
        time.sleep(3)
    return proc.returncode


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--scenarios',nargs='+',choices=SCENES,default=list(SCENES))
    ap.add_argument('--duration',type=int,default=600)
    ap.add_argument('--output',type=Path)
    ap.add_argument('--domain',type=int,default=220)
    ap.add_argument('--encoder',type=Path,required=True)
    args=ap.parse_args()
    if len(set(args.scenarios))!=len(args.scenarios):raise ValueError('Duplicate scenarios')
    if args.duration<=0 or not 0<=args.domain<=232-len(args.scenarios)+1:raise ValueError('Invalid duration/domain')
    preflight(args.scenarios)
    job=(args.output or ROOT/'presentations/scheduled_results'/('ht_multiscene_10min_'+dt.datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))).resolve()
    if job.exists():raise RuntimeError('Refusing to overwrite '+str(job))
    job.mkdir(parents=True)
    state=dict(started_at=dt.datetime.now().astimezone().isoformat(),duration_s=args.duration,
               git_head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
               job=str(job),state='RUNNING',runs=[dict(scenario=s,state='PENDING') for s in args.scenarios])
    write_json(ROOT/'presentations/scheduled_results/latest_multiscene.json',dict(folder=str(job),pid=__import__('os').getpid(),duration_s=args.duration,scenarios=args.scenarios))
    save_report(job,state)
    for index,row in enumerate(state['runs']):
        scene=row['scenario'];folder=job/scene;runner=watcher=None
        try:
            if psutil.virtual_memory().available<1000*1024**2 or __import__('shutil').disk_usage(job).free<8*1024**3:
                raise RuntimeError('Insufficient free RAM/disk for another independent scene')
            with (job/f'{scene}.runner.log').open('w') as log:
                runner=subprocess.Popen([sys.executable,str(Path(__file__).with_name('run_ht_endurance.py')),
                    '--duration',str(args.duration),'--scenario',scene,'--video-fps','15',
                    '--domain',str(args.domain+index),'--output',str(folder)],stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row['runner_pid']=runner.pid
            with (job/f'{scene}.watcher.log').open('w') as log:
                watcher=subprocess.Popen([sys.executable,str(Path(__file__).with_name('watch_ht_endurance.py')),
                    str(folder),'--runner-pid',str(runner.pid),'--encoder',str(args.encoder)],
                    stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            row['watcher_pid']=watcher.pid
            write_json(ROOT/'presentations/scheduled_results/latest_endurance.json',dict(
                folder=str(folder),pid=runner.pid,watcher_pid=watcher.pid,duration_s=args.duration,
                domain=args.domain+index,scenario=scene,suite=str(job),baseline=None))
            print('STARTED',scene,'runner',runner.pid,flush=True)
            result=wait_process(runner,state,job,row,'RECORDING',args.duration+300)
            if result:raise RuntimeError(f'Runner exited {result}; inspect {scene}.runner.log')
            result=wait_process(watcher,state,job,row,'POSTPROCESSING',3000)
            if result:raise RuntimeError(f'Analysis/video worker exited {result}')
            checks=audit_run(folder,args.duration)
            row['checks']=checks
            row['video_ok']=checks['video_full_decode_passed'] and checks['video_duration_matches']
            summary=read_json(folder/'summary.json')
            audit=read_json(folder/'endurance_audit.json')
            row['metrics']=dict(distance_m=summary['distance_m'],visited_1m_xy_cells=summary['visited_1m_xy_cells'],
                observed_free_volume_m3=(audit.get('external_metrics') or {}).get('observed_free_volume_m3'),
                mission=audit['mission_audit']['last_sampled_mission'],
                map_age_p95_s=audit['sampled_map_age_s']['p95'],map_age_max_s=audit['sampled_map_age_s']['max'])
            row['state']='RECORDED' if all(checks.values()) else 'RECORDED_WITH_ISSUES'
            if row['video_ok']:
                preview(folder,args.encoder,args.duration)
                overview(job,state)
            print('FINISHED',scene,row['state'],json.dumps(row['metrics']),flush=True)
        except BaseException as error:
            row['state']='FAILED';row['error']=str(error)
            print('FAILED',scene,repr(error),flush=True)
            if runner and runner.poll() is None:
                runner.send_signal(signal.SIGINT)
                try:runner.wait(timeout=35)
                except subprocess.TimeoutExpired:raise RuntimeError('Owned runner did not clean up; refuse to start another scene')
            if watcher and watcher.poll() is None:
                try:watcher.wait(timeout=12)
                except subprocess.TimeoutExpired:
                    watcher.terminate();watcher.wait(timeout=8)
            if isinstance(error,(KeyboardInterrupt,SystemExit)):raise
        finally:
            row['finished_at']=dt.datetime.now().astimezone().isoformat();save_report(job,state)
    state['state']='COMPLETED' if all(r['state']=='RECORDED' for r in state['runs']) else 'COMPLETED_WITH_ISSUES'
    state['finished_at']=dt.datetime.now().astimezone().isoformat();save_report(job,state)
    (job/'FINISHED.json').write_text(json.dumps(state,ensure_ascii=False,indent=2)+'\n')
    print('RESULTS',job,flush=True)


if __name__=='__main__':main()
