# INFORME TECNICO — BOT TRADER FluxoV2 (XAUUSD, cuenta demo Deriv MT5)
Fecha: 16/09/2026 | Estado: Fase 5 C1 (EA ejecutor compilado, pendiente de adjuntar al grafico)

## 1. RESUMEN EJECUTIVO
FluxoV2 es un sistema de trading algoritmico para XAUUSD basado en una analogia
propietaria fluido-electrica (no usa RSI/MACD clasicos), con filtro probabilistico
Bayesiano de regimen, filtro Monte Carlo de ejecutabilidad, y una gestion de riesgo
dinamica en dos capas (publicador + ejecutor) con memoria en SQLite.
Backtest 2025 validado con costes reales (spread, slippage, swap): capital $1,000 ->
$1,444.92 (+44.49%), max DD 11.34%, PF 1.21, 11/12 meses positivos.

## 2. ARQUITECTURA (flujo de datos)
```
[MT5 Deriv terminal]  <-->  [live_publish.py  = CEREBRO/SENSOR]
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
Principio de diseno: Python NUNCA envia ordenes en esta arquitectura; el EA es el
unico ejecutor. La senal caduca en 180s: si Python muere, el EA deja de operar solo.

## 3. MODULOS Y FUNCION DE CADA UNO
| Archivo | Rol | Detalle |
|---|---|---|
| config.json | Parametros vivos | uz=1.0, pm=0.55, tp_k=2.0, sl_k=0.8, sesion 7-20 UTC, max 3 trades/dia, -2% dia, riesgo 0.5%/0.25%, magic 20260915 |
| .env | Credenciales | MT5_LOGIN/PASSWORD/SERVER/PATH (local, gitignored) |
| live_publish.py | CEREBRO | Conecta a MT5, calcula la senal, escribe fluxov2_signal.json, registra equity/no_trades/cierres en la BD. NO opera |
| FluxoV2_EA.mq5/.ex5 | EJECUTOR | Lee el JSON (FILE_COMMON), duplica cortacircuitos, abre BUY market, maxhold 900 min, BE opcional, log propio fluxov2_ea.log. InpMode 0=sombra 1=trade |
| live_demo.py | Ejecutor Python (opcion A) | Sistema original por watchdog; en pausa con el EA. Tambien contiene las funciones compartidas (flujo/bayes/MC/lote) |
| flux_core.py | Investigacion | Versiones vectorizadas de flujo+Bayes para backtests |
| trading_log.db | MEMORIA | Tablas: equity (cada ciclo), no_trades (por que NO opera), demo_trades (entrada/pnl/cierre), estado (cursor de cierres) |
| monitor.py | SUPERVISION | Lee la BD: winrate, PF, expectancy, DD, accion de riesgo recomendada |
| correr_publish_loop.bat | Watchdog | Relanza el publicador cada 60s; proceso corto = inmune a cuelgues IPC |
| correr_demo_loop.bat | Watchdog (opcion A) | El antiguo loop ejecutor Python. NO usar con EA en modo 1 |
| kill_live.ps1 / kill_publish.ps1 | Limpieza | Matan solo procesos del bot, por nombre de script |
| compilar_ea.ps1 | Build | Recompila el EA y certifica 0 errores |
| backtest_2025.py / opt_grid.py / usd_run.py / metricas_pro.py / plot_usd.py | Research | Backtests con velas reales M15 de Deriv, grid 64 combinaciones, metricas USD y grafico equity/DD |
| data\*.csv, data\*.npz | Datos | M15 (100k velas), ticks 30d, trades y curvas |

## 4. LA ESTRATEGIA FluxoV2 (analogia fluido-electrica)
Traduccion del mercado a un circuito:
- Precio P(t) = voltaje V;  dP/dt = corriente I;  volumen de ticks = carga Q
- Resistencia R = ATR14 / volumen_medio_50  (poco volumen = misma corriente mueve mas)
- Capacitancia C = rango(20) (energia acumulada en rango, se libera en ruptura)
- Caudal Q_flujo = suma(sign(ret) * vol) en 20 velas (presion neta direccional)

Senal por capas (todo debe cumplirse):
1. I se estandariza con su media/std rolling(100) -> z. Exigencia: z > 1.0
   (sobrecarga de corriente: el flujo empuja mas fuerte de lo normal).
2. Filtro Bayesiano de regimen: verosimilitud = 0.5 + 0.3*tanh(Q/Qmed) + 0.2*tanh(z/2),
   actualizacion recursiva p = L*p_prev / (L*p_prev + (1-L)*(1-p_prev)) con decaimiento
   0.98 (recuerda ~50 velas). Exigencia: P(alcista) > 0.55.
3. Filtro Monte Carlo: 1000 caminos GBM con mu/sigma de las ultimas 100 velas M15,
   horizonte 20 velas; P(toques TP antes que toca SL). Exigencia: > 0.30.
4. Entrada SOLO LONG (backtest: LONG +170 pts, SHORT -210): TP = 2.0*ATR, SL = 0.8*ATR
   (R:R 2.5:1, winrate esperado ~34%, gana por payoff 2.4).
5. Sesion 7-20 UTC (Londres+NY), ATR minimo 3x spread.

Por que funciona: la relacion corrente/volumen (I = ret/R) mide la EFICIENCIA del
empuje: precio que sube con poco volumen tiene I alta (mercado "estresado" en una
direccion). El Bayes filtra falsas sobrecargas y el Monte Carlo exige que el camino
tipico toque TP antes que SL dada la volatilidad actual.
## 5. GESTION DE RIESGO DINAMICA (2 capas)
Capa 1 - Publicador (calcula lote):
- Riesgo por trade: 0.5% del balance. Lote = (balance * 0.5%) / (SL_en_dolares).
  Ej: SL=0.8*ATR(18.39)=14.7 pts -> SL$=14.7*100=1470/lote -> lote=0.034 -> 0.03.
- Reduccion automatica a 0.25% si el DD desde el peak de equity supera 10%.
- Cortacircuitos del publicador: sesion 7-20h, max 3 trades/dia, perdida diaria
  max -2% del balance, spread max 30 pts, ATR min 0.48, una posicion a la vez.
Capa 2 - EA ejecutor (duplica y protege si Python falla):
- Senal caducada (>180s) = no opera. Espejo de: spread, max trades/dia, max loss dia,
  DD-pausa 10%. Maxhold 900 min (60 velas M15 = replica exacta del backtest).
- SL/TP viven en el SERVIDOR: aunque el PC se apague, el riesgo de cada operacion
  queda acotado al SL puesto al momento de abrir.
Regla viva del gestor (yo): si winrate <25% con n>=20 o PF<1.1 con n>=15, bajo riesgo
a 0.25% y pauso 24h; recalibro umbrales con el optimizador mensual.

## 6. COMO APRENDE DE SUS GANANCIAS Y PERDIDAS
Memoria (SQLite) por cada decision:
- equity: balance/equity cada ciclo -> base para DD y peak.
- no_trades: cada oportunidad RECHAZADA con razon exacta (sin_senal/mc_bajo/spread...)
- demo_trades: entrada (ticket, lote, sl, tp, z, p_up, p_mc, riesgo) + cierre
  (pnl, exit_px, tipo: tp/sl/maxhold/manual) + recuperacion de huerfanas si el
  proceso murio tras abrir.
- estado: cursor de cierres para no contar dos veces.
Ciclo de aprendizaje:
1. monitor.py consolida: winrate, PF, expectancy, DD, por horas (futuro).
2. Reglas de ajuste automaticas (definidas y activas en monitor):
   PF<1.0 con n>=15 -> riesgo 0.25% + pausa 24h | DD>10% -> 0.25% hasta recuperar peak
3. Recalibracion supervisada (mensual): backtest con datos frescos -> si los umbrales
   optimos se movieron (ej. uz 1.0->1.2, pm 0.55->0.60), actualizo config.json y
   recompilo; NUNCA cambia sola sin auditoria previa.
Lecciones YA aprendidas y aplicadas (historial real):
- V1 (todos los trades): PF 0.99 -> sobreoperacion, se comia el edge el spread.
- V2 (solo LONG + R:R 2.5 + sesion): PF 1.29 / USD 1.21 -> VERSION OFICIAL.
- V3 (trailing BE a +1.0 ATR + filtros duros de noviembre): PF 0.61 -> DESCARTADA.
  Leccion: el trailing prematuro convierte TP potenciales en scratches.
- V3b (on/off por ATR14>ATR100): PF 1.07 -> DESCARTADA. Leccion: filtrar por regimen
  destruye la frecuencia que sostiene el edge (n 525->323).
- Costes reales Deriv (swap -45/lote/noche, triple miercoles): -38.70 USD en 2025,
  PF baja 1.29->1.21. El sistema sigue positivo con costes.

## 7. ESTADO ACTUAL Y PENDIENTES
CERTIFICADO (con ejecucion real): descarga de datos, backtests 2025 (3 versiones),
metricas USD, pipeline de orden demo (entrada TP +2.07 USD, balance 10000->10002.07),
memoria BD, watchdog, publicador vivo (senal BUY publicada 16/09 z=2.07 mc=0.54),
EA compilado 0 errores.
PENDIENTE (tu accion + auditoria mia): 1) adjuntar EA al grafico XAUUSD M15
(InpMode=0 sombra, Algo Trading ON); 2) verificar 24h de sombra (BEAT + senales
identicas Python/EA en fluxov2_ea.log); 3) pasar InpMode=1 y auditar primer trade;
4) acumular ~20 trades demo y primera recalibracion con datos vivos.
LIMITACIONES declaradas: swap estimado con tarifa actual, no historico 2025;
sin slippage intravela en backtest; senal sobre vela M15 CERRADA (latencia hasta
60s por arquitectura watchdog, aceptada como coste de robustez).
## 8. OPERACION DIARIA (guia rapida)
- Abrir MT5 Deriv logueado (perfil Deriv-Demo, XAUUSD en Observacion del mercado).
- Lanzar correr_publish_loop.bat (publica senales cada 60s). Cierra la ventana para parar.
- EA adjunto con InpMode=1: opera solo. Con InpMode=0: solo registra en su log.
- Revisar: py monitor.py -> reporte_monitor.txt | log del EA en
  Common\Files\fluxov2_ea.log | memoria: py db_check.py -> cert_db.txt
- NO lanzar correr_demo_loop.bat y EA modo 1 a la vez (doble ejecucion).
- Si algo cuelga: los watchdogs matan/reinician solos cada ciclo (90s max de parada).