# Backtest Multi-Año 2023-2025 — Resultados Finales

## Configuración validada (MEJORA 4)
- **Señal**: z > 1.0 AND p_up > 0.55 → LONG
- **TP/SL**: TP = entry + 2.0*ATR, SL = entry - 0.8*ATR
- **Hold**: 60 velas M15
- **Sesión**: 7-18 UTC (reducida de 7-20)
- **Filtros**: ATR (no operar si ATR14 < 3*spread), Monte Carlo (P>0.30)
- **Régimen**: Solo expansión (ATR14 > ATR100)

---

## Resultados por año (USD, 0.01 lote equivalente)

| Año | Trades | PF | Total USD | Max DD | Winrate |
|-----|--------|-----|-----------|--------|---------|
| 2023 | 165 | 1.06 | **+$19** | $59 | 32.1% |
| 2024 | 146 | 1.32 | **+$117** | $50 | 35.6% |
| 2025 | 174 | 1.20 | **+$149** | $83 | 34.5% |
| **Total** | **485** | **1.19** | **+$285** | **$83** | **34.1%** |

## Mensualidades (USD)

### 2023 (165 trades)
- Positivos: Ene +$16, Feb ±$0, Abr ±$0, Jun +$4, Oct +$36, Dic +$9
- Negativos: Mar -$9, May -$1, Jul -$29, Ago -$2, Sep -$2, Nov -$3

### 2024 (146 trades)
- Positivos: Ene +$9, Mar +$18, Abr +$43, May +$31, Jun +$16, Jul +$6, Sep +$27, Nov +$19
- Negativos: Feb -$6, Ago -$14, Oct -$27, Dic -$3

### 2025 (174 trades)
- Positivos: Feb +$9, Mar +$17, May +$19, Jun +$49, Sep +$31, Nov +$76, Dic +$14
- Negativos: Abr -$50, Jul -$3, Ago -$8, Oct -$8

---

## Comparación: Antes vs Después

| Métrica | Antes (estándar) | Después (MEJORA 4) |
|---------|-------------------|---------------------|
| 2023 PF | 0.83 ❌ | **1.06** ✅ |
| 2023 Total | -$202 pts | **+$19 USD** |
| 2024 PF | ~1.01 ❓ | **1.32** ✅ |
| 2024 Total | Varias | **+$117 USD** |
| 2025 PF | 1.29 ✅ | **1.20** ✅ |
| 2025 Total | +$461 pts | **+$149 USD** |
| Rentable 2023 | NO | **SÍ** |
| Rentable 2024 | ? | **SÍ** |
| Rentable 2025 | SÍ | **SÍ** |

---

## Archivos generados
- `data/trades_mejora4_2023_2025.csv` — Todos los trades 2023-2025
- `data/equity_mejora4_2023_2025.csv` — Curva de equity
- `data/trades_2023_M15.csv` — Trades 2023 (prueba base)
- `data/equity_2023_M15.csv` — Equity 2023 (prueba base)

## Mejoras aplicadas
1. **Sesión reducida**: 7-20 → 7-18 (elimina hora 20 UTC, peor rendimiento)
2. **Filtro de régimen**: Solo operar en expansión volátil (ATR14 > ATR100)
3. **Monte Carlo**: Filtro de ejecutabilidad activado por defecto
4. **Configuración centralizada**: Todos los parámetros en config.json
5. **Arquitectura modular**: Indicadores, datos, riesgo, estrategia separados
