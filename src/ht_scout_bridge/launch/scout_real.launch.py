"""HT hardware consumer launch; external sensor/TF/mapping remains independent."""
import os
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument,OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory


# TARE contains both relative and absolute topic names. Namespace relative
# publications and remap the absolute navigation/control interfaces too.
# This prevents a simulation path/completion/permission from entering the
# physical follower when someone accidentally shares a ROS domain.
HARDWARE_REMAPS=[(name,'/ht_real'+name) for name in [
    '/collision_cloud','/coverage_boundary','/exploration_start',
    '/ht_execution_rejected_edge','/ht_execution_status','/ht_follower_status',
    '/ht_navigation_allowed','/ht_route_goal','/ht_xytheta_path','/joy',
    '/mission_completed','/mission_state','/navigation_boundary','/nogo_boundary',
    '/reset_waypoint','/runtime','/speed','/stop','/tare_coverage_route',
    '/tare_native_waypoint','/tare_route_branch','/tare_tsp_order',
    '/terrain_map','/terrain_map_ext','/way_point']]
HARDWARE_REMAPS.append(('/elevation_mapping/historical_local','/ht_real/historical_elevation'))


def start(context):
    arg=lambda name:LaunchConfiguration(name).perform(context)
    hw=get_package_share_directory('ht_scout_bridge')
    config=os.path.join(hw,'config','ht_real.yaml')
    # The profile loads the same sensor/viewpoint geometry as existing TARE;
    # it does not silently substitute a simulated terrain/world launch.
    common={'use_sim_time':arg('use_sim_time').lower()=='true','odometry_child_frame':'base_link',
            'ht_topic':'/ht_real/traversability'}
    return [
        Node(package='ht_scout_bridge',executable='scout_inputs',name='ht_scout_inputs',namespace='ht_real',output='screen',
             parameters=[{'calibration_file':arg('calibration_file'),'odometry_topic':arg('odometry_topic'),
                'cloud_topic':arg('cloud_topic'),'elevation_topic':arg('elevation_topic'),
                'source_age_layer':arg('source_age_layer'),'use_sim_time':common['use_sim_time']}]),
        Node(package='tare_planner',executable='cupy_to_ht.py',name='cupy_to_ht_bridge',namespace='ht_real',output='screen',remappings=HARDWARE_REMAPS,
             parameters=[common,{'surface_odometry_topic':'/ht_real/odometry',
                'elevation_topic':'/ht_real/elevation_raw','surface_sensor_ground_offset_m':.23479}]),
        Node(package='tare_planner',executable='tare_planner_node',name='tare_planner_node',namespace='ht_real',output='screen',remappings=HARDWARE_REMAPS,
             parameters=[os.path.join(hw,'config','tare_scout.yaml'),config,common,
                {'sub_state_estimation_topic_':'/ht_real/odometry','sub_registered_scan_topic_':'/ht_real/registered_scan'}]),
        Node(package='tare_planner',executable='xytheta_follower',name='xytheta_follower',namespace='ht_real',output='screen',
             condition=IfCondition(LaunchConfiguration('start_follower')),
             parameters=[config,common,{'odometry_topic':'/ht_real/odometry',
                'registered_scan_topic':'/ht_real/registered_scan','command_topic':arg('command_topic'),'command_frame':'base_link'}],
             remappings=HARDWARE_REMAPS)]


def generate_launch_description():
    hw=get_package_share_directory('ht_scout_bridge')
    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time',default_value='false'),
        DeclareLaunchArgument('start_follower',default_value='false'),
        DeclareLaunchArgument('calibration_file',default_value=os.path.join(hw,'config','scout_extrinsics.yaml')),
        DeclareLaunchArgument('odometry_topic',default_value='/fixposition/odometry_enu'),
        DeclareLaunchArgument('cloud_topic',default_value='/rslidar_points'),
        DeclareLaunchArgument('elevation_topic',default_value='/elevation_mapping_node/elevation_map_raw'),
        DeclareLaunchArgument('source_age_layer',default_value='time'),
        # Avoid competing with an external chassis controller. Hardware launch
        # does not auto-publish to an unverified motor-driver command topic.
        DeclareLaunchArgument('command_topic',default_value='/ht_real/cmd_vel_stamped'),
        OpaqueFunction(function=start)])
