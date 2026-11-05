"""Actual signal and multithreaded ROS callback lifecycle; no vehicle/model."""
import os
import signal
import threading
import time
import rclpy
from rclpy.node import Node
from std_msgs.msg import String
from ht_scout_bridge import node as inputs


def test_stop_drains_active_callback_before_context_or_entities_are_destroyed(monkeypatch):
    entered=threading.Event();completed=[];destroyed=[];closed=[]
    class Fixture(Node):
        def __init__(self):
            super().__init__('input_shutdown_fixture')
            self.publisher=self.create_publisher(String,'/offline_shutdown_fixture',1)
            self.timer=self.create_timer(.001,self.callback)
        def callback(self):
            self.timer.cancel();entered.set();time.sleep(.05)
            assert rclpy.ok()
            self.publisher.publish(String(data='finished'))
            completed.append(True)
        def close_inputs(self):closed.append(True)
        def destroy_node(self):
            destroyed.append(bool(completed));return super().destroy_node()
    def send():
        assert entered.wait(3)
        os.kill(os.getpid(),signal.SIGINT)
    monkeypatch.setattr(inputs,'ScoutInputs',Fixture)
    previous={sig:signal.getsignal(sig) for sig in (signal.SIGINT,signal.SIGTERM)}
    sender=threading.Thread(target=send);sender.start()
    try:inputs.main()
    finally:sender.join(timeout=4)
    assert completed==[True] and destroyed==[True] and closed==[True]
    assert not rclpy.ok()
    assert all(signal.getsignal(sig)==handler for sig,handler in previous.items())
