from pathlib import Path
import pandas as pd
from config.validator import load_config
from backtest.engine import BacktestEngine
BASE=Path(__file__).resolve().parent
def main():
    rows=[]
    for direction in (True,False):
        cfg=load_config(str(BASE/'config.json')); cfg._data['estrategia_params'].update({'uz':1.5,'pm':.60,'solo_long':direction}); cfg._data['sesion_params'].update({'ini_hora_utc':13,'fin_hora_utc':17}); cfg._data['regimen']['max_atr_ratio']=2.0
        e=BacktestEngine(cfg)
        for y in (2023,2024,2025,2026):
            m=e.ejecutar(simbolo='XAUUSD',periodo_inicio=f'{y}-01-01',periodo_fin=f'{y+1}-01-01').metricas
            rows.append({'direction':'LONG' if direction else 'BOTH','year':y,'n':m['n'],'pf':m['pf'],'exp':m['exp'],'total':m['total'],'dd':m['dd'],'wr':m['winrate']})
    out=pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv(BASE/'reportes'/'direction_test.csv',index=False)
if __name__=='__main__':main()
