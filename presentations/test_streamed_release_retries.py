"""Exercise stalled-upload recovery against a local CLI stub; never access GitHub."""
import hashlib,json,os,subprocess,tempfile,unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STUB=r'''#!/usr/bin/python3
import os,json,sys,time,hashlib,fcntl
from pathlib import Path
a=sys.argv[1:];db=Path(os.environ['HT_TEST_RELEASE_DB'])
with db.with_suffix('.lock').open('a') as lock:
 fcntl.flock(lock,fcntl.LOCK_EX)
 state=json.loads(db.read_text()) if db.exists() else {'assets':[],'stalled':False,'uploads':0}
 if a[:2]==['release','list']:print(json.dumps([{'tagName':'fixture'}]))
 elif a[:2]==['release','edit']:pass
 elif a[0]=='api' and '/git/ref/' in a[1]:print(json.dumps({'object':{'type':'commit','sha':os.environ['HT_TEST_COMMIT']}}))
 elif a[0]=='api':print(json.dumps({'assets':state['assets']}))
 elif a[:2]==['release','upload']:
  state['uploads']+=1
  if not state['stalled']:
   state['stalled']=True;db.write_text(json.dumps(state));time.sleep(10)
  p=Path(a[3]);state['assets'].append({'name':p.name,'size':p.stat().st_size,'state':'uploaded','digest':'sha256:'+hashlib.sha256(p.read_bytes()).hexdigest()})
  db.write_text(json.dumps(state))
 else:raise SystemExit('Unexpected stub operation')
'''

class UploadDeadline(unittest.TestCase):
 def test_stalled_attempt_retries_and_preserves_source(self):
  with tempfile.TemporaryDirectory() as temporary:
   root=Path(temporary);bin_dir=root/'bin';bin_dir.mkdir();gh=bin_dir/'gh';gh.write_text(STUB);gh.chmod(0o755)
   def git(*args):return subprocess.check_output(['git',*args],cwd=root,text=True).strip()
   git('init','-q','-b','main');(root/'marker').write_text('local fixture, not measured experiment data\n')
   git('add','marker');git('-c','user.name=Fixture','-c','user.email=fixture@local','commit','-qm','fixture')
   head=git('rev-parse','HEAD');git('tag','fixture')
   suite=root/'suite';trial=suite/'garage';trial.mkdir(parents=True);selected=root/'selected';selected.mkdir()
   def write(p,x):p.write_text(json.dumps(x))
   write(suite/'suite.json',dict(duration_s=600,git_head=head,state='COMPLETED',runs=[dict(scenario='garage',state='RECORDED')]))
   write(trial/'manifest.json',dict(git_head=head));write(trial/'summary.json',dict(duration_s=600))
   write(trial/'COMPLETED.json',{});write(trial/'suite_validation.json',dict(checks=dict(timer_completed=True)))
   (selected/'report.txt').write_text('simulated release fixture\n')
   write(selected/'files_sha256.json',{'report.txt':hashlib.sha256((selected/'report.txt').read_bytes()).hexdigest()})
   notes=root/'notes.txt';notes.write_text('fixture, no remote writes');receipt=root/'receipt.json'
   original={str(p.relative_to(suite)):p.read_bytes() for p in suite.rglob('*') if p.is_file()}
   env=os.environ.copy();env.update(PATH=str(bin_dir)+os.pathsep+env['PATH'],HT_TEST_RELEASE_DB=str(root/'db.json'),HT_TEST_COMMIT=head)
   result=subprocess.run(['python3',str(ROOT/'scripts/publish_streamed_ht_trial.py'),'--suite',str(suite),'--archive',str(selected),'--tag','fixture','--title','fixture','--notes',str(notes),'--receipt',str(receipt),'--upload-timeout-seconds','.2'],cwd=root,env=env,capture_output=True,text=True,timeout=30)
   self.assertEqual(result.returncode,0,result.stdout+result.stderr)
   self.assertIn('TimeoutExpired',result.stdout)
   actual=json.loads(receipt.read_text());self.assertTrue(actual['verified_at'])
   self.assertEqual(actual['publication_status'],'COMPLETE_VALIDATED_COLLECTION')
   self.assertEqual(original,{str(p.relative_to(suite)):p.read_bytes() for p in suite.rglob('*') if p.is_file()})
   state=json.loads((root/'db.json').read_text());self.assertTrue(state['stalled'])
   self.assertGreater(state['uploads'],len(state['assets']))

if __name__=='__main__':unittest.main()
