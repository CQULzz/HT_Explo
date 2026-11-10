#!/usr/bin/env python3
"""Use exactly the previous motion/coverage metric, adding old planner statuses."""
import sys,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'cmu_minimal'))
import collect as shared
from rclpy.utilities import remove_ros_args
from std_msgs.msg import String,Bool
ros_args=list(sys.argv)
sys.argv=remove_ros_args(args=ros_args)
real_init=shared.rclpy.init
shared.rclpy.init=lambda:real_init(args=ros_args)
original=shared.Collect.__init__
def init(self,out):
    original(self,out)
    for topic in ['/ht_real/mission_state','/ht_real/ht_execution_status','/ht_real/ht_follower_status']:
        self.create_subscription(String,topic,lambda m,t=topic:self.event(t,{'status':m.data}),100)
    self.create_subscription(Bool,'/ht_real/ht_navigation_allowed',
        lambda m:self.event('permission',{'allowed':m.data}),10)
shared.Collect.__init__=init
if __name__=='__main__':shared.main()
