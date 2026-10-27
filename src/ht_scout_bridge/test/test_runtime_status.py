import pytest
from ht_scout_bridge.runtime_status import diagnose

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
