"""HT hardware consumer launch; external sensor/TF/mapping remains independent."""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory,get_package_prefix
import yaml
from ht_scout_bridge.runtime_policy import direction_evidence,resolve_runtime


# TARE contains both relative and absolute topic names. Namespace relative
# publications and remap the absolute navigation/control interfaces too.
# This prevents a simulation path/completion/permission from entering the
# physical follower when someone accidentally shares a ROS domain.
HARDWARE_REMAPS=[(name,'/ht_real'+name) for name in [
    '/collision_cloud','/coverage_boundary','/exploration_start',
    '/ht_execution_rejected_edge','/ht_execution_status','/ht_follower_status',
    '/ht_navigation_allowed','/ht_route_goal','/ht_xytheta_path','/joy',
    '/ht_startup_prior',
    '/mission_completed','/mission_state','/navigation_boundary','/nogo_boundary',
    '/reset_waypoint','/runtime','/speed','/stop','/tare_coverage_route',
    '/tare_native_waypoint','/tare_route_branch','/tare_tsp_order',
    '/terrain_map','/terrain_map_ext','/way_point']]
HARDWARE_REMAPS.append(('/elevation_mapping/historical_local','/ht_real/historical_elevation'))
# The configured upstream subscriber uses this spelling.
HARDWARE_REMAPS.append(('/ht_input_status','/ht_real/ht_input_status'))
HARDWARE_REMAPS.append(('/start_exploration','/ht_real/exploration_start'))


def start(context):
    def arg(name,default=None):
        return LaunchConfiguration(name).perform(context) if name in context.launch_configurations else default
    hw=get_package_share_directory('ht_scout_bridge')
    config=os.path.join(hw,'config','ht_real.yaml')
    profile=yaml.safe_load(open(config))['/**']['ros__parameters']
    evidence=arg('direction_validation_file',os.path.join(hw,'config','direction_validation.yaml'))
    weights=os.path.join(get_package_prefix('tare_planner'),'lib','tare_planner','student_best_epoch_weights.pth')
    mapped,physical=direction_evidence(evidence,weights,profile['ht_channel_order'],profile['ht_heading_offset'])
    policy=resolve_runtime(arg('run_mode','inspect'),arg('direction_acceptance','mapping'),mapped,physical,
        arg('start_follower','auto'),arg('start_command_bridge','auto'),arg('command_topic','auto'))
    # The profile loads the same sensor/viewpoint geometry as existing TARE;
    # it does not silently substitute a simulated terrain/world launch.
    common={'use_sim_time':arg('use_sim_time').lower()=='true','odometry_child_frame':'base_link',
            'ht_topic':'/ht_real/traversability','ht_directions_calibrated':policy.direction_accepted}
    nodes=[
        Node(package='ht_scout_bridge',executable='scout_command_bridge',namespace='ht_real',output='screen',
             condition=IfCondition(str(policy.command_bridge).lower()),
             parameters=[{'use_sim_time':common['use_sim_time'],'input_topic':policy.command_topic,
                          'output_topic':arg('chassis_command_topic')}]),
        Node(package='ht_scout_bridge',executable='scout_inputs',name='ht_scout_inputs',namespace='ht_real',output='screen',
             parameters=[{'calibration_file':arg('calibration_file'),'odometry_topic':arg('odometry_topic'),
                'cloud_topic':arg('cloud_topic'),'elevation_topic':arg('elevation_topic'),
                'source_age_layer':arg('source_age_layer'),'use_sim_time':common['use_sim_time']}]),
        Node(package='tare_planner',executable='cupy_to_ht.py',name='cupy_to_ht_bridge',namespace='ht_real',output='screen',remappings=HARDWARE_REMAPS,
             parameters=[common,{'surface_odometry_topic':'/ht_real/odometry',
                'elevation_topic':'/ht_real/elevation_raw','surface_sensor_ground_offset_m':.23479,'ht_device':arg('ht_device'),'ht_quality_backend':arg('ht_quality_backend'),'ht_small_hole_repair':arg('small_hole_repair','true').lower()=='true'}]),
        Node(package='tare_planner',executable='tare_planner_node',name='tare_planner_node',namespace='ht_real',output='screen',remappings=HARDWARE_REMAPS,
             parameters=[os.path.join(hw,'config','tare_scout.yaml'),config,common,
                {'sub_start_exploration_topic_':'/ht_real/exploration_start','sub_state_estimation_topic_':'/ht_real/odometry','sub_registered_scan_topic_':'/ht_real/registered_scan'}]),
        Node(package='tare_planner',executable='xytheta_follower',name='xytheta_follower',namespace='ht_real',output='screen',
             condition=IfCondition(str(policy.follower).lower()),
             parameters=[config,common,{'odometry_topic':'/ht_real/odometry',
                'registered_scan_topic':'/ht_real/registered_scan','command_topic':policy.command_topic,'command_frame':'base_link'}],
             remappings=HARDWARE_REMAPS),
        Node(package='ht_scout_bridge',executable='scout_runtime_status',namespace='ht_real',output='screen',
             parameters=[{'use_sim_time':common['use_sim_time'],'run_mode':policy.mode,
                'direction_acceptance':policy.direction_acceptance,'mapping_verified':policy.mapping_verified,
                'terrain_validated':policy.terrain_validated,'command_topic':policy.command_topic,
                'chassis_command_topic':arg('chassis_command_topic','/cmd_vel')}])]
    if arg('start_rviz','false').lower()=='true':
        nodes.append(Node(package='rviz2',executable='rviz2',arguments=['-d',os.path.join(hw,'rviz','scout_real.rviz')],
            parameters=[{'use_sim_time':common['use_sim_time']}],output='screen'))
    return nodes


def generate_launch_description():
    hw=get_package_share_directory('ht_scout_bridge')
    return LaunchDescription([
        DeclareLaunchArgument('run_mode',default_value='inspect'),
        DeclareLaunchArgument('direction_acceptance',default_value='mapping'),
        DeclareLaunchArgument('direction_validation_file',default_value=os.path.join(hw,'config','direction_validation.yaml')),
        DeclareLaunchArgument('small_hole_repair',default_value='true'),
        DeclareLaunchArgument('start_rviz',default_value='false'),
        DeclareLaunchArgument('ht_quality_backend',default_value='auto'),
        DeclareLaunchArgument('ht_device',default_value='cuda'),
        DeclareLaunchArgument('use_sim_time',default_value='false'),
        DeclareLaunchArgument('start_command_bridge',default_value='auto'),
        DeclareLaunchArgument('chassis_command_topic',default_value='/cmd_vel'),
        DeclareLaunchArgument('start_follower',default_value='auto'),
        DeclareLaunchArgument('calibration_file',default_value=os.path.join(hw,'config','scout_extrinsics.yaml')),
        DeclareLaunchArgument('odometry_topic',default_value='/fixposition/odometry_enu'),
        DeclareLaunchArgument('cloud_topic',default_value='/rslidar_points'),
        DeclareLaunchArgument('elevation_topic',default_value='/elevation_mapping_node/elevation_map_raw'),
        DeclareLaunchArgument('source_age_layer',default_value='observation_age'),
        # Avoid competing with an external chassis controller. Hardware launch
        # does not auto-publish to an unverified motor-driver command topic.
        DeclareLaunchArgument('command_topic',default_value='auto'),
        OpaqueFunction(function=start)])
