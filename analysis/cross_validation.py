"""Validación cruzada walk-forward."""
import numpy as np
import pandas as pd


def validar_permanencia(trades: pd.DataFrame, n_folds: int = 5) -> dict:
    """Walk-forward validation.

    Divide el período en N particiones consecutivas.
    Evalúa el PF de cada partición por separado.
    Si PF varía >50% entre folds → estrategia NO robusta.
    """
    if len(trades) < n_folds * 10:
        return {"robusta": False, "razón": "datos_insuficientes", "pfs": []}

    r = trades["pnl"].values
    fold_size = len(r) // n_folds
    pfs = []
    details = []

    for i in range(n_folds):
        start = i * fold_size
        end = start + fold_size if i < n_folds - 1 else len(r)
        fold = r[start:end]
        gp = fold[fold > 0].sum()
        gl = abs(fold[fold <= 0].sum())
        pf = gp / (gl + 1e-9) if gl > 0 else float("inf")
        total = fold.sum()
        n = len(fold)
        pfs.append(pf)
        details.append({"fold": i, "n": n, "pf": pf, "total": total})

    if len(pfs) < 2:
        return {"robusta": False, "razón": "demasiados_pocos_folds", "pfs": pfs}

    pfs_arr = np.array(pfs)
    media = np.mean(pfs_arr)
    std = np.std(pfs_arr)
    min_pf = np.min(pfs_arr)
    max_pf = np.max(pfs_arr)
    ratio = (max_pf - min_pf) / max_pf if max_pf > 0 else 1.0
    robusta = ratio <= 0.5 and media > 0.8

    return {
        "robusta": robusta,
        "pfs": pfs,
        "media_pf": float(media),
        "std_pf": float(std),
        "min_pf": float(min_pf),
        "max_pf": float(max_pf),
        "variacion_ratio": float(ratio),
        "razón": "robusta" if robusta else f"variación={ratio:.0%}",
        "detalles": details,
    }
