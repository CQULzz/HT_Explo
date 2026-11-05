from pathlib import Path
import numpy as np,json,hashlib
R=Path('/home/w_lzz/ht-iterations-20261105/cycle6');ledger=json.loads((R/'BUDGET.json').read_text())
for entry in ledger['runs']:
 p=R/entry['label'];files=[]
 for file in sorted([*p.glob('*.npy'),*p.glob('*.npz')]):
  loaded=np.load(file,allow_pickle=False)
  if isinstance(loaded,np.lib.npyio.NpzFile):
   with loaded:arrays={k:{'shape':list(loaded[k].shape),'dtype':str(loaded[k].dtype)} for k in loaded.files}
  else:arrays={'array':{'shape':list(loaded.shape),'dtype':str(loaded.dtype)}}
  files.append({'file':file.name,'bytes':file.stat().st_size,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'arrays':arrays})
 for required in ['trajectory.npy','free_voxel_keys.npy']:
  assert any(f['file']==required for f in files),(p,required)
 out={'scope':'Stored NPY/NPZ structural read and SHA256 integrity, allow_pickle=False. NaN/unknown values are allowed; not a semantic terrain-validity check. Supplements MCAP/video verification, particularly observer teardown -2.','files':files,'all_loaded':True}
 (p/'ARRAY_VERIFICATION.json').write_text(json.dumps(out,indent=2));print(entry['label'],len(files),'array archives readable')
