from pathlib import Path
from importlib.machinery import SourceFileLoader
import json
from launch import LaunchDescription
from launch.actions import OpaqueFunction,IncludeLaunchDescription,DeclareLaunchArgument,TimerAction
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
ROOT=Path('/home/lzz/ht_campus_pcd_20261114');PCD=Path('/home/lzz/pcd_test_20261110/runtime');COMMON=Path('/home/lzz/cmu_test_20261110/common_sensor')
def start(context):
 scene=LaunchConfiguration('scene').perform(context)
 if scene not in ['user_pcd','indoor','campus']:raise ValueError(scene)
 source=Path(get_package_share_directory('vehicle_simulator'))/'launch/vehicle_simulator.launch'
 module=SourceFileLoader('ht_only_vehicle',str(source)).load_module();original=module.Node
 spawn_index=[0]
 if scene=='campus':module.TimerAction=lambda **kw: TimerAction(period=90.,actions=kw['actions'])
 def node(*args,**kwargs):
  if kwargs.get('package')=='robot_state_publisher':kwargs['parameters']=[{'use_sim_time':False,'robot_description':(COMMON/'lidar.urdf').read_text()}]
  if kwargs.get('package')=='gazebo_ros' and kwargs.get('executable')=='spawn_entity.py':kwargs['arguments']=[str(COMMON/'robot.sdf') if isinstance(a,str) and a.endswith('/urdf/robot.sdf') else a for a in kwargs.get('arguments',[])]
  if scene=='campus' and kwargs.get('package')=='gazebo_ros' and kwargs.get('executable')=='spawn_entity.py':
   arguments=kwargs.get('arguments',[])
   arguments=[str(ROOT/'scene_assets/camera_without_sensor.sdf') if isinstance(a,str) and a.endswith('/urdf/camera.urdf.xacro') else a for a in arguments]
   kwargs['arguments']=[*arguments,'-timeout','180.0']
   result=original(*args,**kwargs);delay=60.+spawn_index[0]*2.;spawn_index[0]+=1
   return TimerAction(period=delay,actions=[result])
  return original(*args,**kwargs)
 module.Node=node
 context.launch_configurations.update(world_name=('indoor' if scene=='user_pcd' else scene),gui='false',use_sim_time='false',verbose='true',world=str(COMMON/'indoor.world'))
 if scene=='campus':context.launch_configurations.update(world=str(ROOT/'scene_assets/campus.world'))
 if scene=='user_pcd':
  config=json.loads((PCD/'SCENE_MANIFEST.json').read_text())
  context.launch_configurations.update(world=str(PCD/'recorded_map.world'),vehicleX=str(config['spawn_xy'][0]),vehicleY=str(config['spawn_xy'][1]),vehicleZ=str(config['sensor_spawn_z']),terrainZ=str(config['ground_z_at_spawn']),vehicleYaw='0.0')
 def include(package,file,**args):return IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(Path(get_package_share_directory(package))/'launch'/file)),launch_arguments=args.items())
 params=[str(Path(get_package_share_directory('tare_planner'))/('campus.yaml' if scene=='campus' else 'indoor.yaml')),{'kAutoStart':False}]
 if scene=='user_pcd':params[-1].update(kUseCoverageBoundaryOnFrontier=True,kUseCoverageBoundaryOnObjectSurface=True)
 return [module.generate_launch_description(),include('terrain_analysis','terrain_analysis.launch'),include('terrain_analysis_ext','terrain_analysis_ext.launch',checkTerrainConn='false'),include('sensor_scan_generation','sensor_scan_generation.launch'),IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(ROOT/'runtime'/f'{scene}_local_planner.launch.xml')),launch_arguments={'maxSpeed':'.5','autonomySpeed':'.5'}.items()),Node(package='tare_planner',executable='tare_planner_node',name='tare_planner_node',output='screen',parameters=params)]
def generate_launch_description():return LaunchDescription([DeclareLaunchArgument('scene',default_value='user_pcd'),OpaqueFunction(function=start)])
