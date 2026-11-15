"""Current Scout/Helios observation model; old transparent profiles are controls."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
import os,json
from launch import LaunchDescription
from launch.actions import OpaqueFunction,DeclareLaunchArgument,IncludeLaunchDescription,TimerAction,LogInfo,GroupAction
from launch.substitutions import LaunchConfiguration
from launch.launch_description_sources import FrontendLaunchDescriptionSource
from launch_ros.actions import Node,SetParametersFromFile
from ament_index_python.packages import get_package_share_directory
ROOT=Path(os.environ.get('HT_HELIOS_ROOT','/home/lzz/ht_helios_collision_20261115'))
def start(context):
    scene=LaunchConfiguration('scene').perform(context)
    if scene not in ('campus','indoor'):raise ValueError('Unsupported scene')
    common=Path(os.environ.get('HT_HELIOS_ASSETS',str(ROOT/'common_sensor_crop_box')));manifest=json.loads((common/'MANIFEST.json').read_text());height=manifest['lidar_height_above_ground_m'];offset=manifest['base_link_to_lidar_xyz'][0]
    source=Path(get_package_share_directory('vehicle_simulator'))/'launch/vehicle_simulator.launch';module=SourceFileLoader('scout_helios_carrier',str(source)).load_module();original=module.Node;spawn_index=[0]
    if scene=='campus':module.TimerAction=lambda **kw:TimerAction(period=90.,actions=kw['actions'])
    def node(*args,**kwargs):
        if kwargs.get('package')=='robot_state_publisher':kwargs['parameters']=[{'use_sim_time':False,'robot_description':(common/'lidar.urdf').read_text()}]
        if kwargs.get('package')=='vehicle_simulator' and kwargs.get('executable')=='vehicleSimulator':kwargs['package']='helios32_sim'
        if kwargs.get('package')=='gazebo_ros' and kwargs.get('executable')=='spawn_entity.py':
            arguments=kwargs['arguments'];entity=arguments[arguments.index('-entity')+1]
            if entity not in ('robot','lidar','camera'):raise ValueError('Unexpected model')
            kwargs['arguments']=['-entity',entity,'-file',str(common/(entity+'.sdf')),'-x',str(offset),'-y','0','-z',str(height),'-timeout','180.0'];action=original(*args,**kwargs)
            if scene=='campus':
                delay=60.+spawn_index[0]*2.;spawn_index[0]+=1;return TimerAction(period=delay,actions=[action])
            return action
        return original(*args,**kwargs)
    module.Node=node
    context.launch_configurations.update(world_name=scene,world=str(ROOT/'scene_assets'/f'{scene}.world'),gui='false',use_sim_time='false',verbose='true',sensorOffsetX=str(offset),sensorOffsetY='0.0',vehicleHeight=str(height),vehicleX=str(offset),vehicleY='0.0',vehicleZ=str(height),terrainZ='0.0',vehicleYaw='0.0')
    def include(package,file,**args):return IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(Path(get_package_share_directory(package))/'launch'/file)),launch_arguments=args.items())
    return [module.generate_launch_description(),include('terrain_analysis','terrain_analysis.launch'),include('terrain_analysis_ext','terrain_analysis_ext.launch',checkTerrainConn='false'),include('sensor_scan_generation','sensor_scan_generation.launch'),GroupAction([SetParametersFromFile(str(Path(__file__).with_name('initial_support_prior.yaml'))),IncludeLaunchDescription(FrontendLaunchDescriptionSource(str(ROOT/'runtime'/f'{scene}_local_planner.launch.xml')),launch_arguments={'maxSpeed':'.5','autonomySpeed':'.5','sensorOffsetX':str(offset),'sensorOffsetY':'0.0'}.items())]),Node(package='tare_planner',executable='tare_planner_node',name='tare_planner_node',output='screen',parameters=[str(Path(get_package_share_directory('tare_planner'))/f'{scene}.yaml'),{'kAutoStart':False}])]
def generate_launch_description():return LaunchDescription([DeclareLaunchArgument('scene',default_value='campus'),OpaqueFunction(function=start)])
