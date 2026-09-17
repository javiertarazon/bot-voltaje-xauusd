from pathlib import Path
import pandas as pd,numpy as np
import sys
BASE=Path(__file__).resolve().parent.parent
def sim(t,base,cost=0.30):
 bal=peak=1000.; streak=0; month=None; rows=[]
 for _,x in t.sort_values('t_out').iterrows():
  m=x.t_out.tz_localize(None).to_period('M')
  if m!=month:month=m;streak=0
  if streak>=2:continue
  dd=(peak-bal)/peak*100; risk=base if dd<5 else base/2
  if streak:risk/=2
  dist=abs(x.sl-x.entry)
  raw=(bal*risk/100)/(dist*100) if dist>0 else 0
  if raw<.01:continue
  lot=min(raw,100)
  # x.pnl ya incluye el coste usado al generar el CSV (0.30 USD de precio).
  # Reexpresamos el escenario para no mezclar backtests con costes distintos.
  pnl=(x.pnl + 0.30 - cost)*100*lot
  bal+=pnl;peak=max(peak,bal);streak=streak+1 if pnl<=0 else 0
  rows.append((pnl,bal,peak))
 r=np.array([x[0] for x in rows]); eq=r.cumsum(); dd=(np.maximum.accumulate(eq)-eq).max()
 return len(r),bal,dd,(r[r>0].sum()/(abs(r[r<=0].sum())+1e-12))
def main():
 name=sys.argv[1] if len(sys.argv)>1 else 'trades_fluxov2_adaptive.csv'
 t=pd.read_csv(BASE/'data'/name,parse_dates=['t_out'])
 rows=[]
 for c in (.16,.30,.50):
  for b in (.25,.5,1.0):
   n,final,dd,pf=sim(t,b,c)
   rows.append({'cost':c,'base_risk_pct':b,'trades':n,'final':final,'return_pct':(final/1000-1)*100,'dd_usd':dd,'dd_pct':dd/1000*100,'pf':pf})
 out=pd.DataFrame(rows)
 print(out.to_string(index=False,float_format=lambda v:f'{v:.4f}'))
 out.to_csv(BASE/'reportes'/'risk_sensitivity_1000.csv',index=False)
if __name__=='__main__':main()
