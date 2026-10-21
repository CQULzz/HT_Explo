"""Coordinate and byte-stream regressions for the recorded RViz renderer."""
from copy import deepcopy
from types import SimpleNamespace as S
import numpy as np
from PIL import Image
import pytest
from rviz_recorded_comparison import capture_rgb, decode_ht_grid, frame_times, past_row


def grid(n,k,res=.041,offset=(0,0)):
    logical=np.arange(n*k,dtype=np.float32).reshape(n,k)/np.float32(n*k)
    layers=['ht_valid']+[f'ht_dir_{i}' for i in range(8)]
    data=[]
    for index in range(9):
        values=np.ones((n,k),np.float32) if index==0 else logical.copy()
        raw=np.roll(values,offset,(0,1)).flatten(order='F')
        dims=[S(label='column_index',size=k,stride=n*k),S(label='row_index',size=n,stride=n)]
        data.append(S(data=raw,layout=S(dim=dims,data_offset=0)))
    return S(header=S(frame_id='map',stamp=S(sec=10,nanosec=0)),
             info=S(length_x=n*res,length_y=k*res,resolution=res,
                    pose=S(position=S(x=7.,y=-3.),orientation=S(x=0.,y=0.,z=0.,w=1.))),
             layers=layers,data=data,outer_start_index=offset[0],inner_start_index=offset[1]),logical


@pytest.mark.parametrize('n,k',[(1,1),(4,7),(8,5),(241,241),(291,341)])
@pytest.mark.parametrize('stride',[1,3])
def test_rectangular_geometry_and_circular_buffers(n,k,stride):
    m,expected=grid(n,k,offset=(n-1,k-1))
    h=decode_ht_grid(m,12.,stride)
    np.testing.assert_array_equal(h['p'][0],expected[::stride,::stride])
    for i,x in enumerate(h['x']):
        assert int(np.floor(n/2-(x-7)/m.info.resolution+1e-9))==i*stride
    for j,y in enumerate(h['y']):
        assert int(np.floor(k/2-(y+3)/m.info.resolution+1e-9))==j*stride
    assert h['valid'].all() and h['source_age_s']==2.


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-.1,1.1])
def test_bad_scores_never_become_valid_colors(value):
    m,_=grid(4,7);m.data[1].data[0]=value
    assert not decode_ht_grid(m,12.,1)['valid'][0,0]


@pytest.mark.parametrize('size',[(1920,1080),(1280,720),(640,480),(1080,1920),(1919,1079),(3840,2160)])
def test_capture_geometry(size):
    im=Image.new('RGBA',size,(20,40,80,255))
    if size!=(1920,1080):
        with pytest.raises(ValueError,match='No scaling/cropping'): capture_rgb(im)
    else:
        result=capture_rgb(im)
        assert result.mode=='RGB' and len(result.tobytes())==1920*1080*3
        assert result.getpixel((1919,1079))==(20,40,80)


@pytest.mark.parametrize('start,end,speed,fps',[(0,600,4,10),(0,.5,4,10),(10,10.01,4,10),(2,3.01,3,15),(.1,.4,3,10)])
def test_timeline_always_reaches_endpoint(start,end,speed,fps):
    times=frame_times(start,end,speed,fps)
    assert times[0]==start and times[-1]==end
    assert all(a<b for a,b in zip(times,times[1:]))
    assert max(np.diff(times))<=speed/fps+1e-9


@pytest.mark.parametrize('args',[(0,1,float('inf'),10),(0,1,float('nan'),10),(0,1,0,10),(0,600,1e-308,10),(0,1,4,0),(1,1,4,10),(-1,600,4,10)])
def test_bad_timelines(args):
    with pytest.raises(ValueError):frame_times(*args)


def test_no_future_hud_samples_and_empty_input():
    assert past_row([.5,1.],[{'v':1},{'v':2}],0) is None
    assert past_row([],[],0) is None
    assert past_row([.5,1.],[{'v':1},{'v':2}],.5)=={'v':1}


@pytest.mark.parametrize('case',['missing','short','offset','stride','rotation','fractional','buffer','nan_valid'])
def test_malformed_grid(case):
    m,_=grid(4,7)
    if case=='nan_valid':
        m.data[0].data[0]=float('nan'); assert not decode_ht_grid(m,12.,1)['valid'][0,0];return
    if case=='missing':m.layers[0]='missing'
    elif case=='short':m.data[1].data=m.data[1].data[:2]
    elif case=='offset':m.data[0].layout.data_offset=1
    elif case=='stride':m.data[0].layout.dim[0].stride=1
    elif case=='rotation':m.info.pose.orientation.z=.5
    elif case=='fractional':m.info.length_x+=.1*m.info.resolution
    elif case=='buffer':m.outer_start_index=4
    with pytest.raises(ValueError):decode_ht_grid(m,12.)
