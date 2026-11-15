from pathlib import Path
import collections,hashlib,json,yaml
from mcap.reader import make_reader

root=Path('/home/lzz/ht_urdf_compare_20261115');out=Path('/mnt/d/HT-URDF-Compare-20261115/analysis');out.mkdir(exist_ok=True)
def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b''):h.update(chunk)
    return h.hexdigest()
allruns=[]
for variant in ['baseline','urdf']:
    run=root/'runs'/f'{variant}_campus_600s_01';counts=collections.Counter();files=[]
    for path in sorted((run/'bag').glob('*.mcap')):
        local=collections.Counter()
        with path.open('rb') as f:
            for _,channel,msg in make_reader(f,validate_crcs=True).iter_messages(log_time_order=False):local[channel.topic]+=1
        counts.update(local);files.append({'name':path.name,'bytes':path.stat().st_size,'sha256':digest(path),'messages':sum(local.values())})
        print(variant,path.name,sum(local.values()),flush=True)
    metadata=run/'bag/metadata.yaml';meta=yaml.safe_load(metadata.read_text())['rosbag2_bagfile_information']
    expected={v['topic_metadata']['name']:v['message_count'] for v in meta['topics_with_message_count'] if v['message_count']}
    assert dict(counts)==expected and sum(counts.values())==meta['message_count']
    frozen=json.loads((run/'FREEZE.json').read_text());changed=[p for p,h in frozen.items() if digest(Path(p))!=h];assert not changed,changed
    for node in ['localPlanner','pathFollower']:
        params=next(iter(yaml.safe_load((run/(node+'.yaml')).read_text()).values()))['ros__parameters']
        assert params['ht_use_urdf_envelope']==(variant=='urdf')
        assert params['ht_min_probability']==.5 and params['ht_map_timeout']==1.
        if variant=='urdf':
            envelope=json.loads((root/'setup/URDF_ENVELOPE.json').read_text())
            for a,b in zip(params['ht_body_min_xyz'],envelope['min_xyz']):assert abs(a-b)<1e-10
            for a,b in zip(params['ht_body_max_xyz'],envelope['max_xyz']):assert abs(a-b)<1e-10
            assert abs(params['ht_validity_radius']-envelope['required_support_radius'])<1e-10
        else:assert params['ht_validity_radius']==.45 and params['vehicleLength']==.6 and params['vehicleWidth']==.6
    evidence={'variant':variant,'message_count':sum(counts.values()),'topic_counts':dict(counts),'files':files,'metadata_sha256':digest(metadata),'available_crc_validation_passed':True,'metadata_counts_match':True,'final_frozen_file_count':len(frozen),'changed_frozen_files':changed,'effective_parameters_verified':True}
    allruns.append(evidence)
(out/'RECORDING_VALIDATION.json').write_text(json.dumps(allruns,indent=2))
before=[json.loads((root/'runs'/f'{v}_campus_600s_01/FREEZE.json').read_text()) for v in ['baseline','urdf']]
assert before[0]==before[1]
(out/'BETWEEN_RUNS_FREEZE_CHECK.json').write_text(json.dumps({'identical':True,'files':len(before[0]),'difference':'Runtime launch argument envelope only; both pre-generated configs included in identical frozen files.'},indent=2))
budget=json.loads((root/'BUDGET.json').read_text());budget['closed']=True;budget['reason']='Both planned 600s runs finished; no extra candidate or retry required.'
for a in budget['attempts']:a['collection_complete']=True
(root/'BUDGET.json').write_text(json.dumps(budget,indent=2))
print('PAIR_RECORDINGS_VALIDATED')
