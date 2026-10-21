#!/usr/bin/env python3
"""After both campus measurements: compare, audit and record actual RViz."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

import cv2

from finalize_matched_tare_comparison import ROOT, read, write, sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--state',type=Path,required=True);a=ap.parse_args()
    job=read(a.state);suite=Path(job['suite']);out=Path(job['archive']);runtime=a.state.resolve().parent
    if job['stage']!=48 or job['scene']!='campus':
        raise RuntimeError('Wrong job for campus postprocessing')
    while not (suite/'FINISHED.json').exists():
        time.sleep(5)
    if read(suite/'FINISHED.json')['state']!='MEASUREMENTS_COMPLETE':
        raise RuntimeError('Measurements did not complete; raw/partial evidence retained')
    def run(program,log,timeout=1800,env=None):
        with (runtime/log).open('w') as f:
            subprocess.run([str(x) for x in program],cwd=ROOT,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=timeout)
    run([sys.executable,'presentations/finalize_matched_tare_comparison.py','--state',a.state],'analysis.log')
    run([sys.executable,'presentations/render_matched_tare_comparison.py','--state',a.state],'camera_comparison.log')
    run([sys.executable,'presentations/audit_matched_tare_cleanup.py','--state',a.state],'lifecycle.log')
    run([sys.executable,'presentations/audit_tare_waypoint.py',suite/'ht','--output',out/'architecture'],'architecture.log')
    cache=runtime/'rviz.pkl'
    run([sys.executable,'presentations/rviz_recorded_comparison.py','--prepare','--suite',suite,'--cache',cache],'rviz_prepare.log')
    xvfb=ROOT/'.git/experiment-tools/xvfb/root/usr/bin/Xvfb'
    if not xvfb.exists():
        raise RuntimeError('Isolated Xvfb tool missing; do not capture unrelated desktop')
    rviz=out/'rviz';rviz.mkdir()
    servers=[];workers=[];handles=[]
    try:
        for display,mode,folder,domain in [(':98','comparison',rviz,231),(':99','detail',rviz/'detail',232)]:
            if Path('/tmp/.X11-unix/X'+display[1:]).exists():
                raise RuntimeError('Replay display already occupied: '+display)
            log=(runtime/(mode+'_xvfb.log')).open('w');handles.append(log)
            servers.append(subprocess.Popen([str(xvfb),display,'-screen','0','1920x1080x24','-nolisten','tcp','-ac','+extension','GLX','+render','-noreset'],stdout=log,stderr=subprocess.STDOUT))
        time.sleep(2)
        for display,mode,folder,domain in [(':98','comparison',rviz,231),(':99','detail',rviz/'detail',232)]:
            env=dict(os.environ,ROS_DOMAIN_ID=str(domain))
            log=(runtime/('rviz_'+mode+'.log')).open('w');handles.append(log)
            workers.append(subprocess.Popen([sys.executable,'presentations/rviz_recorded_comparison.py','--cache',str(cache),
                '--output',str(folder),'--mode',mode,'--display',display,'--encoder',job['encoder']],cwd=ROOT,env=env,
                stdout=log,stderr=subprocess.STDOUT,start_new_session=True))
        for p in workers:
            p.wait(timeout=900)
            if p.returncode:
                raise RuntimeError('RViz replay failed; original data and camera videos retained')
    finally:
        for p in workers:
            if p.poll() is None:
                os.killpg(p.pid,signal.SIGINT)
                try:p.wait(timeout=30)
                except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
        for p in servers:
            p.terminate()
            try:p.wait(timeout=5)
            except subprocess.TimeoutExpired:p.kill();p.wait()
        for h in handles:h.close()
    video_checks={}
    for rel in ('rviz_comparison_4x.mp4','detail/rviz_detail_4x.mp4'):
        p=rviz/rel;c=cv2.VideoCapture(str(p));n=int(c.get(cv2.CAP_PROP_FRAME_COUNT));fps=c.get(cv2.CAP_PROP_FPS)
        w=int(c.get(cv2.CAP_PROP_FRAME_WIDTH));h=int(c.get(cv2.CAP_PROP_FRAME_HEIGHT));c.release()
        if (n,fps,w,h)!=(1501,10.,1920,1080):
            raise RuntimeError('RViz video frame/size mismatch')
        run([job['encoder'],'-v','error','-xerror','-i',p,'-f','null','-'],('detail' if 'detail' in rel else 'comparison')+'_full_decode.log',600)
        video_checks[rel]=dict(frames=n,fps=fps,duration_s=n/fps,source_duration_s=600,width=w,height=h,
                               full_decode_exit_code=0,sha256=sha(p),bytes=p.stat().st_size)
    write(rviz/'validation.json',video_checks)
    write(rviz/'source_metadata.json',read(cache.with_suffix('.json')))
    # The extra video attachments are uploaded and verified by the publisher.
    prefix=f'https://github.com/CQULzz/HT_Explo/releases/download/{job["tag"]}/'
    body=(out/'REPORT.md').read_text()
    for relative,asset in [('original/camera_h264.mp4',job['tag']+'-original.mp4'),('ht/camera_h264.mp4',job['tag']+'-ht.mp4')]:
        body=body.replace(']('+relative+')',']('+prefix+asset+')')
    extra='\n'.join(['## 实际RViz回放','',
        f'[全局原TARE/HT对比]({prefix}stage48-campus-rviz-comparison-4x.mp4) · [HT局部XY与八层XYθ]({prefix}stage48-campus-rviz-xytheta-4x.mp4)','',
        '1080p、10fps、4倍速，各覆盖原实验0～600秒；真实RViz窗口录包回放，不是原运行实时屏幕录像，也不重新规划。全局同尺度显示累计观测点云、青色实际轨迹、黄色TARE访问路线/航点；HT绿色为已发布执行路径、粉色为路段目标。',
        '局部左侧为当前最近45°方向的预测分数；右侧为八个原始方向层，竖轴是角度。红低绿高，左灰/右透明表示无效；模型分数不等于经过全部足迹/几何/时效检查的最终通行结果。上层可能遮挡下层路径，可对照左侧XY投影。',
        '显示点云15m截断、0.18m体素抽稀，HT每3格显示一个原分数，不插值概率；显示抽稀不参与原指标或控制。完整轨迹在全局，局部XY只显示当前范围片段，XYθ不叠历史轨迹。未记录的搜索树不补造。',
        '全局视野由两轮完整轨迹加15m范围共同确定，属于事后固定取景，不表示车辆提前知道未观测地图。HUD取不晚于当前时刻的最近CSV条目，采样与异步显示有刷新差；不能用回放测量在线延迟。','',
        '![RViz第180秒全局](rviz/comparison_t180.jpg)','', '![RViz第180秒局部XYθ](rviz/detail/detail_t180.jpg)','',
        '[原TARE访问顺序与HT同分支路由审计](architecture/summary.json)；图与记录见architecture目录。',''])
    body=body.replace('## 口径与限制\n',extra+'\n## 口径与限制\n',1)
    # Keep one main downloadable video link in the comparison report.
    body=body.replace('## 视频与数据\n','## 视频与数据\n\n[左右分屏相机对比：左TARE，右HT]('+prefix+'stage48-campus-camera-comparison.mp4)\n',1)
    (out/'REPORT.md').write_text(body)
    # Reports/scripts describe this postprocessing version; the measured tag
    # remains the frozen pre-measurement runtime candidate.
    write(out/'postprocessing.json',dict(measured_candidate=job['candidate_commit'],navigation_control_commit=job['navigation_control_commit'],
          scripts={name:sha(ROOT/'presentations'/name) for name in ('process_campus_comparison.py','finalize_matched_tare_comparison.py',
              'render_matched_tare_comparison.py','audit_matched_tare_cleanup.py','rviz_recorded_comparison.py')},
          all_navigation_inputs_unchanged=read(out/'ht/suite_validation.json')['checks']['source_hashes_unchanged']))
    import shutil
    shutil.copy2(Path(__file__),out/Path(__file__).name)
    write(out/'files_sha256.json',{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*'))
                                  if p.is_file() and p.name!='files_sha256.json'})
    print('CAMPUS_POSTPROCESSING_COMPLETE',out,flush=True)


if __name__=='__main__':
    main()
