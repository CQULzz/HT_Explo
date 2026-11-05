from pathlib import Path
import cv2,json,hashlib
import argparse
parser=argparse.ArgumentParser();parser.add_argument('batch_root',type=Path);args=parser.parse_args()
R=args.batch_root.resolve();out=R/'runs/comparisons';out.mkdir(exist_ok=True);records=[]
for seed,h,t in [(42,'b02_single42','b06_tare42_repeat'),(99,'b03_single99','b05_tare99')]:
 dst=out/f'HT_TARE_seed{seed}.mp4'
 if dst.exists():raise FileExistsError(dst)
 caps=[cv2.VideoCapture(str(R/'runs'/name/'trajectory.mp4')) for name in [h,t]]
 assert all(c.isOpened() for c in caps)
 counts=[int(c.get(cv2.CAP_PROP_FRAME_COUNT)) for c in caps];assert counts[0]==counts[1]
 writer=cv2.VideoWriter(str(dst),cv2.VideoWriter_fourcc(*'mp4v'),2,(1920,680));assert writer.isOpened();frames=0
 while True:
  pair=[c.read() for c in caps]
  if not any(ok for ok,im in pair):break
  assert all(ok for ok,im in pair)
  import numpy as np
  canvas=np.full((680,1920,3),255,np.uint8);canvas[40:,:960]=pair[0][1];canvas[40:,960:]=pair[1][1]
  for text,x in [(f'HT / seed {seed} / {h}',15),(f'TARE geometric+CMU / seed {seed} / {t}',975)]:cv2.putText(canvas,text,(x,27),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,0,0),2,cv2.LINE_AA)
  writer.write(canvas);frames+=1
 writer.release()
 for c in caps:c.release()
 cap=cv2.VideoCapture(str(dst));decoded=0
 while True:
  ok,im=cap.read()
  if not ok:break
  assert im.shape[:2]==(680,1920);decoded+=1
 cap.release();assert decoded==frames==counts[0]
 records.append({'seed':seed,'path':str(dst),'left':h,'right':t,'frames':frames,'all_frames_decoded':True,'fps':2,'bytes':dst.stat().st_size,'sha256':hashlib.sha256(dst.read_bytes()).hexdigest(),'content':'Matched observer sample-index side-by-side2D trajectory/telemetry over reconstructed scene; not Gazebo camera or real-car footage.'})
(out/'VIDEO_VERIFICATION.json').write_text(json.dumps(records,indent=2));print(records)
