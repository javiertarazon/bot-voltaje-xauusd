# XAUUSD Trader FluxoV2 — Arquitectura Modular

Trader algorítmico XAUUSD M15 basado en analogía fluido-eléctrica + filtro Bayesiano + Monte Carlo.

## Arquitectura Modular

```
config/          Configuración centralizada (config.json + validator.py)
core/            Módulos compartidos (indicadores, datos, riesgo, estrategia)
market/          Detección de régimen (alcista/bajista/lateral)
backtest/        Motor unificado (engine.py, pipeline.py)
analysis/        Análisis automático (debilidades, reportes, validación)
live/publish.py  Publicador de señales (refactor de live_publish.py)
data/            Datos históricos CSV/NPZ
reportes/        Reportes generados
debug/           Scripts de diagnóstico (move-13 scripts utilitarios)
```

## Uso Rápido

### Backtest unificado
```bash
python run_backtest.py
# o: python backtest/pipeline.py
```

### Validación de módulos
```bash
python -c "from config.validator import load_config; c=load_config(); print(c.get('estrategia_params.uz'))"
```

### Live trading (refactorado)
```bash
python live/publish.py --iter 1
```

## Estrategia FluxoV2

- **Señal**: z > 1.0 AND p_bayes > 0.55 → LONG
- **TP/SL**: TP = entry + 2.0*ATR, SL = entry - 0.8*ATR
- **Hold**: 60 velas M15 máximo
- **Filtros**: sesión 7-20 UTC, max 3 trades/día, MC ejecutabilidad > 0.30

## Validación

- Indicadores (z, p_up, ATR): **bit-identicales** a backtests validados (diferencia = 0)
- PF 2025: ~1.28 (strict mode) / ~1.29 (con filtros sesión+max3/dia)
- Señales: 1677 (idénticas a backtest_2025.py)

## Requisitos
```
pip install -r requirements.txt
```

## Notas
- `.env` contiene credenciales (gitignored)
- `debug/` contiene scripts legacy de diagnóstico
- Scripts backtest legacy (backtest_2024.py, backtest_2025.py, etc.) siguen operativos pero quedan obsoletos
