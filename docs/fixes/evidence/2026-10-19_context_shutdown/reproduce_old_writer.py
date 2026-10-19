from pathlib import Path
import tempfile,gc,sys
import numpy as np
errors=[];sys.unraisablehook=lambda e:errors.append(str(e.exc_value));old=np.lib.format.write_array
with tempfile.TemporaryDirectory() as directory:
 p=Path(directory)/'old.npz';calls=0
 def interrupted(*args,**kwargs):
  global calls
  calls+=1;old(*args,**kwargs)
  if calls==1:raise KeyboardInterrupt('injected shutdown during compression')
 np.lib.format.write_array=interrupted
 try:
  with p.open('xb') as stream:np.savez_compressed(stream,first=np.arange(10000),second=np.zeros(10000))
 except KeyboardInterrupt:pass
 finally:np.lib.format.write_array=old
 gc.collect()
 try:
  with np.load(p) as data:data.files
  print('unexpected readable old file')
 except Exception as error:print(type(error).__name__,str(error))
 print('unraisable close errors:',errors)
 assert errors and any('closed file' in e for e in errors)
print('PASS reproduced interrupted non-atomic diagnostic writing')
