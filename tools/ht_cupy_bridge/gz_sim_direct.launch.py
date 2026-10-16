"""Use installed Gazebo launch settings, with a directly managed server process."""
from importlib.machinery import SourceFileLoader
from pathlib import Path
import shlex

from ament_index_python.packages import get_package_share_directory


def generate_launch_description():
    path = Path(get_package_share_directory('ros_gz_sim')) / 'launch/gz_sim.launch.py'
    module = SourceFileLoader('ht_gazebo_direct', str(path)).load_module()
    execute = module.ExecuteProcess

    def direct_process(*args, **kwargs):
        # ros_gz_sim builds a fully resolved, shell-quoted command here. The
        # extra /bin/sh neither forwards SIGINT nor waits for orderly cleanup.
        if kwargs.get('name') == 'gazebo' and kwargs.get('shell'):
            kwargs['cmd'] = shlex.split(' '.join(kwargs['cmd']))
            kwargs['shell'] = False
        return execute(*args, **kwargs)

    module.ExecuteProcess = direct_process
    return module.generate_launch_description()
