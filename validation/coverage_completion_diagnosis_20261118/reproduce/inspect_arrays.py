from pathlib import Path
import numpy as np,json
roots=[Path('/home/lzz/tare_native_campus_repeat_20261118/analysis'),Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/mesh/campus')]
for root in roots:
 for p in root.iterdir():
  print(p,p.stat().st_size)
  if p.suffix=='.npz':
   z=np.load(p);print([(k,z[k].shape,str(z[k].dtype)) for k in z.files])
