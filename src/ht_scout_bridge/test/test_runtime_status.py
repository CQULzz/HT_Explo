import pytest
from ht_scout_bridge.runtime_status import diagnose
from ht_scout_bridge.runtime_status import RuntimeStatus
from types import SimpleNamespace
import json

@pytest.mark.parametrize('mode,kw,expected',[
 ('inspect',{},'INSPECT_NO_MOTOR_OUTPUT'),('preview',{},'PREVIEW_NO_MOTOR_OUTPUT'),
 ('drive',{},'COMMAND_SENT_NOT_WHEEL_CONFIRMED'),
 ('drive',{'odom_age':1.},'ODOMETRY_MISSING_OR_STALE'),
 ('drive',{'map_age':1.1},'HT_MAP_MISSING_OR_STALE'),
 ('drive',{'direction_accepted':False},'DIRECTION_EVIDENCE_NOT_ACCEPTED'),
 ('drive',{'planner':'WAIT_START'},'WAIT_START'),
 ('drive',{'follower':'HT_CURRENT_POSE_BLOCKED'},'HT_CURRENT_POSE_BLOCKED'),
 ('drive',{'bridge':'PERMISSION_MISSING_OR_STALE'},'PERMISSION_MISSING_OR_STALE'),
 ('drive',{'output_subscribers':0},'NO_CHASSIS_COMMAND_SUBSCRIBER'),
 ('drive',{'output_publishers':2},'COMMAND_OWNERSHIP_CONFLICT')])
def test_stop_reasons_do_not_mistake_mode_or_command_for_motion(mode,kw,expected):
    args=dict(odom_age=.1,map_age=.4,direction_accepted=True,planner='HT_ASSISTED',
        follower='DRIVING',bridge='FORWARDING',output_publishers=1,output_subscribers=1)
    args.update(kw);assert diagnose(mode,**args)==expected


def test_map_reports_preserve_source_ages_and_reject_malformed_or_unbounded_consumers():
    status=SimpleNamespace(map_consumers={})
    def receive(value):
        RuntimeStatus.map_diagnostics_received(status,SimpleNamespace(data=value))
    for text in ['bad json','[]','null','{}',json.dumps({'consumer':'/planner','diagnostic_only':False})]:
        receive(text)
    assert status.map_consumers=={}
    report={'consumer':'/ht_real/tare_planner','diagnostic_only':True,
        'latest_source_age_s':.4,'cycle_source_age_s':1.2}
    receive(json.dumps(report))
    assert status.map_consumers[report['consumer']][0]==report
    receive(json.dumps({**report,'consumer':'x'*257}))
    receive(' '*16385)
    for i in range(12):receive(json.dumps({**report,'consumer':f'/consumer_{i}'}))
    assert len(status.map_consumers)==8


def test_current_heading_and_discrete_footprint_do_not_use_best_direction_as_permission():
    import math
    import numpy as np
    from ht_scout_bridge.runtime_status import footprint_diagnosis,heading_channel
    r=.04;rr,cc=np.indices((61,61));x=(30-rr)*r;y=(30-cc)*r
    a={'ht_valid':np.ones(x.shape),'ht_observation_valid':np.ones(x.shape),'ht_obstacle':np.zeros(x.shape)}
    for k in range(8):a[f'ht_dir_{k}']=np.full(x.shape,.9 if k==2 else .1)
    # Unknown lies outside the diagnostic disk, inside the execution mask.
    a['ht_observation_valid'][14,30]=0
    d,mask=footprint_diagnosis(a,x,y,.001,0,r,.6,0.)
    assert d['best_probability']==.9 and d['current_heading_probability']==.1 and d['current_heading_low']
    assert d['unknown']==1 and mask[14,30]
    assert ((x**2+y**2<=.6**2)&(a['ht_observation_valid']<.5)).sum()==0
    assert d['center_x']==0 and d['discrete_radius_m']>.6
    assert heading_channel(-math.pi/4)==7
    assert heading_channel(math.pi/4,math.pi/4,[7,6,5,4,3,2,1,0])==7
    d,_=footprint_diagnosis(a,x,y,0,0,r,.6,math.pi/2)
    assert d['current_heading_probability']==.9 and not d['current_heading_low']
