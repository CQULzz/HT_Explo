import numpy as np
import pytest
from elevation_quality import preprocess_elevation
from height_evidence import qualify_height_evidence, overlay_observation_times
from historical_elevation import HistoricalElevation
from evidence_trace import trace_evidence, EVIDENCE_FLAGS, relative_age


@pytest.mark.parametrize('backend',['numpy','numba'])
def test_source_masks_are_identical_without_unused_smoothing(backend):
    rng=np.random.default_rng(32)
    z=rng.normal(0,.01,(61,61)).astype(np.float32)
    z[10:15,10:15]=.4;z[30,30]=1;z[50:55,50:55]=np.nan
    v=np.full_like(z,.01);v[8,8]=.4
    a=preprocess_elevation(z,v,.04,backend=backend)
    b=preprocess_elevation(z,v,.04,backend=backend,denoise=False)
    for name in ('observed_quality','rejected_mask','edge_mask'):
        np.testing.assert_array_equal(getattr(a,name),getattr(b,name))
    np.testing.assert_array_equal(b.height_m,np.where(a.observed_quality,z,np.nan))
    assert a.stats['smoothed_cells']>0 and b.stats['smoothed_cells']==0


def test_current_edge_overlay_uses_its_measurement_time_not_old_floor_time():
    now=1793619491.8;shape=(3,3)
    selected=np.full(shape,now-100);age=np.full(shape,.7,np.float32)
    mask=np.zeros(shape,bool);mask[1,1]=True
    when=overlay_observation_times(selected,age,mask,now)
    np.testing.assert_array_equal(when[~mask],selected[~mask])
    assert when[1,1]==now-float(age[1,1])
    z=np.zeros(shape,np.float32);z[1,1]=.25
    obs=np.ones(shape,bool);reject=np.zeros(shape,bool);obstacle=np.full(shape,np.nan)
    old=qualify_height_evidence(z,obs,reject,obstacle,selected,selected,np.zeros(shape),now)
    new=qualify_height_evidence(z,obs,reject,obstacle,when,selected,np.zeros(shape),now)
    assert old.physical_unknown[1,1] and new.observed[1,1]
    assert not new.physical_unknown[1,1] and new.height[1,1]==.25


@pytest.mark.parametrize('backend',['numpy','numba'])
def test_history_tracks_expired_and_rejected_records_without_reviving_them(backend):
    h=HistoricalElevation(.04,window_backend=backend,fusion_backend=backend,track_evidence_times=True)
    z=np.zeros((3,3),np.float32);v=np.full_like(z,.001)
    h.fuse(z,v,0,0,100,observation_time=100)
    bad=np.zeros(z.shape,bool);bad[1,1]=True
    h.record_rejections(bad,0,0,101,np.full(z.shape,101.),elevation=z+1)
    selected,*_=h.window(0,0,3,701,reference_height=0.)
    assert np.isnan(selected).all()
    assert h.last_window_last_accepted_time[1,1]==100.
    assert h.last_window_last_rejected_time[1,1]==101.
    assert not np.isfinite(h.last_window_observation_time[1,1])


def test_trace_distinguishes_missing_source_from_variance_and_history_rejections():
    shape=(1,3);no=np.zeros(shape,bool);yes=~no
    layers=trace_evidence(source_height=np.array([[np.nan,0,0]]),
        source_variance=np.array([[0,.36,.001]]),source_age=np.array([[0,561,.5]]),
        source_rejected=np.array([[False,True,False]]),history_height=np.array([[np.nan,np.nan,0]]),
        history_incompatible=np.array([[False,True,False]]),final_rejected=no,stale_surface=no,
        quarantined_candidate=no,physical=np.array([[False,False,True]]),context=yes,occupied=no,
        selected_time=np.array([[-np.inf,-np.inf,99.5]]),last_accepted_time=np.array([[-np.inf,90,99.5]]),
        last_rejected_time=np.array([[-np.inf,99,-np.inf]]),stamp_s=100.)
    flags=layers['evidence_flags']
    assert flags[0,0]&EVIDENCE_FLAGS['source_height_missing']
    assert not flags[0,0]&EVIDENCE_FLAGS['source_variance_rejected']
    assert flags[0,1]&EVIDENCE_FLAGS['source_variance_rejected']
    assert layers['last_accepted_age_s'][0,1]==10
    assert np.isnan(layers['last_accepted_age_s'][0,0])
    assert flags[0,2]==0
    assert relative_age(1793619491.8,np.array([1793619491.3]))[0]==.5
