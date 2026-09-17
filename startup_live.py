"""Startup completo para modo VIVO FluxoV2 en NT5.

Uso: python startup_live.py
Inicia:
1. Conexion MT5 verificacion
2. Publicador de senales
3. Instrucciones para EA
"""
import sys
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).parent


def main():
    print("=" * 55, flush=True)
    print("  STARTUP FLUXOV2 VIVO — NT5", flush=True)
    print("=" * 55, flush=True)

    # Paso 1: Verificar configuracion
    print("\n[1/4] Verificando configuracion...", flush=True)
    from config.validator import load_config
    try:
        cfg = load_config(str(BASE / "config.json"))
        print(f"  Config OK: symbol={cfg.get('broker.symbol')}", flush=True)
        print(f"  Sesion: {cfg.get('sesion_params.ini_hora_utc')}-{cfg.get('sesion_params.fin_hora_utc')} UTC", flush=True)
        print(f"  Regimen: activo={cfg.get('regimen.activo')}", flush=True)
    except Exception as e:
        print(f"  ERROR config: {e}", flush=True)
        sys.exit(1)

    # Paso 2: Verificar .env
    print("\n[2/4] Verificando .env...", flush=True)
    env_file = BASE / ".env"
    if not env_file.exists():
        print("  ERROR: .env no existe. Copiar .env.example a .env", flush=True)
        sys.exit(1)
    env_text = env_file.read_text()
    has_login = "MT5_LOGIN" in env_text and len(env_text) > 50
    has_server = "MT5_SERVER" in env_text
    if has_login and has_server:
        print("  .env OK (credenciales presentes)", flush=True)
    else:
        print("  WARNING: .env parece incompleto", flush=True)

    # Paso 3: Verificar datos
    print("\n[3/4] Verificando datos...", flush=True)
    data_m15 = BASE / "data" / "xauusd_M15.csv"
    if data_m15.exists():
        import pandas as pd
        df = pd.read_csv(data_m15)
        print(f"  M15 OK: {len(df)} velas", flush=True)
    else:
        print("  WARNING: falta data/xauusd_M15.csv", flush=True)

    # Paso 4: Instrucciones EA
    print("\n[4/4] Instrucciones EA MT5:", flush=True)
    print("  1. Abre MT5 Deriv y logueate", flush=True)
    print("  2. Abre grafico XAUUSD M15", flush=True)
    print("  3. Adjunta FluxoV2_EA.ex5 (InpMode=0 para sombra)", flush=True)
    print("  4. Verifica Common\\Files\\fluxov2_ea.log", flush=True)
    print("  5. Espera BEAT confirmado", flush=True)

    # Paso 5: Preguntar si iniciar publicador
    print("\n" + "=" * 55, flush=True)
    resp = input("Iniciar publicador de senales? (s/n): ").strip().lower()
    if resp in ["s", "si", "y", "yes"]:
        print("\nIniciando live/publish.py...", flush=True)
        print("Ctrl+C para detener", flush=True)
        print("=" * 55, flush=True)
        try:
            subprocess.run([sys.executable, str(BASE / "live" / "publish.py"), "--iter", "1", "--interval", "60"])
        except KeyboardInterrupt:
            print("\nPublicador detenido", flush=True)
    else:
        print("\nPublicador NO iniciado. Ejecuta manualmente:", flush=True)
        print(f"  python {BASE / 'live' / 'publish.py'} --iter 1 --interval 60", flush=True)

    print("\nStartup completo.", flush=True)


if __name__ == "__main__":
    main()
