import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def start(context):
    share = get_package_share_directory("tare_planner")
    scenario = LaunchConfiguration("scenario").perform(context)
    if scenario not in ("campus", "forest", "garage", "indoor", "matterport", "tunnel"):
        raise ValueError("Unsupported scenario")
    return [Node(
        package="tare_planner", executable="tare_planner_node",
        name="tare_planner_node", output="screen",
        parameters=[os.path.join(share, scenario + ".yaml"),
                    LaunchConfiguration("ht_config").perform(context),
                    {"use_sim_time": LaunchConfiguration("use_sim_time").perform(context).lower() == "true"}])]


def generate_launch_description():
    share = get_package_share_directory("tare_planner")
    return LaunchDescription([
        DeclareLaunchArgument("scenario", default_value="garage"),
        DeclareLaunchArgument("use_sim_time", default_value="false"),
        DeclareLaunchArgument("ht_config", default_value=os.path.join(share, "ht.yaml")),
        OpaqueFunction(function=start),
    ])
