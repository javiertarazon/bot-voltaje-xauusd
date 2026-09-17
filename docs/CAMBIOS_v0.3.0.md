# XAUUSD Trader FluxoV2 — versión 0.3.0

## Resumen

Consolida la corrección del motor M15, el riesgo adaptativo, filtros de régimen, validaciones fuera de muestra y los dos EAs MQL5 compilados. No declara rentabilidad garantizada.

## Correcciones

- Indicadores calculados antes de cortar períodos, conservando el historial previo.
- Filtros de sesión, expansión, máximo diario y pérdidas mensuales corregidos.
- Añadido `atr_ratio` para volatilidad extrema.
- Corregido el circuito de riesgo ATR/spread.
- El lotaje no fuerza 0,01 cuando excede el riesgo calculado.
- El publicador usa tick size/tick value y paso real del broker.
- Monte Carlo reproducible mediante semilla fija.
- MQL5: `PositionInformation.mqh` corregido a `PositionInfo.mqh`.
- Ambos EAs compilados: 0 errores, 0 warnings.
- Corregida la herencia de parámetros de la configuración candidata.

## Mejoras

- `config_adaptive.json` y `config_regime_candidate.json` separados.
- Riesgo dinámico por drawdown, racha y volatilidad.
- Simulación con capital inicial USD 1.000.
- Validaciones anual, trimestral, bootstrap y rolling OOS.
- Snapshot MQL5 de solo lectura con datos de cuenta y símbolo.
- Sensibilidad de costes y riesgo.

## FluxoV2 adaptativo base (M15, coste 0,30)

| Año | Operaciones | PF | Exp. | Total | DD |
|---|---:|---:|---:|---:|---:|
| 2023 | 37 | 1,274 | 0,439 | 16,23 | 25,42 |
| 2024 | 35 | 1,403 | 0,871 | 30,49 | 17,73 |
| 2025 | 31 | 1,611 | 2,176 | 67,45 | 34,32 |
| 2026 parcial | 19 | 1,331 | 2,006 | 38,11 | 53,91 |

## Filtro de régimen candidato

`require_up_prev=true`, `min_trend_strength=0,25`:

| Año | Operaciones | PF | Exp. | Total | DD |
|---|---:|---:|---:|---:|---:|
| 2023 | 23 | 2,041 | 1,388 | 31,93 | 8,93 |
| 2024 | 21 | 1,872 | 1,544 | 32,43 | 10,41 |
| 2025 | 18 | 2,343 | 3,586 | 64,56 | 14,11 |
| 2026 parcial | 7 | 3,621 | 8,945 | 62,62 | 10,69 |

La candidata reduce DD, pero la muestra es pequeña y permanece separada de la configuración oficial.

## Riesgo USD 1.000

Con la candidata, coste 0,30 y riesgo base 0,25%: saldo simulado USD 1.025,42 y DD aproximado USD 13,26. Es una simulación, no una garantía ni un resultado tick-by-tick.

## MT5 y limitaciones

- Pepperstone-Demo fue confirmada desde MT5; balance/equity observados: USD 5.000.
- XAUUSD observado: tick size 0,01, tick value 1, volumen mínimo/paso 0,01 y spread 13 puntos.
- La conexión directa Python–MT5 continúa con `IPC timeout`.
- El gate anual estricto no está superado por la muestra parcial de 2026.
- No se enviaron órdenes reales.

## Reproducción

```bash
python run_adaptive_backtest.py
python run_adaptive_backtest.py regime_candidate
python run_regime_test.py
python analysis/bootstrap_adaptive.py trades_fluxov2_adaptive.csv
python analysis/rolling_oos.py
python validate_adaptive.py
```
