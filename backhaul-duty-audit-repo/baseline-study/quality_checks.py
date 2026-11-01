"""Independent algebra/time checks and new fixed-seed sensitivity, no field calibration."""
import experiment as e
import math,itertools,json,csv,statistics,time
from pathlib import Path
R=Path(__file__).parent

def audit(t,j,d,r,cap):
 seen=[];truck_used=[];km=sum(math.dist(x['end'],x['depot']) for x in t)
 for i,k in r['assignment']:
  x,y=t[i],j[k];a=math.dist(x['end'],y['pos']);b=math.dist(y['pos'],e.RECYCLER);c=math.dist(e.RECYCLER,x['depot']);direct=math.dist(x['end'],x['depot'])
  assert x['compatible'] and y['weight']<=x['capacity']+1e-9
  assert a+b+c-direct<=d+1e-9
  start=max(x['available']+a/e.SPEED*60,y['ready'])
  assert start<=y['due']+1e-9
  assert start+e.HANDLING+b/e.SPEED*60+e.UNLOAD+c/e.SPEED*60<=e.HORIZON+1e-9
  km+=a+b+c-direct;seen.append(k);truck_used.append(i)
 for route in r['collector_routes']:
  ids=route['order'];assert len(ids)<=cap and sum(j[k]['weight'] for k in ids)<=e.COLLECTOR_CAP+1e-9
  pos=e.COLLECTOR_DEPOT;clock=0;routekm=0
  for k in ids:
   leg=math.dist(pos,j[k]['pos']);routekm+=leg;clock=max(clock+leg/e.SPEED*60,j[k]['ready']);assert clock<=j[k]['due']+1e-9
   clock+=e.HANDLING;pos=j[k]['pos'];seen.append(k)
  leg=math.dist(pos,e.RECYCLER);routekm+=leg;clock+=leg/e.SPEED*60+e.UNLOAD
  leg=math.dist(e.RECYCLER,e.COLLECTOR_DEPOT);routekm+=leg;clock+=leg/e.SPEED*60
  assert clock<=e.HORIZON+1e-9 and abs(routekm-route['km'])<1e-8;km+=routekm
 assert sorted(seen)==list(range(len(j))) and len(set(truck_used))==len(truck_used) and abs(km-r['total_km'])<1e-8

# Independent MILP formulation: pair/collector-route binaries; each job exactly once,
# each truck at most once. Only test dependency, not needed for the submitted solver.
from scipy.optimize import milp,Bounds,LinearConstraint
import numpy as np
milp_cases=0
for seed in range(10):
 t,j,d=e.generate(seed,20,120,20)
 for cap in [1,2,3,6]:
  result=e.evaluate(t,j,d,max_jobs=cap)
  cost,_,opts=e.collector_tables(j,max_jobs=cap)
  cols=[];obj=[]
  for i,x in enumerate(t):
   for k,y in enumerate(j):
    p=e.backhaul(x,y,d)
    if p is None:continue
    col=np.zeros(20);col[k]=1;col[10+i]=1;cols.append(col);obj.append(p['delta'])
  for mask,r in opts.items():
   col=np.zeros(20)
   for k in range(10):col[k]=int(bool(mask&(1<<k)))
   cols.append(col);obj.append(r['km'])
  v=milp(np.array(obj),integrality=np.ones(len(obj)),bounds=Bounds(0,1),constraints=LinearConstraint(np.array(cols).T,np.r_[np.ones(10),np.zeros(10)],np.ones(20)),options={'time_limit':30})
  assert v.success,v.message
  target=sum(math.dist(x['end'],x['depot']) for x in t)+v.fun
  assert abs(target-result['joint']['total_km'])<1e-6
  for r in result.values():audit(t,j,d,r,cap)
  milp_cases+=1
print('PASS independent full-size MILP objectives:',milp_cases)
# Fixed holdout seeds declared here, not chosen after results. Broad descriptive check.
rows=[]
for seed in range(100,200):
 t,j,d=e.generate(seed,20,120,20)
 for cap in [1,2,3,6]:
  r=e.evaluate(t,j,d,max_jobs=cap);b=r['separate']['total_km']
  for method,v in r.items():
   audit(t,j,d,v,cap);rows.append(dict(setting='holdout',seed=seed,cap=cap,method=method,total_km=v['total_km'],saving_pct=100*(b-v['total_km'])/b))
# No >6 group is possible by payload for original base seeds: a certificate,
# not an expensive rerun of every infeasible permutation.
cert=[]
for seed in range(20):
 t,j,d=e.generate(seed,20,120,20);lightest7=sum(sorted(x['weight'] for x in j)[:7]);assert lightest7>e.COLLECTOR_CAP
 cert.append(dict(seed=seed,lightest_seven_tonnes=lightest7))
(R/'cap6_payload_certificate.json').write_text(json.dumps(cert,indent=2))
# Layout sensitivity, same base seeds, only depot/recycler changed.
old=(e.COLLECTOR_DEPOT,e.RECYCLER)
layouts=[('central', (20,20),(20,20)),('reversed',(35,5),(5,5)),('opposite_corners',(0,0),(40,40))]
for name,depot,recycler in layouts:
 e.COLLECTOR_DEPOT,e.RECYCLER=depot,recycler
 for seed in range(20):
  t,j,d=e.generate(seed,20,120,20);r=e.evaluate(t,j,d,max_jobs=6);b=r['separate']['total_km']
  for method,v in r.items():
   audit(t,j,d,v,6);rows.append(dict(setting=name,seed=seed,cap=6,method=method,total_km=v['total_km'],saving_pct=100*(b-v['total_km'])/b))
e.COLLECTOR_DEPOT,e.RECYCLER=old
with (R/'quality_sensitivity.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
s=[]
for setting,cap in dict.fromkeys((r['setting'],r['cap']) for r in rows):
 v=[r for r in rows if r['setting']==setting and r['cap']==cap and r['method']=='joint']
 s.append(dict(setting=setting,cap=cap,n=len(v),mean_saving_pct=statistics.mean(r['saving_pct'] for r in v),zero=sum(abs(r['saving_pct'])<1e-8 for r in v),min_saving=min(r['saving_pct'] for r in v),max_saving=max(r['saving_pct'] for r in v)))
(R/'quality_sensitivity.json').write_text(json.dumps(s,indent=2));print(json.dumps(s,indent=2));print('PASS all new route/time/capacity checks using separate arithmetic')