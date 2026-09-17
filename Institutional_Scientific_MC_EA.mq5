//+------------------------------------------------------------------+
//|                               Institutional_Scientific_MC_EA.mq5 |
//|                                  Copyright 2026, Agente Gema     |
//|                                  https://github.com/javiertarazon|
//+------------------------------------------------------------------+
#property copyright "Agente Gema - Cuantitativo MT5"
#property link      "https://github.com/javiertarazon"
#property version   "4.10"
#property description "EA Institucional Nativo MQL5 - Sin Dependencias Externe de Python"

#include <Trade\Trade.mqh>
#include <Trade\PositionInfo.mqh>

//--- ENUMERACIÓN DE PERFILES DE RIESGO
enum ENUM_PROFILE_MODE
  {
   PROFILE_CONSERVATIVE, // Conservador (0.5% Riesgo, SL Ajustado)
   PROFILE_MODERATE,     // Moderado (1.0% Riesgo, SL Estándar)
   PROFILE_AGGRESSIVE,   // Agresivo (2.0% Riesgo, R/R Extendido)
   PROFILE_CUSTOM        // Personalizado
  };

//--- INPUTS DEL SISTEMA
input group "=== Selector de Perfil ==="
input ENUM_PROFILE_MODE InpProfileMode = PROFILE_MODERATE; 

input group "=== Configuración Personalizada (Profile Custom) ==="
input double   InpCustomRiskPercent   = 1.0;     // % Riesgo por Operación
input double   InpCustomRR            = 1.5;     // Ratio Riesgo/Beneficio
input int      InpCustomATRPeriod     = 14;      // Período ATR
input double   InpCustomATRMult       = 1.5;     // Multiplicador ATR para Stop Loss

input group "=== Filtro Científico y Probabilístico ==="
input bool     InpUseLogisticFilter   = true;    // Activar Filtro Logístico Nativo
input double   InpProbThreshold       = 0.55;    // Umbral de Probabilidad Mínima (0.0 - 1.0)
input double   InpMinCLV              = 0.20;    // Close Location Value Mínimo (-1.0 a 1.0)
input double   InpMaxWickRatio        = 0.45;    // Rechazo de Mecha Máximo Permitido

input group "=== Control de Riesgo Institucional / Prop Firm ==="
input double   InpMaxDailyDrawdownPct = 4.0;     // Drawdown Máximo Diario Permisible (%)
input double   InpMaxSpreadPoints    = 30.0;    // Spread máximo
input int      InpStartHour          = 7;
input int      InpEndHour            = 18;
input ulong    InpMagicNumber         = 8882026;  // Número Mágico del Bot

//--- VARIABLES GLOBALES
CTrade         m_trade;
CPositionInfo  m_position;
int            m_handle_atr;
int            m_handle_ema_fast;
int            m_handle_ema_slow;
double         m_equity_start_day;
int            m_last_day;

// Coeficientes del Modelo Logístico Interno (Optimizados en MQL5)
const double   W_INTERCEPT= -0.5;
const double   W_EMA_DIFF = 12.5;
const double   W_CLV      = 1.8;

void WriteReadOnlySnapshot()
  {
   int h=FileOpen("fluxov2_mt5_snapshot.csv",FILE_WRITE|FILE_CSV|FILE_COMMON|FILE_SHARE_READ,',');
   if(h==INVALID_HANDLE) return;
   FileWrite(h,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS),
             AccountInfoInteger(ACCOUNT_LOGIN),AccountInfoString(ACCOUNT_SERVER),
             AccountInfoDouble(ACCOUNT_BALANCE),AccountInfoDouble(ACCOUNT_EQUITY),
             _Symbol,SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE),
             SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_VALUE),
             SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN),
             SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP),
             SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MAX),
             SymbolInfoInteger(_Symbol,SYMBOL_SPREAD));
   FileClose(h);
  }

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   m_trade.SetExpertMagicNumber(InpMagicNumber);
   
   // Inicialización de Indicadores Nativos en MT5
   m_handle_atr      = iATR(_Symbol, _Period, GetATRPeriod());
   m_handle_ema_fast = iMA(_Symbol, _Period, 9, 0, MODE_EMA, PRICE_CLOSE);
   m_handle_ema_slow = iMA(_Symbol, _Period, 21, 0, MODE_EMA, PRICE_CLOSE);

   if(m_handle_atr == INVALID_HANDLE || m_handle_ema_fast == INVALID_HANDLE || m_handle_ema_slow == INVALID_HANDLE)
     {
      Print("Error: No se pudieron crear los handles de los indicadores en MT5.");
      return(INIT_FAILED);
     }

   m_equity_start_day = AccountInfoDouble(ACCOUNT_EQUITY);
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   m_last_day = dt.day;
   WriteReadOnlySnapshot();

   Print("EA Autónomo MQL5 Inicializado. Perfil: ", EnumToString(InpProfileMode));
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   IndicatorRelease(m_handle_atr);
   IndicatorRelease(m_handle_ema_fast);
   IndicatorRelease(m_handle_ema_slow);
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   WriteReadOnlySnapshot();
   // 1. Control de Cambio de Día / Restablecimiento de Equidad
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.day != m_last_day)
     {
      m_last_day = dt.day;
      m_equity_start_day = AccountInfoDouble(ACCOUNT_EQUITY);
     }

   // 2. Control de Daily Drawdown
   double current_equity = AccountInfoDouble(ACCOUNT_EQUITY);
   double daily_loss_pct = ((m_equity_start_day - current_equity) / m_equity_start_day) * 100.0;
   
   if(daily_loss_pct >= InpMaxDailyDrawdownPct)
     {
      return; 
     }

   // 3. Ejecución Exclusiva al Cierre de Vela
   static datetime last_bar_time = 0;
   datetime current_bar_time = iTime(_Symbol, _Period, 0);
   if(current_bar_time == last_bar_time) return;
   last_bar_time = current_bar_time;

   MqlDateTime session_dt; TimeToStruct(TimeCurrent(), session_dt);
   if(session_dt.hour < InpStartHour || session_dt.hour >= InpEndHour) return;
   MqlTick tick; if(!SymbolInfoTick(_Symbol, tick)) return;
   if((tick.ask-tick.bid)/_Point > InpMaxSpreadPoints) return;

   // 4. Verificar si existe posición abierta
   if(HasOpenPosition()) return;

   // 5. Lectura de Velas e Indicadores
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, _Period, 1, 2, rates) < 2) return;

   double ema_fast[], ema_slow[], atr[];
   ArraySetAsSeries(ema_fast, true);
   ArraySetAsSeries(ema_slow, true);
   ArraySetAsSeries(atr, true);

   if(CopyBuffer(m_handle_ema_fast, 0, 1, 1, ema_fast) < 1 ||
      CopyBuffer(m_handle_ema_slow, 0, 1, 1, ema_slow) < 1 ||
      CopyBuffer(m_handle_atr, 0, 1, 1, atr) < 1) return;

   // 6. Cálculo Estructural de la Vela (CLV y Mechas)
   double range = rates[0].high - rates[0].low;
   if(range <= 0) return;

   double clv = ((rates[0].close - rates[0].low) - (rates[0].high - rates[0].close)) / range;
   double upper_wick = (rates[0].high - MathMax(rates[0].open, rates[0].close)) / range;
   double lower_wick = (MathMin(rates[0].open, rates[0].close) - rates[0].low) / range;

   // 7. Evaluador Probabilístico Logístico Sigmoide Nativo
   double ema_diff_norm = (ema_fast[0] - ema_slow[0]) / rates[0].close;
   double z = W_INTERCEPT + (W_EMA_DIFF * ema_diff_norm) + (W_CLV * clv);
   double win_probability = 1.0 / (1.0 + MathExp(-z)); 

   // 8. Carga de Parámetros de Riesgo
   double risk_percent = GetRiskPercent();
   double atr_mult     = GetATRMultiplier();
   double rr_ratio     = GetRewardRatio();

   // --- LÓGICA DE COMPRA (BUY)
   if(ema_fast[0] > ema_slow[0] && clv > InpMinCLV && lower_wick < InpMaxWickRatio)
     {
      if(!InpUseLogisticFilter || win_probability >= InpProbThreshold)
        {
         double sl_distance = atr[0] * atr_mult;
         double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
         double sl  = ask - sl_distance;
         double tp  = ask + (sl_distance * rr_ratio);
         double lot = CalculateLotSize(sl_distance, risk_percent);

         if(lot > 0 && m_trade.Buy(lot, _Symbol, ask, NormalizeDouble(sl,_Digits), NormalizeDouble(tp,_Digits), "Scientific EA Buy"))
            Print("BUY retcode=",m_trade.ResultRetcode());
        }
     }
   // --- LÓGICA DE VENTA (SELL)
   else if(ema_fast[0] < ema_slow[0] && clv < -InpMinCLV && upper_wick < InpMaxWickRatio)
     {
      if(!InpUseLogisticFilter || (1.0 - win_probability) >= InpProbThreshold)
        {
         double sl_distance = atr[0] * atr_mult;
         double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
         double sl  = bid + sl_distance;
         double tp  = bid - (sl_distance * rr_ratio);
         double lot = CalculateLotSize(sl_distance, risk_percent);

         if(lot > 0 && m_trade.Sell(lot, _Symbol, bid, NormalizeDouble(sl,_Digits), NormalizeDouble(tp,_Digits), "Scientific EA Sell"))
            Print("SELL retcode=",m_trade.ResultRetcode());
        }
     }
  }

//+------------------------------------------------------------------+
//| Funciones Auxiliares                                             |
//+------------------------------------------------------------------+
double GetRiskPercent()
  {
   switch(InpProfileMode)
     {
      case PROFILE_CONSERVATIVE: return 0.5;
      case PROFILE_MODERATE:     return 1.0;
      case PROFILE_AGGRESSIVE:   return 2.0;
      default:                   return InpCustomRiskPercent;
     }
  }

double GetRewardRatio()
  {
   switch(InpProfileMode)
     {
      case PROFILE_CONSERVATIVE: return 1.2;
      case PROFILE_MODERATE:     return 1.5;
      case PROFILE_AGGRESSIVE:   return 2.5;
      default:                   return InpCustomRR;
     }
  }

double GetATRMultiplier()
  {
   switch(InpProfileMode)
     {
      case PROFILE_CONSERVATIVE: return 2.0;
      case PROFILE_MODERATE:     return 1.5;
      case PROFILE_AGGRESSIVE:   return 1.0;
      default:                   return InpCustomATRMult;
     }
  }

int GetATRPeriod()
  {
   return (InpProfileMode == PROFILE_CUSTOM) ? InpCustomATRPeriod : 14;
  }

bool HasOpenPosition()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      if(m_position.SelectByIndex(i))
        {
         if(m_position.Symbol() == _Symbol && m_position.Magic() == InpMagicNumber)
            return true;
        }
     }
   return false;
  }

double CalculateLotSize(double sl_distance, double risk_pct)
  {
   if(sl_distance <= 0) return 0.0;

   double balance     = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount = balance * (risk_pct / 100.0);
   double tick_size   = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   double tick_value  = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double point       = SymbolInfoDouble(_Symbol, SYMBOL_POINT);

   if(tick_size == 0 || tick_value == 0) return 0.0;

   double points_at_risk = sl_distance / point;
   double lot_step       = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   double raw_lot        = risk_amount / (points_at_risk * (tick_value / (tick_size / point)));

   double min_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);

   double lot = MathFloor(raw_lot / lot_step) * lot_step;
   if(lot < min_lot) return 0.0;
   return MathMin(max_lot, lot);
  }
//+------------------------------------------------------------------+
