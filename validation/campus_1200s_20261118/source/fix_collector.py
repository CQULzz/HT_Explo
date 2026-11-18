from pathlib import Path
import json,ast,collections
root=Path('/home/lzz/ht_campus_1200s_20261118');p=root/'startup_collect.py';old=p.read_text();s=old.replace('lambda m,t=topic:self.event(t,json.loads(m.data))','lambda m,t=topic:self.diagnostic(t,m.data)')
needle=' def event(self,name,data):'
method=''' def diagnostic(self,topic,raw):
  try:data=json.loads(raw)
  except json.JSONDecodeError as exc:
   self.count['malformed_'+topic]+=1
   self.event('malformed_diagnostic',{'topic':topic,'raw':raw,'parse_error':str(exc)})
   return
  self.event(topic,data)
'''
assert needle in s and s!=old;s=s.replace(needle,method+needle);tree=ast.parse(s);fn=next(n for n in next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Collect').body if isinstance(n,ast.FunctionDef) and n.name=='diagnostic');space={'json':json};exec(compile(ast.fix_missing_locations(ast.Module(body=[fn],type_ignores=[])),'collector-test','exec'),space)
class Fake:
 def __init__(self):self.count=collections.Counter();self.events=[]
 def event(self,k,d):self.events.append((k,d))
f=Fake();space['diagnostic'](f,'valid','{"x":1}');space['diagnostic'](f,'invalid','{"x":-nan}');space['diagnostic'](f,'invalid','truncated');assert f.events[0]==('valid',{'x':1});assert f.events[1][0]=='malformed_diagnostic' and f.events[1][1]['raw']=='{"x":-nan}';assert len(f.events)==3 and f.count['malformed_invalid']==2
(root/'setup/COLLECTOR_FIX_TEST.json').write_text(json.dumps({'valid_json_preserved':True,'malformed_raw_payload_preserved':True,'callback_continues_after_parse_error':True,'navigation_changed':False,'cases':3},indent=2));(root/'setup/startup_collect_before_json_fix.py').write_text(old);p.write_text(s)
budget=json.loads((root/'BUDGET.json').read_text());budget['maximum_formal_launch_attempts']=3;budget['extension_reason']='One final observation-only retry to fulfill requested1200s: second attempt ended early because JSONDecodeError in observer; no user-imposed attempt cap, original two-attempt bound was agent-planned; all attempts retained';budget['extra_attempt']='One startup retry plus one observer-malformed-JSON retry only; no navigation changes';budget['status']='active';(root/'BUDGET.json').write_text(json.dumps(budget,indent=2))
plan=json.loads((root/'PLAN.json').read_text());plan['observer_retry']={'failed_attempt':'explicit_labels_campus_1200s_02','failure':'Observer JSONDecodeError from malformed diagnostic String; original raw bag retained','fix':'Read-only callback logs raw invalid JSON and parse error then continues; no invalid value converted to valid navigation data','extra_attempts_allowed':1,'tests_passed':3,'navigation_changed':False};(root/'PLAN.json').write_text(json.dumps(plan,indent=2))
p=root/'run_1200s.sh';p.write_text(p.read_text().replace('explicit_labels_campus_1200s_02','explicit_labels_campus_1200s_03').replace('run_retry.log','run_observer_retry.log'))
for name in ['monitor.py','postprocess_long.py','assess_coverage.py','deliver.py','audit.sh']:
 p=Path('/mnt/d/HT-Campus-1200s-20261118')/name;p.write_text(p.read_text().replace('explicit_labels_campus_1200s_02','explicit_labels_campus_1200s_03'))
print('Observer-only fix passed3 checks; final retry planned; previous raw runs preserved')
