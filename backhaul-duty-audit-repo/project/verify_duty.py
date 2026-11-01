"""Independent LP timing checks, exhaustive joint checks, and regression tests."""
import duty_tradeoff as x
import experiment as e
import numpy as np
from scipy.optimize import linprog
import itertools,random,math,json

def lp_duty(jobs,order):
 # Variables: departure, service start at each pickup, final depot arrival.
 k=len(order);c=np.zeros(k+2);c[0]=-1;c[-1]=1
 A=[];b=[]
 def con(terms,rhs):
  row=np.zeros(k+2)
  for i,v in terms.items():row[i]=v
  A.append(row);b.append(rhs)
 con({0:1,1:-1},-e.minutes(e.dist(e.COLLECTOR_DEPOT,jobs[order[0]]['pos'])))
 for v in range(k-1):con({v+1:1,v+2:-1},-e.HANDLING-e.minutes(e.dist(jobs[order[v]]['pos'],jobs[order[v+1]]['pos'])))
 con({k:1,k+1:-1},-e.HANDLING-e.minutes(e.dist(jobs[order[-1]]['pos'],e.RECYCLER))-e.UNLOAD-e.minutes(e.dist(e.RECYCLER,e.COLLECTOR_DEPOT)))
 bounds=[(0,None)]+[(jobs[j]['ready'],jobs[j]['due']) for j in order]+[(0,e.HORIZON)]
 return linprog(c,A_ub=A,b_ub=b,bounds=bounds,method='highs')

# Fixed timing hand checks: waiting can be moved before departure, not dropped inside duty.
j=[dict(pos=(5,5),weight=1,ready=100,due=200)]
r=x.collector(j,[0]);assert r and math.isclose(r['duty'],150)
# Depot -> pickup zero, pickup -> recycler60min, unload15, return60, pickup15 =150.
assert math.isclose(r['start'],100)
# Intra-route waiting cannot always be eliminated.
rng=random.Random(20261029);lp_checks=0
for seed in range(30):
 t,j,d=e.generate(seed,20,120,20)
 for z in range(30):
  order=rng.sample(range(10),rng.randint(1,6))
  if sum(j[v]['weight'] for v in order)>e.COLLECTOR_CAP+1e-9:continue
  r=x.collector(j,order);lp=lp_duty(j,order)
  assert (r is not None)==lp.success,(seed,order,r,lp.message)
  if r:assert abs(r['duty']-lp.fun)<1e-6,(seed,order,r,lp.fun)
  lp_checks+=1
# Exhaustively enumerate small truck assignments + residual collector partitions.
def partitions(mask,opts):
 if not mask:yield (0,0);return
 bit=mask&-mask
 for p,rs in opts.items():
  if p&bit and p&mask==p:
   for r in rs:
    for km,du in partitions(mask^p,opts):yield (r['km']+km,r['duty']+du)
checks=0
for seed in range(15):
 t,j,d=e.generate(seed,20,120,20);t=t[:3];j=j[:4];opts=x.all_routes(j,3)
 pairs=[[e.backhaul(v,z,d) for z in j] for v in t]
 for w,limit in [(0,None),(30,None),(None,None),(0,60)]:
  b,r=x.solve(t,j,d,opts,w,limit)
  def key(km,du):return (du,km) if w is None else (km+w*du/60,du,km)
  best=None
  for a in itertools.product(range(-1,4),repeat=3):
   js=[v for v in a if v>=0]
   if len(js)!=len(set(js)):continue
   ps=[pairs[i][v] for i,v in enumerate(a) if v>=0]
   if any(p is None or (limit is not None and p['extra_minutes']>limit+1e-8) for p in ps):continue
   remaining=15
   for v in js:remaining^=1<<v
   for km,du in partitions(remaining,opts):
    k=key(km+sum(p['delta'] for p in ps),du+sum(p['extra_minutes'] for p in ps))
    if best is None or k<best:best=k
  direct=sum(e.dist(v['end'],v['depot']) for v in t)
  actual=key(r['km']-direct,r['duty_minutes']-e.minutes(direct))
  assert np.allclose(actual,best,atol=1e-7),(seed,w,actual,best)
  checks+=1
# Full-size regression to existing distance solver and collector feasibility.
regressions=0
for seed in range(20):
 t,j,d=e.generate(seed,20,120,20);opts=x.all_routes(j,6)
 b,r=x.solve(t,j,d,opts,0)
 old=e.evaluate(t,j,d,max_jobs=6)
 assert abs(b['km']-old['separate']['total_km'])<1e-7
 assert abs(r['km']-old['joint']['total_km'])<1e-7
 regressions+=2
print(json.dumps(dict(status='PASS',independent_route_LP_checks=lp_checks,exhaustive_small_joint_checks=checks,full_size_distance_regressions=regressions)))
