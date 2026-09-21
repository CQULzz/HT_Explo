#!/usr/bin/env python3
import sys,argparse,json,math
from pathlib import Path
import numpy as np,rclpy
from std_msgs.msg import String, Bool
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE.parent))
from exploration_probe import ExplorationProbe
class RealProbe(ExplorationProbe):
 def __init__(self,args):
  self.mission_state='WAIT_START';self.execution_status='WAIT_START';self.mission_completed=False;self.completion_time=None;self.state_events=[]
  super().__init__(args)
  self.create_subscription(String,'/mission_state',lambda m:self.state('mission_state',m.data),10)
  self.create_subscription(String,'/ht_execution_status',lambda m:self.state('execution_status',m.data),10)
  self.create_subscription(Bool,'/mission_completed',self.complete,10)
 def state(self,key,value):
  if getattr(self,key)!=value:
   self.state_events.append(dict(t=self.elapsed(),kind=key,value=value))
   setattr(self,key,value)
 def complete(self,msg):
  self.mission_completed=msg.data
  if msg.data and self.completion_time is None:self.completion_time=self.elapsed()
 def record(self):
  n=len(self.rows);super().record()
  if len(self.rows)>n:self.rows[-1].update(mission_state=self.mission_state,execution_status=self.execution_status,mission_completed=self.mission_completed)
 def publish_map(self):pass
 def save(self,final=False):
  super().save(final)
  p=Path(self.args.output)/'metrics.json';d=json.loads(p.read_text());d['mission_completed']=self.mission_completed;d['mission_completion_time_s']=self.completion_time;d['state_events']=self.state_events;d['synthetic_ht']=False;d.pop('ht_probability',None);d.pop('ht_map_rate_hz',None);d['ht_source']='separate lidar-only eight-direction student node, running in both conditions';p.write_text(json.dumps(d,indent=2))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--output',required=True);ap.add_argument('--duration',type=float,default=120);args=ap.parse_args();args.reference=str(HERE/'assets/reference.npz');args.warmup=15;args.map_rate=5;args.probabilities=[.9]*8;args.map_length=80
 rclpy.init();node=RealProbe(args);success=False
 try:
  while rclpy.ok() and node.elapsed()<args.duration:rclpy.spin_once(node,timeout_sec=.1)
  node.record();success=True
 finally:node.save(final=success);node.destroy_node();rclpy.try_shutdown()
if __name__=='__main__':main()
