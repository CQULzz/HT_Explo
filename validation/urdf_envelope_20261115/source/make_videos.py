from pathlib import Path
import subprocess,json,os,time
r=Path('/mnt/d/HT-URDF-Compare-20261115');runtime=Path('/home/lzz/ht_urdf_compare_20261115');tools=r/'video_tools'
envgeom=json.loads((runtime/'setup/URDF_ENVELOPE.json').read_text());tasks=[]
for index,variant in enumerate(['baseline','urdf']):
    out=r/'video'/variant;out.mkdir(parents=True,exist_ok=True)
    env=os.environ.copy();env.update(HT_VIDEO_ROOT=str(out),HT_VIDEO_RUN=str(runtime/'runs'/f'{variant}_campus_600s_01'),HT_VIDEO_DOMAIN=str(227+index),HT_VIDEO_DISPLAY=':'+str(94+index),DISPLAY=':'+str(94+index),HT_VIDEO_TEXT_ROOT=str(runtime/'video_text'/variant),HT_VIDEO_TITLE='旧0.6米包络' if variant=='baseline' else 'URDF包络')
    if (out/'STOP').exists():(out/'STOP').unlink()
    body={'size':[.6,.6,.45],'center':[0,0,.28]}
    if variant=='urdf':body={'size':envgeom['size_xyz'],'center':[envgeom['center_xyz'][0],envgeom['center_xyz'][1],.23479+envgeom['center_xyz'][2]]}
    (out/'BODY.json').write_text(json.dumps(body))
    if not (out/'snapshots.json').exists():subprocess.run(['python3',str(tools/'prepare.py')],env=env,check=True,stdout=(out/'prepare.log').open('w'))
    subprocess.run(['python3',str(tools/'configure.py')],env=env,check=True)
    provenance=json.loads((out/'PROVENANCE.json').read_text());provenance['vehicle']='Recorded occupancy envelope: '+json.dumps(body)+'; no physical contact simulation; Z visualized, occupancy uses conservative XY projection.';provenance['recording_display']=env['DISPLAY'];provenance['subtitle_store']=env['HT_VIDEO_TEXT_ROOT'];(out/'PROVENANCE.json').write_text(json.dumps(provenance,indent=2))
    log=(out/'start.log').open('w');p=subprocess.Popen(['bash',str(tools/'start.sh')],env=env,stdout=log,stderr=subprocess.STDOUT);tasks.append((out,env,p,log))
# Let both RViz windows initialize, then record each independent display.
time.sleep(12)
recordings=[]
for out,env,p,log in tasks:
    if p.poll() is not None:raise RuntimeError('RViz startup failed '+str(out))
    q=subprocess.Popen(['python3',str(tools/'record.py')],env=env,stdout=(out/'record.log').open('w'),stderr=subprocess.STDOUT);recordings.append((out,q))
try:
    for out,q in recordings:
        if q.wait()!=0:raise RuntimeError('Recording failed '+str(out))
finally:
    for out,env,p,log in tasks:(out/'STOP').touch()
    for out,env,p,log in tasks:
        try:p.wait(timeout=10)
        except subprocess.TimeoutExpired:p.terminate();p.wait()
        log.close()
for out,q in recordings:
    video=out/'rviz_exploration_full_4x.mp4'
    subprocess.run(['ffmpeg','-v','error','-i',str(video),'-f','null','-'],check=True,stderr=(out/'full_decode.log').open('w'))
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-ss','85','-i',str(video),'-frames:v','1',str(out/'preview.png')],check=True)
print('BOTH_VIDEOS_COMPLETE')
