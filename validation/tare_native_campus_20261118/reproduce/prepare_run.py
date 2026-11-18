from pathlib import Path
import ast, hashlib, json, shutil, xml.etree.ElementTree as ET
root=Path('/home/lzz/tare_native_campus_20261118');work=Path('/mnt/d/TARE-Native-Campus-20261118')
for name in ['simulation.launch.py','run.py']:
    text=(work/name).read_text();ast.parse(text);(root/name).write_text(text)
old=Path('/home/lzz/ht_campus_to_finish_20261118')
shutil.copy2(old/'mission_stop.py',root/'mission_stop.py')
text=(old/'startup_collect.py').read_text().replace('from grid_map_msgs.msg import GridMap\n','')
text=text.replace("  self.create_subscription(GridMap,'/ht_traversability/global_local',self.ht,1)\n",'')
begin=text.index("  for topic in ['/ht_minimal/recovery'")
end=text.index('\n def diagnostic',begin)
text=text[:begin]+text[end:]
text=text.replace('.1725','0.0')
text=text.replace("n.last_ht is not None and 0<=now-n.last_ht<=1. and ",'')
ast.parse(text);(root/'observer.py').write_text(text)
for name in ['recording_qos.yaml','mcap.yaml']:shutil.copy2(old/name,root/name)
source=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator/world/campus.world')
tree=ET.parse(source);world=tree.getroot().find('world')
removed=[]
for element in list(world.findall('plugin')):
    if element.get('filename')=='librotors_gazebo_ros_interface_plugin.so':removed.append(element.attrib);world.remove(element)
tree.write(root/'campus.world',encoding='unicode',xml_declaration=True)
for name in ['CAMPUS_REFERENCE_05M.npz','CAMPUS_REFERENCE.json','REFERENCE_GROUND_PROXY.npz','REFERENCE_GROUND_PROXY.json']:shutil.copy2(old/'analysis'/name,root/'analysis'/name)
with (root/'env.sh').open('a') as file:file.write('\nsource /home/lzz/tare_native_campus_20261118/project/install/local_setup.bash\n')
plan={'purpose':'Native upstream TARE/AEDE campus reference mission through completion/return; no HT adaptation','navigation_source':{'tare_commit':'b6760adb4280b379567c76f4e684ce628e28ef71','cmu_commit':'158e67b31b644ed1e8b06eb1d7f70e183cc62591','source_verification':'GitHub pinned tree blob IDs;2401 TARE package files restored to upstream before one documented ROS2 parameter binding line;66 CMU files identical','shared_sources_modified':False},'configuration':{'sensor':'native VLP16 xacro,16 beams,6.3Hz simulated,350 horizontal samples','local_planner':'native local_planner package,geometry collision/traversability','vehicle_xy_m':[.6,.6],'vehicleHeight_m':.75,'sensor_offset_xy_m':[0.,0.],'maxSpeed_mps':2.,'autonomySpeed_mps':2.,'tare_yaml':'unmodified upstream campus.yaml, except kAutoStart false until passive input readiness'},'ht':{'mapper':False,'neural_inference':False,'command_gate':False,'recovery_adapter':False},'isolation':{'domain':205,'gazebo_port':11589,'display':':109'},'infrastructure_only_changes':{'spawn_delays_s':[120,122,124],'carrier_delay_s':150,'headless':True,'removed_unavailable_world_plugins':removed,'frontier_parameter_declaration_patch':'setup/frontier_ros2_parameter.patch'},'termination':'No20min cap. finish+home<=0.5m+zero/fresh/stationary20s. Persistent300s stagnation is failure, not completion. Input/process/disk failures retained.','comparison_limit':'Reference configuration differs from HT Scout/Helios0.5mps; cannot attribute differences only to HT. One mission cannot establish broad stability.','raw_upload':False}
(root/'PLAN.json').write_text(json.dumps(plan,indent=2))
(root/'BUDGET.json').write_text(json.dumps({'maximum_formal_launch_attempts':2,'planned_successful_runs':1,'extra_attempt':'Infrastructure retry only','termination':'task_outcome','duration_s':None,'attempts':[],'status':'active','authorization':'2026-11-18 user explicitly requested direct native TARE campus exploration'},indent=2))
(root/'run_native.sh').write_text('''set -e
R=/home/lzz/tare_native_campus_20261118
source "$R/env.sh"
Xvfb :109 -screen 0 1920x1080x24 -ac > "$R/setup/xvfb.log" 2>&1 &
xvfb_pid=$!
trap 'kill "$xvfb_pid" 2>/dev/null || true' EXIT
python3 "$R/run.py" > "$R/setup/run.log" 2>&1
''')
monitor=Path('/mnt/d/HT-Campus-To-Finish-20261118/monitor.py').read_text().replace('/home/lzz/ht_campus_to_finish_20261118','/home/lzz/tare_native_campus_20261118').replace('campus_to_finish_01','native_campus_01')
monitor=monitor.replace("if 'EXPLORATION_DIAG' in x", "if any(k in x for k in ['Exploration finished','exploration finished','Exploration is finished','Returning home'])")
(work/'monitor.py').write_text(monitor)
print('Prepared native mission, no HT processes or constraints')
