import os,json,importlib.util
from pathlib import Path
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource,FrontendLaunchDescriptionSource
from ament_index_python.packages import get_package_share_directory
HERE=Path(__file__).resolve().parent

def generate_launch_description():
 share=Path(get_package_share_directory('vehicle_simulator'));spec=importlib.util.spec_from_file_location('cmu_vehicle',share/'launch/vehicle_simulator.launch');module=importlib.util.module_from_spec(spec) if spec else None
 # .launch has no registered Python suffix: load explicitly.
 from importlib.machinery import SourceFileLoader
 module=SourceFileLoader('cmu_vehicle',str(share/'launch/vehicle_simulator.launch')).load_module()
 import shlex
 def custom_server(context,world_name):
  return [IncludeLaunchDescription(PythonLaunchDescriptionSource(str(Path(get_package_share_directory('ros_gz_sim'))/'launch/gz_sim.launch.py')),launch_arguments={'gz_args':'-r -s --physics-engine libgz-physics-tpe-plugin '+shlex.quote(str(HERE/'assets/mountain.world'))}.items())]
 module.start_gzserver=custom_server
 # Keep CMU robot/controller unchanged; optional downward sensing for paired evaluation.
 from launch_ros.actions import Node
 original_node=module.Node
 def custom_node(*args,**kwargs):
  if os.environ.get('HT_DOWNWARD_LIDAR')=='1' and kwargs.get('executable')=='create':
   arguments=kwargs.get('arguments',[])
   mapping={'lidar.sdf':'lidar_downward.sdf','robot.sdf':'robot_sensor_mask.sdf','camera.sdf':'camera_sensor_mask.sdf'}
   kwargs['arguments']=[str(HERE/'assets'/mapping[Path(v).name]) if isinstance(v,str) and '/urdf/' in v and Path(v).name in mapping else v for v in arguments]
  return original_node(*args,**kwargs)
 module.Node=custom_node
 vehicle=module.generate_launch_description()
 from launch.actions import SetLaunchConfiguration
 x,y,z=json.loads((HERE/'assets/terrain.json').read_text())['spawn_ground_xyz']
 actions=[SetLaunchConfiguration(k,str(v)) for k,v in dict(vehicleX=x,vehicleY=y,vehicleZ=z,terrainZ=z,gui='false',use_sim_time='false').items()]
 for pkg in ['local_planner','terrain_analysis','terrain_analysis_ext','sensor_scan_generation']:
  actions.append(IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(Path(get_package_share_directory(pkg))/'launch'/f'{pkg}.launch')),launch_arguments={'autonomySpeed':'0.5','goalX':str(x),'goalY':str(y)}.items() if pkg=='local_planner' else {}))
 return LaunchDescription(actions+list(vehicle.entities))
