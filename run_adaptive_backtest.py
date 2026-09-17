"""Backtest real de FluxoV2_M15_Adaptive por períodos no solapados."""
from pathlib import Path
import pandas as pd
import sys
from config.validator import load_adaptive_config
from backtest.engine import BacktestEngine

BASE=Path(__file__).resolve().parent
def main():
    variant = sys.argv[1] if len(sys.argv)>1 else 'adaptive'
    override = BASE/'config_adaptive.json' if variant=='adaptive' else BASE/f'config_{variant}.json'
    cfg=load_adaptive_config(str(BASE/'config.json'),str(override))
    if variant == 'candidate_z225':
        cfg._data['estrategia_params'].update({'uz':2.25})
        cfg._data['sesion_params'].update({'ini_hora_utc':10,'fin_hora_utc':17})
    engine=BacktestEngine(cfg); rows=[]; all_trades=[]
    for y in range(2023,2027):
        r=engine.ejecutar(simbolo='XAUUSD',periodo_inicio=f'{y}-01-01',periodo_fin=f'{y+1}-01-01')
        m=r.metricas; rows.append({'year':y,'n':m['n'],'pf':m['pf'],'exp':m['exp'],'total':m['total'],'dd':m['dd'],'wr':m['winrate']})
        if len(r.trades):
            q=r.trades.copy(); q['year']=y; all_trades.append(q)
    out=pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv(BASE/'reportes'/f'fluxov2_{variant}_years.csv',index=False)
    if all_trades: pd.concat(all_trades,ignore_index=True).to_csv(BASE/'data'/f'trades_fluxov2_{variant}.csv',index=False)
    print('\nCriterio robustez: PF>=1.05, expectativa>0, n>=30 en cada año con datos.')
if __name__=='__main__': main()
