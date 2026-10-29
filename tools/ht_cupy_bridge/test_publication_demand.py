"""Unused map outputs must not acquire map locks or touch GPU layers."""
from threading import RLock
from types import SimpleNamespace as S

import numpy as np
import pytest
from rclpy.time import Time
from elevation_mapping_cupy.elevation_mapping_ros import ElevationMappingNode


class Publisher:
    def __init__(self,count=0):self.count=count;self.messages=[]
    def get_subscription_count(self):return self.count
    def publish(self,msg):self.messages.append(msg)


class Map:
    def __init__(self):self.calls=[];self.variance=2.;self.resolution=.04;self.map_length=11.64;self.center=S(get=lambda:np.array([1.,2.,0.]))
    def get_map_with_name_ref(self,name,array):self.calls.append(name);array[:]=1. if name=='elevation' else self.variance
    def get_observation_age_ref(self,stamp,array):assert stamp==10.;self.calls.append('age');array[:]=3.


def proxy():
    return S(map_translation=True,last_integrated_stamp=Time(seconds=10),offline_tf_bag='',
             publisher_configs={'raw':{'layers':['elevation','variance','observation_age'],'basic_layers':['elevation']}},
             map_publishers={'raw':Publisher()},map_frame='map',map=Map(),
             map_access_lock=RLock(),map_data=np.zeros((291,291),np.float32),publication_skipped_no_subscribers={})


def test_zero_demand_skips_lock_and_layers_then_late_subscriber_gets_coherent_map():
    n=proxy()
    class ForbiddenLock:
        def __enter__(self):raise AssertionError('unused publication acquired the map lock')
    n.map_access_lock=ForbiddenLock()
    ElevationMappingNode.publish_map(n,'raw')
    assert n.map.calls==[] and n.publication_skipped_no_subscribers=={'raw':1}
    n.map_access_lock=RLock();n.map_publishers['raw'].count=1
    ElevationMappingNode.publish_map(n,'raw')
    result=n.map_publishers['raw'].messages[-1]
    assert result.header.stamp.sec==10 and result.info.pose.position.x==1.
    assert result.layers==['elevation','variance','observation_age']
    assert [d.data[0] for d in result.data]==[1.,2.,3.]
    # Variance/geometry changes are NOT suppressed merely for an equal stamp.
    n.map.variance=5.;ElevationMappingNode.publish_map(n,'raw')
    assert n.map_publishers['raw'].messages[-1].data[1].data[0]==5.


@pytest.mark.parametrize('override',['offline','explicit','capture_proxy'])
def test_offline_and_explicit_capture_keep_unconditional_publication(override):
    n=proxy()
    if override=='offline':n.offline_tf_bag='recorded-input'
    elif override=='explicit':n.publisher_configs['raw']['publish_without_subscribers']=True
    else:
        messages=[];n.map_publishers['raw']=S(publish=messages.append)
    ElevationMappingNode.publish_map(n,'raw')
    assert n.map.calls==['elevation','variance','age']
    assert n.publication_skipped_no_subscribers=={}
