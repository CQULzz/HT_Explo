"""CMU vehicle simulator with a downward-looking lidar for HT evaluation.

Only the three spawn SDF paths are replaced. The CMU simulator, controller,
worlds, and ROS interfaces remain in their own workspace.
"""

from importlib.machinery import SourceFileLoader
from pathlib import Path

from ament_index_python.packages import get_package_share_directory


ASSETS = Path(__file__).resolve().parent / "assets"
SDF_NAMES = {
    "lidar.sdf": "lidar_downward.sdf",
    "robot.sdf": "robot_sensor_mask.sdf",
    "camera.sdf": "camera_sensor_mask.sdf",
}


def generate_launch_description():
    cmu_launch = Path(get_package_share_directory("vehicle_simulator")) / "launch" / "vehicle_simulator.launch"
    module = SourceFileLoader("cmu_vehicle_downward", str(cmu_launch)).load_module()
    original_node = module.Node
    original_source = module.PythonLaunchDescriptionSource

    def direct_gazebo_source(path, *args, **kwargs):
        if Path(path).name == 'gz_sim.launch.py':
            path = str(Path(__file__).with_name('gz_sim_direct.launch.py'))
        return original_source(path, *args, **kwargs)

    def node_with_downward_lidar(*args, **kwargs):
        if kwargs.get("package") == "ros_gz_sim" and kwargs.get("executable") == "create":
            replacement = []
            for argument in kwargs.get("arguments", []):
                name = Path(argument).name if isinstance(argument, str) else None
                if name in SDF_NAMES and "/urdf/" in argument:
                    replacement.append(str(ASSETS / SDF_NAMES[name]))
                else:
                    replacement.append(argument)
            kwargs["arguments"] = replacement
        return original_node(*args, **kwargs)

    module.Node = node_with_downward_lidar
    module.PythonLaunchDescriptionSource = direct_gazebo_source
    return module.generate_launch_description()
