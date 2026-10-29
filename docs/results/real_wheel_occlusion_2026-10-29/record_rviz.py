from pathlib import Path
import subprocess,os,time,json
O=Path(__file__).parent;R=Path('/home/lzz/my test/HT_Explo-real-review-20261028');env=os.environ.copy();env['ROS_DOMAIN_ID']='188';env['LIBGL_ALWAYS_SOFTWARE']='1';env['QT_X11_NO_MITSHM']='1'
assert not Path('/tmp/.X98-lock').exists(),'Display98 is already owned; do not capture an unrelated display'
server=subprocess.Popen(['/usr/bin/Xephyr',':98','-screen','2560x1440','-ac','-br','-noreset','-nolisten','tcp','-title','HT offline RViz recording'],env=env,stdout=(O/'xephyr.log').open('w'),stderr=subprocess.STDOUT)
try:
 for _ in range(50):
  if server.poll() is not None:raise RuntimeError('Private Xephyr failed')
  if Path('/tmp/.X11-unix/X98').exists():break
  time.sleep(.1)
 else:raise RuntimeError('Private display missing')
 subprocess.run(['/home/lzz/.venvs/ht_real_gpu_20261028/bin/python',str(R/'tools/ht_cupy_bridge/record_newbags_rviz.py'),'--input',str(O/'frozen_registered_moving'),'--output',str(O/'rviz_after'),'--label','HT_body_filter_fixed'],env=env,check=True)
finally:
 server.terminate()
 try:server.wait(timeout=10)
 except subprocess.TimeoutExpired:server.kill();server.wait()
