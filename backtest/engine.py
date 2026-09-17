"""Motor unificado de backtest."""
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import numpy as np
import pandas as pd


@dataclass
class BacktestResult:
    trades: pd.DataFrame
    metricas: dict
    equity: pd.Series
    config: dict


class BacktestEngine:
    def __init__(self, config: "Config"):
        self.config = config
        self.base_path = Path(config.raw_path).parent if config.raw_path else Path(".")

    def ejecutar(
        self,
        df: Optional[pd.DataFrame] = None,
        simbolo: str = "XAUUSD",
        periodo_inicio: Optional[str] = None,
        periodo_fin: Optional[str] = None,
        solo_long: bool = True,
        filtro_atr: bool = True,
        filtro_mc: bool = True,
    ) -> BacktestResult:
        """Ejecuta backtest. Si df es None, carga datos automáticamente.

        Args:
            filtro_atr: Skip trades when ATR < 3*spread (coincide con backtest_v3)
            filtro_mc: Monte Carlo ejecutabilidad check (coincide con live)
        """
        from core.data import preparar_backtest, cargar_velas

        if df is None:
            ruta = self.base_path / "data" / f"{simbolo.replace('.', '_')}_M15.csv"
            if not ruta.exists():
                ruta = self.base_path / "data" / f"{simbolo}_M15.csv"
            if ruta.exists():
                df = cargar_velas(str(ruta))
            else:
                raise FileNotFoundError(f"Sin datos para {simbolo}")

        # Los indicadores necesitan historial anterior al período evaluado.
        # Calcularlos antes de cortar evita reinicios artificiales de ATR/z/Bayes.
        d = preparar_backtest(df, self.config)
        from core.data import filtrar_periodo
        d = filtrar_periodo(d, periodo_inicio, periodo_fin)

        uz = self.config.get("estrategia_params.uz", self.config.get("estrategia.uz", 1.0))
        pm = self.config.get("estrategia_params.pm", self.config.get("estrategia.pm", 0.55))
        tp_k = self.config.get("estrategia_params.tp_k", self.config.get("estrategia.tp_k", 2.0))
        sl_k = self.config.get("estrategia_params.sl_k", self.config.get("estrategia.sl_k", 0.8))
        max_hold = self.config.get("estrategia_params.max_hold_velas", self.config.get("estrategia.max_hold", 60))
        spread = self.config.get("backtest_params.costes_spread", 0.16)
        solo_long = self.config.get("estrategia_params.solo_long", solo_long)
        mc_paths = self.config.get("backtest_params.max_paths_mc", 2000)
        mc_horizon = self.config.get("backtest_params.horizon_mc", 20)
        mc_umbral = self.config.get("backtest_params.umbral_mc", 0.30)
        ses_ini, ses_fin = self.config.get("sesion_params.ini_hora_utc", 7), self.config.get("sesion_params.fin_hora_utc", 18)
        filtro_exp = bool(self.config.get("filtro_expansion", self.config.get("regimen.activo", False)))
        max_atr_ratio = self.config.get("regimen.max_atr_ratio", None)
        require_up_prev = bool(self.config.get("regimen.require_up_prev", False))
        min_trend_strength = float(self.config.get("regimen.min_trend_strength", 0.0))
        ema20 = d["close"].ewm(span=20, adjust=False).mean() if min_trend_strength > 0 else None
        ema50 = d["close"].ewm(span=50, adjust=False).mean() if min_trend_strength > 0 else None

        z_vals = d["z"].values if "z" in d.columns else np.zeros(len(d))
        p_vals = d["p_up"].values if "p_up" in d.columns else np.zeros(len(d))
        atr_vals = d["atr"].values if "atr" in d.columns else np.ones(len(d))
        hi_vals = d["high"].values if "high" in d.columns else d["close"].values
        lo_vals = d["low"].values if "low" in d.columns else d["close"].values
        cl_vals = d["close"].values if "close" in d.columns else d["px"].values
        tm = d["time"] if "time" in d.columns else pd.Series(range(len(d)))

        trs = []
        trades_by_day = {}
        month_loss_streak = {}
        max_month_losses = int(self.config.get("riesgo_params.max_losses_month", 0))
        i = 120
        n = len(d)
        while i < n - 2:
            if "time" in d.columns:
                hora = int(pd.Timestamp(d["time"].iloc[i]).hour)
                if hora < ses_ini or hora >= ses_fin:
                    i += 1
                    continue
                day = pd.Timestamp(d["time"].iloc[i]).date()
                if trades_by_day.get(day, 0) >= int(self.config.get("riesgo_params.max_trades_dia", 3)):
                    i += 1
                    continue
                month = pd.Timestamp(d["time"].iloc[i]).strftime("%Y-%m")
                if max_month_losses > 0 and month_loss_streak.get(month, 0) >= max_month_losses:
                    i += 1
                    continue
            if filtro_exp and "exp" in d.columns and not bool(d["exp"].iloc[i]):
                i += 1
                continue
            if max_atr_ratio is not None and "atr_ratio" in d.columns and float(d["atr_ratio"].iloc[i]) > float(max_atr_ratio):
                i += 1
                continue
            if min_trend_strength > 0 and float(ema20.iloc[i] - ema50.iloc[i]) / max(float(atr_vals[i]), 1e-12) < min_trend_strength:
                i += 1
                continue
            if require_up_prev and "up_prev" in d.columns and not bool(d["up_prev"].iloc[i]):
                i += 1
                continue
            lado = 0
            if solo_long:
                if z_vals[i] > uz and p_vals[i] > pm:
                    lado = 1
            else:
                if z_vals[i] > uz and p_vals[i] > pm:
                    lado = 1
                elif z_vals[i] < -uz and p_vals[i] < (1 - pm):
                    lado = -1

            if not lado:
                i += 1
                continue

            a = float(atr_vals[i])
            if filtro_atr and a < spread * 3:
                i += 1
                continue

            # Monte Carlo
            p_mc = 0.0
            if filtro_mc:
                ventana = d.iloc[max(0, i - 100):i + 1]
                if len(ventana) >= 20:
                    from core.indicators import calcular_monte_carlo
                    p_mc = calcular_monte_carlo(
                        ventana["close"] if "close" in ventana.columns else ventana["px"],
                        float(d["atr"].iloc[i]),
                        paths=mc_paths,
                        horizon=mc_horizon,
                    )
                if p_mc < mc_umbral:
                    i += 1
                    continue

            e = float(cl_vals[i])
            tp = e + lado * tp_k * a
            sl = e - lado * sl_k * a

            s = float(cl_vals[min(i + max_hold, n - 1)])
            m = "timeout"
            j_out = min(i + max_hold, n - 1)

            for j in range(i + 1, min(i + max_hold + 1, n)):
                h, l, c = float(hi_vals[j]), float(lo_vals[j]), float(cl_vals[j])
                if lado == 1:
                    btp = h >= tp
                    bsl = l <= sl
                else:
                    btp = l <= tp
                    bsl = h >= sl
                if btp and bsl:
                    s, m, j_out = (sl if lado == 1 else sl), "SL_amb", j
                    break
                if bsl:
                    s, m, j_out = sl, "SL", j
                    break
                if btp:
                    s, m, j_out = tp, "TP", j
                    break
                s, j_out = c, j

            pnl = lado * (s - e) - spread
            trs.append({
                "t_in": tm.iloc[i],
                "t_out": tm.iloc[j_out],
                "lado": lado,
                "entry": e,
                "exit": s,
                "tp": tp,
                "sl": sl,
                "pnl": pnl,
                "motivo": m,
                "z": float(z_vals[i]),
                "p_up": float(p_vals[i]),
                "p_mc": p_mc,
                "atr": a,
                "expansion": int(bool(d["exp"].iloc[i])) if "exp" in d.columns else 0,
                "bars": j_out - i,
            })
            if "time" in d.columns:
                trades_by_day[day] = trades_by_day.get(day, 0) + 1
                month = pd.Timestamp(d["time"].iloc[i]).strftime("%Y-%m")
                month_loss_streak[month] = month_loss_streak.get(month, 0) + (1 if pnl <= 0 else 0)
            # Una nueva entrada sólo puede producirse después del cierre.
            i = j_out + 1

        T = pd.DataFrame(trs)
        if len(T) > 0:
            T["t_out"] = pd.to_datetime(T["t_out"], utc=True)
            T = T.sort_values("t_out").reset_index(drop=True)
            T["eq"] = T["pnl"].cumsum()

        metricas = self._calcular_metricas(T)
        equity = T["eq"] if len(T) > 0 else pd.Series(dtype=float)

        return BacktestResult(
            trades=T,
            metricas=metricas,
            equity=equity,
            config=self.config.as_dict(),
        )

    def ejecutar_grid(self, params: Optional[dict] = None) -> pd.DataFrame:
        """Ejecuta grid de combinaciones de parámetros."""
        if params is None:
            params = {
                "uz": [1.0, 1.5],
                "pm": [0.55, 0.60],
                "tp_k": [1.5, 2.0],
                "sl_k": [0.8, 1.0],
                "max_hold": [40, 60],
            }
        import itertools
        results = []
        keys = list(params.keys())
        for combo in itertools.product(*[params[k] for k in keys]):
            cfg_temp = dict(zip(keys, combo))
            # Temporalmente sobreescribir config
            orig = {k: self.config.get(f"estrategia_params.{k}", None) for k in keys}
            for k, v in cfg_temp.items():
                self.config._data[f"estrategia_params.{k}"] = v
            try:
                r = self.ejecutar()
                if len(r.trades) > 0:
                    results.append({
                        **dict(zip(keys, combo)),
                        "n": len(r.trades),
                        "winrate": r.metricas["winrate"],
                        "pf": r.metricas["pf"],
                        "total": r.metricas["total"],
                        "exp": r.metricas["exp"],
                        "dd": r.metricas["dd"],
                    })
            finally:
                for k, v in orig.items():
                    if v is None:
                        self.config._data.pop(f"estrategia_params.{k}", None)
                    else:
                        self.config._data[f"estrategia_params.{k}"] = v
        return pd.DataFrame(results)

    def _calcular_metricas(self, T: pd.DataFrame) -> dict:
        if len(T) == 0:
            return {"n": 0, "winrate": 0.0, "pf": 0.0, "total": 0.0, "exp": 0.0,
                     "dd": 0.0, "sharpe": 0.0, "sortino": 0.0, "calmar": 0.0}
        r = T["pnl"].values
        n = len(r)
        wins = (r > 0).sum()
        winrate = wins / n
        gp = r[r > 0].sum()
        gl = abs(r[r <= 0].sum())
        pf = gp / (gl + 1e-9)
        exp = r.mean()
        tot = r.sum()
        eq = np.cumsum(r)
        peak = np.maximum.accumulate(eq)
        dd = float((peak - eq).max())
        sharpe = float(r.mean() / (r.std(ddof=1) + 1e-9) * np.sqrt(n))
        dn = r[r < 0]
        sortino = float(r.mean() / (dn.std(ddof=1) + 1e-9) * np.sqrt(n)) if len(dn) > 1 else 0.0
        calmar = float(tot / (dd + 1e-9))
        avgw = float(r[r > 0].mean()) if wins > 0 else 0.0
        avgl = float(r[r <= 0].mean()) if (n - wins) > 0 else 0.0
        payoff = avgw / (abs(avgl) + 1e-9)
        # Rachas
        w = (r > 0).astype(int)
        maxrw = maxrl = curw = curl = 0
        for x in w:
            if x:
                curw += 1; maxrw = max(maxrw, curw); curl = 0
            else:
                curl += 1; maxrl = max(maxrl, curl); curw = 0
        # Mensual
        T2 = T.copy()
        T2["mes"] = T2["t_out"].dt.tz_localize(None).dt.to_period("M").astype(str) if "t_out" in T2.columns else [""]
        mensual = T2.groupby("mes")["pnl"].agg(["sum", "count", "mean"]) if len(T2) > 0 else pd.DataFrame()
        return {
            "n": n, "winrate": winrate, "pf": pf, "exp": exp, "total": tot,
            "dd": dd, "sharpe": sharpe, "sortino": sortino, "calmar": calmar,
            "avg_win": avgw, "avg_loss": avgl, "payoff": payoff,
            "max_racha_ganancia": maxrw, "max_racha_perdida": maxrl,
            "mensual": mensual,
        }
