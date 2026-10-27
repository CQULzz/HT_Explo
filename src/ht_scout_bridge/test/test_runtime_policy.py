from pathlib import Path
import pytest
from ht_scout_bridge.runtime_policy import resolve_runtime,direction_evidence
ROOT=Path(__file__).resolve().parents[3]

@pytest.mark.parametrize('mode,follow,bridge,topic',[('inspect',False,False,'/ht_real/cmd_vel_stamped'),
    ('preview',True,False,'/ht_real/preview/cmd_vel_stamped'),('drive',True,True,'/ht_real/cmd_vel_stamped')])
def test_modes(mode,follow,bridge,topic):
    p=resolve_runtime(mode,mapping_verified=True)
    assert (p.follower,p.command_bridge,p.command_topic)==(follow,bridge,topic)
    assert p.direction_accepted and not p.terrain_validated

@pytest.mark.parametrize('kw',[dict(mode='bad'),dict(mode='inspect',start_follower='true'),
    dict(mode='preview',start_command_bridge='true'),dict(mode='preview',command_topic='/cmd_vel'),
    dict(mode='drive',mapping_verified=False),dict(mode='drive',mapping_verified=True,direction_acceptance='validated'),
    dict(direction_acceptance='bad')])
def test_conflicting_or_unverified_drive_is_rejected(kw):
    with pytest.raises(ValueError):resolve_runtime(**kw)

def test_weight_and_axis_evidence(tmp_path):
    file=ROOT/'src/ht_scout_bridge/config/direction_validation.yaml'
    weights=ROOT/'tools/ht_cupy_bridge/student_best_epoch_weights.pth'
    assert direction_evidence(file,weights,list(range(8)),0.)==(True,False)
    assert direction_evidence(file,weights,list(reversed(range(8))),0.)==(False,False)
    wrong=tmp_path/'weights';wrong.write_bytes(b'wrong')
    assert direction_evidence(file,wrong,list(range(8)),0.)==(False,False)
