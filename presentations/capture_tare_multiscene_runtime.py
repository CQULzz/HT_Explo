#!/usr/bin/env python3
"""Read effective parameters and topic isolation once per active scene."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import time
import yaml


def main():
    ap=argparse.ArgumentParser();ap.add_argument('suite',type=Path);ap.add_argument('--domain',type=int,required=True);a=ap.parse_args()
    done=set()
    while True:
        try:state=json.loads((a.suite/'suite.json').read_text())
        except (FileNotFoundError,json.JSONDecodeError):time.sleep(1);continue
        for i,row in enumerate(state['runs']):
            scene=row['scenario'];folder=a.suite/scene
            if scene in done or row['state']!='RECORDING' or not (folder/'current/measurement_started.json').exists():continue
            env=os.environ.copy();env.update(ROS_DOMAIN_ID=str(a.domain+i),ROS_LOCALHOST_ONLY='1')
            records=[]
            for node,name in [('/tare_planner_node','planner_parameters.yaml'),('/xytheta_follower','follower_parameters.yaml')]:
                for attempt in range(2):
                    result=subprocess.run(['ros2','param','dump',node,'--no-daemon','--spin-time','6'],env=env,capture_output=True,text=True,timeout=35)
                    data=yaml.safe_load(result.stdout)
                    records.append(dict(node=node,attempt=attempt,returncode=result.returncode,stderr=result.stderr,stdout_bytes=len(result.stdout)))
                    if isinstance(data,dict) and node in data:
                        (folder/name).write_text(result.stdout);break
                    (folder/(name+f'.attempt{attempt}')).write_text(result.stdout+'\n'+result.stderr)
            (folder/'parameter_capture_attempts.json').write_text(json.dumps(records,indent=2)+'\n')
            program='''import rclpy,json,time
rclpy.init();n=rclpy.create_node('ht_multiscene_topic_audit')
topics=['/terrain_map','/terrain_map_ext','/simulation/terrain_map','/simulation/terrain_map_ext','/ht_traversability/global_local','/tare_tsp_order','/tare_native_waypoint','/ht_xytheta_path']
deadline=time.monotonic()+10
while time.monotonic()<deadline:rclpy.spin_once(n,timeout_sec=.2)
rows={t:[dict(node_name=p.node_name,node_namespace=p.node_namespace,topic_type=p.topic_type) for p in n.get_publishers_info_by_topic(t)] for t in topics}
print(json.dumps(dict(publishers=rows,navigation_cmu_terrain_isolated=not rows['/terrain_map'] and not rows['/terrain_map_ext'],ht_map_published=bool(rows['/ht_traversability/global_local']))));n.destroy_node();rclpy.shutdown()
'''
            result=subprocess.run(['python3','-c',program],env=env,capture_output=True,text=True,timeout=25)
            try:topic=json.loads(result.stdout.strip().splitlines()[-1])
            except (ValueError,IndexError):topic=dict(error=result.stderr,stdout=result.stdout,returncode=result.returncode)
            (folder/'terrain_topic_isolation.json').write_text(json.dumps(topic,ensure_ascii=False,indent=2)+'\n')
            done.add(scene);print('CAPTURED',scene,flush=True)
        if (a.suite/'FINISHED.json').exists():break
        time.sleep(2)


if __name__=='__main__':main()
