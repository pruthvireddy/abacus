"""Prespecified dependence-aware helpers; no automatic outcome exploration."""
from datetime import date,timedelta
import numpy as np


def development_quintiles(values,years):
    values=np.asarray(values,dtype=float);years=np.asarray(years)
    selected=values[(years>=2020)&(years<=2023)&np.isfinite(values)]
    if not len(selected):raise ValueError('no development volatility observations')
    return np.quantile(selected,[.2,.4,.6,.8])


def volatility_bin(values,cutoffs):
    values=np.asarray(values,dtype=float)
    bins=np.searchsorted(cutoffs,values,side='right').astype(np.int8)
    bins[~np.isfinite(values)]=-1
    return bins


def moving_week_mean_interval(weeks,values,block=2,replicates=2000,seed=1414):
    """Moving calendar-week blocks; all event/control pairs stay together.

    Pass paired event-minus-control differences to estimate a matched effect.
    Empty calendar weeks remain in the sampling clock. Sparse support is
    returned explicitly, not converted to a spurious precise zero interval.
    """
    values=np.asarray(values,dtype=float)
    weeks=np.asarray(weeks,dtype='datetime64[D]')
    valid=np.isfinite(values);values=values[valid];weeks=weeks[valid]
    if not len(values):return {'estimate':None,'lower':None,'upper':None,'events':0,'weeks':0}
    first,last=weeks.min(),weeks.max()
    index=((weeks-first).astype(int)//7).astype(int)
    count=int((last-first).astype(int)//7)+1
    sums=np.bincount(index,weights=values,minlength=count)
    counts=np.bincount(index,minlength=count)
    support=int((counts>0).sum())
    result={'estimate':float(values.mean()),'events':len(values),'weeks':support,
            'calendar_weeks':count,'block_weeks':block,'replicates':replicates,'seed':seed}
    if support<2 or count<block:
        return dict(result,lower=None,upper=None)
    rng=np.random.default_rng(seed)
    # Keep exactly count sampled weeks; do not overweight the final block.
    starts=rng.integers(0,count-block+1,size=(replicates,(count+block-1)//block))
    selected=(starts[:,:,None]+np.arange(block)).reshape(replicates,-1)[:,:count]
    numerator=sums[selected].sum(axis=1);denominator=counts[selected].sum(axis=1)
    draws=numerator[denominator>0]/denominator[denominator>0]
    lower,upper=np.quantile(draws,[.025,.975])
    return dict(result,lower=float(lower),upper=float(upper),valid_replicates=len(draws))


def support(events,sessions,weeks):
    return 'adequate' if events>=50 and sessions>=30 and weeks>=12 else 'low_support'
