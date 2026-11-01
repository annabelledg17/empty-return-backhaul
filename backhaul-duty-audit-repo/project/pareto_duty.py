"""Exact nondominated km/duty labels; coupled no-total-duty-increase constraint.
No monetary calibration; routes retain both criteria, unlike scalar shortest-km tables.
"""
import duty_tradeoff as x
import experiment as e
from pathlib import Path
import json,time,csv,statistics
R=Path(__file__).parent

def prune(labels):
 # (km,duty,payload). Sorted scan keeps strict duty improvements only.
 labels.sort(key=lambda z:(z[0],z[1]));out=[];best=float('inf')
 for l in labels:
  if l[1]<best-1e-8:out.append(l);best=l[1]
 return out

def frontier(t,j,d,opts,limit=None):
 n=len(j);full=(1<<n)-1
 opt={p:prune([(r['km'],r['duty'],[r]) for r in rs]) for p,rs in opts.items()}
 coll=[None]*(1<<n);coll[0]=[(0,0,[])]
 for m in range(1,1<<n):
  bit=m&-m;labels=[]
  for p,rs in opt.items():
   if not p&bit or p&m!=p:continue
   for a,b,r in rs:
    for c,v,s in coll[m^p]:labels.append((a+c,b+v,r+s))
  coll[m]=prune(labels)
 pairs=[[e.backhaul(v,z,d) for z in j] for v in t];dp={0:[(0,0,[])]}
 for i in range(len(t)):
  nxt={m:list(ls) for m,ls in dp.items()}
  for m,ls in dp.items():
   for q,p in enumerate(pairs[i]):
    if p is None or m&(1<<q) or (limit is not None and p['extra_minutes']>limit+1e-8):continue
    a=m|(1<<q);nxt.setdefault(a,[])
    for km,du,ass in ls:nxt[a].append((km+p['delta'],du+p['extra_minutes'],ass+[(i,q)]))
  dp={m:prune(ls) for m,ls in nxt.items()}
 labels=[]
 for m,ls in dp.items():
  for km,du,a in ls:
   for ck,cd,rs in coll[full^m]:labels.append((km+ck,du+cd,dict(assignments=a,routes=rs)))
 direct=sum(e.dist(v['end'],v['depot']) for v in t)
 def fmt(l):
  km,du,p=l;extra=[pairs[i][q]['extra_minutes'] for i,q in p['assignments']]
  return dict(km=direct+km,duty_minutes=e.minutes(direct)+du,**p,matched=len(extra),extra_delivery_minutes=sum(extra),max_delivery_extra=max(extra,default=0),collector_trips=len(p['routes']),collector_duty_minutes=sum(r['duty'] for r in p['routes']))
 base=min(coll[full],key=lambda v:(v[0],v[1]));base=(base[0],base[1],dict(assignments=[],routes=base[2]))
 return fmt(base),[fmt(l) for l in prune(labels)]

def main(seeds=range(20),prefix='pareto_duty'):
 rows=[];details={};start=time.time()
 for seed in seeds:
  t,j,d=e.generate(seed,20,120,20);opts=x.all_routes(j,6)
  for limit in [None,60]:
   base,front=frontier(t,j,d,opts,limit)
   # Baseline and no-match remain feasible. Pareto may omit identical/dominated baseline.
   feasible=[v for v in front if v['duty_minutes']<=base['duty_minutes']+1e-8]
   assert feasible
   best=min(feasible,key=lambda v:(v['km'],v['duty_minutes']))
   x.verify(t,j,d,best,limit)
   assert best['km']<=base['km']+1e-8 and best['duty_minutes']<=base['duty_minutes']+1e-8
   for method,r in [('separate',base),('distance_no_duty_increase',best)]:
    rows.append(dict(seed=seed,individual_limit=limit or 'none',method=method,**{k:v for k,v in r.items() if k not in ['routes','assignments']}))
   details[f'{seed}/{limit}']=dict(baseline=base,frontier=front,chosen=best)
  print(seed,round(time.time()-start,2),flush=True)
 with (R/f'{prefix}.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0]);w.writeheader();w.writerows(rows)
 (R/f'{prefix}_details.json').write_text(json.dumps(details,indent=2)+'\n')
 summary=[]
 for limit in ['none',60]:
  a=[v for v in rows if v['individual_limit']==limit and v['method']=='separate'];b=[v for v in rows if v['individual_limit']==limit and v['method']!='separate']
  s=dict(individual_limit=limit,n=len(a),mean_pct_km_saving=statistics.mean(100*(v['km']-w['km'])/v['km'] for v,w in zip(a,b)),mean_pct_duty_saving=statistics.mean(100*(v['duty_minutes']-w['duty_minutes'])/v['duty_minutes'] for v,w in zip(a,b)),positive_worlds=sum(w['km']<v['km']-1e-8 for v,w in zip(a,b)))
  for label,rs in [('separate',a),('joint',b)]:s[label]={k:statistics.mean(v[k] for v in rs) for k in ['km','duty_minutes','matched','extra_delivery_minutes','max_delivery_extra','collector_trips']}
  summary.append(s)
 (R/f'{prefix}_summary.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
