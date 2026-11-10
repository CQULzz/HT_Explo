"""Run the unmodified real-vehicle planner in CMU, without hardware drivers."""
from pathlib import Path
from importlib.machinery import SourceFileLoader
from launch import LaunchDescription
from launch.actions import OpaqueFunction
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import yaml

HERE=Path(__file__).resolve().parent
OLD=Path('/home/lzz/HT_Explo_review')

def start(context):
    shared=SourceFileLoader('common_cmu_sim',str(HERE.parent/'cmu_minimal/simulation.launch.py')).load_module()
    context.launch_configurations.update(mode='native',sensor='downward')
    # First four actions are official vehicle, terrain, terrain-ext and scan generation.
    actions=shared.start(context)[:4]
    old=SourceFileLoader('old_real_launch',str(OLD/'src/ht_scout_bridge/launch/scout_real.launch.py')).load_module()
    config=OLD/'src/ht_scout_bridge/config'
    profile=yaml.safe_load((config/'ht_real.yaml').read_text())['/**']['ros__parameters']
    mapped,physical=old.direction_evidence(str(config/'direction_validation.yaml'),
        str(OLD/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'),
        profile['ht_channel_order'],profile['ht_heading_offset'])
    if not mapped:raise RuntimeError('Old direction mapping evidence does not match weights')
    common={'use_sim_time':False,'odometry_child_frame':'base_link',
            'ht_topic':'/ht_real/traversability','ht_directions_calibrated':True}
    actions.extend([
        Node(package='tare_planner',executable='tare_planner_node',namespace='ht_real',name='tare_planner_node',
             output='screen',remappings=old.HARDWARE_REMAPS,
             parameters=[str(config/'tare_scout.yaml'),str(config/'ht_real.yaml'),common,
                         {'sensor_origin_offset':[0.0,0.0,0.51521]}]),
        Node(package='tare_planner',executable='xytheta_follower',namespace='ht_real',name='xytheta_follower',
             output='screen',remappings=old.HARDWARE_REMAPS,
             parameters=[str(config/'ht_real.yaml'),common,{'odometry_topic':'/ht_real/odometry',
                         'registered_scan_topic':'/ht_real/registered_scan',
                         'command_topic':'/cmd_vel','command_frame':'base_link'}]),
    ])
    return actions

def generate_launch_description():
    return LaunchDescription([OpaqueFunction(function=start)])
