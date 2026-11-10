#!/usr/bin/env python3
"""CMU sensor pose -> virtual Scout base pose; preserve acquisition stamps/clouds."""
import copy
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from nav_msgs.msg import Odometry
from sensor_msgs.msg import PointCloud2
from geometry_msgs.msg import TransformStamped
from tf2_ros import TransformBroadcaster

class Adapter(Node):
    def __init__(self):
        super().__init__('cmu_old_real_adapter')
        self.odom_pub=self.create_publisher(Odometry,'/ht_real/odometry',100)
        self.tf=TransformBroadcaster(self)
        self.create_subscription(Odometry,'/state_estimation',self.odom,qos_profile_sensor_data)
        for source,dest in [('/registered_scan','/ht_real/registered_scan'),
                            ('/terrain_map','/ht_real/terrain_map'),('/terrain_map_ext','/ht_real/terrain_map_ext')]:
            pub=self.create_publisher(PointCloud2,dest,5)
            self.create_subscription(PointCloud2,source,pub.publish,5)
    def odom(self,msg):
        result=copy.deepcopy(msg);q=msg.pose.pose.orientation
        # Rotate sensor->base translation by the measured orientation.
        v=np.array([q.x,q.y,q.z]);offset=np.array([0.,0.,-0.51521])
        delta=offset+2*np.cross(v,np.cross(v,offset)+q.w*offset)
        p=result.pose.pose.position;p.x+=float(delta[0]);p.y+=float(delta[1]);p.z+=float(delta[2])
        result.child_frame_id='base_link';self.odom_pub.publish(result)
        tf=TransformStamped();tf.header=copy.deepcopy(result.header);tf.child_frame_id='base_link'
        tf.transform.translation.x=p.x;tf.transform.translation.y=p.y;tf.transform.translation.z=p.z
        tf.transform.rotation=copy.deepcopy(q);self.tf.sendTransform(tf)

def main():
    rclpy.init();node=Adapter()
    try:rclpy.spin(node)
    except KeyboardInterrupt:pass
    finally:node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
