import numpy as np
import pytest

from height_evidence import qualify_height_evidence
from historical_elevation import HistoricalElevation
from ht_support import prepare_ht_context


def evidence(*, age=0., delta=0., rejected=False, occupied=False):
    shape=(291,291);now=1793521000.125
    z=np.full(shape,-.65,np.float32);z[145,145]+=delta
    obs=np.ones(shape,bool);mask=np.zeros(shape,bool);obstacle=np.full(shape,np.nan,np.float32)
    if rejected:mask[145,145]=True;obs[145,145]=False
    if occupied:obstacle[145,145]=z[145,145]
    when=np.full(shape,now-age,np.float64)
    return qualify_height_evidence(z,obs,mask,obstacle,when,when,np.full(shape,-.65),now)


def test_stale_height_becomes_physical_unknown_not_free_or_hard_obstacle():
    q=evidence(age=96.,delta=1.,rejected=True,occupied=True)
    assert np.isnan(q.height[145,145]) and np.isnan(q.obstacle[145,145])
    assert q.physical_unknown[145,145]
    _,support,occupied,physical=prepare_ht_context(q.height,q.observed,np.zeros_like(q.observed),
        q.obstacle,.04,physical_exclusion=q.physical_unknown)
    assert not support[120,120] and support[120,121]
    assert not occupied[120,120] and not physical[120,120]


@pytest.mark.parametrize('delta',[.8,-.4])
def test_fresh_positive_and_negative_rejected_features_remain_occupied(delta):
    q=evidence(age=.25,delta=delta,rejected=True,occupied=True)
    assert np.isfinite(q.obstacle[145,145])
    assert not q.physical_unknown[145,145]


def test_uncertain_flat_height_does_not_invent_an_obstacle_or_an_observation():
    q=evidence(age=.2,rejected=True,occupied=True)
    assert np.isnan(q.obstacle[145,145]) and not q.observed[145,145]
    assert q.physical_unknown[145,145]


def test_old_accepted_off_surface_height_is_excluded_from_nearest_context():
    q=evidence(age=20.,delta=.7)
    assert q.physical_unknown[145,145] and not q.observed[145,145]
    assert np.isnan(q.height[145,145])


def test_old_compatible_ground_and_fresh_accepted_step_are_unchanged():
    assert evidence(age=100.).observed[145,145]
    q=evidence(age=.1,delta=.2)
    assert q.observed[145,145] and abs(q.height[145,145]+.45)<1e-6


@pytest.mark.parametrize('backend',['numpy','numba'])
def test_mode_and_rejected_obstacle_times_follow_selected_evidence(backend):
    h=HistoricalElevation(.04,window_backend=backend,fusion_backend=backend,track_evidence_times=True)
    z=np.full((3,3),-.65,np.float32);v=np.full_like(z,.001)
    h.fuse(z,v,0.,0.,100.,observation_time=np.full(z.shape,100.))
    h.fuse(z+1.2,v,0.,0.,101.,observation_time=np.full(z.shape,101.))
    h.window(0.,0.,3,102.,reference_height=-.65)
    assert np.isfinite(h.last_window_obstacle_elevation[1,1])
    assert h.last_window_obstacle_time[1,1]==101.
    h.window(0.,0.,3,102.,reference_height=-.65,preferred_elevation=z)
    assert h.last_window_observation_time[1,1]==100.


def test_expired_ground_does_not_veto_entire_context_but_stays_physically_unknown():
    h=HistoricalElevation(.04,window_backend='numpy',fusion_backend='numpy',track_evidence_times=True)
    z=np.full((291,291),-.65,np.float32);v=np.full_like(z,.001)
    h.fuse(z,v,0.,0.,100.,observation_time=np.full(z.shape,100.))
    fresh=z.copy();fresh[145,145]=np.nan
    h.fuse(fresh,v,0.,0.,701.,observation_time=np.full(z.shape,701.))
    height,_,_,_=h.window(0.,0.,291,701.,reference_height=-.65,preferred_elevation=fresh)
    q=qualify_height_evidence(height,np.isfinite(height),h.last_window_incompatible_mask,
        h.last_window_obstacle_elevation,h.last_window_observation_time,h.last_window_obstacle_time,
        np.full(z.shape,-.65),701.)
    _,support,_,physical=prepare_ht_context(q.height,q.observed,np.zeros(z.shape,bool),q.obstacle,.04,
        physical_exclusion=q.physical_unknown)
    assert not support[120,120] and support[120,121] and not physical[120,120]


def test_full_epoch_seconds_do_not_round_old_evidence_into_fresh_evidence():
    assert evidence(age=5.01,delta=.5,rejected=True,occupied=True).physical_unknown[145,145]
    assert np.isfinite(evidence(age=4.99,delta=.5,rejected=True,occupied=True).obstacle[145,145])
