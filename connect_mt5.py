"""Fase 0: verifica conexion MT5 demo + simbolo XAUUSD.
Uso: python connect_mt5.py
Lee credenciales de .env (MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, MT5_SYMBOL, MT5_PATH).
Solo Windows con terminal MT5 instalado y abierto.
"""
import os
import sys

try:
    from dotenv import load_dotenv
except ImportError:
    print("ERROR: falta python-dotenv. Ejecuta: pip install -r requirements.txt")
    sys.exit(2)

load_dotenv()

LOGIN = os.getenv("MT5_LOGIN", "")
PASSWORD = os.getenv("MT5_PASSWORD", "")
SERVER = os.getenv("MT5_SERVER", "")
SYMBOL = os.getenv("MT5_SYMBOL", "XAUUSD")
MT5_PATH = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")

# Servidores Deriv conocidos para probar en orden si el configurado falla.
DERIV_FALLBACKS = ["Deriv-Demo", "DerivSVG-Server", "Deriv-Server", "Deriv-Demo02"]

try:
    import MetaTrader5 as mt5
except ImportError:
    print("ERROR: paquete MetaTrader5 no instalado o no Windows.")
    print("Ejecuta: pip install -r requirements.txt (solo Windows + MT5 instalado)")
    sys.exit(2)


def main():
    print("=== FASE 0 connect_mt5 ===", flush=True)
    print(f"Symbol objetivo: {SYMBOL}", flush=True)
    print(f"MT5_PATH: {MT5_PATH} existe={os.path.exists(MT5_PATH)}", flush=True)
    if not LOGIN or not PASSWORD or not SERVER:
        print("ERROR: .env incompleto. Copia .env.example a .env y rellena MT5_LOGIN/PASSWORD/SERVER.")
        sys.exit(2)
    print(f"Login: ***{str(LOGIN)[-3:]} Servidor configurado: {SERVER}", flush=True)

    print("initialize() ...", flush=True)
    if MT5_PATH and os.path.exists(MT5_PATH):
        ok = mt5.initialize(path=MT5_PATH, timeout=15000)
    else:
        ok = mt5.initialize(timeout=15000)
    if not ok:
        print(f"ERROR initialize: {mt5.last_error()}", flush=True)
        print("Causa probable: terminal MT5 cerrado o path incorrecto.", flush=True)
        sys.exit(1)
    print(f"initialize OK. Version: {mt5.version()}", flush=True)
    try:
        ti = mt5.terminal_info()
        print(f"Terminal: company={ti.company} path={ti.path}", flush=True)
    except Exception as e:
        print(f"terminal_info exc: {e}", flush=True)

    candidatos = [SERVER] + [s for s in DERIV_FALLBACKS if s != SERVER]
    conectado_con = None
    for srv in candidatos:
        print(f"Probando login en servidor: {srv} ...", flush=True)
        try:
            if mt5.login(int(LOGIN), password=PASSWORD, server=srv):
                conectado_con = srv
                print(f"login OK en servidor: {srv}", flush=True)
                break
            else:
                print(f"  fallo: {mt5.last_error()}", flush=True)
        except Exception as e:
            print(f"  excepcion: {e}", flush=True)
    if not conectado_con:
        print("ERROR: no se pudo hacer login en ningun servidor candidato.", flush=True)
        print("Corrige MT5_SERVER en .env con el nombre exacto del Navigator MT5.", flush=True)
        mt5.shutdown()
        sys.exit(1)

    acc = mt5.account_info()
    if acc is None:
        print(f"ERROR account_info: {mt5.last_error()}", flush=True)
        mt5.shutdown()
        sys.exit(1)
    print(f"Cuenta: login={acc.login} server={acc.server} balance={acc.balance} "
          f"equity={acc.equity} leverage=1:{acc.leverage} currency={acc.currency} trade_mode={acc.trade_mode}", flush=True)

    print(f"Buscando simbolo que contenga: {SYMBOL} ...", flush=True)
    todos = mt5.symbols_get(f"*{SYMBOL}*")
    if todos:
        print("Coincidencias:", flush=True)
        for s in todos[:10]:
            print(f"  - {s.name} digits={s.digits} trade_mode={s.trade_mode}", flush=True)
    info = mt5.symbol_info(SYMBOL)
    if info is None and todos:
        cand = todos[0].name
        print(f"Intentando symbol_select({cand}) ...", flush=True)
        mt5.symbol_select(cand, True)
        info = mt5.symbol_info(cand)
        if info is not None:
            print(f"Usando alternativo: {cand}", flush=True)
    if info is None:
        print(f"AVISO: symbol_info({SYMBOL}) es None. Ajusta MT5_SYMBOL en .env", flush=True)
        mt5.shutdown()
        sys.exit(1)

    mt5.symbol_select(info.name, True)
    tick = mt5.symbol_info_tick(info.name)
    print(f"Symbol: {info.name} digits={info.digits} spread={info.spread} "
          f"tick_value={info.trade_tick_value} tick_size={info.trade_tick_size} "
          f"vol_min={info.volume_min} vol_step={info.volume_step} vol_max={info.volume_max}", flush=True)
    if tick is not None:
        print(f"Tick: bid={tick.bid} ask={tick.ask} time={tick.time}", flush=True)
    print("FASE 0 OK: conexion y simbolo verificados.", flush=True)
    mt5.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
