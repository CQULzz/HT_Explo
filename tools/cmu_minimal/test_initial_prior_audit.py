"""Independent audit history regressions; no ROS graph or simulator required."""
import numpy as np
import audit_commands as audit
from grid_map_msgs.msg import GridMap
from std_msgs.msg import Float32MultiArray,MultiArrayDimension

def fixture(stamp,measured=False,score=.9,obstacle=0.,unknown=False,cx=0.):
    m=GridMap();m.header.frame_id='map';m.header.stamp.sec=stamp
    m.info.resolution=.04;m.info.length_x=m.info.length_y=101*.04;m.info.pose.position.x=cx
    m.layers=['ht_dir_'+str(k) for k in range(8)]+['ht_valid','ht_observation_valid','ht_obstacle','ht_measured_valid']
    for k in range(12):
        a=Float32MultiArray();a.layout.dim=[MultiArrayDimension(label='column_index',size=101,stride=10201),MultiArrayDimension(label='row_index',size=101,stride=101)]
        v=np.full((101,101),.9 if k<8 else (0. if k==10 else 1.),np.float32)
        if k<8:v[50,50]=score
        if k==10:v[50,50]=obstacle
        if k==11:v[:]=float(measured)
        if unknown and k in (8,9):v[50,50]=0.
        a.data=v.flatten(order='F').tolist();m.data.append(a)
    return audit.decode(m)

def main():
    audit.RADIUS=.6
    history=audit.InitialLabels(0.,0.,.65)
    def run(m):
        history.apply(m)
        d=dict(time=m['stamp']+.1,map_stamp=m['stamp'],linear_candidate=0.,angular_candidate=0.,x=0.,y=0.,yaw=0.,reaction_time=.1,linear_brake_accel=2.5,angular_brake_accel=3.,initial_support_prior_enabled=True,initial_support_prior_ready=True,initial_support_prior_policy='explicit_labels_v1',initial_support_prior_x=0.,initial_support_prior_y=0.,initial_support_prior_radius=.65)
        return audit.check(m,d)
    assert run(fixture(100,unknown=True,score=np.nan))[0]
    assert run(fixture(101,measured=True))[0]
    assert run(fixture(102,unknown=True,score=np.nan))[0]
    assert not run(fixture(103,measured=True,score=.1))[0]
    assert not run(fixture(104,unknown=True))[0]
    assert run(fixture(105,measured=True,obstacle=1.))[1]=='OCCUPIED'
    assert run(fixture(106,unknown=True))[1]=='OCCUPIED'
    # Stale positive cannot erase a retained negative.
    stale=fixture(107,measured=True);stale['received']=109.
    assert run(stale)[1]=='OCCUPIED'
    assert run(fixture(108,measured=True))[0]
    history.apply(fixture(109,cx=8.))
    assert run(fixture(110,unknown=True,score=np.nan))[0]
    print('PASS 10 independent initial-label audit transitions')

if __name__=='__main__':main()
