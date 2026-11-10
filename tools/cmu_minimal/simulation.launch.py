from pathlib import Path
from importlib.machinery import SourceFileLoader
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,IncludeLaunchDescription,OpaqueFunction
from launch.launch_description_sources import PythonLaunchDescriptionSource,FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

def start(context):
 mode=LaunchConfiguration('mode').perform(context)
 if mode not in ['native','ht']:raise ValueError(mode)
 def include(package,file,python=False,**args):
  cls=PythonLaunchDescriptionSource if python else FrontendLaunchDescriptionSource
  return IncludeLaunchDescription(cls(str(Path(get_package_share_directory(package))/'launch'/file)),launch_arguments=args.items())
 local=Path(get_package_share_directory('local_planner'))/'launch/local_planner.launch'
 if mode=='ht':
  text=local.read_text().replace('pkg="local_planner"','pkg="cmu_local_planner_ht"')
  text=text.replace('<param name="sensorOffsetX"', '<param name="ht_enabled" value="true"/>\n    <param name="ht_validity_radius" value="0.45"/>\n    <param name="sensorOffsetX"')
  local=Path('/home/lzz/cmu_test_20261110/ht_local_planner.launch.xml');local.write_text(text)
 sensor=LaunchConfiguration('sensor').perform(context)
 if sensor not in ['stock','downward']:raise ValueError(sensor)
 vehicle=include('vehicle_simulator','vehicle_simulator.launch',True,world_name='indoor',gui='false',use_sim_time='false',verbose='true')
 if sensor=='downward':
  # Reuse the official vehicle launch; change only the declared shared sensor assets.
  source=Path(get_package_share_directory('vehicle_simulator'))/'launch/vehicle_simulator.launch'
  module=SourceFileLoader('cmu_common_vehicle',str(source)).load_module()
  original=module.Node
  def node(*args,**kwargs):
   if kwargs.get('package')=='robot_state_publisher':
    kwargs['parameters']=[{'use_sim_time':False,'robot_description':Path('/home/lzz/cmu_test_20261110/common_sensor/lidar.urdf').read_text()}]
   if kwargs.get('package')=='gazebo_ros' and kwargs.get('executable')=='spawn_entity.py':
    kwargs['arguments']=[('/home/lzz/cmu_test_20261110/common_sensor/robot.sdf' if isinstance(a,str) and a.endswith('/urdf/robot.sdf') else a) for a in kwargs.get('arguments',[])]
   return original(*args,**kwargs)
  module.Node=node
  vehicle=module.generate_launch_description()
  context.launch_configurations.update({'world_name':'indoor','gui':'false','use_sim_time':'false','verbose':'true','world':'/home/lzz/cmu_test_20261110/common_sensor/indoor.world'})
 return [
  vehicle,
  include('terrain_analysis','terrain_analysis.launch'),
  include('terrain_analysis_ext','terrain_analysis_ext.launch',checkTerrainConn='false'),
  include('sensor_scan_generation','sensor_scan_generation.launch'),
  IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(local)),launch_arguments={'maxSpeed':'.5','autonomySpeed':'.5'}.items()),
  Node(package='tare_planner',executable='tare_planner_node',name='tare_planner_node',output='screen',
       parameters=[str(Path(get_package_share_directory('tare_planner'))/'indoor.yaml'),{'kAutoStart':False}]),
 ]
def generate_launch_description():
 return LaunchDescription([DeclareLaunchArgument('mode',default_value='native'),DeclareLaunchArgument('sensor',default_value='stock'),OpaqueFunction(function=start)])
