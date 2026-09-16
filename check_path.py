"""Check rapido sin MT5: verifica path terminal + .env. Uso: py check_path.py"""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
p = os.getenv("MT5_PATH", r"D:\mt5\terminal64.exe")
print(f"MT5_PATH={p}")
print(f"existe={os.path.exists(p)}")
# listar D:\mt5
try:
    print("contenido D:\\mt5:")
    for f in Path(r"D:\mt5").iterdir():
        print(f"  {f.name}")
except Exception as e:
    print(f"ERR listar: {e}")
print("CHECK OK")
