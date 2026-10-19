from pathlib import Path
import shlex,subprocess
root=Path.cwd();build=root/'build_standalone/tare_planner';flags={}
for l in (build/'CMakeFiles/geometry_pose_test.dir/flags.make').read_text().splitlines():
 if ' = ' in l:
  k,v=l.split(' = ',1);flags[k]=shlex.split(v)
with open('/tmp/ht_tare_connectivity_probe_build.log','w') as log:
 subprocess.run(['/usr/bin/c++',*flags['CXX_DEFINES'],*flags['CXX_INCLUDES'],*flags['CXX_FLAGS'],'-c','/tmp/ht_tare_connectivity_probe.cpp','-o','/tmp/ht_tare_connectivity_probe.o'],cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
 link=shlex.split((build/'CMakeFiles/geometry_pose_test.dir/link.txt').read_text());link=['/tmp/ht_tare_connectivity_probe.o' if x.endswith('tests/geometry_pose_test.cpp.o') else x for x in link];link[link.index('-o')+1]='/tmp/ht_tare_connectivity_probe';subprocess.run(link,cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
