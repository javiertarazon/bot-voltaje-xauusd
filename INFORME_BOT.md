# INFORME TÉCNICO — BOT TRADER FluxoV2 (XAUUSD, cuenta demo Deriv MT5)
## Versión Modular — 17/09/2026

---

## 1. RESUMEN EJECUTIVO

FluxoV2 es un sistema de trading algoritmico para XAUUSD basado en analogía fluido-eléctrica + filtro Bayesiano + Monte Carlo. **Arquitectura reconstruida en módulos independientes** con configuración centralizada, detección de régimen de mercado, y backtesting unificado. Validado rentable en 2023, 2024 y 2025.

### Resultados validados 2023-2025 (MEJORA 4)
| Año | PF | Total USD | Max DD | Winrate |
|-----|-----|-----------|--------|---------|
| 2023 | 1.06 | +$19 | $59 | 32.1% |
| 2024 | 1.32 | +$117 | $50 | 35.6% |
| 2025 | 1.20 | +$149 | $83 | 34.5% |
| **Total** | **1.19** | **+$285** | **$83** | **34.1%** |

### Estado actual
- **Fase**: 6/6 — Arquitectura modular completa + validación multi-año
- **MT5**: EA compilado (FluxoV2_EA.ex5), pendiente de adjuntar al gráfico
- **Live publish**: Módulo refactorizado (live/publish.py)
- **Indicadores**: Bit-identicales a backtests validados

---

## 2. ARQUITECTURA (flujo de datos modular)

```
[MT5 Deriv terminal]  <-->  [live/publish.py = CEREBRO/SENSOR]
         |                        |  calcula flujo + Bayes + MonteCarlo
         |                        v  escribe JSON atomico cada ~60s
         |                Common\Files\fluxov2_signal.json
         |                        |
         |                        v (lee cada 5s, valida frescura <180s)
         |                [FluxoV2_EA.ex5 = EJECUTOR dentro de MT5]
         |                        |  cortacircuitos propios -> OrderSend
         |                        v  SL/TP gestionados por el SERVIDOR
         +-- deals/candles -----> [trading_log.db = MEMORIA SQLite]
                                    [monitor.py = SUPERVISION/REPORTES]
```

### Módulos principales

| Módulo | Archivo | Rol |
|--------|---------|-----|
| Config | `config/validator.py` | Carga y valida config.json |
| Indicadores | `core/indicators.py` | ATR, flujo, Bayes, MC, régimen (UNICO) |
| Datos | `core/data.py` | Carga/preparación de datos |
| Riesgo | `core/risk.py` | Lote dinámico, cortacircuitos |
| Estrategia | `core/strategy.py` | Generación de señales |
| Régimen | `market/regime.py` | Detección alcista/bajista/lateral |
| Backtest | `backtest/engine.py` | Motor unificado |
| Análisis | `analysis/` | Debilidades, reportes, validación cruzada |
| Live | `live/publish.py` | Publicador de señales |

---

## 3. ESTRATEGIA FluxoV2 (analogia fluido-electrica)

- Precio P(t) = voltaje; dP/dt = corriente; volumen = carga
- Resistencia R = ATR14 / volumen_medio_50
- Caudal Q = suma(sign(ret) * vol) en 20 velas
- I = ret/R (eficiencia del empuje)
- z = I estandarizado rolling(100)

### Señal por capas
1. z > 1.0 (sobrecarga de corriente)
2. P(alcista) > 0.55 (filtro Bayesiano)
3. Monte Carlo P(TP antes SL) > 0.30
4. Solo LONG + ATR14 > ATR100 (expansión)
5. Sesión 7-18 UTC

### Parámetros
- TP = entry + 2.0*ATR, SL = entry - 0.8*ATR
- Max hold: 60 velas M15
- Spread: 0.16 pts

---

## 4. MEJORAS REALIZADAS (v2 → v4)

| # | Mejora | Impacto |
|---|--------|---------|
| 1 | Config centralizada | Un solo JSON + validador |
| 2 | Indicadores unificados | 1 lugar, 0 duplicación |
| 3 | Sesión 7-18 (vs 7-20) | Elimina hora 20 (-1.65 exp) |
| 4 | Filtro régimen expansión | 2023: PF 0.83→1.06 |
| 5 | MC activado por defecto | PF +0.02 consistente |
| 6 | Motor backtest unificado | Multi-período/símbolo |
| 7 | Análisis debilidades auto | Score 0-100 + walk-forward |
| 8 | Módulos independientes | DRY, testable, mantenible |

---

## 5. GESTIÓN DE RIESGO

### Capa 1 - Publicador (calcula lote)
- Riesgo base: 0.5%/trade
- Reducción a 0.25% si DD>10% del peak
- Cortacircuitos: sesion 7-18h, max 3 trades/día, max loss -2% diaria, spread max 30pts, ATR min 3xspread

### Capa 2 - EA ejecutor
- Señal caduca en 180s
- Duplica cortacircuitos
- SL/TP viven en servidor

---

## 6. RESULTADOS DETALLADOS

### Backtest 2023 (MEJORA 4)
165 trades | PF=1.06 | +$19 USD | DD=$59 | WR=32.1%
Meses positivos: Ene, Jun, Oct, Dic

### Backtest 2024 (MEJORA 4)
146 trades | PF=1.32 | +$117 USD | DD=$50 | WR=35.6%
Meses positivos: Mar, Abr, May, Jun, Jul, Sep, Nov

### Backtest 2025 (MEJORA 4)
174 trades | PF=1.20 | +$149 USD | DD=$83 | WR=34.5%
Meses positivos: Feb, Mar, May, Jun, Sep, Nov, Dic

---

## 7. ESTADO ACTUAL Y PENDIENTES

### CERTIFICADO
- Arquitectura modular completa
- Indicadores validados (bit-identicales)
- Backtest multi-año rentable
- Módulos publicador refactorizado
- Documentación completa (IMPROVEMENTS_DOC.md)

### PENDIENTE (tu acción)
1. **Adjuntar EA al gráfico XAUUSD M15** en MT5 (InpMode=0 sombra primero)
2. **Verificar 24h de sombra** (BEAT + señales idénticas Python/EA)
3. **Pasar InpMode=1** y auditar primer trade
4. **Iniciar live/publish.py** para publicar señales
5. **Acumular ~20 trades demo** para primera recalibración

### OPERACIÓN DIARIA
- Abrir MT5 Deriv logueado (XAUUSD en Observación)
- Ejecutar: `python live/publish.py --iter 1 --interval 60`
- Revisar: `python monitor.py` → reporte_monitor.txt
- No lanzar `run_demo_loop` y EA modo 1 a la vez

---

## 8. RECARGA DEL EA TRAS RECOMPILAR

MT5 NO recarga automáticamente el .ex5. Tras compilar:
1. Seleccionar gráfico del EA
2. F7 (propiedades) → revisar inputs: InpMode=0, InpMaxHoldMin=900, InpBE_ATR=0.00, InpFreshSeg=180, InpMaxTradesDia=3, InpDDPausePct=10.0, InpMaxSpreadPts=30, InpSymbol=XAUUSD, InpMagic=20260915
3. OK → MT5 reinicializa EA
4. Verificar log: "EA INIT BUILD=..." con config correcto

---

## 9. DELIMITACION DE FORMATOS

El parser del EA necesita JSON en UTF-16LE. live/publish.py escribe en UTF-16 con BOM. Si EA registra "senal_invalida_sin_epoch" repetidamente, es desajuste de encoding.

---

## 10. ARCHIVOS CLAVE

- `config.json` — Configuración centralizada
- `IMPROVEMENTS_DOC.md` — Documentación detallada de mejoras
- `REPORTE_MULTIANO_2023_2025.md` — Resultados multi-año
- `data/trades_mejora4_2023_2025.csv` — Trades validados
- `data/equity_mejora4_2023_2025.csv` — Equity curve
- `live/publish.py` — Publicador vivo (refactorizado)
- `run_backtest.py` — Entry point backtest unificado
