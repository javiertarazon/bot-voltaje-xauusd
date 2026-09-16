"""Diag MT5 con TIMEOUT real via subprocess (no cuelga la sesion).
Uso: py diag_timeout.py
Lanza diag_mt5.py en subproceso con timeout 25s y reporta.
"""
import subprocess, sys
from pathlib import Path
BASE = Path(__file__).parent
obj = BASE / "diag_mt5.py"
print("lanzando diag_mt5.py con timeout 25s ...")
try:
    r = subprocess.run([sys.executable, str(obj)], capture_output=True, text=True, timeout=25)
    print(f"returncode={r.returncode}")
    print("--- STDOUT ---")
    print(r.stdout[-3000:])
    print("--- STDERR ---")
    print((r.stderr or "")[-1500:])
except subprocess.TimeoutExpired as e:
    print("TIMEOUT 25s: mt5.initialize() se quedo colgado.")
    print("Causa probable: paquete MetaTrader5 no encuentra terminal MT5 abierto/logueado,")
    print("o el terminal Deriv es de otro path y hay que pasarle path explicito.")
    out = (e.stdout or b"").decode(errors="ignore") if isinstance(e.stdout, bytes) else (e.stdout or "")
    print(out[-1500:])
    sys.exit(3)
