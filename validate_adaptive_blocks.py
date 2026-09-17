"""Valida estabilidad por bloques trimestrales sin modificar parámetros."""
from pathlib import Path
import pandas as pd
import numpy as np

BASE = Path(__file__).resolve().parent

def main():
    t = pd.read_csv(BASE/'data'/'trades_fluxov2_adaptive.csv', parse_dates=['t_out'])
    t['block'] = t['t_out'].dt.to_period('Q').astype(str)
    rows=[]
    for block, x in t.groupby('block', sort=True):
        r=x.pnl.to_numpy(); gp=r[r>0].sum(); gl=abs(r[r<=0].sum())
        eq=r.cumsum(); dd=float((np.maximum.accumulate(eq)-eq).max())
        rows.append({'block':block,'n':len(r),'pf':gp/(gl+1e-12),'exp':r.mean(),'total':r.sum(),'dd':dd,'wr':(r>0).mean()})
    out=pd.DataFrame(rows)
    out.to_csv(BASE/'reportes'/'adaptive_blocks.csv',index=False)
    print(out.to_string(index=False, float_format=lambda v:f'{v:.4f}'))
    eligible=out[out.n>=8]
    print(f'BLOQUES={len(out)} | elegibles={len(eligible)} | PF_medio={eligible.pf.mean():.3f} | exp_positiva={(eligible.exp>0).mean():.1%}')

if __name__=='__main__': main()
