from pathlib import Path
import collections,hashlib,json,yaml,tarfile,numpy as np
from mcap.reader import make_reader
from rclpy.serialization import deserialize_message
from rosidl_runtime_py.utilities import get_message
r=Path('/home/lzz/ht_helios_collision_20261115');out=Path('/mnt/d/HT-Helios-Collision-20261115/analysis');out.mkdir(exist_ok=True)
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(4*1024**2),b''):h.update(block)
 return h.hexdigest()
results=[]
for run in sorted((r/'runs').iterdir()):
 counts=collections.Counter();files=[];stamps=[];nonzero=0;status=[]
 for p in sorted((run/'bag').glob('*.mcap')):
  with p.open('rb') as f:
   for schema,ch,m in make_reader(f,validate_crcs=True).iter_messages(log_time_order=False):
    counts[ch.topic]+=1
    if ch.topic=='/cmd_vel':
     msg=deserialize_message(m.data,get_message(schema.name));v=msg.twist if hasattr(msg,'twist') else msg
     nonzero+=int(abs(v.linear.x)>1e-7 or abs(v.angular.z)>1e-7)
    elif ch.topic=='/helios_sim/scan_status':
     msg=deserialize_message(m.data,get_message(schema.name));status.append(json.loads(msg.data));stamps.append(m.log_time/1e9)
  files.append({'file':p.name,'bytes':p.stat().st_size,'sha256':sha(p)})
 meta=yaml.safe_load((run/'bag/metadata.yaml').read_text())['rosbag2_bagfile_information'];expected={v['topic_metadata']['name']:v['message_count'] for v in meta['topics_with_message_count'] if v['message_count']}
 assert dict(counts)==expected and sum(counts.values())==meta['message_count']
 frozen=json.loads((run/'FREEZE.json').read_text());checked={}
 with tarfile.open(run/'frozen_runtime.tar.gz','r:gz') as a:
  for member in a:
   if member.isfile():checked['/'+member.name]=hashlib.sha256(a.extractfile(member).read()).hexdigest()
 assert checked==frozen
 reasons=collections.Counter();last={}
 for line in (run/'observations/events.jsonl').read_text().splitlines():
  event=json.loads(line);kind=event['kind'];d=event.get('data',{})
  if kind.endswith('command_audit'):reasons[d.get('reason',str(d.get('allowed','unknown')))]+=1
  if kind in ['/ht_minimal/localPlanner','/ht_minimal/pathFollower']:last[kind]=d
 item={'run':run.name,'available_crc_checks_passed':True,'metadata_counts_match':True,'frozen_archive_matches_original_manifest':True,'frozen_files':len(frozen),'files':files,'topic_counts':dict(counts),'nonzero_commands':nonzero,'scan_status_receipt_rate_hz':(len(stamps)-1)/(max(stamps)-min(stamps)) if len(stamps)>1 else None,'median_forwarded_points':float(np.median([s['forwarded'] for s in status])) if status else None,'command_audit_reasons':dict(reasons),'last_gate_status':last,'acceptance_scope':'Mount-origin development model only; final optical-datum assets were corrected afterwards. Not navigation acceptance for final source.'}
 results.append(item);print(run.name,'validated',sum(counts.values()),'messages',flush=True)
(out/'RECORDING_VALIDATION.json').write_text(json.dumps(results,indent=2))
source=[];repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes')
for p in (repo/'src/helios32_sim').rglob('*'):
 if p.is_file():
  compiled=r/'project/src/helios32_sim'/p.relative_to(repo/'src/helios32_sim')
  assert p.read_bytes()==compiled.read_bytes(),str(p)
  source.append({'file':str(p.relative_to(repo)),'sha256':sha(p)})
(out/'COMPILED_SOURCE_CHECK.json').write_text(json.dumps({'passed':True,'files':source},indent=2))
budget=json.loads((r/'BUDGET.json').read_text());budget.update(closed=True,reason='Two development formal attempts retained. Final optical-datum correction verified by static and 90-degree registration probes; no corrected 600s navigation acceptance claimed.')
for v in budget['attempts']:
 result=json.loads((r/'runs'/v['name']/'RESULT.json').read_text());v['collection_complete']=result['collection_complete']
(r/'BUDGET.json').write_text(json.dumps(budget,indent=2));print('EVIDENCE_VALIDATED')
