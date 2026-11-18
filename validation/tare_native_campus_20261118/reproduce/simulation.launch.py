"""Headless CMU campus + native terrain/local planning + native TARE."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import OpaqueFunction, TimerAction, IncludeLaunchDescription
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch_ros.actions import Node

ROOT=Path('/home/lzz/tare_native_campus_20261118')

def start(context):
    share=Path(get_package_share_directory('vehicle_simulator'))
    module=SourceFileLoader('native_campus_carrier',str(share/'launch/vehicle_simulator.launch')).load_module()
    original=module.Node;index=[0]
    module.TimerAction=lambda **kw:TimerAction(period=150.,actions=kw['actions'])
    def spawn(*args,**kwargs):
        if kwargs.get('package')=='gazebo_ros' and kwargs.get('executable')=='spawn_entity.py':
            kwargs['arguments']=kwargs['arguments']+['-timeout','180.0']
            action=original(*args,**kwargs);delay=120.+2.*index[0];index[0]+=1
            return TimerAction(period=delay,actions=[action])
        return original(*args,**kwargs)
    module.Node=spawn
    context.launch_configurations.update(world_name='campus',world=str(ROOT/'campus.world'),gui='false',verbose='true',use_sim_time='false',vehicleX='0.0',vehicleY='0.0',vehicleZ='0.0',terrainZ='0.0',vehicleYaw='0.0',vehicleHeight='0.75',sensorOffsetX='0.0',sensorOffsetY='0.0',cameraOffsetZ='0.0')
    def include(package,name,arguments=None):
        return IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(Path(get_package_share_directory(package))/'launch'/name)),launch_arguments=(arguments or {}).items())
    return [module.generate_launch_description(),include('terrain_analysis','terrain_analysis.launch'),include('terrain_analysis_ext','terrain_analysis_ext.launch',{'checkTerrainConn':'false'}),include('sensor_scan_generation','sensor_scan_generation.launch'),include('local_planner','local_planner.launch'),Node(package='tare_planner',executable='tare_planner_node',name='tare_planner_node',output='screen',parameters=[str(Path(get_package_share_directory('tare_planner'))/'campus.yaml'),{'kAutoStart':False}])]

def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=start)])
