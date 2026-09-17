//+------------------------------------------------------------------+
//|                                        MSNR_Advanced_AEU.mq5     |
//|                                  Agente Gema - Expert Advisor    |
//|                   Basado en Malaysian SNR + Liquidity Sweep      |
//+------------------------------------------------------------------+
#property copyright "Copyright 2026, Agente Gema"
#property link      "https://www.mql5.com"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
CTrade trade;

//--- Parámetros de Entrada
input group "--- Configuración de Gestión de Riesgo ---"
input double   InpRiskPercent     = 1.0;     // Riesgo por operación (% del Balance)
input double   InpRiskRewardRatio = 3.0;     // Relación Riesgo/Beneficio (R:R)
input double   InpMaxSpread       = 30;      // Spread máximo permitido (en puntos)

input group "--- Filtros de Sesión y Horario ---"
input bool     InpUseSessionFilter = true;   // Activar filtro por sesiones operativas
input int      InpStartHour        = 7;      // Hora de inicio (GMT)
input int      InpEndHour          = 17;     // Hora de finalización (GMT)

input group "--- Parámetros Técnicos MSNR ---"
input int      InpLookbackBars     = 100;    // Velas de análisis histórico para buscar picos A/V
input double   InpBufferPips       = 5.0;    // Margen de tolerancia (buffer) en puntos para el nivel

//--- Variables Globales
datetime g_last_bar_time = 0;
double   g_point_value   = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
{
   // Configuración inicial del símbolo y tipo de punto
   if(_Digits == 3 || _Digits == 5)
      g_point_value = _Point * 10;
   else
      g_point_value = _Point;

   trade.SetExpertMagicNumber(20260914);
   Print("Agente Gema: EA MSNR Inicializado correctamente para ", _Symbol);
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   Print("Agente Gema: EA MSNR Desconectado.");
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
{
   // 1. Validar nueva barra en M5 para evitar sobreprocesamiento por tick
   datetime current_bar_time = iTime(_Symbol, PERIOD_CURRENT, 0);
   if(current_bar_time == g_last_bar_time) return;
   g_last_bar_time = current_bar_time;
   
   // 2. Validar filtro de horario y sesiones
   if(InpUseSessionFilter && !CheckSessionTime()) return;

   // 3. Validar spread del broker
   long current_spread = SymbolInfoInteger(_Symbol, SYMBOL_SPREAD);
   if(current_spread > InpMaxSpread) return;

   // 4. Validar si ya existe una posición abierta para evitar sobreexposición
   if(HasOpenPosition()) return;

   // 5. Análisis de Estructura MSNR y Detección de Niveles Activos
   double snr_resistance = 0;
   double snr_support    = 0;
   FindMSNRLevels(snr_resistance, snr_support);

   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);

   // 6. Lógica de Ejecución de Venta (Rechazo en Resistencia MSNR + Liquidity Sweep)
   if(snr_resistance > 0 && ask >= (snr_resistance - InpBufferPips * g_point_value))
   {
      if(CheckLiquiditySweep(true)) // True para barrido alcista previo a venta
      {
         double sl = snr_resistance + (15 * g_point_value); // Stop Loss técnico ajustado
         double tp = ask - ((sl - ask) * InpRiskRewardRatio);
         double lot = CalculateLotSize(MathAbs(ask - sl));
         
         if(lot > 0)
         {
            trade.Sell(lot, _Symbol, bid, NormalizeDouble(sl, _Digits), NormalizeDouble(tp, _Digits), "MSNR Sell AEU");
            g_last_bar_time = current_bar_time;
         }
      }
   }

   // 7. Lógica de Ejecución de Compra (Rechazo en Soporte MSNR + Liquidity Sweep)
   if(snr_support > 0 && bid <= (snr_support + InpBufferPips * g_point_value))
   {
      if(CheckLiquiditySweep(false)) // False para barrido bajista previo a compra
      {
         double sl = snr_support - (15 * g_point_value);
         double tp = bid + ((bid - sl) * InpRiskRewardRatio);
         double lot = CalculateLotSize(MathAbs(bid - sl));
         
         if(lot > 0)
         {
            trade.Buy(lot, _Symbol, ask, NormalizeDouble(sl, _Digits), NormalizeDouble(tp, _Digits), "MSNR Buy AEU");
            g_last_bar_time = current_bar_time;
         }
      }
   }
}

//+------------------------------------------------------------------+
//| Función para identificar niveles MSNR basados en Cierres/Aperturas|
//+------------------------------------------------------------------+
void FindMSNRLevels(double &res_level, double &sup_level)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   int copied = CopyRates(_Symbol, PERIOD_CURRENT, 0, InpLookbackBars, rates);
   if(copied <= 0) return;

   // Lógica simplificada de detección de cuerpos (Cierre/Apertura)
   for(int i = 2; i < copied - 2; i++)
   {
      // Patrón 'A' (Resistencia: Cierre alcista seguido de apertura bajista)
      if(rates[i].close > rates[i].open && rates[i+1].open < rates[i].close)
      {
         res_level = rates[i].close;
         break;
      }
   }

   for(int i = 2; i < copied - 2; i++)
   {
      // Patrón 'V' (Soporte: Cierre bajista seguido de apertura alcista)
      if(rates[i].close < rates[i].open && rates[i+1].open > rates[i].close)
      {
         sup_level = rates[i].close;
         break;
      }
   }
}

//+------------------------------------------------------------------+
//| Validación de Barrido de Liquidez (MISS / Wick Sweep)            |
//+------------------------------------------------------------------+
bool CheckLiquiditySweep(bool is_sell_setup)
{
   MqlRates rates[];
   ArraySetAsSeries(rates, true);
   if(CopyRates(_Symbol, PERIOD_CURRENT, 1, 3, rates) <= 0) return false;

   if(is_sell_setup)
   {
      // La mecha supera el máximo anterior pero el cuerpo cierra por debajo (Rechazo)
      if(rates[0].high > rates[1].high && rates[0].close < rates[0].open)
         return true;
   }
   else
   {
      // La mecha perfora el mínimo anterior pero el cuerpo cierra por encima
      if(rates[0].low < rates[1].low && rates[0].close > rates[0].open)
         return true;
   }
   return false;
}

//+------------------------------------------------------------------+
//| Gestión de Riesgo: Cálculo dinámico de lotaje por % de cuenta    |
//+------------------------------------------------------------------+
double CalculateLotSize(double risk_distance_price)
{
   double account_balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double risk_amount     = account_balance * (InpRiskPercent / 100.0);
   double tick_value      = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tick_size       = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   
   if(risk_distance_price <= 0 || tick_value <= 0 || tick_size <= 0) return 0.0;

   double lot = (risk_amount / (risk_distance_price / tick_size)) / tick_value;
   
   double min_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double max_lot  = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double lot_step = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);

   if(lot < min_lot) return 0.0;
   lot = NormalizeDouble(MathFloor(lot / lot_step) * lot_step, 2);
   if(lot > max_lot) lot = max_lot;

   return lot;
}

//+------------------------------------------------------------------+
//| Filtro Horario de Sesiones                                       |
//+------------------------------------------------------------------+
bool CheckSessionTime()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   if(dt.hour >= InpStartHour && dt.hour < InpEndHour)
      return true;
   return false;
}

bool HasOpenPosition()
{
   for(int i=PositionsTotal()-1; i>=0; i--)
   {
      ulong ticket=PositionGetTicket(i);
      if(ticket>0 && PositionGetString(POSITION_SYMBOL)==_Symbol &&
         PositionGetInteger(POSITION_MAGIC)==20260914) return true;
   }
   return false;
}
