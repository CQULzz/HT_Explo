"""Read-only parameter capture after discovery; no command or parameter writes."""
import argparse
import json
import time
from pathlib import Path
import rclpy
from rclpy.parameter_client import AsyncParameterClient
from rclpy.parameter import parameter_value_to_python


def main():
    p=argparse.ArgumentParser();p.add_argument('--wait-file',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    deadline=time.monotonic()+1500
    while not a.wait_file.exists():
        if time.monotonic()>deadline:raise TimeoutError('Measurement never started')
        time.sleep(.5)
    a.output.mkdir(parents=True,exist_ok=True)
    rclpy.init();node=rclpy.create_node('test_parameter_observer')
    try:
        for _ in range(20):rclpy.spin_once(node,timeout_sec=.25)
        for name in ['tare_planner_node','xytheta_follower','cupy_to_ht_bridge']:
            client=AsyncParameterClient(node,name)
            if not client.wait_for_services(timeout_sec=10):raise TimeoutError(name)
            f=client.list_parameters([],depth=0);rclpy.spin_until_future_complete(node,f,timeout_sec=10)
            if not f.done():raise TimeoutError(name+' list')
            names=f.result().result.names
            f=client.get_parameters(names);rclpy.spin_until_future_complete(node,f,timeout_sec=10)
            if not f.done():raise TimeoutError(name+' get')
            data=dict(zip(names,[parameter_value_to_python(v) for v in f.result().values]))
            (a.output/(name+'.json')).write_text(json.dumps(data,indent=2)+'\n')
            print('Captured',name,len(data),flush=True)
    finally:node.destroy_node();rclpy.shutdown()


if __name__=='__main__':main()
