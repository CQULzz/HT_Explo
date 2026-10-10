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

    return [
        Node(
            package="fixposition_driver_ros2",
            executable="fixposition_driver_ros2_exec",
            name="fixposition_driver_ros2",
            output="screen",
            parameters=[fixposition_config, {"nav2_mode": True, "use_sim_time": use_sim_time}],
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
                    "sub_state_estimation_topic_": "/fixposition/odometry_enu",
                    "use_sim_time": use_sim_time,
                },
            ],
        ),
    ]


def generate_launch_description():
    share = get_package_share_directory("tare_planner")
    return LaunchDescription([
        DeclareLaunchArgument("scenario", default_value="garage"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("start_lidar", default_value="true"),
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
