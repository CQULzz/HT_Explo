"""ROS mechanism checks only: no map model, bag playback or physics simulator."""
import os
import threading
import time
from pathlib import Path
import importlib.util
from types import SimpleNamespace

import pytest
import rclpy
from geometry_msgs.msg import TransformStamped
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor, MultiThreadedExecutor
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.time import Time
from rosgraph_msgs.msg import Clock
from tf2_ros import Buffer, TransformBroadcaster, TransformListener
from mapper_execution import TfListenerWorker, execution_mode, make_executor


@pytest.fixture
def owner():
    rclpy.init()
    node = Node('mapper_execution_check')
    yield node
    node.destroy_node()
    rclpy.shutdown()


def test_modes_are_validated_and_legacy_default_retained():
    assert execution_mode({}) == 'multi'
    assert execution_mode({'CUPY_MAPPER_EXECUTOR_MODE': 'single'}) == 'single'
    with pytest.raises(ValueError):
        execution_mode({'CUPY_MAPPER_EXECUTOR_MODE': 'invalid'})
    with pytest.raises(ValueError):
        make_executor('invalid')


def test_receives_exact_tf_while_map_callback_waits(owner):
    buffer = Buffer()
    legacy = os.environ.get('MAPPER_TEST_LEGACY_TF') == '1'
    worker = None if legacy else TfListenerWorker(buffer, owner)
    listener = TransformListener(buffer, owner) if legacy else worker.listener
    broadcaster = TransformBroadcaster(owner)
    executor = SingleThreadedExecutor(context=owner.context)
    executor.add_node(owner)
    deadline = time.monotonic() + 4
    while broadcaster.pub_tf.get_subscription_count() == 0 and time.monotonic() < deadline:
        time.sleep(.01)
    assert broadcaster.pub_tf.get_subscription_count() > 0
    requested = owner.get_clock().now() + Duration(seconds=1)
    transform = TransformStamped()
    transform.header.frame_id = 'scheduler_test_map'
    transform.child_frame_id = 'scheduler_test_sensor'
    transform.header.stamp = requested.to_msg()
    transform.transform.translation.x = .37
    transform.transform.rotation.w = 1.
    waiting = threading.Event()
    elapsed = []
    errors = []

    def send():
        if waiting.wait(2):
            time.sleep(.05)
            broadcaster.sendTransform(transform)

    def lookup():
        timer.cancel()
        waiting.set()
        start = time.monotonic()
        try:
            result = buffer.lookup_transform('scheduler_test_map', 'scheduler_test_sensor',
                       requested, timeout=Duration(seconds=.6))
            assert result.header.stamp == transform.header.stamp
            assert result.transform.translation.x == .37
            elapsed.append(time.monotonic() - start)
        except Exception as error:
            errors.append(error)

    timer = owner.create_timer(.01, lookup)
    sender = threading.Thread(target=send)
    sender.start()
    try:
        deadline = time.monotonic() + 3
        while not elapsed and not errors and time.monotonic() < deadline:
            executor.spin_once(timeout_sec=.1)
        assert not errors, errors
        assert len(elapsed) == 1
        assert elapsed[0] < .6
        print('exact_tf_lookup_wall_s', elapsed[0])
    finally:
        sender.join()
        executor.shutdown()
        if worker:
            worker.close()
            worker.close()
            assert not worker.thread.is_alive()
        else:
            listener.unregister()


def test_worker_preserves_clock_namespace_remaps_and_is_not_owner():
    rclpy.init()
    owner = Node('clock_owner', namespace='/scheduler',
                 cli_args=['--ros-args', '-r', '/clock:=/scheduler/test_clock',
                           '-r', '/tf:=/scheduler/test_tf'],
                 parameter_overrides=[Parameter('use_sim_time', value=True)])
    worker = TfListenerWorker(Buffer(), owner)
    try:
        assert worker.node is not owner
        assert worker.node.get_namespace() == owner.get_namespace()
        assert worker.node.get_parameter('use_sim_time').value is True
        assert worker.node.resolve_topic_name('/tf') == '/scheduler/test_tf'
        publisher = owner.create_publisher(Clock, '/clock', 10)
        value = Clock(); value.clock.sec = 13
        deadline = time.monotonic() + 3
        while worker.node.get_clock().now().nanoseconds != 13_000_000_000 and time.monotonic() < deadline:
            publisher.publish(value)
            time.sleep(.01)
        assert worker.node.get_clock().now().nanoseconds == 13_000_000_000
        assert owner.get_clock().now().nanoseconds == 0  # Owner never spun.
    finally:
        worker.close(); owner.destroy_node(); rclpy.shutdown()


def test_worker_failure_is_not_silently_hidden(owner):
    worker = TfListenerWorker(Buffer(), owner)
    worker.failure = ValueError('injected test failure')
    with pytest.raises(RuntimeError, match='TF receiver failed'):
        worker.check_health()
    with pytest.raises(RuntimeError, match='TF receiver failed'):
        worker.close()
    assert not worker.thread.is_alive()


@pytest.mark.parametrize('mode', ['multi', 'single'])
def test_actual_patched_wrapper_selects_expected_topology(mode, monkeypatch):
    path = os.environ.get('MAPPER_TEST_WRAPPER')
    if not path:
        pytest.skip('Set MAPPER_TEST_WRAPPER to the staged, hash-verified runtime wrapper')
    spec = importlib.util.spec_from_file_location('candidate_mapper_wrapper', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setenv('CUPY_MAPPER_EXECUTOR_MODE', mode)
    monkeypatch.setattr(module, 'ElevationMap', lambda _: SimpleNamespace(cell_n=293))
    rclpy.init()
    node = module.ElevationMappingNode()
    executor = make_executor(node.executor_mode, node.context)
    try:
        assert node.executor_mode == mode
        assert isinstance(executor, SingleThreadedExecutor if mode == 'single' else MultiThreadedExecutor)
        assert (node.tf_worker is not None) == (mode == 'single')
        assert (node.tf_listener.node is not node) == (mode == 'single')
    finally:
        executor.shutdown()
        if node.tf_worker:
            node.tf_worker.close()
        else:
            node.tf_listener.unregister()
        node.destroy_node(); rclpy.shutdown()

def test_failed_map_initialization_closes_tf_receiver(monkeypatch):
    path = os.environ.get('MAPPER_TEST_WRAPPER')
    if not path:
        pytest.skip('Set MAPPER_TEST_WRAPPER to the staged wrapper')
    spec = importlib.util.spec_from_file_location('failing_mapper_wrapper', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    monkeypatch.setenv('CUPY_MAPPER_EXECUTOR_MODE', 'single')
    captured = []
    class Receiver:
        def __init__(self, buffer, owner):
            self.owner = owner; self.listener = object(); self.closed = False
            captured.append(self)
        def close(self):
            self.closed = True
    def fail_map(_):
        raise RuntimeError('injected map initialization failure')
    monkeypatch.setattr(module, 'TfListenerWorker', Receiver)
    monkeypatch.setattr(module, 'ElevationMap', fail_map)
    rclpy.init()
    try:
        with pytest.raises(RuntimeError, match='injected map initialization'):
            module.ElevationMappingNode()
        assert len(captured) == 1
        assert captured[0].closed
    finally:
        for worker in captured:
            worker.owner.destroy_node()
        rclpy.shutdown()

def test_main_failure_still_closes_worker_and_context(monkeypatch):
    path = os.environ.get('MAPPER_TEST_WRAPPER')
    if not path:
        pytest.skip('Set MAPPER_TEST_WRAPPER to the staged wrapper')
    import signal
    spec = importlib.util.spec_from_file_location('failing_main_wrapper', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    closed = []; destroyed = []
    signals = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    node = SimpleNamespace(executor_mode='single', context=None,
        tf_worker=SimpleNamespace(close=lambda: closed.append(True)),
        destroy_node=lambda: destroyed.append(True))
    monkeypatch.setattr(module, 'ElevationMappingNode', lambda: node)
    monkeypatch.setattr(module, 'make_executor', lambda *args: SimpleNamespace(
        add_node=lambda node:None, spin_once=lambda **kwargs:spin_failure()))
    def spin_failure(*args, **kwargs):
        raise RuntimeError('injected map callback failure')
    def stop_failure(*args, **kwargs):
        raise RuntimeError('injected executor stop failure')
    monkeypatch.setattr(module, '_stop_executor', stop_failure)
    try:
        with pytest.raises(RuntimeError):
            module.main()
        assert closed == [True]
        assert destroyed == [True]
        assert not rclpy.ok()
        assert all(signal.getsignal(s) == value for s, value in signals.items())
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        for sig, handler in signals.items():
            signal.signal(sig, handler)

def test_main_constructor_failure_restores_context_and_signals(monkeypatch):
    path = os.environ.get('MAPPER_TEST_WRAPPER')
    if not path:
        pytest.skip('Set MAPPER_TEST_WRAPPER to the staged wrapper')
    import signal
    spec = importlib.util.spec_from_file_location('failing_start_wrapper', path)
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    signals = {s: signal.getsignal(s) for s in (signal.SIGINT, signal.SIGTERM)}
    def fail():
        raise RuntimeError('injected constructor failure')
    monkeypatch.setattr(module, 'ElevationMappingNode', fail)
    try:
        with pytest.raises(RuntimeError, match='injected constructor failure'):
            module.main()
        assert not rclpy.ok()
        assert all(signal.getsignal(s) == value for s, value in signals.items())
    finally:
        if rclpy.ok():
            rclpy.shutdown()
        for sig, handler in signals.items():
            signal.signal(sig, handler)


def test_single_mapper_signal_finishes_current_callback_before_shutdown(monkeypatch):
    import signal
    path=os.environ.get('MAPPER_TEST_WRAPPER')
    if not path:pytest.skip('Set MAPPER_TEST_WRAPPER')
    spec=importlib.util.spec_from_file_location('signal_mapper',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    completed=[];destroyed=[]
    class Mapper(Node):
        def __init__(self):
            super().__init__('signal_callback_fixture')
            self.executor_mode='single';self.tf_worker=None
            self.create_timer(.001,self.work)
        def work(self):
            # Actual POSIX signal inside the active executor callback.
            os.kill(os.getpid(),signal.SIGINT)
            completed.append(True)
        def destroy_node(self):
            destroyed.append(bool(completed));return super().destroy_node()
    monkeypatch.setattr(module,'ElevationMappingNode',Mapper)
    before={s:signal.getsignal(s) for s in (signal.SIGINT,signal.SIGTERM)}
    module.main()
    assert completed==[True] and destroyed==[True]
    assert not rclpy.ok()
    assert all(signal.getsignal(s)==handler for s,handler in before.items())
