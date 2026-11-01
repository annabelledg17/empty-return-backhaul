import pareto_duty as p
import duty_tradeoff as x
import experiment as e
from verify_duty import partitions
import itertools,numpy as np,json
checks=0
for seed in range(20):
 t,j,d=e.generate(seed,20,120,20);t=t[:3];j=j[:4];opts=x.all_routes(j,3)
 for limit in [None,60]:
  base,front=p.frontier(t,j,d,opts,limit)
  pairs=[[e.backhaul(v,z,d) for z in j] for v in t];all_labels=[]
  for a in itertools.product(range(-1,4),repeat=3):
   js=[v for v in a if v>=0]
   if len(js)!=len(set(js)):continue
   ps=[pairs[i][v] for i,v in enumerate(a) if v>=0]
   if any(v is None or (limit is not None and v['extra_minutes']>limit+1e-8) for v in ps):continue
   mask=15
   for q in js:mask^=1<<q
   for km,du in partitions(mask,opts):all_labels.append((km+sum(v['delta'] for v in ps),du+sum(v['extra_minutes'] for v in ps),None))
  want=p.prune(all_labels);direct=sum(e.dist(v['end'],v['depot']) for v in t)
  got=[(v['km']-direct,v['duty_minutes']-e.minutes(direct)) for v in front]
  assert len(want)==len(got)
  assert np.allclose([v[:2] for v in want],got,atol=1e-7)
  for v in front:x.verify(t,j,d,v,limit)
  checks+=1
print(json.dumps(dict(status='PASS',complete_frontiers_compared_to_exhaustive=checks)))
