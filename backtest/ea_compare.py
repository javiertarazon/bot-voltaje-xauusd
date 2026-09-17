"""Backtest reproducible de MSNR y Scientific MC sobre velas M5.
No mezcla períodos: optimización y evaluación se ejecutan por ventanas temporales.
"""
from pathlib import Path
import itertools
import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent.parent

def metrics(trades):
    if not trades: return {"n":0,"pf":0.0,"exp":0.0,"total":0.0,"dd":0.0,"wr":0.0}
    r=np.array([x["pnl"] for x in trades],float); gp=r[r>0].sum(); gl=abs(r[r<=0].sum())
    eq=r.cumsum(); peak=np.maximum.accumulate(eq)
    return {"n":len(r),"pf":float(gp/(gl+1e-12)),"exp":float(r.mean()),"total":float(r.sum()),
            "dd":float((peak-eq).max()),"wr":float((r>0).mean())}

def load():
    d=pd.read_csv(BASE/"data"/"xauusd_M5.csv")
    d["time"]=pd.to_datetime(d["time"],utc=True)
    d=d.sort_values("time").drop_duplicates("time").reset_index(drop=True)
    return d.iloc[:5000].reset_index(drop=True)

def finish(d,i,side,entry,sl,tp,hold,cost):
    hi=d.high.to_numpy(); lo=d.low.to_numpy(); close=d.close.to_numpy()
    end=min(len(d)-1,i+hold); out=entry; reason="timeout"
    for j in range(i+1,end+1):
        h,l=float(hi[j]),float(lo[j])
        if side==1:
            if l<=sl: out=sl; reason="SL"; break
            if h>=tp: out=tp; reason="TP"; break
        else:
            if h>=sl: out=sl; reason="SL"; break
            if l<=tp: out=tp; reason="TP"; break
        out=float(close[j])
    return {"t_in":d.time.iloc[i],"t_out":d.time.iloc[min(j,end)],"idx_out":min(j,end),"pnl":side*(out-entry)-cost,"reason":reason}

def scientific(d, atr_mult=1.5, rr=1.5, threshold=.55, risk_cost=.16, hold=72):
    c=d.close.astype(float); ema9=c.ewm(span=9,adjust=False).mean().to_numpy(); ema21=c.ewm(span=21,adjust=False).mean().to_numpy()
    tr=pd.concat([d.high-d.low,(d.high-c.shift()).abs(),(d.low-c.shift()).abs()],axis=1).max(axis=1)
    atr=tr.rolling(14).mean()
    out=[]; i=30
    while i<len(d)-hold-1:
        if not 7<=d.time.iloc[i].hour<18: i+=1; continue
        r=float(d.high.iloc[i]-d.low.iloc[i]);
        if r<=0 or pd.isna(atr.iloc[i]): i+=1; continue
        clv=((d.close.iloc[i]-d.low.iloc[i])-(d.high.iloc[i]-d.close.iloc[i]))/r
        uw=(d.high.iloc[i]-max(d.open.iloc[i],d.close.iloc[i]))/r; lw=(min(d.open.iloc[i],d.close.iloc[i])-d.low.iloc[i])/r
        z=-.5+12.5*((ema9[i]-ema21[i])/c.iloc[i])+1.8*clv; p=1/(1+np.exp(-z)); a=float(atr.iloc[i])
        side=1 if ema9[i]>ema21[i] and clv>.20 and lw<.45 and p>=threshold else -1 if ema9[i]<ema21[i] and clv<-.20 and uw<.45 and 1-p>=threshold else 0
        if not side: i+=1; continue
        e=float(c.iloc[i]); dist=a*atr_mult; sl=e-side*dist; tp=e+side*dist*rr
        out.append(finish(d,i,side,e,sl,tp,hold,risk_cost)); i=out[-1]["idx_out"]+1
    return out

def msnr(d, buffer=.5, sl_atr=1.0, rr=3.0, lookback=100, cost=.16, hold=72):
    tr=pd.concat([d.high-d.low,(d.high-d.close.shift()).abs(),(d.low-d.close.shift()).abs()],axis=1).max(axis=1); atr=tr.rolling(14).mean(); out=[]
    # Precalcular niveles para evitar reconstruir DataFrames en cada vela.
    res_sig=d.close.where((d.close>d.open)&(d.open.shift(-1)<d.close)); sup_sig=d.close.where((d.close<d.open)&(d.open.shift(-1)>d.close))
    res=res_sig.ffill(); sup=sup_sig.ffill(); last_res=np.full(len(d),np.nan); last_sup=np.full(len(d),np.nan)
    rv=sv=np.nan
    for k in range(len(d)):
        if not pd.isna(res_sig.iloc[k]): rv=float(res_sig.iloc[k])
        if not pd.isna(sup_sig.iloc[k]): sv=float(sup_sig.iloc[k])
        last_res[k]=rv; last_sup[k]=sv
    i=max(lookback,20)
    while i<len(d)-hold-1:
        if not 7<=d.time.iloc[i].hour<17: i+=1; continue
        if pd.isna(last_res[i]) or pd.isna(last_sup[i]) or pd.isna(atr.iloc[i]): i+=1; continue
        r0=d.iloc[i]; prev=d.iloc[i-1]; side=0; level=0
        if float(r0.high)>float(prev.high) and r0.close<r0.open and abs(float(r0.close)-last_res[i])<=buffer: side=-1; level=last_res[i]
        elif float(r0.low)<float(prev.low) and r0.close>r0.open and abs(float(r0.close)-last_sup[i])<=buffer: side=1; level=last_sup[i]
        if not side: i+=1; continue
        e=float(r0.close); dist=max(float(atr.iloc[i])*sl_atr,0.15); sl=level-side*dist; tp=e+side*(abs(sl-e)*rr)
        out.append(finish(d,i,side,e,sl,tp,hold,cost)); i=out[-1]["idx_out"]+1
    return out

def run():
    d=load(); results=[]
    # Parámetros optimizados únicamente en train; el resto es evaluación fuera de muestra.
    # Este archivo M5 contiene 2026-01 a 2026-09: usamos corte temporal 60/40.
    cut=d.time.iloc[int(len(d)*0.60)]; train=d[d.time<cut]; test=d[d.time>=cut]
    best_s=max(((metrics(scientific(train,am,rr,th)),am,rr,th) for am,rr,th in itertools.product([1.0,1.5],[1.2,1.5],[.55,.60])),key=lambda x:x[0]["total"]-x[0]["dd"]*.5)
    best_m=max(((metrics(msnr(train,ba,sa,rr)),ba,sa,rr) for ba,sa,rr in itertools.product([.5,1.0],[1.0,1.5],[2.0,3.0])),key=lambda x:x[0]["total"]-x[0]["dd"]*.5)
    for name,fn,args in [("Scientific",scientific,best_s[1:]),("MSNR",msnr,best_m[1:])]:
        for label,x in [("train",train),("test",test)]: results.append({"strategy":name,"period":label,**metrics(fn(x,*args)),"params":str(args)})
    out=pd.DataFrame(results); print(out.to_string(index=False)); out.to_csv(BASE/"reportes"/"ea_compare_walkforward.csv",index=False)
if __name__=="__main__": run()
