"""Preflight MT5 de solo lectura para FluxoV2 adaptive."""
import os,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
def main():
    try:
        import MetaTrader5 as mt5
    except ImportError: print('FAIL: falta MetaTrader5'); return 2
    path=os.getenv('MT5_PATH',r'D:\mt5\terminal64.exe')
    if not mt5.initialize(path=path,timeout=10000): print('FAIL initialize',mt5.last_error()); return 3
    try:
        a=mt5.account_info(); s=mt5.symbol_info(os.getenv('MT5_SYMBOL','XAUUSD')); t=mt5.symbol_info_tick(os.getenv('MT5_SYMBOL','XAUUSD'))
        if a is None or s is None or t is None: print('FAIL datos MT5',mt5.last_error()); return 4
        print({'login':a.login,'server':a.server,'balance':a.balance,'equity':a.equity,'trade_mode':a.trade_mode,'symbol':s.name,'digits':s.digits,'point':s.point,'tick_size':s.trade_tick_size,'tick_value':s.trade_tick_value,'volume_min':s.volume_min,'volume_step':s.volume_step,'spread_points':s.spread,'bid':t.bid,'ask':t.ask})
        print('PREFLIGHT=PASS_READ_ONLY'); return 0
    finally: mt5.shutdown()
if __name__=='__main__':sys.exit(main())
