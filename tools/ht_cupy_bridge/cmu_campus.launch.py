"""CMU Jazzy campus simulation without desktop visualization processes."""
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource, FrontendLaunchDescriptionSource


def include(package, filename, python=False, **arguments):
    source = PythonLaunchDescriptionSource if python else FrontendLaunchDescriptionSource
    return IncludeLaunchDescription(source(os.path.join(
        get_package_share_directory(package), 'launch', filename)),
        launch_arguments=arguments.items())


def generate_launch_description():
    # CMU Jazzy's vehicleSimulator stamps the navigation stream with wall time
    # by default. Use that same clock for HT and TARE (use_sim_time=false).
    return LaunchDescription([
        include('local_planner', 'local_planner.launch', autonomySpeed='0.5'),
        include('terrain_analysis', 'terrain_analysis.launch'),
        include('terrain_analysis_ext', 'terrain_analysis_ext.launch'),
        include('sensor_scan_generation', 'sensor_scan_generation.launch'),
        IncludeLaunchDescription(PythonLaunchDescriptionSource(os.path.join(
            os.path.dirname(__file__), 'cmu_vehicle_downward.launch.py')),
            launch_arguments={'world_name': 'campus', 'gui': 'false',
                              'use_sim_time': 'false'}.items()),
    ])
