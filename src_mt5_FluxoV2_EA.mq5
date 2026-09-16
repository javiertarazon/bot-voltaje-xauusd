//+------------------------------------------------------------------+
//| FluxoV2_EA.mq5 - Ejecutor de senales FluxoV2 publicadas por Python|
//| Modo 0 = SOLO_LOG (prueba en sombra) | Modo 1 = TRADE             |
//+------------------------------------------------------------------+
#property strict
#property copyright "proyectos_javier"
#property version "1.00"

input int    InpMode          = 0;        // 0=SOLO_LOG 1=TRADE
input long   InpMagic         = 20260915; // magic
input int    InpMaxSpreadPts  = 30;       // spread maximo en puntos
input int    InpMaxTradesDia  = 3;        // max trades por dia
input double InpMaxLossDiaPct = 2.0;      // stop diario % balance
input int    InpMaxHoldMin    = 900;      // maxhold minutos (60 velas M15 = V2 backtest)
input int    InpFreshSeg      = 180;      // senal valida si epoch < N seg
input double InpBE_ATR        = 0.0;      // 0=BE desactivado (V2). >0 = mover SL a BE a +N*ATR
input double InpDDPausePct    = 10.0;     // pausa si DD % desde peak
input string InpSymbol        = "XAUUSD";

string SIGF = "fluxov2_signal.json";
string LOGF = "fluxov2_ea.log";
double g_peak = 0.0;
datetime g_lastbeat = 0;

int OnInit()
{
   EventSetTimer(5);
   g_peak = AccountInfoDouble(ACCOUNT_EQUITY);
   Log("EA INIT mode=" + (string)InpMode + " peak=" + DoubleToString(g_peak, 2));
   return(INIT_SUCCEEDED);
}
void OnDeinit(const int r) { EventKillTimer(); Log("EA DEINIT"); }

void Log(string s)
{
   int h = FileOpen(LOGF, FILE_READ|FILE_WRITE|FILE_TXT|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE) return;
   FileSeek(h, 0, SEEK_END);
   FileWrite(h, TimeToString(TimeGMT(), TIME_DATE|TIME_SECONDS) + " " + s);
   FileClose(h);
}
double JNum(const string j, const string key, double def)
{
   int p = StringFind(j, "\"" + key + "\"");
   if(p < 0) return def;
   p = StringFind(j, ":", p);
   if(p < 0) return def;
   int e = p + 1;
   while(e < StringLen(j) && StringGetCharacter(j, e) == ' ') e++;
   int end = e;
   while(end < StringLen(j))
   {
      ushort c = StringGetCharacter(j, end);
      if(c == ' ' || c == ',' || c == '}') break;
      end++;
   }
   string v = StringSubstr(j, e, end - e);
   if(v == "") return def;
   return StringToDouble(v);
}
string JStr(const string j, const string key)
{
   int p = StringFind(j, "\"" + key + "\"");
   if(p < 0) return "";
   p = StringFind(j, "\"", p + StringLen(key) + 3);
   int s = StringFind(j, "\"", p + 1);
   if(p < 0 || s < 0) return "";
   return StringSubstr(j, p + 1, s - p - 1);
}

string LeerSenal()
{
   int h = FileOpen(SIGF, FILE_READ|FILE_TXT|FILE_COMMON|FILE_SHARE_READ|FILE_SHARE_WRITE);
   if(h == INVALID_HANDLE) return "";
   string j = "", linea;
   while(!FileIsEnding(h)) { linea = FileReadString(h); j += linea; }
   FileClose(h);
   return j;
}

int TradesHoy()
{
   datetime ahora = TimeCurrent();
   datetime d0 = ahora - (ahora % 86400);
   if(!HistorySelect(d0, ahora + 3600)) return 999;
   int n = 0;
   for(int i = 0; i < HistoryDealsTotal(); i++)
   {
      ulong tk = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(tk, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetString(tk, DEAL_SYMBOL) != InpSymbol) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) == DEAL_ENTRY_IN) n++;
   }
   return n;
}

double PnlDia()
{
   datetime ahora = TimeCurrent();
   datetime d0 = ahora - (ahora % 86400);
   if(!HistorySelect(d0, ahora + 3600)) return 0.0;
   double s = 0.0;
   for(int i = 0; i < HistoryDealsTotal(); i++)
   {
      ulong tk = HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(tk, DEAL_MAGIC) != InpMagic) continue;
      if(HistoryDealGetString(tk, DEAL_SYMBOL) != InpSymbol) continue;
      if((ENUM_DEAL_ENTRY)HistoryDealGetInteger(tk, DEAL_ENTRY) == DEAL_ENTRY_OUT)
         s += HistoryDealGetDouble(tk, DEAL_PROFIT);
   }
   return s;
}
bool MiPosicion(ulong &ticket, double &entry, double &sl, double &tp, double &vol, datetime &topen)
{
   for(int i = 0; i < PositionsTotal(); i++)
   {
      if(PositionGetSymbol(i) != InpSymbol) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      ticket = (ulong)PositionGetInteger(POSITION_TICKET);
      entry  = PositionGetDouble(POSITION_PRICE_OPEN);
      sl     = PositionGetDouble(POSITION_SL);
      tp     = PositionGetDouble(POSITION_TP);
      vol    = PositionGetDouble(POSITION_VOLUME);
      topen  = (datetime)PositionGetInteger(POSITION_TIME);
      return true;
   }
   return false;
}

void ModificarSL(ulong ticket, double sl, double tp)
{
   MqlTradeRequest rq; MqlTradeResult rs;
   ZeroMemory(rq); ZeroMemory(rs);
   rq.action   = TRADE_ACTION_SLTP;
   rq.symbol   = InpSymbol;
   rq.position = ticket;
   rq.sl       = NormalizeDouble(sl, 2);
   rq.tp       = NormalizeDouble(tp, 2);
   if(!OrderSend(rq, rs)) Log("ERR modify " + (string)rs.retcode);
   else Log("SL_TO_BE ticket=" + (string)ticket + " sl=" + DoubleToString(sl, 2) + " ret=" + (string)rs.retcode);
}

void CerrarPos(ulong ticket, double vol, string motivo)
{
   MqlTradeRequest rq; MqlTradeResult rs;
   ZeroMemory(rq); ZeroMemory(rs);
   rq.action    = TRADE_ACTION_DEAL;
   rq.symbol    = InpSymbol;
   rq.position  = ticket;
   rq.volume    = vol;
   rq.type      = ORDER_TYPE_SELL;
   rq.deviation = 20;
   rq.magic     = InpMagic;
   rq.comment   = motivo;
   uint fm = (uint)SymbolInfoInteger(InpSymbol, SYMBOL_FILLING_MODE);
   rq.type_filling = ((fm & SYMBOL_FILLING_IOC) != 0) ? ORDER_FILLING_IOC : ORDER_FILLING_FOK;
   if(!OrderSend(rq, rs)) Log("ERR close " + (string)rs.retcode);
   else Log("CLOSE ticket=" + (string)ticket + " " + motivo + " ret=" + (string)rs.retcode);
}

void Abrir(double lot, double sl, double tp, const string j)
{
   MqlTick tick;
   if(!SymbolInfoTick(InpSymbol, tick)) { Log("ERR tick"); return; }
   double spread = (tick.ask - tick.bid) / SymbolInfoDouble(InpSymbol, SYMBOL_POINT);
   if(spread > InpMaxSpreadPts) { Log("SKIP spread=" + DoubleToString(spread, 0)); return; }
   if(TradesHoy() >= InpMaxTradesDia) { Log("SKIP max_trades_dia"); return; }
   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   if(PnlDia() <= -bal * InpMaxLossDiaPct / 100.0) { Log("SKIP max_loss_dia"); return; }
   double eq = AccountInfoDouble(ACCOUNT_EQUITY);
   if(eq > g_peak) g_peak = eq;
   if(g_peak > 0 && eq < g_peak * (1.0 - InpDDPausePct / 100.0)) { Log("SKIP dd_pause"); return; }

   if(InpMode == 0)
   {
      Log("SOLO_LOG senalBUY lote=" + DoubleToString(lot, 2) + " entry~" + DoubleToString(tick.ask, 2)
          + " sl=" + DoubleToString(sl, 2) + " tp=" + DoubleToString(tp, 2)
          + " z=" + DoubleToString(JNum(j, "z", 0), 2) + " p=" + DoubleToString(JNum(j, "p_up", 0), 3)
          + " mc=" + DoubleToString(JNum(j, "p_mc", 0), 2));
      return;
   }
   MqlTradeRequest rq; MqlTradeResult rs;
   ZeroMemory(rq); ZeroMemory(rs);
   rq.action    = TRADE_ACTION_DEAL;
   rq.symbol    = InpSymbol;
   rq.volume    = lot;
   rq.type      = ORDER_TYPE_BUY;
   rq.price     = tick.ask;
   rq.sl        = NormalizeDouble(sl, 2);
   rq.tp        = NormalizeDouble(tp, 2);
   rq.deviation = 20;
   rq.magic     = InpMagic;
   rq.comment   = "FluxoV2";
   uint fm = (uint)SymbolInfoInteger(InpSymbol, SYMBOL_FILLING_MODE);
   rq.type_filling = ((fm & SYMBOL_FILLING_IOC) != 0) ? ORDER_FILLING_IOC : ORDER_FILLING_FOK;
   if(!OrderSend(rq, rs)) Log("ERR buy " + (string)rs.retcode);
   else Log("BUY ticket=" + (string)rs.order + " deal=" + (string)rs.deal + " ret=" + (string)rs.retcode
            + " lote=" + DoubleToString(lot, 2) + " sl=" + DoubleToString(sl, 2) + " tp=" + DoubleToString(tp, 2));
}

void OnTimer()
{
   if(TimeGMT() - g_lastbeat >= 60)
   {
      g_lastbeat = TimeGMT();
      double eq = AccountInfoDouble(ACCOUNT_EQUITY);
      if(eq > g_peak) g_peak = eq;
      Log("BEAT eq=" + DoubleToString(eq, 2) + " peak=" + DoubleToString(g_peak, 2)
          + " tradesHoy=" + (string)TradesHoy() + " pnlDia=" + DoubleToString(PnlDia(), 2));
   }
   string j = LeerSenal();
   if(j == "") return;
   double ep = JNum(j, "epoch", 0);
   if(ep <= 0) { Log("senal_invalida_sin_epoch"); return; }
   if(TimeGMT() - (datetime)ep > InpFreshSeg) return; // senal vieja, silencio
   string act = JStr(j, "action");
   string sym = JStr(j, "symbol");
   if(sym != InpSymbol) { Log("SKIP simbolo=" + sym); return; }
   double atr = JNum(j, "atr", 0);
   double lot = JNum(j, "lot", 0);
   double sl  = JNum(j, "sl", 0);
   double tp  = JNum(j, "tp", 0);

   ulong tk; double entry, slp, tpp, vol; datetime topen;
   if(MiPosicion(tk, entry, slp, tpp, vol, topen))
   {
      MqlTick tick;
      if(SymbolInfoTick(InpSymbol, tick))
      {
         if(InpBE_ATR > 0 && atr > 0 && slp < entry && tick.bid >= entry + InpBE_ATR * atr)
         {
            if(InpMode == 1) ModificarSL(tk, entry + 2 * SymbolInfoDouble(InpSymbol, SYMBOL_POINT), tpp);
            else Log("SOLO_LOG BE ticket=" + (string)tk + " sl_actual=" + DoubleToString(slp, 2));
         }
      }
      if(TimeCurrent() - topen >= InpMaxHoldMin * 60)
      {
         if(InpMode == 1) CerrarPos(tk, vol, "maxhold");
         else Log("SOLO_LOG maxhold ticket=" + (string)tk);
      }
   }
   if(act == "BUY")
   {
      ulong tk2; double e2, s2, t2, v2; datetime t2o;
      if(MiPosicion(tk2, e2, s2, t2, v2, t2o)) { Log("SKIP ya_hay_posicion"); return; }
      if(lot <= 0 || sl <= 0 || tp <= 0 || atr <= 0) { Log("SKIP datos_incompletos"); return; }
      Abrir(lot, sl, tp, j);
   }
}
//+------------------------------------------------------------------+