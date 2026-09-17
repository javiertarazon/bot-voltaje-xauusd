"""Loop ligero de mejoras sobre resultados M15 ya calculados.
Evalúa filtros horarios sin tocar el conjunto de prueba final.
"""
from pathlib import Path
import itertools
import pandas as pd
import numpy as np
BASE=Path(__file__).resolve().parent.parent
def pf(s):
    return s[s>0].sum()/(abs(s[s<=0].sum())+1e-12)
def score(t):
    if len(t)<80:return None
    r=t.pnl.to_numpy(); eq=r.cumsum(); dd=(np.maximum.accumulate(eq)-eq).max()
    return {'n':len(t),'pf':pf(t.pnl),'exp':r.mean(),'total':r.sum(),'dd':dd,'wr':(r>0).mean(),'score':r.sum()-.5*dd}
def main():
    t=pd.read_csv(BASE/'data'/'trades_backtest.csv',parse_dates=['t_in','t_out']); t['hour']=t.t_in.dt.hour; t['year']=t.t_out.dt.year
    candidates=[]
    for a,b in itertools.product(range(7,14),range(15,19)):
        if a>=b:continue
        x=t[(t.hour>=a)&(t.hour<b)]; s=score(x)
        if s:candidates.append((s,a,b))
    candidates.sort(key=lambda z:z[0]['score'],reverse=True); best=candidates[0]
    lines=['FLUXOV2_M15_ADAPTIVE LOOP','Candidatos ordenados por total - 0.5*DD (diagnóstico; no selección final)']
    for s,a,b in candidates[:10]: lines.append(f'{a:02d}-{b:02d} n={s["n"]} PF={s["pf"]:.2f} exp={s["exp"]:.3f} total={s["total"]:.2f} DD={s["dd"]:.2f}')
    lines.append(f'PROPUESTA={best[1]:02d}-{best[2]:02d} UTC')
    lines.append('Advertencia: este ranking usa todos los trades y requiere validación temporal independiente.')
    (BASE/'reportes'/'adaptive_loop.txt').write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))
if __name__=='__main__':main()
