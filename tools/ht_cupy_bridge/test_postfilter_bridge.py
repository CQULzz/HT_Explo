"""Exercise the real ROS bridge and model after historical post-filter rejection."""
from array import array
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
import rclpy
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Float32MultiArray, MultiArrayLayout, MultiArrayDimension

from cupy_to_ht import CupyToHt


class FrozenHistoricalCrop:
    """A previously accepted height now isolated in the current crop neighbourhood."""
    def __init__(self, resolution):
        self.resolution=resolution;self.tiles={}
        self.last_window_obstacle_elevation=np.full((291,291),np.nan,np.float32)
        self.last_window_incompatible_mask=np.zeros((291,291),bool)

    def record_rejections(self,*args,**kwargs):return 0
    def fuse(self,*args,**kwargs):return 0
    def aligned_source_window(self, source,*args,**kwargs):return np.asarray(source).copy()
    def window(self,*args,**kwargs):
        raw=np.zeros((291,291),np.float32);variance=np.full_like(raw,.001)
        raw[145,164]=.46;variance[145,164]=.008
        return raw,variance,0.,0.


class CapturedPublisher:
    def __init__(self):self.messages=[]
    def get_subscription_count(self):return 1
    def publish(self,msg):self.messages.append(msg)


class PostfilterBridgeTest(unittest.TestCase):
    def test_actual_model_output_keeps_rejected_height_as_eight_direction_hard_obstacle(self):
        rclpy.init();node=None
        try:
            node=CupyToHt();node.history=FrozenHistoricalCrop(.04093567251461988)
            output=CapturedPublisher();node.pub=output;node.history_pub=CapturedPublisher()
            source=GridMap();source.header.frame_id='map';source.header.stamp=node.get_clock().now().to_msg()
            source.info.resolution=node.history.resolution
            source.info.length_x=source.info.length_y=291*source.info.resolution
            source.info.pose.orientation.w=1.
            source.layers=['elevation','variance','observation_age']
            for value in [0.,.001,0.]:
                data=Float32MultiArray()
                data.layout=MultiArrayLayout(dim=[
                    MultiArrayDimension(label='column_index',size=291,stride=291*291),
                    MultiArrayDimension(label='row_index',size=291,stride=291)])
                data.data=array('f',np.full((291,291),value,np.float32).tobytes());source.data.append(data)
            with tempfile.TemporaryDirectory() as temporary, patch.dict(os.environ,{'HT_CONTEXT_DUMP':temporary}):
                node.on_map(source)
                self.assertEqual(len(output.messages),1)
                result=output.messages[0]
                self.assertEqual(result.header.stamp,source.header.stamp)
                def layer(name):return np.asarray(result.data[result.layers.index(name)].data).reshape((241,241),order='F')
                self.assertEqual(len(result.layers),12)
                self.assertAlmostEqual(float(layer('ht_elevation')[120,120]),0.,places=6)
                self.assertTrue(np.isnan(layer('ht_elevation')[120,139]))
                self.assertEqual(layer('ht_valid')[120,120],1.)
                self.assertEqual(layer('ht_obstacle')[120,139],1.)
                for k in range(8):self.assertEqual(layer(f'ht_dir_{k}')[120,139],0.)
                self.assertEqual(node.diagnostics[-1]['retained_filtered_obstacle_cells'],1)
                captures=list(Path(temporary).glob('*.npz'));self.assertEqual(len(captures),1)
                with np.load(captures[0]) as capture:
                    self.assertAlmostEqual(float(capture['height'][145,164]),.46,places=6)
                    self.assertTrue(capture['quality_rejected'][145,164])
                    self.assertTrue(capture['occupied'][120,139])
                    self.assertTrue(np.all(capture['probabilities'][:,120,139]==0.))
                    self.assertEqual(capture['history_variance'].shape,(291,291))
                    self.assertAlmostEqual(float(capture['history_variance'][145,164]),.008,places=6)
                    np.testing.assert_array_equal(capture['source_elevation'],np.zeros((291,291),np.float32))
                    np.testing.assert_array_equal(capture['source_observation_age'],np.zeros((291,291),np.float32))
                    self.assertAlmostEqual(float(capture['source_variance'][145,164]),.001,places=6)
        finally:
            if node is not None:node.destroy_node()
            rclpy.try_shutdown()


if __name__=='__main__':unittest.main()

class FrozenSmallHoleCrop(FrozenHistoricalCrop):
    def window(self,*args,**kwargs):
        z=np.zeros((291,291),np.float32);z[144:147,144:147]=np.nan
        return z,np.full_like(z,.001),0.,0.

class SmallHoleBridgeTest(unittest.TestCase):
    def test_interpolation_is_separate_from_measurement_and_not_persisted(self):
        rclpy.init(args=['--ros-args','-p','ht_small_hole_repair:=true']);node=None
        try:
            node=CupyToHt();history=FrozenSmallHoleCrop(.04);node.history=history
            output=CapturedPublisher();node.pub=output
            source=GridMap();source.header.frame_id='map';source.header.stamp=node.get_clock().now().to_msg()
            source.info.resolution=.04;source.info.length_x=source.info.length_y=11.64;source.info.pose.orientation.w=1.
            source.layers=['elevation','variance','observation_age']
            source_z=np.zeros((291,291),np.float32);source_z[144:147,144:147]=np.nan
            for value in [source_z,np.full_like(source_z,.001),np.zeros_like(source_z)]:
                data=Float32MultiArray();data.layout=MultiArrayLayout(dim=[MultiArrayDimension(label='column_index',size=291,stride=84681),MultiArrayDimension(label='row_index',size=291,stride=291)])
                data.data=array('f',value.flatten(order='F'));source.data.append(data)
            node.on_map(source);assert len(output.messages)==1
            result=output.messages[0]
            def layer(k):return np.asarray(result.data[result.layers.index(k)].data).reshape(241,241,order='F')
            assert len(result.layers)==14 and layer('ht_interpolated')[120,120]==1
            assert layer('ht_measured_valid')[120,120]==0
            assert layer('ht_elevation')[120,120]==0 and layer('ht_obstacle')[120,120]==0
            assert np.isnan(source.data[0].data[145*291+145])
            assert np.isnan(history.window()[0][145,145])
            assert result.header.stamp==source.header.stamp
        finally:
            if node:node.destroy_node()
            rclpy.try_shutdown()
