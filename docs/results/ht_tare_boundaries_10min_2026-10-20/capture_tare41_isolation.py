from pathlib import Path
import time,json
p=Path(Path('/tmp/ht_tare41_run_path').read_text().strip())/'garage'
while not (p/'current/measurement_started.json').exists():time.sleep(1)
import rclpy
rclpy.init();node=rclpy.create_node('tare_input_isolation_audit')
for _ in range(30):rclpy.spin_once(node,timeout_sec=.1)
result={}
for topic in ['/terrain_map','/terrain_map_ext','/simulation/terrain_map','/simulation/terrain_map_ext']:
 result[topic]={'publishers':[i.node_name for i in node.get_publishers_info_by_topic(topic)],'subscribers':[i.node_name for i in node.get_subscriptions_info_by_topic(topic)]}
(p/'terrain_topic_isolation.json').write_text(json.dumps(result,indent=2)+'\n');print(result)
node.destroy_node();rclpy.shutdown()
