"""Simulation-only TARE geometric branch + CMU terrain/local planner/follower.

The current fork's geometric branch is the baseline, not an untouched upstream
binary. HT hardware launch and all HT safety parameters remain unchanged.
"""
from pathlib import Path
import json
import runpy
import numpy as np
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ht_scout_bridge.geometry import load_calibration


def start(context):
    def arg(key):return LaunchConfiguration(key).perform(context)
    tools=Path(__file__).parent
    hw=Path(get_package_share_directory('ht_scout_bridge'))
    remaps=runpy.run_path(str(hw/'launch/scout_real.launch.py'))['HARDWARE_REMAPS']
    _,base,lidar=load_calibration(arg('calibration_file'))
    offset=(np.linalg.inv(base)@lidar)[:3,3].tolist()
    common={'use_sim_time':True}
    data_remaps=[('/state_estimation','/ht_real/odometry'),
        ('/registered_scan','/ht_real/registered_scan'),('/terrain_map','/ht_real/terrain_map'),
        ('/terrain_map_ext','/ht_real/terrain_map_ext'),('/path','/sim/tare/path'),
        ('/way_point','/ht_real/way_point'),('/cmd_vel','/sim/tare/raw_command'),
        ('/stop','/ht_real/stop'),('/speed','/ht_real/speed'),('/joy','/sim/tare/joy'),
        ('/navigation_boundary','/ht_real/navigation_boundary')]
    nodes=[
        Node(package='ht_scout_bridge',executable='scout_inputs',namespace='ht_real',
             parameters=[common,{'calibration_file':arg('calibration_file'),
                'cloud_topic':'/sim/raw_cloud','odometry_topic':'/sim/fixposition_odom',
                'elevation_topic':'/elevation_mapping_node/elevation_map_raw',
                'source_age_layer':'observation_age'}],output='screen'),
        Node(package='tare_planner',executable='tare_planner_node',namespace='ht_real',
             parameters=[str(hw/'config/tare_scout.yaml'),common,
                {'ht_enabled':False,'odometry_child_frame':'base_link',
                 'tare_sampling_seed':int(arg('seed')),'sensor_origin_offset':offset,
                 'sub_coverage_boundary_topic_':'/ht_real/coverage_boundary',
                 'sub_viewpoint_boundary_topic_':'/ht_real/navigation_boundary',
                 'kUseCoverageBoundaryOnFrontier':True,
                 'kUseCoverageBoundaryOnObjectSurface':True,
                 'sub_start_exploration_topic_':'/ht_real/exploration_start',
                 'sub_state_estimation_topic_':'/ht_real/odometry',
                 'sub_registered_scan_topic_':'/ht_real/registered_scan'}],
             remappings=remaps,output='screen'),
        Node(executable='/usr/bin/python3',arguments=[str(tools/'tare_sim_command.py')],
             parameters=[common,{'input_topic':'/sim/tare/raw_command','output_topic':'/sim/cmd_vel'}],
             output='screen')]
    parameters=json.loads((tools/'tare_cmu_parameters.json').read_text())
    for package,executable in [('terrain_analysis','terrainAnalysis'),
            ('terrain_analysis_ext','terrainAnalysisExt'),('local_planner','localPlanner'),
            ('local_planner','pathFollower')]:
        values=parameters[executable].copy()
        if executable=='localPlanner':
            values['pathFolder']=str(Path(get_package_share_directory(package))/'paths')
        nodes.append(Node(package=package,executable=executable,namespace='sim_tare',
            parameters=[common,values],remappings=data_remaps,output='screen'))
    return nodes


def generate_launch_description():
    return LaunchDescription([DeclareLaunchArgument('calibration_file'),
        DeclareLaunchArgument('seed',default_value='42'),OpaqueFunction(function=start)])
