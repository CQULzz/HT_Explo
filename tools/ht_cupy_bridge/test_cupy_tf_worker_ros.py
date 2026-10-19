"""Real ROS regression: a blocked map callback must still receive fresh TF."""
import threading
import time
import unittest

import rclpy
from rclpy.duration import Duration
from rclpy.executors import SingleThreadedExecutor
from rclpy.node import Node
from rclpy.time import Time
from geometry_msgs.msg import TransformStamped
from tf2_ros import Buffer, TransformBroadcaster
from elevation_mapping_cupy.elevation_mapping_ros import TfListenerWorker


class TfWorkerRegression(unittest.TestCase):
    def test_lookup_during_blocked_map_callback_and_clean_shutdown(self):
        rclpy.init()
        owner=Node('map_worker_regression')
        buffer=Buffer()
        worker=TfListenerWorker(buffer,owner)
        broadcaster=TransformBroadcaster(owner)
        executor=SingleThreadedExecutor();executor.add_node(owner)
        waiting=threading.Event();finished=[];errors=[]
        deadline=time.monotonic()+5
        while broadcaster.pub_tf.get_subscription_count()==0 and time.monotonic()<deadline:
            time.sleep(.02)
        self.assertGreater(broadcaster.pub_tf.get_subscription_count(),0)
        requested=owner.get_clock().now()+Duration(seconds=1)
        transform=TransformStamped();transform.header.frame_id='regression_map'
        transform.child_frame_id='regression_sensor';transform.header.stamp=requested.to_msg()
        transform.transform.translation.x=.37;transform.transform.rotation.w=1.

        def send_while_lookup_waits():
            if not waiting.wait(3):return
            time.sleep(.05)
            broadcaster.sendTransform(transform)

        def map_callback():
            timer.cancel();waiting.set();started=time.monotonic()
            try:
                value=buffer.lookup_transform('regression_map','regression_sensor',
                    Time.from_msg(transform.header.stamp),timeout=Duration(seconds=1))
                finished.append((value.transform.translation.x,time.monotonic()-started))
            except Exception as error:errors.append(error)

        sender=threading.Thread(target=send_while_lookup_waits)
        timer=owner.create_timer(.01,map_callback);sender.start()
        try:
            deadline=time.monotonic()+4
            while not finished and not errors and time.monotonic()<deadline:
                executor.spin_once(timeout_sec=.1)
            self.assertEqual(errors,[])
            self.assertEqual(len(finished),1)
            self.assertAlmostEqual(finished[0][0],.37)
            self.assertLess(finished[0][1],1)
            self.assertIsNot(worker.node,owner)
            self.assertEqual(worker.node.get_parameter('use_sim_time').value,
                             owner.get_parameter('use_sim_time').value)
        finally:
            sender.join();executor.shutdown();worker.close();worker.close()
            self.assertFalse(worker.thread.is_alive())
            owner.destroy_node();rclpy.shutdown()


if __name__=='__main__':unittest.main()
