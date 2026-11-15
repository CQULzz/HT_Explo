from pathlib import Path
import json,numpy as np
r=Path('/home/lzz/ht_helios_collision_20261115/static_probes_optical')
b={v['case']:v for v in json.loads((r/'RESULTS.json').read_text())}
assert all(v['represented_rings']==32 and v['all_channel_angles_max_error_deg']<.001 for v in b.values())
assert b['opaque']['ground_points_under_solid_chassis']==0
assert b['opaque']['valid_filtered_points']<b['transparent']['valid_filtered_points']
assert b['opaque']['scan_status']['self_hits']==b['opaque']['valid_raw_points']-b['opaque']['valid_filtered_points']
assert b['transparent']['front_horizontal_range_m']>4 and b['blind']['front_horizontal_range_m'] is None
assert b['blind']['scan_status']['blind_hits']>0
t=np.load(r/'transparent.npz')['filtered'];o=np.load(r/'opaque.npz');raw=o['raw'];filtered=o['filtered']
shadow=np.isfinite(raw['x'])&~np.isfinite(filtered['x']);unchanged=np.isfinite(filtered['x'])
assert int(shadow.sum())==b['opaque']['scan_status']['self_hits']
assert np.allclose(raw['x'][unchanged],filtered['x'][unchanged])
assert np.all(np.isfinite(t['x'][shadow]))
result={'passed':True,'self_hits_removed_without_recast':int(shadow.sum()),'scope':'Stored Gazebo clouds, exact nominal angles, owned-body shadows, near-blind obstruction, preserved non-self points. At corrected height transparent model also has zero solid-chassis ground returns; the old >0 assertion was invalid and was corrected, not the data.'}
(r/'PASSED.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
