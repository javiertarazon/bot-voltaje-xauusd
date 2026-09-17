from pathlib import Path
import pandas as pd
from config.validator import load_config
from backtest.engine import BacktestEngine
BASE=Path(__file__).resolve().parent
def main():
    rows=[]
    for uz,pm,ini,fin in [(1.5,.60,13,17),(1.5,.65,13,17),(1.7,.60,12,17),(1.7,.65,13,17)]:
        cfg=load_config(str(BASE/'config.json'))
        cfg._data['estrategia_params'].update({'uz':uz,'pm':pm})
        cfg._data['sesion_params'].update({'ini_hora_utc':ini,'fin_hora_utc':fin})
        cfg._data['backtest_params']['costes_spread']=0.30
        cfg._data.setdefault('regimen',{})['max_atr_ratio']=2.0
        cfg._data.setdefault('riesgo_params',{})['max_losses_month']=2
        e=BacktestEngine(cfg); vals=[]
        for y in (2023,2024,2025,2026):
            m=e.ejecutar(simbolo='XAUUSD',periodo_inicio=f'{y}-01-01',periodo_fin=f'{y+1}-01-01').metricas; vals.append(m)
        row={'uz':uz,'pm':pm,'session':f'{ini}-{fin}'}
        row.update({f'pf{y}':v['pf'] for y,v in zip((2023,2024,2025,2026),vals)})
        row.update({f'n{y}':v['n'] for y,v in zip((2023,2024,2025,2026),vals)})
        row.update({f'exp{y}':v['exp'] for y,v in zip((2023,2024,2025,2026),vals)})
        rows.append(row)
    out=pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv(BASE/'reportes'/'adaptive_candidates.csv',index=False)
if __name__=='__main__':main()
