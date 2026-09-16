"""Diag MT5: prueba initialize con timeout, sin colgarse.
Uso: py diag_mt5.py
"""
import sys
print("diag inicio")
try:
    import MetaTrader5 as mt5
    print(f"MT5 pkg OK version pkg")
except Exception as e:
    print(f"ERROR import MT5: {e}")
    sys.exit(2)

# 1. initialize sin path (usa ultimo terminal abierto)
print("probando initialize(timeout=10000)...")
try:
    ok = mt5.initialize(timeout=10000)
    print(f"initialize={ok} last_error={mt5.last_error()}")
    if ok:
        print(f"version={mt5.version()} terminal={mt5.terminal_info()}")
        mt5.shutdown()
        print("diag OK con terminal por defecto")
        sys.exit(0)
except Exception as e:
    print(f"EXC initialize: {e}")

# 2. buscar terminales tipicos
import os
candidatos = [
    os.path.expandvars(r"%ProgramFiles%\MetaTrader 5\terminal64.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\MetaTrader 5\terminal64.exe"),
    os.path.expandvars(r"%APPDATA%\MetaQuotes\Terminal"),
]
print("candidatos path:")
for c in candidatos:
    print(f"  {c} existe={os.path.exists(c)}")

# listar terminales Deriv tipicos
import glob
for base in [os.path.expandvars(r"%ProgramFiles%"), os.path.expandvars(r"%ProgramFiles(x86)%")]:
    try:
        for d in glob.glob(os.path.join(base, "*eriv*")):
            print(f"  dir deriv-like: {d}")
        for d in glob.glob(os.path.join(base, "*eta*")):
            print(f"  dir meta-like: {d}")
    except Exception as e:
        print(e)
print("diag fin sin conexion")
sys.exit(1)
