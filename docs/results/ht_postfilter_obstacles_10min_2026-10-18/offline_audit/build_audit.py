from pathlib import Path
import subprocess,shlex,os
root=Path.cwd();build=root/'build_standalone/tare_planner';out=root/'presentations/scheduled_results/ht_postfilter_obstacles_10min_2026-10-18_16-27-00/indoor/offline_audit';flags={}
for line in (build/'CMakeFiles/ht_ros_test.dir/flags.make').read_text().splitlines():
 if ' = ' in line:
  key,value=line.split(' = ',1);flags[key]=shlex.split(value)
args=['/usr/bin/c++',*flags['CXX_DEFINES'],*flags['CXX_INCLUDES'],*flags['CXX_FLAGS'],'-c',str(out/'resolution_audit.cpp'),'-o',str(out/'resolution_audit.o')]
with (out/'compile.log').open('w') as log:
 subprocess.run(args,cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
 link=shlex.split((build/'CMakeFiles/ht_ros_test.dir/link.txt').read_text());link=[str(out/'resolution_audit.o') if x.endswith('tests/ht_ros_test.cpp.o') else x for x in link];link[link.index('-o')+1]=str(out/'audit');subprocess.run(link,cwd=build,stdout=log,stderr=subprocess.STDOUT,check=True)
env=os.environ.copy();env.update(ROS_DOMAIN_ID='218',HT_FIELD11_FIXTURE=str(out/'field11.txt'))
with (out/'resolution_audit.log').open('w') as log:subprocess.run([str(out/'audit'),'--gtest_filter=HtConfigurationRosTest.FrozenPostfilterStopResolutionAudit'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
