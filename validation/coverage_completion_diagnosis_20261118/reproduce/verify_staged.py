from pathlib import Path
import subprocess,json,hashlib,ast
repo=Path('/mnt/c/Users/李哲舟/Desktop/python code/work/ht_execution_fixes');relative='validation/coverage_completion_diagnosis_20261118';root=repo/relative
manifest=json.loads((root/'DATA_MANIFEST.json').read_text());git='/mnt/c/Program Files/WindowsApps/OpenAI.CodexPrimaryRuntime.v26-1112-737-0_26.1112.737.0_x64__3k8sg7r9htsxt/dependencies/native/git/cmd/git.exe';windows_repo='C:/Users/李哲舟/Desktop/python code/work/ht_execution_fixes'
p=subprocess.Popen([git,'-C',windows_repo,'cat-file','--batch'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
for e in manifest['files']:
 file=root/e['file'];data=file.read_bytes();assert len(data)==e['bytes'] and hashlib.sha256(data).hexdigest()==e['sha256'],e['file']
 if file.suffix=='.json':json.loads(data.decode('utf-8-sig'))
 if file.suffix=='.py':ast.parse(data.decode('utf-8-sig'))
 p.stdin.write((':'+relative+'/'+e['file']+'\n').encode());p.stdin.flush();header=p.stdout.readline().decode().split();assert header[1]=='blob',header;blob=p.stdout.read(int(header[2]));assert p.stdout.read(1)==b'\n';assert blob==data,e['file']
p.stdin.close();assert p.wait()==0
out={'staged_files_checked':len(manifest['files']),'all_staged_bytes_match_sha256_manifest':True,'all_json_and_python_parse':True,'data_manifest_sha256':hashlib.sha256((root/'DATA_MANIFEST.json').read_bytes()).hexdigest()}
Path('/mnt/d/HT-TARE-Coverage-Diagnosis-20261118/STAGED_VERIFICATION.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
