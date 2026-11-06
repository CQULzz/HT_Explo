from types import SimpleNamespace
import json

import numpy as np
import rclpy
from nav_msgs.msg import Odometry
from sensor_msgs_py.point_cloud2 import create_cloud_xyz32
from std_msgs.msg import Header

from observe import Observer
from scene_config import SceneConfig


def test_actual_observer_counts_measured_rays_beyond_old_15m_crop(tmp_path,monkeypatch):
    runtime=tmp_path/'runtime';runtime.mkdir()
    config=SceneConfig(bounds_xy_m=(-30,30,-30,30))
    config.write(runtime/'scene_config.json')
    np.save(runtime/'local_map.npy',np.array([[20,0,0],[25,0,0]],dtype=np.float32))
    monkeypatch.delenv('HT_SIM_SCENE_CONFIG',raising=False)
    rclpy.init()
    observer=Observer(tmp_path/'recording',runtime)
    tf=SimpleNamespace(transform=SimpleNamespace(translation=SimpleNamespace(x=20.,y=0.,z=0.)))
    monkeypatch.setattr(observer.tf,'lookup_transform',lambda *args:tf)
    message=create_cloud_xyz32(Header(frame_id='map'),[[25.,0.,0.]])
    message.header.stamp.sec=1
    pose=Odometry();pose.pose.pose.position.x=20
    try:
        observer.odom(pose)
        observer.scan(message)
        assert observer.free and observer.scans==1
        observer.sample()
    finally:
        observer.close();observer.destroy_node();rclpy.shutdown()
    result=json.loads((tmp_path/'recording/metric_geometry.json').read_text())
    assert result['scene']['bounds_xy_m']==[-30,30,-30,30]
    assert np.load(tmp_path/'recording/free_voxel_keys.npy').size>0
