"""Fixed-design sensitivity to request count, payload and two-pickup returns."""
import experiment as e
import itertools,random,json,csv,statistics,math
from pathlib import Path
R=Path(__file__).parent

def multi(t,jobs,order,d):
 if not t['compatible'] or sum(jobs[k]['weight'] for k in order)>t['capacity']+1e-9:return None
 pos=t['end'];clock=t['available'];km=0
 for k in order:
  y=jobs[k];leg=math.dist(pos,y['pos']);km+=leg;clock=max(clock+e.minutes(leg),y['ready'])
  if clock>y['due']+1e-9:return None
  clock+=e.HANDLING;pos=y['pos']
 leg=math.dist(pos,e.RECYCLER);km+=leg;clock+=e.minutes(leg)+e.UNLOAD
 leg=math.dist(e.RECYCLER,t['depot']);km+=leg;clock+=e.minutes(leg)
 delta=km-math.dist(t['end'],t['depot'])
 if clock>e.HORIZON+1e-9 or delta>d+1e-9:return None
 return delta

def multi_exact(t,j,d,fallback,maxpick):
 opts=[]
 for truck in t:
  row={}
  for n in range(1,maxpick+1):
   for sub in itertools.combinations(range(len(j)),n):
    vs=[x for order in itertools.permutations(sub) if (x:=multi(truck,j,order,d)) is not None]
    if vs:row[sum(1<<k for k in sub)]=min(vs)
  opts.append(row)
 dp={0:0}
 for row in opts:
  nxt=dict(dp)
  for used,value in dp.items():
   for mask,delta in row.items():
    if not used&mask:
     new=used|mask;nxt[new]=min(nxt.get(new,math.inf),value+delta)
  dp=nxt
 full=(1<<len(j))-1
 return sum(math.dist(x['end'],x['depot']) for x in t)+min(v+fallback[full^m] for m,v in dp.items())
rows=[]
for seed in range(20):
 t,j,d=e.generate(seed,20,120,20)
 for cap in [2,6]:
  fallback,_,_=e.collector_tables(j,max_jobs=cap)
  single=e.evaluate(t,j,d,max_jobs=cap)['joint']['total_km'];one=multi_exact(t,j,d,fallback,1);two=multi_exact(t,j,d,fallback,2)
  assert abs(single-one)<1e-8 and two<=one+1e-8
  base=sum(math.dist(x['end'],x['depot']) for x in t)+fallback[-1]
  rows.append(dict(test='return_pickup_count',seed=seed,value=cap,baseline_km=base,single_km=one,joint_km=two,saving_pct=100*(base-two)/base,baseline_routes=None,joint_routes=None))
# Vary jobs while retaining 10 returning trucks and first 9-10 original jobs.
# Additional jobs use separate seeded RNG; no seed chosen for a favorable result.
for seed in range(20):
 t,j,d=e.generate(seed,20,120,20);rng=random.Random(50000+seed)
 for _ in range(2):
  ready=rng.uniform(30,120);j.append(dict(pos=(20+rng.uniform(-10,10),20+rng.uniform(-10,10)),weight=rng.uniform(.5,2.5),ready=ready,due=ready+120))
 for n in [9,10,11,12]:
  for cap in [2,3,4]:
   r=e.evaluate(t,j[:n],d,max_jobs=cap);base=r['separate']['total_km'];v=r['joint']['total_km']
   rows.append(dict(test='job_count',seed=seed,value=f'{n}:{cap}',baseline_km=base,single_km=None,joint_km=v,saving_pct=100*(base-v)/base,baseline_routes=len(r['separate']['collector_routes']),joint_routes=len(r['joint']['collector_routes'])))
old=e.COLLECTOR_CAP
for tonnes in [3,6,12]:
 e.COLLECTOR_CAP=tonnes
 for seed in range(20):
  t,j,d=e.generate(seed,20,120,20);r=e.evaluate(t,j,d,max_jobs=6);b=r['separate']['total_km'];v=r['joint']['total_km']
  rows.append(dict(test='collector_tonnes_at_cap6',seed=seed,value=tonnes,baseline_km=b,single_km=None,joint_km=v,saving_pct=100*(b-v)/b,baseline_routes=len(r['separate']['collector_routes']),joint_routes=len(r['joint']['collector_routes'])))
e.COLLECTOR_CAP=old
with (R/'structural_checks.csv').open('w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
s=[]
for test,value in dict.fromkeys((r['test'],r['value']) for r in rows):
 v=[r for r in rows if r['test']==test and r['value']==value]
 s.append(dict(test=test,value=value,n=len(v),mean_saving_pct=statistics.mean(r['saving_pct'] for r in v),zero=sum(abs(r['saving_pct'])<1e-8 for r in v),mean_baseline_routes=statistics.mean(r['baseline_routes'] for r in v) if v[0]['baseline_routes'] is not None else None,mean_joint_routes=statistics.mean(r['joint_routes'] for r in v) if v[0]['joint_routes'] is not None else None))
(R/'structural_checks.json').write_text(json.dumps(s,indent=2));print(json.dumps(s,indent=2))