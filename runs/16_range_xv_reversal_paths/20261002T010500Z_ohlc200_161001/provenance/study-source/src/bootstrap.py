"""Shared synchronized session and five-session moving-block resamples."""
import numpy as np
import pandas as pd
from .common import SEED

class Bootstrap:
    def __init__(self,dates,reps=2000):
        self.dates=sorted(set(dates));self.index={d:i for i,d in enumerate(self.dates)};n=len(self.dates)
        rng=np.random.default_rng(SEED)
        self.weights=np.array([np.bincount(rng.integers(n,size=n),minlength=n) for _ in range(reps)],dtype=float)
        rng=np.random.default_rng(SEED);width=min(5,n)
        self.blocks=np.array([np.bincount((rng.integers(n-width+1,size=int(np.ceil(n/width)))[:,None]+np.arange(width)).ravel()[:n],minlength=n) for _ in range(reps)],dtype=float)
    def sums(self,df,column):
        g=df.loc[df[column].notna()].groupby('session_date')[column].agg(['sum','count'])
        s=np.zeros(len(self.dates));n=s.copy()
        for d,row in g.iterrows():s[self.index[d]]=row['sum'];n[self.index[d]]=row['count']
        return s,n
    def distribution(self,df,column,block=False):
        s,n=self.sums(df,column);w=self.blocks if block else self.weights
        den=w@n;num=w@s
        return np.divide(num,den,out=np.full(len(den),np.nan),where=den>0)
    @staticmethod
    def ci(v):
        good=v[np.isfinite(v)];u=int(len(v)-len(good))
        return (*np.quantile(good,[.025,.975]),u) if len(good) else (np.nan,np.nan,u)
    def mean(self,df,column,block=False):return self.ci(self.distribution(df,column,block))
    def difference(self,a,acol,b,bcol,block=False):return self.ci(self.distribution(a,acol,block)-self.distribution(b,bcol,block))
