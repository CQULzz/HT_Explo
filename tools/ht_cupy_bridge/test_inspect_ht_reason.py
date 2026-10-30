import numpy as np
import pytest
from inspect_ht_reason import inspect_cell,locate_cell


def test_diagnostic_cell_uses_same_floor_index_as_planner():
    assert locate_cell((241,241),[1.,-2.],.04,1.,-2.)==(120,120)
    assert locate_cell((241,241),[1.,-2.],.04,1.+.06,-2.)==(119,120)
    with pytest.raises(ValueError):locate_cell((241,241),[1.,-2.],.04,100.,0.)


def test_inspection_refuses_mixed_stamps_and_exports_exact_input_window():
    frame={'stamp_ns':np.array(10),'center':np.array([0.,0.]),'resolution':np.array(.04),
        'ht_valid':np.ones((3,3)), 'ht_observation_valid':np.zeros((3,3)),
        'ht_obstacle':np.zeros((3,3)),'ht_dir_0':np.full((3,3),.2)}
    reason={'stamp_ns':np.array(10),'center':np.array([0.,0.]),'resolution':np.array(.04),
        'reason_flags':np.full((3,3),9),'raw_model_min_probability':np.full((3,3),.2)}
    height=np.arange(53*53,dtype=np.float32).reshape(53,53)
    context={'stamp_ns':np.array(10),'height':height}
    detail,window=inspect_cell(frame,reason,context,0.,0.,0)
    assert detail['row']==detail['column']==1
    assert detail['reasons']==['physical_unsupported','model_low_with_context']
    np.testing.assert_array_equal(window,height[1:52,1:52])
    context['stamp_ns']=np.array(11)
    with pytest.raises(ValueError,match='source stamps'):inspect_cell(frame,reason,context,0.,0.,0)
