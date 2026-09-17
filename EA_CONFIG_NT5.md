# CONFIGURACION EA FLUXOV2 EN MT5 (NT5)
## Cuenta demo Deriv

## Prerrequisitos
1. MT5 instalado y conectado a Deriv (demo cuenta 32393895)
2. XAUUSD en ventana Observacion
3. Archivo `FluxoV2_EA.ex5` compilado (o `FluxoV2_EA.mq5` fuente)
4. `live/publish.py` corriendo en segundo plano (genera JSON)
5. `data/xauusd_M15.csv` existente (ultimas 500 velas minimo)

## Adjunta EA al grafico
1. Abre MT5 -> Conecta a Deriv (login demo)
2. En Observacion: clic XAUUSD -> Grafico
3. Timeframe: **M15** (OBLIGATORIO)
4. Navegador (Ctrl+N) -> Asesores Expertos -> `FluxoV2_EA.ex5`
5. Arrastra al grafico XAUUSD M15
6. Aparece dialogo de configuracion

## Inputs del EA (valores recomendados)

### Comportamiento
| Input | Valor | Descripcion |
|-------|-------|-------------|
| InpMode | **0** | 0=Sombra (solo senal, no ejecuta), 1=Modo real |
| InpMagic | 20260915 | Identificador de orden magic |

### Timing y frescura
| Input | Valor | Descripcion |
|-------|-------|-------------|
| InpFreshSeg | **180** | Max segundos senal fresca (3 min) |
| InpMaxHoldMin | **900** | Max segundos holding senal (15 min) |
| InpDivergenceEMA | 200 | Periodo EMA divergencia |

### Gestion riesgo
| Input | Valor | Descripcion |
|-------|-------|-------------|
| InpBE_ATR | **0.00** | Breakeven en ATR (0=desactivado) |
| InpBE_Plus_Pips | 10 | Lock-in despues BE |
| InpMaxSpreadPts | **30** | Max spread permitido (puntos) |
| InpMaxTradesDia | **3** | Max trades abiertos simultaneos |
| InpTrailingStart | 500 | Puntos inicio trailing |
| InpTrailingStep | 150 | Puntos paso trailing |
| InpTrailingStop | 300 | Puntos stop trailing |

### Sesion y limites
| Input | Valor | Descripcion |
|-------|-------|-------------|
| InpMaxDDDraw | **15** | Max drawdown (comparado con balance) |
| InpDDPausePct | **10.0** | Pausa por drawdown (%) |

### Filtros tecnicos
| Input | Valor | Descripcion |
|-------|-------|-------------|
| InpRSIMode | 0 | 0=RSI simple, 1=Fractal+RSI |
| InpRSIPeriod | 14 | Periodo RSI |
| InpRSI_high | 70 | Umbral RSI alto |
| InpRSI_low | 30 | Umbral RSI bajo |
| InpBearEscalationATR | 0 | Factor escalacion ATR bajista |
| InpBullEscalationATR | 0 | Factor escalacion ATR alcista |

### Simbolo
| Input | Valor | Descripcion |
|-------|-------|-------------|
| InpSymbol | **XAUUSD** | Symbol nombre en broker |

## Proceso post-compilacion

MT5 **NO** recarga automaticamente el .ex5. Tras compilar en MetaEditor:

1. Selecciona el grafico donde esta el EA
2. Click derecho en grafico -> Asesores Expertos -> [EA] -> Propiedades (F7)
3. Revisa todos los inputs arriba
4. Click OK -> MT5 reinicializa el EA
5. Verifica en log: `EA INIT BUILD=...` con config correcto
6. En `Common\Files\fluxov2_ea.log` debe aparecer inicio correcto

## Verificacion post-inicio
- EA log debe mostrar INIT exitoso
- `Common\Files\fluxov2_ea.log` debe actualizarse
- Si `senal_invalida_sin_epoch` aparece -> problema encoding JSON (verificar UTF-16LE)
- Si EA no genera senales -> verificar `publish.json` existe y es fresco (<180s)

## Flujo operativo diario
1. Abrir MT5 Deriv logueado (cuenta demo)
2. Verificar XAUUSD M15 abierto
3. Asegurar publish.py corriendo
4. EA modo 0 (sombra) = simulacion segura
5. Para modo real: InpMode=1, monitorear primer trade cercano

## Reset de cuenta demo
Si necesitas resetear cuenta demo en Deriv:
1. Login Deriv -> Cuenta -> Resetear contraseña demo
2. Actualizar .env con nuevas credenciales
3. Reiniciar publish.py
