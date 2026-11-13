from pathlib import Path
import sys
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'tools/cmu_minimal'))
from audit_commands import check
m=dict(rows=81,cols=81,res=.04,cx=0.,cy=0.,scores=np.full((8,81,81),.9),valid=np.ones((81,81)),missing=np.zeros((81,81)),occupied=np.ones((81,81)),raw_occupied=np.zeros((81,81),bool))
m['raw_occupied'][:,29]=True
d=dict(x=0.,y=0.,yaw=0.,linear_candidate=.15,angular_candidate=0.,time=1.,map_stamp=1.,reaction_time=.1,linear_brake_accel=2.5,angular_brake_accel=3.,obstacle_footprint='oriented_box_v1',body_length=.6,body_width=.6,support_radius=.45)
assert check(m,d)[0]
assert check(m,{**d,'linear_candidate':-.15})[0]
assert not check(m,{**d,'yaw':.45,'linear_candidate':0.,'angular_candidate':1.})[0]
assert not check(m,{**d,'obstacle_footprint':'circle_v1'})[0]
assert not check(m,{**d,'time':3.})[0]
m['raw_occupied'][40,40]=True
assert not check(m,d)[0]
print('PASS 6 independent footprint/legacy/TTL audit checks')
