#!/usr/bin/env python3
"""Entry point unificado de backtest — XAUUSD Trader FluxoV2.

Uso: python run_backtest.py [config.json]
"""
from pathlib import Path
import sys

BASE = Path(__file__).parent
sys.path.insert(0, str(BASE))

if __name__ == "__main__":
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else str(BASE / "config.json")
    from backtest.pipeline import main
    sys.argv = ["run_backtest", cfg_path]
    main()
