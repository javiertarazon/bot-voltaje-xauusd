"""Optimización de filtros adaptativos sin contaminar el período de prueba."""
from pathlib import Path
import itertools
import pandas as pd
import numpy as np
BASE=Path(__file__).resolve().parent.parent
def stats(x):
    if len(x)<30:return None
    r=x.pnl.to_numpy(); gp=r[r>0].sum(); gl=abs(r[r<=0].sum()); eq=r.cumsum(); dd=(np.maximum.accumulate(eq)-eq).max()
    return {'n':len(r),'pf':gp/(gl+1e-12),'exp':r.mean(),'total':r.sum(),'dd':dd,'wr':(r>0).mean()}
def main():
    t=pd.read_csv(BASE/'data'/'trades_backtest.csv',parse_dates=['t_in','t_out']); t['year']=t.t_out.dt.year; t['hour']=t.t_in.dt.hour
    train=t[t.year==2023]; valid=t[t.year==2024]; test=t[t.year==2025]
    candidates=[]
    for ini,fin,zmin,pmin in itertools.product([7,9,10,11,12,13],[16,17,18],[1.0,1.2,1.5],[.55,.60]):
        if ini>=fin: continue
        filt=lambda x:x[(x.hour>=ini)&(x.hour<fin)&(x.z.abs()>=zmin)&((x.p_up>=pmin)|(x.p_up<=1-pmin))]
        a,b=stats(filt(train)),stats(filt(valid))
        if a and b: candidates.append((a['total']-a['dd']*.5+b['total']-b['dd']*.5,ini,fin,zmin,pmin,a,b))
    candidates.sort(reverse=True,key=lambda x:x[0]); lines=['FLUXOV2_M15_ADAPTIVE WALK-FORWARD','Train=2023, validación=2024, prueba final=2025']
    for _,ini,fin,zmin,pmin,a,b in candidates[:10]:
        x=test[(test.hour>=ini)&(test.hour<fin)&(test.z.abs()>=zmin)&((test.p_up>=pmin)|(test.p_up<=1-pmin))]; c=stats(x)
        lines.append(f'{ini:02d}-{fin:02d} z>={zmin} p>={pmin} | train PF={a["pf"]:.2f} n={a["n"]} valid PF={b["pf"]:.2f} n={b["n"]} test PF={(c or {}).get("pf",0):.2f} n={(c or {}).get("n",0)}')
    (BASE/'reportes'/'adaptive_walkforward.txt').write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
if __name__=='__main__':main()
