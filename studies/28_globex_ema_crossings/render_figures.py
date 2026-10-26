"""Presentation only: standard matplotlib plots from saved CSV; no calculations rerun."""
import csv
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import sys
os.environ.setdefault('MPLCONFIGDIR','/private/tmp/abacus-study28-matplotlib')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np


def main(stage):
    config=json.loads((stage/'config.json').read_text())
    if config['primary_timeframe'] != '3m' or config['timeframes'] != ['3m']:
        raise ValueError('Current figures require the corrected 3-minute-only study')
    start,end=config['common_calendar']
    def read(name):
        with (stage/f'tables/{name}.csv').open() as f:return list(csv.DictReader(f))
    s,m=read('summary'),read('monthly')
    def select(rows,**criteria):return [r for r in rows if all(r[k]==v for k,v in criteria.items())]
    colors={'ES':'#226ba6','NQ':'#c47520','GC':'#47907c'}
    fixed={'timeframe':'3m','window':'globex','cohort':'common_calendar'}
    fig,axes=plt.subplots(1,2,figsize=(12,5.2))
    for ax,seg,cats,title in [(axes[0],'atr_regime',['low','normal','high'],'Prior ATR14% regime'),(axes[1],'realized_regime',['quiet','normal','active'],'Realized range / prior ATR')]:
        largest=0
        for j,p in enumerate(['ES','NQ','GC']):
            sub={r['regime']:r for r in select(s,product=p,segmentation=seg,**fixed)}
            means=np.array([float(sub[c]['mean_crosses']) for c in cats]);largest=max(largest,max(means))
            low=np.array([float(sub[c]['mean_ci95_low']) for c in cats]);high=np.array([float(sub[c]['mean_ci95_high']) for c in cats])
            x=np.arange(3)+(j-1)*.24
            ax.bar(x,means,.23,label=p,color=colors[p])
            ax.errorbar(x,means,yerr=[means-low,high-means],fmt='none',color='#203040',capsize=3,linewidth=1)
            for xi,v,c in zip(x,means,cats):ax.text(xi,v+.6,f"n={sub[c]['sessions']}",ha='center',fontsize=7,rotation=90)
        ax.set_ylim(0,largest*1.3);ax.set_xticks(range(3),cats);ax.set_title(title);ax.set_ylabel('Mean EMA6/VWAP crosses per session');ax.legend(loc='upper right');ax.grid(axis='y',alpha=.2);ax.set_axisbelow(True)
    fig.suptitle(f'3-minute close EMA6 | {start} to {end}\n95% observed-session block bootstrap intervals; selected eligible days',fontsize=11)
    fig.tight_layout();fig.savefig(stage/'figures/volatility.png',dpi=160);plt.close(fig)
    fig,axes=plt.subplots(3,1,figsize=(12,8),sharex=True)
    for ax,p in zip(axes,['ES','NQ','GC']):
        sub=select(m,product=p,segmentation='all',**fixed)
        dates=[datetime.strptime(r['month'],'%Y-%m') for r in sub]
        means=[float(r['mean_crosses']) for r in sub]
        ax.plot(dates,means,color=colors[p],marker='.',label=p)
        sparse=[r for r in sub if int(r['sessions'])<10]
        ax.scatter([datetime.strptime(r['month'],'%Y-%m') for r in sparse],[float(r['mean_crosses']) for r in sparse],facecolors='none',edgecolors='red',s=45,label='fewer than 10 days')
        ax.set_ylabel('Mean crosses');ax.legend(loc='upper right');ax.grid(alpha=.2)
    fig.suptitle('Calendar-month crossing frequency | 3-minute close EMA6, full Globex\nSample sizes vary; red rings flag sparse months. Missing months have no estimate.',fontsize=11)
    fig.tight_layout();fig.savefig(stage/'figures/monthly.png',dpi=160);plt.close(fig)
    (stage/'figure-environment.json').write_text(json.dumps({'python':sys.version,'executable':sys.executable,'platform':platform.platform(),'matplotlib':matplotlib.__version__,'numpy':np.__version__,'input':'saved tables only','argv':sys.argv},indent=2)+'\n')


if __name__=='__main__': main(Path(sys.argv[1]).resolve())
