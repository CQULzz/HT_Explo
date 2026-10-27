"""Exercise RViz marker/cloud payloads without a display or vehicle."""
from array import array
import numpy as np
import rclpy
from grid_map_msgs.msg import GridMap
from nav_msgs.msg import Odometry
from std_msgs.msg import Float32MultiArray
from tare_planner.msg import StartupPrior
from ht_scout_bridge.runtime_status import RuntimeStatus,decode_grid

class Sink:
    def __init__(self):self.messages=[]
    def get_subscription_count(self):return 1
    def publish(self,m):self.messages.append(m)

def test_diagnostic_ring_is_distinct_from_prior_and_cloud_is_valid():
    rclpy.init();n=RuntimeStatus()
    try:
        g=GridMap();g.header.frame_id='map';g.header.stamp=n.get_clock().now().to_msg()
        g.info.resolution=.04;g.info.length_x=g.info.length_y=2.44;g.info.pose.orientation.w=1.
        g.layers=[f'ht_dir_{k}' for k in range(8)]+['ht_valid','ht_observation_valid','ht_obstacle','ht_elevation','ht_measured_valid','ht_interpolated']
        for name in g.layers:
            value=0. if name in ('ht_obstacle','ht_elevation','ht_interpolated') else 1.
            g.data.append(Float32MultiArray(data=array('f',np.full(61*61,value,np.float32))))
        n.grid=g;n.decoded=decode_grid(g);n.odom=Odometry();n.odom.pose.pose.orientation.w=1.
        n.prior=StartupPrior();n.prior.radius=1.2
        n.markpub=Sink();n.bestpub=Sink();n.rawpub=Sink()
        result={'reason':'INSPECT_NO_MOTOR_OUTPUT','ht_map_age_s':.1}
        n.visualize(result,True,20.)
        markers={m.id:m for m in n.markpub.messages[0].markers}
        assert abs(markers[1].points[0].x-.6)<1e-6
        assert abs(markers[2].points[0].x-1.2)<1e-6
        assert len(markers[3].points)==result['body']['cells']>0
        c=n.bestpub.messages[0];assert c.width==61*61 and len(c.data)==c.width*c.point_step
        assert n.count_publishers('/cmd_vel')==0
    finally:n.destroy_node();rclpy.try_shutdown()
