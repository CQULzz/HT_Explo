"""Overlapping explanation flags, independent of execution permission."""
import numpy as np

REASON_FLAGS={'physical_unsupported':1,'context_unsupported':2,'measured_occupied':4,
              'model_low_with_context':8,'input_rejected_center':16,'interpolated_center':32,
              'model_nonfinite_with_context':64}


def explain_ht(probabilities,context_support,physical_support,occupied,rejected_center,inferred_center):
    p=np.asarray(probabilities)
    context=np.asarray(context_support,bool);physical=np.asarray(physical_support,bool)
    occupied=np.asarray(occupied,bool);rejected=np.asarray(rejected_center,bool);inferred=np.asarray(inferred_center,bool)
    if p.ndim!=3 or p.shape[0]!=8 or any(a.shape!=p.shape[1:] for a in (context,physical,occupied,rejected,inferred)):
        raise ValueError('HT reason arrays must match eight-direction output geometry')
    flags=np.zeros(context.shape,np.uint8)
    finite=np.isfinite(p);low=finite&(p<.5)
    reasons={'physical_unsupported':~physical,'context_unsupported':~context,'measured_occupied':occupied,
             'model_low_with_context':context&np.any(low,axis=0),
             'input_rejected_center':rejected,'interpolated_center':inferred,
             'model_nonfinite_with_context':context&~np.all(finite,axis=0)}
    counts={}
    for name,mask in reasons.items():
        flags[mask]|=REASON_FLAGS[name];counts[name]=int(mask.sum())
    direction_bits=np.zeros(context.shape,np.uint8)
    for k in range(8):direction_bits[context&low[k]]|=np.uint8(1<<k)
    # Scores with insufficient context stay unreported, even if the raw model
    # happens to be confident. Flags may overlap and do not create free cells.
    minimum=np.min(p,axis=0)
    minimum=np.where(context&np.isfinite(minimum),minimum,np.nan).astype(np.float32)
    return flags,direction_bits,minimum,{'cells':int(context.size),'counts':counts,
        'counts_overlap':True,'threshold':.5,'permission_semantics':'diagnostic only; execution gates unchanged'}
