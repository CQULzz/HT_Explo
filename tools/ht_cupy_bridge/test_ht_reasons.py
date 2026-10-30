import numpy as np
from ht_reasons import explain_ht,REASON_FLAGS


def test_reasons_overlap_and_do_not_change_probabilities_or_support():
    p=np.full((8,3,4),.8,np.float32);p[3,1,1]=.2
    context=np.ones((3,4),bool);physical=context.copy();physical[1,1]=False
    occupied=np.zeros_like(context);occupied[1,1]=True
    rejected=np.zeros_like(context);rejected[1,1]=True
    inferred=np.zeros_like(context);inferred[1,1]=True
    args=[p,context,physical,occupied,rejected,inferred];before=[a.copy() for a in args]
    flags,bits,minimum,stats=explain_ht(*args)
    assert flags[1,1]==1|4|8|16|32
    assert bits[1,1]==8 and minimum[1,1]==np.float32(.2)
    assert stats['counts_overlap'] and sum(stats['counts'].values())>1
    for a,b in zip(args,before):np.testing.assert_array_equal(a,b)


def test_no_context_is_never_reported_as_an_accepted_model_score():
    p=np.full((8,2,2),.9,np.float32);context=np.zeros((2,2),bool)
    other=np.zeros_like(context)
    flags,bits,minimum,stats=explain_ht(p,context,context,other,other,other)
    assert np.isnan(minimum).all() and not bits.any()
    assert np.all(flags==REASON_FLAGS['physical_unsupported']|REASON_FLAGS['context_unsupported'])
