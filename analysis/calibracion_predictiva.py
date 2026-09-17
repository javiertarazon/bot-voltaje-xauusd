"""Comprueba si las variables de Fluxo predicen retorno futuro fuera de muestra."""
from pathlib import Path
import sys
import numpy as np,pandas as pd
BASE=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(BASE))
from core.indicators import calcular_flujo,calcular_atr,calcular_bayes,calcular_atr_medio
def fit(X,y):
    w=np.zeros(X.shape[1]); b=0.;
    for _ in range(600):
        p=1/(1+np.exp(-np.clip(X@w+b,-30,30))); g=X.T@(p-y)/len(y); w-=.15*g; b-=.15*(p-y).mean()
    return w,b
def auc(y,p):
    order=np.argsort(p); ranks=np.argsort(order)+1; pos=y==1; neg=~pos
    return ((ranks[pos].sum()-pos.sum()*(pos.sum()+1)/2)/(pos.sum()*neg.sum()+1e-12)) if pos.any() and neg.any() else .5
def main():
    d=pd.read_csv(BASE/'data'/'xauusd_M15.csv'); d.time=pd.to_datetime(d.time,utc=True); f=calcular_flujo(d); a=calcular_atr(d); ar=a/(calcular_atr_medio(d)+1e-12); p=calcular_bayes(f.Q,f.z)
    X=pd.DataFrame({'z':f.z,'p':p,'atr_ratio':ar,'ret4':d.close.pct_change(4),'hour':np.sin(2*np.pi*d.time.dt.hour/24)}).replace([np.inf,-np.inf],np.nan).dropna(); y=(d.close.shift(-4)>d.close).astype(float).loc[X.index]; X=X.loc[y.index]; years=d.time.dt.year.loc[X.index]
    tr=years==2023; mu=X[tr].mean(); sd=X[tr].std().replace(0,1); z=(X-mu)/sd; w,b=fit(z[tr].to_numpy(),y[tr].to_numpy()); rows=[]
    for year in (2023,2024,2025,2026):
        q=years==year; prob=1/(1+np.exp(-np.clip(z[q].to_numpy()@w+b,-30,30))); yy=y[q].to_numpy(); rows.append({'year':year,'n':int(q.sum()),'auc':auc(yy,prob),'brier':float(np.mean((prob-yy)**2)),'wr_at_60':float(yy[prob>=.6].mean()) if (prob>=.6).any() else 0.0,'n_at_60':int((prob>=.6).sum())})
    out=pd.DataFrame(rows); print(out.to_string(index=False)); out.to_csv(BASE/'reportes'/'calibracion_predictiva.csv',index=False)
if __name__=='__main__':main()
