"""Gestión de riesgo centralizada."""
import numpy as np

def calcular_riesgo_adaptativo(base_pct: float, reducido_pct: float,
                               dd_pct: float, atr_actual: float,
                               atr_mediano: float, racha_perdidas: int = 0,
                               max_dd_pct: float = 10.0) -> float:
    """Riesgo porcentual adaptado a drawdown, volatilidad y racha."""
    riesgo = float(base_pct)
    if dd_pct >= max_dd_pct:
        riesgo = min(riesgo, float(reducido_pct))
    if atr_mediano > 0 and atr_actual > atr_mediano * 1.5:
        riesgo *= 0.5
    if racha_perdidas >= 3:
        riesgo *= 0.5
    return max(0.0, min(float(base_pct), riesgo))


def calcular_lote(
    balance: float,
    riesgo_pct: float,
    sl_puntos: float,
    tick_value: float,
    tick_size: float,
    volume_step: float,
    volume_min: float = 0.01,
    volume_max: float = 100.0,
    usd_por_pt_lote: float = 100.0,
) -> float:
    """Calcula lote dinámico basado en riesgo porcentual y SL.

    Para XAUUSD: 1.00 precio = ~100 USD/lote (verificado en INFORME_BOT.md).
    Para otros pares, usar tick_value/tick_size directamente.
    """
    riesgo_usd = balance * (riesgo_pct / 100.0)
    if sl_puntos <= 0:
        return volume_min
    # sl_puntos está en precio (ej: 14.7 puntos). Convertir a USD:
    # Para XAUUSD: sl_usd = sl_puntos * 100 / lote  → lote = (sl_puntos * usd_por_pt_lote * lote_factor)
    # Simplificado: lote = riesgo_usd / (sl_puntos * usd_por_pt_lote)
    # Pero mejor usar tick_value/tick_size para generalidad:
    sl_usd_por_lote = (sl_puntos / tick_size) * tick_value if tick_size > 0 else sl_puntos * usd_por_pt_lote
    if sl_usd_por_lote <= 0:
        return volume_min
    lote_raw = riesgo_usd / sl_usd_por_lote
    step = volume_step if volume_step > 0 else 0.01
    # No forzar el volumen mínimo: podría superar el riesgo máximo autorizado.
    if lote_raw < volume_min:
        return 0.0
    lote = round(max(volume_min, min(volume_max, np.floor(lote_raw / step) * step)), 6)
    return lote


def ajustar_riesgo_por_dd(
    equity_actual: float,
    peak: float,
    config: "Config",
) -> float:
    """Devuelve porcentaje de riesgo según drawdown.

    Normal: risk_pct_por_trade
    Si DD > reduccion_dd_pct del peak: risk_reducido_pct
    """
    dd_pct = (peak - equity_actual) / peak * 100 if peak > 0 else 0.0
    reduccion = config.get("riesgo_params.reduccion_dd_pct", config.get("riesgo.reduccion_dd_pct", 10.0))
    if dd_pct > reduccion:
        return config.get("riesgo_params.reducido_pct", config.get("riesgo.reducido_pct", 0.25))
    return config.get("riesgo_params.base_pct", config.get("riesgo.base_pct", 0.5))


def verificar_cortacircuitos(estado: dict, config: "Config") -> tuple:
    """Verifica todas las condiciones de corte.

    Retorna (puede_operar: bool, razon: str).
    """
    hora = estado.get("hora_utc", 0)
    ini = config.get("sesion_params.ini_hora_utc", config.get("sesion.inicia_hora_utc", 7))
    fin = config.get("sesion_params.fin_hora_utc", config.get("sesion.fin_hora_utc", 20))
    if hora < ini or hora >= fin:
        return False, f"fuera_sesion h={hora}"

    n_dia = estado.get("trades_hoy", 0)
    max_t = config.get("riesgo_params.max_trades_dia", config.get("riesgo.max_trades_dia", 3))
    if n_dia >= max_t:
        return False, f"max_trades_dia={n_dia}"

    pnl_dia = estado.get("pnl_dia", 0.0)
    bal = estado.get("balance", 1000.0)
    max_loss = config.get("riesgo_params.max_daily_loss_pct", config.get("riesgo.max_daily_loss_pct", 2.0))
    if pnl_dia <= -bal * max_loss / 100.0:
        return False, f"max_loss_dia pnl={pnl_dia:.2f}"

    dd_pct = estado.get("dd_pct", 0.0)
    red = config.get("riesgo_params.reduccion_dd_pct", config.get("riesgo.reduccion_dd_pct", 10.0))
    if dd_pct > red:
        return False, f"dd={dd_pct:.1f}%>red{red}%"

    spread = estado.get("spread", 0.0)
    point = estado.get("point", 1.0)
    spread_max = config.get("estrategia_params.spread_max_pts", config.get("estrategia.spread_max_pts", 30))
    if spread > spread_max:
        return False, f"spread_alto={spread}"

    atr = estado.get("atr", 0.0)
    atr_min_mult = config.get("estrategia_params.atr_min_mult_spread", config.get("estrategia.atr_min_mult_spread", 3))
    if atr < (spread * point * atr_min_mult) if spread > 0 and point > 0 else False:
        return False, f"atr_bajo={atr:.2f}"

    return True, ""
