#!/usr/bin/env python3
import sys,argparse,json,math
from pathlib import Path
import numpy as np,rclpy
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from exploration_probe import ExplorationProbe
class RealProbe(ExplorationProbe):
 def publish_map(self):pass
 def save(self,final=False):
  super().save(final)
  p=Path(self.args.output)/'metrics.json';d=json.loads(p.read_text());d['synthetic_ht']=False;d.pop('ht_probability',None);d.pop('ht_map_rate_hz',None);d['ht_source']='separate lidar-only eight-direction student node, running in both conditions';p.write_text(json.dumps(d,indent=2))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--duration',type=float,default=120);args=ap.parse_args();args.reference=str(HERE/'assets/reference.npz');args.warmup=15;args.map_rate=5;args.probabilities=[.9]*8;args.map_length=80
 rclpy.init();node=RealProbe(args);success=False
 try:
  while rclpy.ok() and node.elapsed()<args.duration:rclpy.spin_once(node,timeout_sec=.1)
  node.record();success=True
 finally:node.save(final=success);node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
