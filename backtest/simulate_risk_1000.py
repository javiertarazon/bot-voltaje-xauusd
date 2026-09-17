"""Simula gestión monetaria sobre operaciones adaptativas con capital USD 1000."""
from pathlib import Path
import pandas as pd,numpy as np
BASE=Path(__file__).resolve().parent.parent
def main():
 t=pd.read_csv(BASE/'data'/'trades_fluxov2_adaptive.csv',parse_dates=['t_out']).sort_values('t_out'); bal=1000.; peak=bal; rows=[]; streak=0; month=None
 for _,x in t.iterrows():
  m=x.t_out.to_period('M')
  if m!=month: month=m; streak=0
  if streak>=2: continue
  dd=max(0,(peak-bal)/peak*100); risk=.5 if dd<5 else .25
  if streak>=1:risk*=.5
  dist=abs(float(x.sl)-float(x.entry)); lot=max(0.01,(bal*risk/100)/(dist*100)) if dist>0 else 0.0
  if lot<=0: continue
  pnl=float(x.pnl)*100*lot; bal+=pnl; peak=max(peak,bal); streak=streak+1 if pnl<=0 else 0
  rows.append({'time':x.t_out,'pnl':pnl,'balance':bal,'risk_pct':risk,'lot':lot,'dd_pct':(peak-bal)/peak*100})
 q=pd.DataFrame(rows); print(q.groupby(q.time.dt.year).pnl.agg(['count','mean','sum']).to_string()); print('final',bal,'max_dd_pct',q.dd_pct.max(),'trades',len(q)); q.to_csv(BASE/'reportes'/'risk_sim_1000.csv',index=False)
if __name__=='__main__':main()
