"""Resolve source launch actions without starting processes."""
from pathlib import Path
import importlib.util
import pytest
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument
from launch.utilities import perform_substitutions
from launch_ros.utilities import evaluate_parameters

ROOT=Path(__file__).resolve().parents[3]
spec=importlib.util.spec_from_file_location('hardware_mode_launch',ROOT/'src/ht_scout_bridge/launch/scout_real.launch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

@pytest.mark.parametrize('mode',['inspect','preview','drive'])
def test_actual_launch_modes_and_start_topic(monkeypatch,mode):
    monkeypatch.setattr(m,'get_package_share_directory',lambda name:str(ROOT/'src'/name))
    c=LaunchContext()
    for a in m.generate_launch_description().entities:
        if isinstance(a,DeclareLaunchArgument):c.launch_configurations[a.name]=perform_substitutions(c,a.default_value)
    c.launch_configurations['run_mode']=mode
    rows={}
    for a in m.start(c):
        params=evaluate_parameters(c,a._Node__parameters)
        rows[a.node_executable]={'enabled':a.condition is None or a.condition.evaluate(c),
            'params':{k:v for d in params if isinstance(d,dict) for k,v in d.items()}}
    assert rows['xytheta_follower']['enabled']==(mode!='inspect')
    assert rows['scout_command_bridge']['enabled']==(mode=='drive')
    assert rows['tare_planner_node']['params']['sub_start_exploration_topic_']=='/ht_real/exploration_start'
    assert rows['tare_planner_node']['params']['ht_directions_calibrated'] is True
    assert rows['scout_runtime_status']['params']['terrain_validated'] is False
    assert rows['scout_runtime_status']['params']['mapping_verified'] is True
    topic='/ht_real/preview/cmd_vel_stamped' if mode=='preview' else '/ht_real/cmd_vel_stamped'
    assert rows['xytheta_follower']['params']['command_topic']==topic
    assert rows['scout_command_bridge']['params']['input_topic']==topic
    assert rows['cupy_to_ht.py']['params']['ht_small_hole_repair'] is True
    assert rows['cupy_to_ht.py']['params']['ht_history_backend']=='auto'
    assert rows['cupy_to_ht.py']['params']['ht_fuse_bn'] is True
    assert rows['cupy_to_ht.py']['params']['ht_small_hole_backend']=='auto'
    assert rows['cupy_to_ht.py']['params']['ht_small_hole_profile']=='moderate'
    assert rows['cupy_to_ht.py']['params']['ht_context_backend']=='auto'
    assert rows['cupy_to_ht.py']['params']['ht_profile_runtime'] is True
    assert rows['cupy_to_ht.py']['params']['ht_reason_interval_s']==1.
    assert ('/ht_performance','/ht_real/ht_performance') in m.HARDWARE_REMAPS
    assert ('/ht_runtime','/ht_real/ht_runtime') in m.HARDWARE_REMAPS
    assert ('/ht_reasons','/ht_real/ht_reasons') in m.HARDWARE_REMAPS
    assert rows['scout_inputs']['params']['source_age_layer']=='observation_age'
    assert rows['scout_inputs']['params']['cloud_reliability']=='reliable'
    assert rows['tare_planner_node']['params']['sensor_origin_offset']==pytest.approx([.1725,0.,.5502])


def test_mapper_profile_preserves_sensor_origin_and_measured_age():
    import yaml
    p=yaml.safe_load((ROOT/'src/ht_scout_bridge/config/mapper_for_ht.yaml').read_text())['/elevation_mapping_node']['ros__parameters']
    assert p['subscribers']['lidar']['topic_name']=='/ht_real/lidar_filtered'
    assert p['subscribers']['lidar']['qos_reliability']=='reliable'
    assert not p['self_filter_enabled']  # Already filtered by the physical body geometry.
    assert p['publishers']['elevation_map_raw']['layers']==['elevation','variance','observation_age']
    assert p['map_length']/p['resolution']==pytest.approx(291)
