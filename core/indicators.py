"""Indicadores FluxoVoltaic — cálculo centralizado.
Todas las funciones son puras: reciben arrays/DataFrame, devuelven arrays/Series.
Iguales a los backtests validados (backtest_2025.py, opt_grid.py).
"""
import numpy as np
import pandas as pd


def calcular_true_range(df: pd.DataFrame) -> pd.Series:
    """True Range = max(high-low, |high-prev_close|, |low-prev_close|)."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.bfill()


def calcular_atr(df: pd.DataFrame, periodo: int = 14) -> pd.Series:
    """ATR basado en True Range, media móvil simple + bfill."""
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        df["high"] - df["low"],
        (df["high"] - prev_close).abs(),
        (df["low"] - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.rolling(periodo).mean().bfill()


def calcular_atr_medio(df: pd.DataFrame, periodo: int = 100) -> pd.Series:
    """Media móvil de ATR para filtro de régimen."""
    return calcular_atr(df, 14).rolling(periodo).mean().bfill()


def calcular_flujo(df: pd.DataFrame) -> pd.DataFrame:
    """Calcula I, R, C, Q, z (análogo fluido-eléctrico).

    Retorna DataFrame con columns: px, I, R, C, Q, z.
    Idéntico a flux_core.py y backtest_2025.py.
    """
    px = df["close"].astype(float)
    vol = (df["tick_volume"].astype(float)
           if "tick_volume" in df.columns
           else pd.Series(1.0, index=df.index))
    ret = px.diff().fillna(0.0)
    atr = calcular_atr(df, 14)
    vol_med = vol.rolling(50).mean().bfill().fillna(1.0) + 1e-9
    R = atr / vol_med
    I = ret / (R + 1e-9)
    C = (px.rolling(20).max() - px.rolling(20).min()).fillna(0.0)
    Q = (np.sign(ret) * vol).rolling(20).sum().fillna(0.0)
    z = ((I - I.rolling(100).mean()) / (I.rolling(100).std() + 1e-9)).fillna(0.0)
    return pd.DataFrame({"px": px, "I": I, "R": R, "C": C, "Q": Q, "z": z})


def calcular_bayes(Q: pd.Series, z: pd.Series, lam: float = 0.98) -> pd.Series:
    """Probabilidad alcista vía filtro Bayesiano recursivo con decaimiento.

    like = 0.5 + 0.3*tanh(Q/Qmed) + 0.2*tanh(z/2)
    p[i] = li * prev / (li * prev + (1 - li) * (1 - prev) + 1e-12)
    prev = lam * p[i-1] + (1 - lam) * 0.5
    """
    qm = abs(Q).rolling(50, min_periods=1).mean() + 1e-9
    like = (0.5 + 0.3 * np.tanh(Q / qm) + 0.2 * np.tanh(z / 2.0)).clip(0.05, 0.95)
    p = np.empty(len(like)); p[0] = 0.5
    lv = like.values
    for i in range(1, len(like)):
        prev = lam * p[i - 1] + (1 - lam) * 0.5
        li = float(lv[i])
        p[i] = li * prev / (li * prev + (1 - li) * (1 - prev) + 1e-12)
    return pd.Series(p, index=Q.index, name="p_up")


def calcular_monte_carlo(
    px: pd.Series,
    atr: float,
    paths: int = 1000,
    horizon: int = 20,
) -> float:
    """Probabilidad de que TP toque antes que SL vía caminos GBM.

    Usa últimos 100 retornos para mu/sigma.
    TP = precio + atr, SL = precio - 0.7*atr (criterio suave de ejecutabilidad).
    """
    win = px.iloc[-100:].values
    lr = np.diff(np.log(win + 1e-12))
    mu = float(np.mean(lr))
    sigma = float(np.std(lr) + 1e-9)
    av = float(atr)
    p0 = float(px.iloc[-1])
    ps = p0 * np.exp(np.cumsum(np.random.normal(mu, sigma, (paths, horizon)), axis=1))
    hit_tp = ps.max(axis=1) >= p0 + av
    hit_sl = ps.min(axis=1) <= p0 - 0.7 * av
    p_ok = float(((hit_tp) & (~hit_sl)).mean() + 0.5 * (hit_tp & hit_sl).mean())
    return p_ok


def calcular_regimen(
    df: pd.DataFrame,
    atr_ratio: float = 1.2,
) -> pd.DataFrame:
    """Detecta régimen de volatilidad y momentum.

    Añade columnas:
    - exp: 1 si ATR14 > ATR100 (expansión), 0 si no
    - up_prev: True si cierre día previo > apertura del día anterior
    """
    atr14 = calcular_atr(df, 14)
    atr100 = calcular_atr_medio(df, 100)
    exp = (atr14 > atr100).astype(int).values

    result = pd.DataFrame({"exp": exp}, index=df.index)

    if "time" in df.columns and "open" in df.columns and "close" in df.columns:
        fecha = df["time"].dt.date
        g = df.groupby(fecha).agg(op=("open", "first"), cl=("close", "last"))
        g["up"] = g["cl"] > g["op"]
        g["up_prev"] = g["up"].shift(1).fillna(False)
        up_map = g["up_prev"].to_dict()
        up_prev_arr = np.array([up_map.get(d, False) for d in fecha])
        result["up_prev"] = up_prev_arr

    else:
        result["up_prev"] = False

    return result
