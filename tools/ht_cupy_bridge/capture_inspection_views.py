#!/usr/bin/env python3
"""Capture real Gazebo camera images from stationary inspection cameras."""
import argparse
import time
from pathlib import Path
import cv2
import rclpy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    rclpy.init();node=Node('inspection_view_capture');bridge=CvBridge();views={}
    for name in ['front','rear','oblique','top']:
        def receive(msg,name=name):
            views[name]=bridge.imgmsg_to_cv2(msg,desired_encoding='bgr8')
        node.create_subscription(Image,f'/inspection/{name}/image',receive,qos_profile_sensor_data)
    started=time.monotonic()
    while time.monotonic()-started<40:
        rclpy.spin_once(node,timeout_sec=.1)
        if len(views)==4 and time.monotonic()-started>8:break
    for name,frame in views.items():
        cv2.imwrite(str(args.output/f'environment_{name}.png'),frame)
    node.destroy_node();rclpy.shutdown()
    if len(views)!=4:raise RuntimeError(f'Missing cameras; got {list(views)}')
    print('Captured front/rear/oblique/top Gazebo views')


if __name__=='__main__':main()
