"""Generación de señales centralizada."""
import numpy as np
import pandas as pd


def generar_senal(
    df: pd.DataFrame,
    i: int,
    config: "Config",
) -> dict:
    """Genera señal de trading para la barra i.

    Retorna dict con:
    - lado: 1 (LONG), -1 (SHORT), 0 (FLAT)
    - z, p_up, p_mc
    - razon: por qué no se opera (si lado==0)
    - size_factor: 1.0 (tamaño completo) o 0.5 (reducido)
    - tp, sl: precios de TP/SL (0 si FLAT)
    """
    from core.indicators import calcular_monte_carlo

    z_val = float(df["z"].iloc[i]) if "z" in df.columns else 0.0
    p_up = float(df["p_up"].iloc[i]) if "p_up" in df.columns else 0.5
    atr_val = float(df["atr"].iloc[i]) if "atr" in df.columns else 1.0
    px_val = float(df["close"].iloc[i]) if "close" in df.columns else 0.0

    uz = config.get("estrategia_params.uz", config.get("estrategia.uz", 1.0))
    pm = config.get("estrategia_params.pm", config.get("estrategia.pm", 0.55))

    resultado = {
        "lado": 0,
        "z": z_val,
        "p_up": p_up,
        "p_mc": 0.0,
        "razón": "",
        "size_factor": 1.0,
        "tp": 0.0,
        "sl": 0.0,
        "entry": px_val,
    }

    if z_val > uz and p_up > pm:
        resultado["lado"] = 1  # LONG
    elif z_val < -uz and p_up < (1 - pm):
        resultado["lado"] = -1  # SHORT
    else:
        resultado["razón"] = f"sin_senal z={z_val:.2f} p={p_up:.3f}"
        return resultado

    # Monte Carlo de ejecutabilidad
    hora = config.get("sesion_params.ini_hora_utc", 7)
    if "time" in df.columns and i > 0:
        ventana = df.iloc[max(0, i - 100):i + 1]
        if len(ventana) >= 20:
            resultado["p_mc"] = calcular_monte_carlo(
                ventana["close"],
                df["atr"].iloc[i],
                paths=config.get("backtest_params.max_paths_mc", 1000),
                horizon=config.get("backtest_params.horizon_mc", 20),
            )

    if resultado["p_mc"] < config.get("backtest_params.umbral_mc", 0.30):
        resultado["lado"] = 0
        resultado["razón"] = f"mc_bajo={resultado['p_mc']:.2f}"
        return resultado

    # Régimen para ajuste de tamaño
    if "exp" in df.columns:
        es_expansion = bool(df["exp"].iloc[i])
        resultado["size_factor"] = 1.0 if es_expansion else 0.5

    tp_k = config.get("estrategia_params.tp_k", config.get("estrategia.tp_k", 2.0))
    sl_k = config.get("estrategia_params.sl_k", config.get("estrategia.sl_k", 0.8))

    resultado["tp"] = px_val + resultado["lado"] * tp_k * atr_val
    resultado["sl"] = px_val - resultado["lado"] * sl_k * atr_val

    return resultado
