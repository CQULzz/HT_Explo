"""Declare the recorded scene's cropped mission area; publish no terrain."""
from pathlib import Path
import json
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PolygonStamped,Point32

class Boundary(Node):
    def __init__(self):
        super().__init__('recorded_map_boundary')
        self.bounds=json.loads(Path('/home/lzz/pcd_test_20261110/runtime/SCENE_MANIFEST.json').read_text())['mission_bounds_xy_m']
        self.pubs=[self.create_publisher(PolygonStamped,t,5) for t in ['/navigation_boundary','/sensor_coverage_planner/coverage_boundary']]
        self.create_timer(.5,self.publish)
    def publish(self):
        xmin,xmax,ymin,ymax=self.bounds;m=PolygonStamped();m.header.frame_id='map';m.header.stamp=self.get_clock().now().to_msg()
        m.polygon.points=[Point32(x=float(x),y=float(y),z=0.) for x,y in [(xmin,ymin),(xmax,ymin),(xmax,ymax),(xmin,ymax)]]
        for pub in self.pubs:pub.publish(m)

if __name__=='__main__':
    rclpy.init();n=Boundary()
    try:rclpy.spin(n)
    except KeyboardInterrupt:pass
    finally:n.destroy_node();rclpy.try_shutdown()
