from pathlib import Path
from importlib.machinery import SourceFileLoader
import json
from launch import LaunchDescription
from launch.actions import OpaqueFunction,IncludeLaunchDescription
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory

ROOT=Path('/home/lzz/pcd_test_20261110/runtime');COMMON=Path('/home/lzz/cmu_test_20261110/common_sensor')

def start(context):
    config=json.loads((ROOT/'SCENE_MANIFEST.json').read_text())
    source=Path(get_package_share_directory('vehicle_simulator'))/'launch/vehicle_simulator.launch'
    module=SourceFileLoader('user_pcd_vehicle',str(source)).load_module();original=module.Node
    def node(*args,**kwargs):
        if kwargs.get('package')=='robot_state_publisher':
            kwargs['parameters']=[{'use_sim_time':False,'robot_description':(COMMON/'lidar.urdf').read_text()}]
        if kwargs.get('package')=='gazebo_ros' and kwargs.get('executable')=='spawn_entity.py':
            kwargs['arguments']=[str(COMMON/'robot.sdf') if isinstance(a,str) and a.endswith('/urdf/robot.sdf') else a for a in kwargs.get('arguments',[])]
        return original(*args,**kwargs)
    module.Node=node
    context.launch_configurations.update(world_name='user_pcd',gui='false',use_sim_time='false',verbose='true',
        world=str(ROOT/'recorded_map.world'),vehicleX=str(config['spawn_xy'][0]),vehicleY=str(config['spawn_xy'][1]),
        vehicleZ=str(config['sensor_spawn_z']),terrainZ=str(config['ground_z_at_spawn']),vehicleYaw='0.0')
    def include(package,file):
        return IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(Path(get_package_share_directory(package))/'launch'/file)))
    return [module.generate_launch_description(),include('terrain_analysis','terrain_analysis.launch'),
        IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(Path(get_package_share_directory('terrain_analysis_ext'))/'launch/terrain_analysis_ext.launch')),launch_arguments={'checkTerrainConn':'false'}.items()),
        include('sensor_scan_generation','sensor_scan_generation.launch'),
        IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(ROOT/'local_planner.launch.xml')),launch_arguments={'maxSpeed':'.5','autonomySpeed':'.5'}.items()),
        Node(package='tare_planner',executable='tare_planner_node',name='tare_planner_node',output='screen',
            parameters=[str(Path(get_package_share_directory('tare_planner'))/'indoor.yaml'),
                {'kAutoStart':False,'kUseCoverageBoundaryOnFrontier':True,'kUseCoverageBoundaryOnObjectSurface':True}])]

def generate_launch_description():return LaunchDescription([OpaqueFunction(function=start)])
