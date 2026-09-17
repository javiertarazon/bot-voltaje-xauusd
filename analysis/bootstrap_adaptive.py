from pathlib import Path
import numpy as np,pandas as pd
import sys
BASE=Path(__file__).resolve().parent.parent
def main():
    name=sys.argv[1] if len(sys.argv)>1 else 'trades_fluxov2_adaptive.csv'
    t=pd.read_csv(BASE/'data'/name); r=t.pnl.to_numpy(); rng=np.random.default_rng(20260917); sims=10000; finals=[]; dds=[]
    for _ in range(sims):
        x=rng.choice(r,len(r),replace=True); eq=x.cumsum(); finals.append(eq[-1]); dds.append((np.maximum.accumulate(eq)-eq).max())
    print(f'{name} n={len(r)} mean_total={np.mean(finals):.2f} p(total<0)={np.mean(np.array(finals)<0):.2%} p(DD>100)={np.mean(np.array(dds)>100):.2%} DD95={np.percentile(dds,95):.2f}')
    pd.DataFrame({'final':finals,'dd':dds}).to_csv(BASE/'reportes'/f'bootstrap_{Path(name).stem}.csv',index=False)
if __name__=='__main__':main()
