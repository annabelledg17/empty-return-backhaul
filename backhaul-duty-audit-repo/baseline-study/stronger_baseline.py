"""Predeclared extension: same 20 base seeds, collectors up to 4/5/6 jobs.
Not added to the original 140-world experiment count. Synthetic, not road data.
"""
import experiment as e
import csv,json,statistics,time
from pathlib import Path
R=Path(__file__).parent
rows=[];start=time.time()
for seed in range(20):
 t,j,d=e.generate(seed,20,120,20)
 prev=None
 for cap in [3,4,5,6]:
  r=e.evaluate(t,j,d,max_jobs=cap);b=r['separate']['total_km']
  if prev is not None:
   assert b<=prev['separate']['total_km']+1e-8
   assert r['joint']['total_km']<=prev['joint']['total_km']+1e-8
  for method,v in r.items():
   rows.append(dict(seed=seed,cap=cap,method=method,total_km=v['total_km'],matched=v['matched'],saving_pct=100*(b-v['total_km'])/b,extra_truck_minutes=v['extra_truck_minutes']))
  prev=r
 print('finished seed',seed,flush=True)
with (R/'stronger_baseline.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
s=[]
for cap in [3,4,5,6]:
 for method in ['separate','greedy','joint']:
  v=[r for r in rows if r['cap']==cap and r['method']==method]
  s.append(dict(cap=cap,method=method,mean_total_km=statistics.mean(x['total_km'] for x in v),mean_saving_pct=statistics.mean(x['saving_pct'] for x in v),zero_worlds=sum(abs(x['saving_pct'])<1e-8 for x in v)))
(R/'stronger_baseline.json').write_text(json.dumps(s,indent=2)+'\
')
print(json.dumps(s,indent=2));print('elapsed seconds',time.time()-start)