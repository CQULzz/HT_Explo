"""CMU simulation sensing stack without CMU's competing /cmd_vel controller."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration


def include(package, filename):
    return IncludeLaunchDescription(FrontendLaunchDescriptionSource(os.path.join(
        get_package_share_directory(package), "launch", filename)))


def generate_launch_description():
    vehicle = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(os.path.dirname(__file__), "cmu_vehicle_downward.launch.py")),
        launch_arguments={"world_name": LaunchConfiguration("world_name"),
                          "gui": "false", "use_sim_time": "false"}.items())
    return LaunchDescription([
        DeclareLaunchArgument("world_name", default_value="garage"),
        include("terrain_analysis", "terrain_analysis.launch"),
        include("terrain_analysis_ext", "terrain_analysis_ext.launch"),
        include("sensor_scan_generation", "sensor_scan_generation.launch"),
        vehicle,
    ])
