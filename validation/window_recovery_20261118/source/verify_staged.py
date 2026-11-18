import pathlib,subprocess,json,hashlib,gzip
repo=pathlib.Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');prefix='validation/window_recovery_20261118/'
def blob(path):return subprocess.check_output(['git','-C',str(repo),'show',':'+path])
m=json.loads(blob(prefix+'DELIVERY_MANIFEST.json'))
for f in m['files']:
 b=blob(prefix+f['file']);assert len(b)==f['bytes'] and hashlib.sha256(b).hexdigest()==f['sha256'],f['file']
raw=gzip.decompress(blob(prefix+'fixture/campus_stop.cdr.gz'));assert hashlib.sha256(raw).hexdigest()==json.loads(blob(prefix+'FIXTURE.json'))['sha256']
runtime=json.loads(blob(prefix+'RUNTIME.json'))
for name,h in runtime['git_lf_source_sha256'].items():
 assert hashlib.sha256(blob('src/cmu_local_planner_ht/'+name)).hexdigest()==h,name
 actual=pathlib.Path(runtime['navigation_source'])/name
 assert hashlib.sha256(actual.read_bytes()).hexdigest()==runtime['frozen']['source/'+name],name
print(json.dumps({'manifest_staged_files_verified':len(m['files']),'raw_fixture_decompression_sha_verified':True,'staged_sources_match_compiled_candidate_after_git_eol_normalization':True}))
