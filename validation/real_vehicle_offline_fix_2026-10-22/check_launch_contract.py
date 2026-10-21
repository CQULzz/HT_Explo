"""Resolve the real launch actions without executing any node/process."""
from pathlib import Path
import importlib.util,json
from launch import LaunchContext
from launch_ros.utilities import evaluate_parameters

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('real_launch',ROOT/'src/tare_planner/launch/explore_ht_fixposition.launch.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
# Resolve package-share resources to this candidate's source, not old install.
m.get_package_share_directory=lambda _:str(ROOT/'src/tare_planner/config')
context=LaunchContext()
context.launch_configurations.update(dict(
 scenario='garage',fixposition_config=str(ROOT/'src/tare_planner/config/fixposition.yaml'),
 rslidar_config=str(ROOT/'src/tare_planner/config/rslidar_helios32.yaml'),
 ht_config=str(ROOT/'src/tare_planner/config/ht.yaml'),use_sim_time='false',
 odometry_topic='/external/vehicle_odom',registered_scan_topic='/external/registered_cloud',
 elevation_topic='/external/elevation_raw',ht_topic='/candidate/ht',
 odometry_child_frame='base_link',command_topic='/offline_test/cmd_vel',
 start_fixposition='false',start_lidar='false',start_ht_bridge='true',start_follower='true'))
actions=m.start(context)
rows=[]
for action in actions:
 params=evaluate_parameters(context,action._Node__parameters)
 dictionaries=[p for p in params if isinstance(p,dict)]
 values={k:v for p in dictionaries for k,v in p.items()}
 executable=action.node_executable
 rows.append(dict(executable=executable if isinstance(executable,str) else ''.join(x.perform(context) for x in executable),
                  enabled=action.condition is None or action.condition.evaluate(context),
                  overrides=values))
by_exec={row['executable']:row for row in rows}
assert by_exec['tare_planner_node']['overrides']['sub_state_estimation_topic_']=='/external/vehicle_odom'
assert by_exec['xytheta_follower']['overrides']['odometry_topic']=='/external/vehicle_odom'
assert by_exec['cupy_to_ht.py']['overrides']['surface_odometry_topic']=='/external/vehicle_odom'
assert by_exec['tare_planner_node']['overrides']['sub_registered_scan_topic_']=='/external/registered_cloud'
assert by_exec['xytheta_follower']['overrides']['registered_scan_topic']=='/external/registered_cloud'
for name in ['tare_planner_node','xytheta_follower','cupy_to_ht.py']:
 assert by_exec[name]['overrides']['ht_topic']=='/candidate/ht'
 assert by_exec[name]['overrides']['odometry_child_frame']=='base_link'
assert not by_exec['fixposition_driver_ros2_exec']['enabled'] and not by_exec['rslidar_sdk_node']['enabled']
assert by_exec['xytheta_follower']['enabled'] and by_exec['cupy_to_ht.py']['enabled']
print(json.dumps({'passed':True,'started_processes':0,'nodes':rows},ensure_ascii=False,indent=2))
