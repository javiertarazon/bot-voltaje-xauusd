"""Sensibilidad estricta de filtros sobre señales M15.
Selección únicamente con 2023-2024; 2025-2026 sólo evaluación.
"""
from pathlib import Path
import itertools,pandas as pd,numpy as np
BASE=Path(__file__).resolve().parent.parent
def stat(x):
    if len(x)<30:return None
    r=x.pnl.to_numpy()
    gp=r[r>0].sum(); gl=abs(r[r<=0].sum()); eq=r.cumsum(); dd=(np.maximum.accumulate(eq)-eq).max()
    return {'n':len(r),'pf':gp/(gl+1e-12),'exp':r.mean(),'total':r.sum(),'dd':dd,'wr':(r>0).mean()}
def filt(x,ini,fin,z): return x[(x.hour>=ini)&(x.hour<fin)&(x.z>=z)&(x.expansion==1)]
def main():
    t=pd.read_csv(BASE/'data'/'trades_fluxov2_adaptive.csv',parse_dates=['t_in','t_out']); t['year']=t.t_out.dt.year;t['hour']=t.t_in.dt.hour
    tr=t[t.year.isin([2023,2024])]; rows=[]
    for ini,fin,z in itertools.product([10,11,12,13],[16,17,18],[1.5,1.75,2.0,2.25]):
        if ini>=fin:continue
        a=stat(filt(tr,ini,fin,z))
        if a: rows.append((a['total']-.5*a['dd'],ini,fin,z,a))
    rows.sort(reverse=True,key=lambda q:q[0]); best=rows[0]; ini,fin,z=best[1:4]
    lines=['SENSIBILIDAD ESTRICTA FLUXOV2_M15_ADAPTIVE','Selección: 2023-2024 | Prueba ciega: 2025-2026','']
    for score,a,b,c,s in rows[:10]:
        test=stat(filt(t[t.year.isin([2025,2026])],a,b,c)); lines.append(f'{a:02d}-{b:02d} z>={c:.2f} train n={s["n"]} PF={s["pf"]:.2f} exp={s["exp"]:.3f} | test n={(test or {}).get("n",0)} PF={(test or {}).get("pf",0):.2f} exp={(test or {}).get("exp",0):.3f}')
    lines.append(f'PARAMETROS_CONGELADOS={ini:02d}-{fin:02d},z>={z:.2f},expansion=1')
    (BASE/'reportes'/'sensitivity_strict.txt').write_text('\n'.join(lines),encoding='utf-8');print('\n'.join(lines))
if __name__=='__main__':main()
