from pathlib import Path
import pandas as pd
from config.validator import load_config
from backtest.engine import BacktestEngine
BASE=Path(__file__).resolve().parent
def run(k,y):
 c=load_config(str(BASE/'config.json')); c._data['estrategia_params'].update({'uz':2.0,'pm':.60}); c._data['sesion_params'].update({'ini_hora_utc':13,'fin_hora_utc':17}); c._data['regimen']['max_atr_ratio']=2.0; c._data['riesgo_params']['max_losses_month']=k
 return BacktestEngine(c).ejecutar(simbolo='XAUUSD',periodo_inicio=f'{y}-01-01',periodo_fin=f'{y+1}-01-01').metricas
def main():
 rows=[]
 for k in (0,1,2,3):
  for y in (2023,2024,2025):
   m=run(k,y); rows.append({'loss_limit':k,'year':y,'n':m['n'],'pf':m['pf'],'exp':m['exp'],'total':m['total'],'dd':m['dd']})
 out=pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv(BASE/'reportes'/'streak_walkforward.csv',index=False)
 print('Selección: máxima suma(total-.5*DD) en 2023-2024; 2025 es ciego.')
for_main=main
if __name__=='__main__': main()
