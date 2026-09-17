"""Gate de aceptación: falla si la candidata no es robusta por período."""
from pathlib import Path
import pandas as pd
BASE=Path(__file__).resolve().parent
def main():
    p=BASE/'reportes'/'fluxov2_adaptive_years.csv'
    t=pd.read_csv(p); complete=t[t.n>=30]
    failures=t[(t.n<30)|(t.pf<1.05)|(t.exp<=0)]
    print(t.to_string(index=False))
    if len(failures):
        print('\nGATE=FAIL'); print(failures.to_string(index=False)); raise SystemExit(2)
    print('\nGATE=PASS')
if __name__=='__main__':main()
