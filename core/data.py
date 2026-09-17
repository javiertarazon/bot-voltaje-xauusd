"""Carga y preparación de datos."""
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd


def cargar_velas(ruta: str) -> pd.DataFrame:
    """Lee CSV de velas con parse automático de timezone."""
    df = pd.read_csv(ruta)
    if "time" in df.columns:
        col = df["time"]
        if col.astype(str).str.replace(".", "", 1).str.replace("-", "", 1).str.replace(":", "").str.replace("T", "").str.isdigit().all():
            df["time"] = pd.to_datetime(df["time"].astype(float), unit="s", utc=True)
        else:
            df["time"] = pd.to_datetime(df["time"], utc=True)
    return df


def filtrar_periodo(
    df: pd.DataFrame,
    inicio: Optional[str] = None,
    fin: Optional[str] = None,
) -> pd.DataFrame:
    """Filtra DataFrame por rango de fechas."""
    if "time" not in df.columns:
        return df
    mask = pd.Series(True, index=df.index)
    if inicio:
        mask &= df["time"] >= pd.Timestamp(inicio, tz="UTC")
    if fin:
        mask &= df["time"] < pd.Timestamp(fin, tz="UTC")
    return df[mask].reset_index(drop=True)


def preparar_backtest(
    df: pd.DataFrame,
    config: "Config",
    periodo_inicio: Optional[str] = None,
    periodo_fin: Optional[str] = None,
) -> pd.DataFrame:
    """Pipeline completo: filtra período, calcula indicadores.

    Devuelve DataFrame con columns: close, high, low, open, tick_volume, time,
    z, p_up, atr, exp, up_prev, prev_daily_chg
    """
    from core.indicators import (
        calcular_atr, calcular_atr_medio, calcular_bayes,
        calcular_flujo, calcular_regimen,
    )

    d = filtrar_periodo(df, periodo_inicio, periodo_fin)
    if len(d) < 500:
        raise ValueError(f"Sólo {len(d)} velas, se necesitan >= 500")
    for c in ["open", "high", "low", "close", "tick_volume"]:
        if c in d.columns:
            d[c] = d[c].astype(float)

    flujo_df = calcular_flujo(d)
    d["z"] = flujo_df["z"]
    d["p_up"] = calcular_bayes(flujo_df["Q"], flujo_df["z"])
    d["atr"] = calcular_atr(d, 14)

    reg = calcular_regimen(d)
    d["exp"] = reg["exp"]
    d["up_prev"] = reg["up_prev"]

    return d


def cargar_npz(ruta: str) -> dict:
    """Carga npz existente (para retrocompatibilidad)."""
    return np.load(ruta, allow_pickle=True)
