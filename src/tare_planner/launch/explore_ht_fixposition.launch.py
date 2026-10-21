"""Run HT exploration with Fixposition as the pose source."""

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    share = get_package_share_directory("tare_planner")
    scenario = LaunchConfiguration("scenario").perform(context)
    if scenario not in ("campus", "forest", "garage", "indoor", "matterport", "tunnel"):
        raise ValueError("Unsupported scenario")

    fixposition_config = LaunchConfiguration("fixposition_config").perform(context)
    rslidar_config = LaunchConfiguration("rslidar_config").perform(context)
    ht_config = LaunchConfiguration("ht_config").perform(context)
    use_sim_time = LaunchConfiguration("use_sim_time").perform(context).lower() == "true"
    odometry_topic = LaunchConfiguration("odometry_topic").perform(context)
    scan_topic = LaunchConfiguration("registered_scan_topic").perform(context)
    ht_topic = LaunchConfiguration("ht_topic").perform(context)
    child = LaunchConfiguration("odometry_child_frame").perform(context)

    return [
        Node(
            package="fixposition_driver_ros2",
            executable="fixposition_driver_ros2_exec",
            name="fixposition_driver_ros2",
            output="screen",
            parameters=[fixposition_config, {"nav2_mode": True, "use_sim_time": use_sim_time}],
            condition=IfCondition(LaunchConfiguration("start_fixposition")),
        ),
        Node(
            package="rslidar_sdk",
            executable="rslidar_sdk_node",
            namespace="rslidar_sdk",
            output="screen",
            parameters=[{"config_path": rslidar_config}],
            condition=IfCondition(LaunchConfiguration("start_lidar")),
        ),
        Node(
            package="tare_planner",
            executable="tare_planner_node",
            name="tare_planner_node",
            output="screen",
            parameters=[
                os.path.join(share, scenario + ".yaml"),
                ht_config,
                {
                    "sub_state_estimation_topic_": odometry_topic,
                    "sub_registered_scan_topic_": scan_topic,
                    "odometry_child_frame": child,
                    "ht_topic": ht_topic,
                    "use_sim_time": use_sim_time,
                },
            ],
        ),
        Node(
            package="tare_planner", executable="xytheta_follower", name="xytheta_follower",
            output="screen", condition=IfCondition(LaunchConfiguration("start_follower")),
            parameters=[ht_config, {"odometry_topic": odometry_topic,
                "registered_scan_topic": scan_topic, "ht_topic": ht_topic,
                "odometry_child_frame": child, "use_sim_time": use_sim_time,
                "command_topic": LaunchConfiguration("command_topic").perform(context)}],
        ),
        Node(
            package="tare_planner", executable="cupy_to_ht.py", name="cupy_to_ht_bridge",
            output="screen", condition=IfCondition(LaunchConfiguration("start_ht_bridge")),
            parameters=[{"surface_odometry_topic": odometry_topic,
                "odometry_child_frame": child, "ht_topic": ht_topic,
                "elevation_topic": LaunchConfiguration("elevation_topic").perform(context),
                "use_sim_time": use_sim_time}],
        ),
    ]


def generate_launch_description():
    share = get_package_share_directory("tare_planner")
    return LaunchDescription([
        DeclareLaunchArgument("scenario", default_value="garage"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("start_lidar", default_value="true"),
        DeclareLaunchArgument("start_fixposition", default_value="true"),
        DeclareLaunchArgument("start_ht_bridge", default_value="true"),
        DeclareLaunchArgument("start_follower", default_value="true"),
        # All three consumers must use one upstream *vehicle-reference* map
        # odometry. If the VRTK POI differs, choose the externally transformed
        # topic; this launch does not invent or duplicate calibrated TF.
        DeclareLaunchArgument("odometry_topic", default_value="/fixposition/odometry_enu"),
        DeclareLaunchArgument("odometry_child_frame", default_value=""),
        DeclareLaunchArgument("registered_scan_topic", default_value="/registered_scan"),
        DeclareLaunchArgument("elevation_topic", default_value="/elevation_mapping/elevation_map_raw"),
        DeclareLaunchArgument("ht_topic", default_value="/ht_traversability/global_local"),
        DeclareLaunchArgument("command_topic", default_value="/cmd_vel"),
        DeclareLaunchArgument("ht_config", default_value=os.path.join(share, "ht.yaml")),
        DeclareLaunchArgument(
            "rslidar_config", default_value=os.path.join(share, "rslidar_helios32.yaml")
        ),
        DeclareLaunchArgument(
            "fixposition_config",
            default_value=os.path.join(share, "fixposition.yaml"),
        ),
        OpaqueFunction(function=start),
    ])
