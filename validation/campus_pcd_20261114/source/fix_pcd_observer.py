from pathlib import Path
import shutil,importlib.util,json,math
r=Path('/home/lzz/ht_campus_pcd_20261114');p=r/'startup_collect.py';backup=r/'setup/collect_before_nonfinite.py'
if not backup.exists():shutil.copy2(p,backup)
s=backup.read_text()
helper='''def json_safe_payload(data,path='data'):
 if isinstance(data,float) and not math.isfinite(data):return None,[{'path':path,'original':repr(data)}]
 if isinstance(data,dict):
  out={};fields=[]
  for key,value in data.items():
   out[key],bad=json_safe_payload(value,path+'.'+str(key));fields+=bad
  return out,fields
 if isinstance(data,list):
  out=[];fields=[]
  for i,value in enumerate(data):
   clean,bad=json_safe_payload(value,path+'['+str(i)+']');out.append(clean);fields+=bad
  return out,fields
 return data,[]

'''
s=s.replace('class Collect(Node):',helper+'class Collect(Node):')
old="  self.count[name]+=1;self.events.write(json.dumps({'time':self.get_clock().now().nanoseconds/1e9,'kind':name,'data':data},allow_nan=False)+'\\n')"
new="""  self.count[name]+=1;clean,fields=json_safe_payload(data)
  event={'time':self.get_clock().now().nanoseconds/1e9,'kind':name,'data':clean}
  if fields:
   event['nonfinite_fields']=fields;self.count['nonfinite_events']+=1;self.count['nonfinite_'+name]+=1
  self.events.write(json.dumps(event,allow_nan=False)+'\\n')"""
assert old in s;s=s.replace(old,new);p.write_text(s)
spec=importlib.util.spec_from_file_location('collector',str(p));m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
clean,fields=m.json_safe_payload({'x':float('nan'),'y':float('inf'),'z':-.1})
assert clean=={'x':None,'y':None,'z':-.1} and len(fields)==2
assert m.json_safe_payload({'x':1.,'points':[[1.,2.]]})==({'x':1.,'points':[[1.,2.]]},[])
json.dumps({'data':clean,'nonfinite_fields':fields},allow_nan=False)
(r/'setup/observer_nonfinite_test.log').write_text('PASS: finite events unchanged; NaN/Inf become null with exact field/original markers; strict JSON encoding succeeds.\n')
print('Observer-only robustness fix passed; navigation binaries unchanged')
