"""CMU sensing/physics without CMU's competing /cmd_vel controller.

The vehicle simulator needs its own ground-height/attitude estimate. In HT
mode it is kept on private simulation topics; TARE never consumes those maps.
"""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, GroupAction
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch.conditions import IfCondition, UnlessCondition
from launch_ros.actions import SetRemap


def include(package, filename):
    return IncludeLaunchDescription(FrontendLaunchDescriptionSource(os.path.join(
        get_package_share_directory(package), "launch", filename)))


def physics():
    vehicle = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(os.path.dirname(__file__), "cmu_vehicle_downward.launch.py")),
        launch_arguments={"world_name": LaunchConfiguration("world_name"),
                          "gui": "false", "use_sim_time": "false"}.items())
    return [include("terrain_analysis", "terrain_analysis.launch"),
            include("terrain_analysis_ext", "terrain_analysis_ext.launch"), vehicle]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument("world_name", default_value="garage"),
        DeclareLaunchArgument("use_terrain_analysis", default_value="false",
                              description="Expose CMU terrain to navigation (upstream baseline only)"),
        GroupAction(condition=IfCondition(LaunchConfiguration("use_terrain_analysis")), actions=physics()),
        GroupAction(condition=UnlessCondition(LaunchConfiguration("use_terrain_analysis")), actions=[
            SetRemap(src="/terrain_map", dst="/simulation/terrain_map"),
            SetRemap(src="/terrain_map_ext", dst="/simulation/terrain_map_ext"),
            *physics()]),
        include("sensor_scan_generation", "sensor_scan_generation.launch"),
    ])
