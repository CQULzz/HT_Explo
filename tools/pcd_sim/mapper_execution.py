"""Opt-in single-owner map scheduling with independently serviced exact TF."""
import os
import threading

from rclpy.executors import (ExternalShutdownException, MultiThreadedExecutor,
                            ShutdownException, SingleThreadedExecutor)
from rclpy.node import Node
from rclpy.parameter import Parameter
from tf2_ros import TransformListener


def execution_mode(environment=None):
    value = (os.environ if environment is None else environment).get(
        'CUPY_MAPPER_EXECUTOR_MODE', 'multi')
    if value not in ('multi', 'single'):
        raise ValueError('CUPY_MAPPER_EXECUTOR_MODE must be multi or single')
    return value


def make_executor(mode, context=None):
    if mode == 'single':
        return SingleThreadedExecutor(context=context)
    if mode == 'multi':
        return MultiThreadedExecutor(num_threads=4, context=context)
    raise ValueError('Unknown mapper executor mode')


class TfListenerWorker:
    """Own a separate node so TF keeps arriving during a map callback/TF wait.

    Never spin the owner's node in a second executor. Copy its ROS context,
    namespace and clock mode while ignoring global __node remappings.
    """
    def __init__(self, buffer, owner):
        self.failure = None
        self._closed = False
        self._close_lock = threading.Lock()
        self.node = Node(owner.get_name() + '_tf_receiver',
                         namespace=owner.get_namespace(), context=owner.context,
                         use_global_arguments=False, enable_rosout=False,
                         cli_args=['--ros-args',
                             '-r', '/tf:=' + owner.resolve_topic_name('/tf'),
                             '-r', '/tf_static:=' + owner.resolve_topic_name('/tf_static'),
                             '-r', '/clock:=' + owner.resolve_topic_name('/clock')],
                         start_parameter_services=False,
                         parameter_overrides=[Parameter('use_sim_time', value=
                             owner.get_parameter('use_sim_time').value)])
        self.listener = TransformListener(buffer, self.node, spin_thread=False)
        self.executor = SingleThreadedExecutor(context=owner.context)
        self.executor.add_node(self.node)
        self.thread = threading.Thread(target=self._spin, name='mapper-TF', daemon=False)
        self.thread.start()

    def _spin(self):
        try:
            self.executor.spin()
        except (ExternalShutdownException, ShutdownException):
            pass
        except BaseException as error:
            self.failure = error

    def check_health(self):
        if self.failure is not None:
            raise RuntimeError('Mapper TF receiver failed') from self.failure

    def close(self):
        with self._close_lock:
            if self._closed:
                self.check_health()
                return
            if threading.current_thread() is self.thread:
                raise RuntimeError('TF receiver cannot join itself')
            # TF callbacks never acquire the map lock or wait for inference.
            self.executor.shutdown(timeout_sec=2.0)
            self.thread.join(timeout=2.0)
            if self.thread.is_alive():
                raise RuntimeError('Mapper TF receiver did not stop')
            self.executor.remove_node(self.node)
            self.listener.unregister()
            self.node.destroy_node()
            self._closed = True
            self.check_health()
