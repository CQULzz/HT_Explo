from pathlib import Path
import json,shutil,hashlib,ast,numpy as np
root=Path('/home/lzz/ht_tare_coverage_diagnosis_20261118');work=Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118');out=work/'results';out.mkdir(exist_ok=True)
for name in ['REPORT_zh.md','PARAMETER_DIFF.json','corrected_observation_comparison.png','R1_mesh_path.png','regional_geometry.png']:
 shutil.copy2(work/name,out/name)
for p in root.iterdir():
 if p.suffix in ['.json','.csv','.txt'] and p.name!='MESH_INDEX.json':shutil.copy2(p,out/p.name)
arrays={}
for name in ['R1_proxy_path.npy','R1_unmatched_all_frames.npy','native_pre_finish_filtered_frontier_cloud.npy','native_pre_finish_uncovered_cloud.npy','ht_pre_finish_filtered_frontier_cloud.npy','ht_pre_finish_uncovered_cloud.npy']:
 arrays[name[:-4]]=np.load(root/name)
np.savez_compressed(out/'REGION_AND_TERMINAL_POINTS.npz',**arrays)
# Compact full-range real return voxel centers support independent recomputation; no raw bag or original mesh.
np.savez_compressed(out/'FULL_RANGE_OBSERVED_VOXELS.npz',native=np.load(root/'native_full_range_sampled_observations.npy'),ht=np.load(root/'ht_full_range_sampled_observations.npy'))
source=out/'reproduce';source.mkdir(exist_ok=True)
for p in work.glob('*.py'):
 q=source/p.name;q.write_bytes(p.read_bytes().replace(b'\r\n',b'\n'));ast.parse(q.read_text(encoding='utf-8-sig'))
q=out/'REPORT_zh.md';q.write_bytes(q.read_bytes().replace(b'\r\n',b'\n'))
(out/'.gitattributes').write_text('* -text\n*.csv whitespace=cr-at-eol\nHT_FINISH_LOG_CONTEXT.txt -whitespace\n')
inputs={'native_raw':'/home/lzz/tare_native_campus_repeat_20261118/runs/native_campus_02','ht_raw':'/home/lzz/ht_campus_to_finish_20261118/runs/campus_to_finish_01','native_code_and_raw_integrity_index':'../tare_native_campus_20261118/','ht_code_and_raw_integrity_index':'../campus_to_finish_20261118/','new_gazebo_runs':0,'navigation_modified':False,'comparison_is_causal_ablation':False,'missing_original_native_cell_trace':True,'raw_scans_in_existing_bags_unchanged':True,'only_observation_evaluation_distance_filter_removed':True}
(out/'INPUTS_AND_SCOPE.json').write_text(json.dumps(inputs,indent=2))
assert json.loads((out/'PARAMETER_DIFF.json').read_text())['tare_planner_node.yaml']=={}
assert json.loads((out/'R1_MESH_PATH_VERIFICATION.json').read_text())['passed']
assert json.loads((out/'R1_TURN_ENVELOPE_VERIFICATION.json').read_text())['passed']
a=json.loads((out/'FULL_RANGE_OBSERVATION_CHECK.json').read_text());b=json.loads((out/'HT_FULL_RANGE_OBSERVATION_CHECK.json').read_text());assert .93<a['reference_surface_matched_fraction_full_range_sampled']<.95 and .26<b['reference_surface_matched_fraction_full_range_sampled']<.28
assert a['regions_all_frames_raw_matched'][1]['matched_in_all_raw_scans_full_range']==30
for p in out.rglob('*.json'):json.loads(p.read_text(encoding='utf-8-sig'))
entries=[]
for p in sorted(out.rglob('*')):
 if p.is_file() and p.name!='DATA_MANIFEST.json':entries.append({'file':str(p.relative_to(out)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
(out/'DATA_MANIFEST.json').write_text(json.dumps({'files':entries,'count':len(entries),'bytes':sum(e['bytes'] for e in entries),'scope':'Passive diagnosis, compact source/data only. Existing full raw bags retained locally.'},indent=2));print(json.dumps({'files':len(entries),'bytes':sum(e['bytes'] for e in entries),'assertions_passed':True},indent=2))
