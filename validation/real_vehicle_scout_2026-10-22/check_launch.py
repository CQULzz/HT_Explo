"""Resolve hardware launch only; no node/process action is executed."""
from pathlib import Path
import json,importlib.util,yaml
from launch import LaunchContext
from launch_ros.utilities import evaluate_parameters
ROOT=Path(__file__).resolve().parents[2]
p=ROOT/'src/ht_scout_bridge/launch/scout_real.launch.py'
spec=importlib.util.spec_from_file_location('scout_launch',p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
m.get_package_share_directory=lambda name:str(ROOT/'src'/name)
context=LaunchContext();context.launch_configurations.update(dict(use_sim_time='false',start_follower='false',
 calibration_file=str(ROOT/'src/ht_scout_bridge/config/scout_extrinsics.yaml'),
 odometry_topic='/fixposition/odometry_enu',cloud_topic='/rslidar_points',
 elevation_topic='/elevation_mapping_node/elevation_map_raw',source_age_layer='time',command_topic='/ht_real/cmd_vel_stamped'))
rows=[]
for action in m.start(context):
 parameters=evaluate_parameters(context,action._Node__parameters)
 direct={k:v for d in parameters if isinstance(d,dict) for k,v in d.items()}
 executable=action.node_executable
 row={'executable':executable,'enabled':action.condition is None or action.condition.evaluate(context),
      'parameters':direct,'parameter_files':[str(d) for d in parameters if not isinstance(d,dict)]}
 rows.append(row)
by={r['executable']:r for r in rows}
assert set(by)=={'scout_inputs','cupy_to_ht.py','tare_planner_node','xytheta_follower'}
assert not by['xytheta_follower']['enabled']
assert by['xytheta_follower']['parameters']['command_frame']=='base_link'
assert by['xytheta_follower']['parameters']['command_topic']=='/ht_real/cmd_vel_stamped'
assert by['tare_planner_node']['parameters']['sub_state_estimation_topic_']=='/ht_real/odometry'
assert by['cupy_to_ht.py']['parameters']['surface_odometry_topic']=='/ht_real/odometry'
assert by['xytheta_follower']['parameters']['odometry_topic']=='/ht_real/odometry'
assert all('garage' not in name and 'campus' not in name for r in rows for name in r['parameter_files'])
for key in ['/ht_xytheta_path','/ht_navigation_allowed','/mission_completed','/collision_cloud','/stop']:
 assert (key,'/ht_real'+key) in m.HARDWARE_REMAPS
config=yaml.safe_load((ROOT/'src/ht_scout_bridge/config/ht_real.yaml').read_text())['/**']['ros__parameters']
assert not config['ht_directions_calibrated'] and config['ht_startup_radius']==0
mapping=yaml.safe_load((ROOT/'src/ht_scout_bridge/config/mapper_for_ht.yaml').read_text())['/elevation_mapping_node']['ros__parameters']
assert round(mapping['map_length']/mapping['resolution'])==291
assert mapping['resolution']==.04 and mapping['publishers']['elevation_map_raw']['layers']==['elevation','variance','time']
print(json.dumps({'passed':True,'processes_started':0,'nodes':rows,'native_grid_cells':291,'native_resolution_m':.04},ensure_ascii=False,indent=2))
