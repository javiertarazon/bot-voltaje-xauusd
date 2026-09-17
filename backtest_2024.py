#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Backtest 2024 XAUUSD M15 — FlujoV2 — USD/%, costes reales Deriv.
Capital inicial 1000 USD. Sin datos M5 2024 (no disponibles en data/).
"""
from __future__ import annotations
import csv, math, os, sys, datetime
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA_M15 = os.path.join(HERE, "data", "xauusd_M15.csv")

# costes reales Deriv (verificados en cert_costs.txt)
BNY_FIX_SPREAD_PTS = 0.0
COST_SLIP_PTS = 5.0
SWAP_LONG_PER_NIGHT_USD = -45.0

def is_swap_triple_night(ts):
    return ts.weekday() in (1,2)

def load_m15():
    rows=[]
    with open(DATA_M15, newline="", encoding="utf-8") as f:
        r=csv.DictReader(f)
        for row in r:
            ts_str=row["time"].split(".")[0]
            ts=datetime.datetime.fromisoformat(ts_str)
            if ts.hour<7 or ts.hour>=20:
                continue
            rows.append({
                "ts":ts,"o":float(row["open"]),"h":float(row["high"]),
                "l":float(row["low"]),"c":float(row["close"]),
                "vol":int(row["tick_volume"]),"spread_real":float(row["spread"]),
            })
    return [r for r in rows if r["ts"].year==2024]

def atr_value(rows, idx, n=14):
    ws=rows[max(0,idx-n):idx+1]
    trs=[max(r["h"],prev["c"])-min(r["l"],prev["c"]) for r,prev in zip(ws[1:],ws[:-1])]
    if not trs: return 0.0
    return sum(trs)/len(trs)

def compute_flujo_simple(r, atr):
    if atr<=0: return 0.0,0.0,0.0
    prev4=r["c"]-r["o"]
    return prev4/atr, prev4*1.0, atr

def bayes_simple(prior, llr):
    odds=prior/(1-prior)*math.exp(llr)
    return odds/(1+odds)

def metrics(trades, equilibrium, dd_series, d0=1000.0):
    n=len(trades)
    wins=[t for t in trades if t["pnl"]>0]
    wins_usd=sum(t["pnl"] for t in wins)
    loses=[t for t in trades if t["pnl"]<=0]
    loses_usd=sum(t["pnl"] for t in loses)
    gross=equilibrium[-1]-d0
    pf=wins_usd/abs(loses_usd) if loses_usd!=0 else float("inf")
    expo=(wins_usd+loses_usd)/n if n>0 else 0.0
    winrate=len(wins)/n if n>0 else 0
    total_ret=(equilibrium[-1]-d0)/d0
    ddmax=dd_series[-1] if dd_series else 0
    max_dd_pct=ddmax/d0 if d0 else 0
    calmar=(equilibrium[-1]-d0)/(ddmax) if ddmax>0 else float("inf")
    avg_win_usd=sum(t["pnl"] for t in wins)/len(wins) if wins else 0
    avg_lose_usd=(sum(t["pnl"] for t in loses)/len(loses)) if loses else 0
    pull=sum(t["pnl"] for t in trades)/n if n else 0
    payoff=(avg_win_usd/avg_lose_usd) if avg_lose_usd!=0 else 0
    return dict(n=n,winrate=winrate,matlabroot=len(wins),losers=len(loses),
                wins_usd=wins_usd,loses_usd=loses_usd,pnl_total=wins_usd+loses_usd,
                pf=pf,expo=expo,winrate_pct=winrate*100,total_ret=total_ret,
                ddmax=ddmax,max_dd_pct=max_dd_pct,calmar=calmar,
                avg_win=avg_win_usd,avg_lose=avg_lose_usd,payoff=payoff,
                final=d0+(wins_usd+loses_usd) if trades else d0, equity=equilibrium, dd=dd_series)
