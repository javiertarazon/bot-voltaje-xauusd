"""Comparación rolling de variantes predefinidas; la elección usa solo entrenamiento."""
from pathlib import Path
import pandas as pd
import numpy as np
BASE=Path(__file__).resolve().parent.parent

def stats(x):
    if len(x)==0:return {'n':0,'pf':0,'exp':0,'total':0,'dd':0}
    r=x.pnl.to_numpy(); eq=r.cumsum(); return {'n':len(r),'pf':r[r>0].sum()/(abs(r[r<=0].sum())+1e-12),'exp':r.mean(),'total':r.sum(),'dd':(np.maximum.accumulate(eq)-eq).max()}
def main():
    sets={}
    for v in ('adaptive','both'):
        sets[v]=pd.read_csv(BASE/'data'/f'trades_fluxov2_{v}.csv',parse_dates=['t_out'])
        sets[v]['year']=sets[v].t_out.dt.year
    rows=[]
    for test_year in (2025,2026):
        train={v:x[x.year<test_year] for v,x in sets.items()}
        scores={v:stats(x)['total']-.5*stats(x)['dd'] for v,x in train.items()}
        chosen=max(scores,key=scores.get)
        s=stats(sets[chosen][sets[chosen].year==test_year])
        rows.append({'train_until':test_year-1,'chosen':chosen,'train_score':scores[chosen],'test_year':test_year,**s})
    out=pd.DataFrame(rows); out.to_csv(BASE/'reportes'/'rolling_oos.csv',index=False); print(out.to_string(index=False))
if __name__=='__main__':main()
