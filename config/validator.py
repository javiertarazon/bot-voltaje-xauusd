"""Validador y carga de configuración centralizada."""
import json
from pathlib import Path
from typing import Any, Optional


class Config:
    def __init__(self, data: dict, raw_path: Optional[str] = None):
        self._data = data
        self._raw_path = raw_path

    def get(self, key: str, default: Any = None) -> Any:
        parts = key.split(".")
        cur = self._data
        for p in parts:
            if isinstance(cur, dict) and p in cur:
                cur = cur[p]
            else:
                return default
        return cur

    def has(self, key: str) -> bool:
        return self.get(key) is not None

    def as_dict(self) -> dict:
        return self._data.copy()

    @property
    def raw_path(self) -> Optional[str]:
        return self._raw_path


_VALIDATORS = {
    "broker_activo": str,
    "symbol": str,
    "timeframes_historia": list,
    "fecha_inicio_historia": str,
    "data_dir": str,
    "magic": int,
}

_RANGES = {
    "uz": (0.1, 5.0),
    "pm": (0.5, 0.95),
    "tp_k": (0.5, 5.0),
    "sl_k": (0.3, 3.0),
    "max_hold": (10, 500),
    "risk_pct_por_trade": (0.01, 5.0),
    "risk_reducido_pct": (0.01, 2.0),
    "max_trades_dia": (1, 20),
    "max_daily_loss_pct": (0.5, 10.0),
}


def load_config(path: str = "config.json") -> Config:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Configuración no encontrada: {path}")
    raw = json.loads(p.read_text(encoding="utf-8"))
    errors = _validate(raw)
    if errors:
        raise ValueError(f"Configuración inválida:\n  " + "\n  ".join(errors))
    return Config(raw, raw_path=str(p.resolve()))


def _validate(cfg: dict) -> list:
    errs = []
    for key, typ in _VALIDATORS.items():
        val = cfg.get(key)
        if val is None:
            errs.append(f"{key}: obligatorio")
        elif not isinstance(val, typ):
            errs.append(f"{key}: esperado {typ.__name__}, obtenido {type(val).__name__}")
    for key, (lo, hi) in _RANGES.items():
        val = cfg.get(key)
        if val is None:
            continue
        if not (lo <= float(val) <= hi):
            errs.append(f"{key}: {val} fuera de rango [{lo}, {hi}]")
    ses = cfg.get("sesion_utc")
    if isinstance(ses, list) and len(ses) == 2:
        if not (0 <= ses[0] < ses[1] <= 24):
            errs.append(f"sesion_utc: rango inválido {ses}")
    return errs
