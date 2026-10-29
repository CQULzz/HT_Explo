from pathlib import Path
import json,numpy as np,hashlib
O=Path(__file__).parent; PREV=Path('/media/lzz/My Passport/HT_body_occlusion_fix_2026-10-29')
checks={}
for case in ['moving','stationary']:
 a=O/case;b=PREV/('frozen_registered_'+case);x=json.loads((a/'RESULTS.json').read_text());y=json.loads((b/'RESULTS.json').read_text());assert len(x['frames'])==len(y['frames'])
 for u,v in zip(x['frames'],y['frames']):
  assert u['stamp_ns']==v['stamp_ns']
  with np.load(a/'frames'/u['file']) as p,np.load(b/'frames'/v['file']) as q:
   assert set(p.files)==set(q.files)
   assert all(np.array_equal(p[k],q[k],equal_nan=True) for k in p.files)
 checks[case]={'all_arrays_identical_to_previous':True,'outputs':x['outputs'],'input_scans':x['input_scans'],'integrated':x['integrated']}
freeze=json.loads((O/'FREEZE.json').read_text());assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in freeze['source_sha256'].items())
print(json.dumps(checks,indent=2))
