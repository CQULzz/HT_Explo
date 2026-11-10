from pathlib import Path
import subprocess,xml.etree.ElementTree as E,hashlib,json
root=Path('/home/lzz/cmu_test_20261110');source=Path('/home/lzz/cmu_sim_20261110/src/vehicle_simulator');out=root/'common_sensor';out.mkdir(exist_ok=False)
xacro=subprocess.check_output(['xacro',str(source/'urdf/lidar.urdf.xacro')])
robot=E.fromstring(xacro)
for parent in robot.iter():
 for child in list(parent):
  if child.tag=='collision':parent.remove(child)
for scan in robot.findall('.//scan'):
 v=scan.find('vertical');v.find('samples').text='64';v.find('min_angle').text='-1.3089969389957472';v.find('max_angle').text='0.2617993877991494'
E.ElementTree(robot).write(out/'lidar.urdf',encoding='unicode')
r=E.parse(source/'urdf/robot.sdf')
for parent in r.iter():
 for child in list(parent):
  if child.tag=='collision':parent.remove(child)
r.write(out/'robot.sdf')
w=E.parse(source/'world/indoor.world')
for parent in w.iter():
 for child in list(parent):
  if child.tag=='plugin' and child.get('filename')=='librotors_gazebo_ros_interface_plugin.so':parent.remove(child)
w.write(out/'indoor.world')
manifest={'description':'Shared simulated observation profile: 64 beams, -75 to +15 degrees, stock horizontal sampling and CMU sensor pose; remove only teleported robot/lidar self collisions from ray sensor. Native world collision mesh unchanged. This is not a Helios calibration.','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in out.iterdir()}}
(out/'MANIFEST.json').write_text(json.dumps(manifest,indent=2))
