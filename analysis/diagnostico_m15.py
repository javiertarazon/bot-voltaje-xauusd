"""Diagnóstico de causas de fallo del backtest M15."""
from pathlib import Path
import pandas as pd
import numpy as np

BASE=Path(__file__).resolve().parent.parent

def pf(s):
    g=s[s>0].sum(); l=abs(s[s<=0].sum()); return float(g/(l+1e-12))

def main():
    p=BASE/'data'/'trades_backtest.csv'
    if not p.exists(): raise SystemExit('Ejecuta run_backtest.py primero')
    t=pd.read_csv(p,parse_dates=['t_in','t_out'])
    t['year']=t.t_out.dt.year; t['month']=t.t_out.dt.to_period('M').astype(str); t['hour']=t.t_in.dt.hour
    t['r_multiple']=t.pnl/(abs(t.sl-t.entry)+1e-12)
    sections=[]
    for name,g in [('year',t.groupby('year')),('month',t.groupby('month')),('hour',t.groupby('hour')),('motivo',t.groupby('motivo'))]:
        rows=[]
        for k,x in g:
            rows.append({'group':k,'n':len(x),'pf':pf(x.pnl),'exp':x.pnl.mean(),'total':x.pnl.sum(),'wr':(x.pnl>0).mean(),'dd':(x.pnl.cumsum().cummax()-x.pnl.cumsum()).max()})
        sections.append((name,pd.DataFrame(rows).sort_values('group')))
    out=BASE/'reportes'/'diagnostico_m15.txt'; lines=['DIAGNOSTICO M15','']
    for name,x in sections:
        lines += [f'[{name}]',x.to_string(index=False),'']
    lines += ['[conclusiones automaticas]']
    y=sections[0][1]
    if len(y):
        bad=y.sort_values('pf').iloc[0]; lines.append(f"Peor año: {bad['group']} PF={bad['pf']:.2f}, exp={bad['exp']:.3f}, DD={bad['dd']:.2f}")
    h=sections[2][1]
    if len(h):
        bad=h.sort_values('exp').iloc[0]; good=h.sort_values('exp',ascending=False).iloc[0]
        lines.append(f"Peor hora: {bad['group']} UTC exp={bad['exp']:.3f}; mejor hora: {good['group']} UTC exp={good['exp']:.3f}")
    lines.append('No se recomienda red neuronal si no supera estos cortes fuera de muestra y con costes reales.')
    out.write_text('\n'.join(lines),encoding='utf-8'); print('\n'.join(lines))

if __name__=='__main__': main()
