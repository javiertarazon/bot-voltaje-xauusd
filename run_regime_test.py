from pathlib import Path
import pandas as pd
from config.validator import load_adaptive_config
from backtest.engine import BacktestEngine

BASE=Path(__file__).resolve().parent

def main():
    rows=[]
    for name, extra in [('base',{}),('up_prev',{'require_up_prev':True}),('both_010',{'require_up_prev':True,'min_trend_strength':.10}),('trend_025',{'min_trend_strength':.25}),('trend_050',{'min_trend_strength':.50}),('both',{'require_up_prev':True,'min_trend_strength':.25})]:
        cfg=load_adaptive_config(str(BASE/'config.json'),str(BASE/'config_adaptive.json'))
        cfg._data.setdefault('regimen',{}).update(extra)
        e=BacktestEngine(cfg)
        selected=[]
        for y in (2023,2024,2025,2026):
            result=e.ejecutar(simbolo='XAUUSD',periodo_inicio=f'{y}-01-01',periodo_fin=f'{y+1}-01-01')
            m=result.metricas
            if name=='both' and len(result.trades): selected.append(result.trades)
            rows.append({'variant':name,'year':y,'n':m['n'],'pf':m['pf'],'exp':m['exp'],'total':m['total'],'dd':m['dd'],'wr':m['winrate']})
    out=pd.DataFrame(rows); out.to_csv(BASE/'reportes'/'regime_test.csv',index=False)
    if selected: pd.concat(selected,ignore_index=True).to_csv(BASE/'data'/'trades_fluxov2_both.csv',index=False)
    print(out.to_string(index=False,float_format=lambda v:f'{v:.4f}'))

if __name__=='__main__': main()
