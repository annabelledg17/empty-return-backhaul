"""Exact synthetic route/duty tradeoff; no calibrated labour prices.
Collectors may choose departures >=0; elapsed duty includes all waiting after
 departure, pickup service, recycler unloading and return to depot. Delivery
 duty starts at fixed availability; prior delivery work is a cancelling constant.
One pickup per returning truck. Unlimited parallel collector trips, cap6/6tonnes.
"""
import experiment as e
import itertools,json,csv,statistics,time,math
from pathlib import Path
R=Path(__file__).parent

def collector(jobs,order):
 if sum(jobs[j]['weight'] for j in order)>e.COLLECTOR_CAP+1e-9:return None
 # Latest feasible departure: reverse all time-window and end-of-duty constraints.
 latest=e.HORIZON-e.minutes(e.dist(e.RECYCLER,e.COLLECTOR_DEPOT))-e.UNLOAD
 pos=e.RECYCLER
 for j in reversed(order):
  latest=min(jobs[j]['due'],latest-e.minutes(e.dist(jobs[j]['pos'],pos))-e.HANDLING)
  pos=jobs[j]['pos']
 start=latest-e.minutes(e.dist(e.COLLECTOR_DEPOT,pos))
 if start < -1e-8:return None
 # Among minimum-duty departures choose earliest, retaining deadline slack.
 # Finish(s)=max(s+no_wait_duration,finish(0)); duty is nonincreasing.
 no_wait=e.minutes(e.dist(e.COLLECTOR_DEPOT,jobs[order[0]]['pos']))
 f0=0;pos=e.COLLECTOR_DEPOT
 for j in order:
  f0=max(f0+e.minutes(e.dist(pos,jobs[j]['pos'])),jobs[j]['ready'])+e.HANDLING
  pos=jobs[j]['pos']
 tail=e.minutes(e.dist(pos,e.RECYCLER))+e.UNLOAD+e.minutes(e.dist(e.RECYCLER,e.COLLECTOR_DEPOT))
 f0+=tail
 no_wait=sum(e.minutes(e.dist(a,b)) for a,b in zip([e.COLLECTOR_DEPOT]+[jobs[j]['pos'] for j in order], [jobs[j]['pos'] for j in order]+[e.RECYCLER]))+len(order)*e.HANDLING+e.UNLOAD+e.minutes(e.dist(e.RECYCLER,e.COLLECTOR_DEPOT))
 optimum=max(no_wait,f0-max(0,start))
 start=max(0,f0-optimum)
 t=start;pos=e.COLLECTOR_DEPOT;km=0;visits=[]
 for j in order:
  leg=e.dist(pos,jobs[j]['pos']);km+=leg
  t=max(t+e.minutes(leg),jobs[j]['ready'])
  if t>jobs[j]['due']+1e-8:return None
  visits.append((j,t));t+=e.HANDLING;pos=jobs[j]['pos']
 leg=e.dist(pos,e.RECYCLER);km+=leg;t+=e.minutes(leg)+e.UNLOAD
 leg=e.dist(e.RECYCLER,e.COLLECTOR_DEPOT);km+=leg;t+=e.minutes(leg)
 if t>e.HORIZON+1e-8:return None
 return dict(km=km,duty=t-start,start=start,finish=t,order=list(order),visits=visits)

def all_routes(jobs,cap):
 opts={}
 for k in range(1,min(cap,len(jobs))+1):
  for subset in itertools.combinations(range(len(jobs)),k):
   routes=[r for order in itertools.permutations(subset) if (r:=collector(jobs,order)) is not None]
   if routes:opts[sum(1<<j for j in subset)]=routes
 assert all(1<<j in opts for j in range(len(jobs)))
 return opts

def solve(trucks,jobs,detour,opts,weight,limit=None):
 # weight is km per driver-hour; None means duty-only with distance tie-break.
 def key(km,duty):return (duty,km) if weight is None else (km+weight*duty/60,duty,km)
 n=len(jobs);full=(1<<n)-1
 selected={m:min(rs,key=lambda r:key(r['km'],r['duty'])) for m,rs in opts.items()}
 cost=[(0,0)]*(1<<n);choice={}
 for m in range(1,1<<n):
  bit=m&-m
  feasible=[p for p in selected if p&bit and p&m==p]
  p=min(feasible,key=lambda p:key(selected[p]['km']+cost[m^p][0],selected[p]['duty']+cost[m^p][1]))
  cost[m]=(selected[p]['km']+cost[m^p][0],selected[p]['duty']+cost[m^p][1]);choice[m]=p
 pairs=[[e.backhaul(t,j,detour) for j in jobs] for t in trucks]
 dp={0:(0,0,[])}
 for i in range(len(trucks)):
  nxt=dict(dp)
  for mask,(km,duty,a) in dp.items():
   for j,p in enumerate(pairs[i]):
    if p is None or mask&(1<<j) or (limit is not None and p['extra_minutes']>limit+1e-8):continue
    m=mask|(1<<j);cand=(km+p['delta'],duty+p['extra_minutes'],a+[(i,j)])
    if m not in nxt or key(*cand[:2])<key(*nxt[m][:2]):nxt[m]=cand
  dp=nxt
 mask=min(dp,key=lambda m:key(dp[m][0]+cost[full^m][0],dp[m][1]+cost[full^m][1]))
 km,duty,a=dp[mask];remaining=full^mask;routes=[]
 while remaining:
  p=choice[remaining];routes.append(selected[p]);remaining^=p
 direct=sum(e.dist(t['end'],t['depot']) for t in trucks)
 def out(km,duty,a,routes):
  extra=[pairs[i][j]['extra_minutes'] for i,j in a]
  return dict(km=direct+km,duty_minutes=e.minutes(direct)+duty,extra_delivery_minutes=sum(extra),max_delivery_extra=max(extra,default=0),collector_duty_minutes=sum(r['duty'] for r in routes),matched=len(a),collector_trips=len(routes),assignments=a,routes=routes)
 return out(cost[full][0],cost[full][1],[],_routes(full,choice,selected)),out(km+cost[full^mask][0],duty+cost[full^mask][1],a,routes)

def _routes(mask,choice,selected):
 rs=[]
 while mask:p=choice[mask];rs.append(selected[p]);mask^=p
 return rs

def verify(trucks,jobs,detour,result,limit):
 seen=[];km=sum(e.dist(t['end'],t['depot']) for t in trucks);duty=e.minutes(km)
 assert len({i for i,j in result['assignments']})==len(result['assignments'])
 for i,j in result['assignments']:
  p=e.backhaul(trucks[i],jobs[j],detour);assert p
  if limit is not None:assert p['extra_minutes']<=limit+1e-8
  km+=p['delta'];duty+=p['extra_minutes'];seen.append(j)
 for r in result['routes']:
  q=collector(jobs,r['order']);assert q
  assert math.isclose(q['km'],r['km'],abs_tol=1e-8)
  km+=q['km'];duty+=q['duty'];seen.extend(q['order'])
 assert sorted(seen)==list(range(len(jobs)))
 assert math.isclose(km,result['km'],abs_tol=1e-7)
 assert math.isclose(duty,result['duty_minutes'],abs_tol=1e-7)

def main():
 rows=[];examples={};start=time.time()
 modes=[('distance',0,None),('distance_limit30',0,30),('distance_limit60',0,60),('tradeoff15',15,None),('tradeoff30',30,None),('tradeoff60',60,None),('duty',None,None)]
 for seed in range(20):
  trucks,jobs,d=e.generate(seed,20,120,20);opts=all_routes(jobs,6)
  for label,w,limit in modes:
   base,joint=solve(trucks,jobs,d,opts,w,limit)
   for name,r in [('separate',base),('joint',joint)]:
    verify(trucks,jobs,d,r,limit)
    rows.append(dict(seed=seed,mode=label,method=name,**{k:v for k,v in r.items() if k not in ['assignments','routes']}))
   if seed==0:examples[label]=dict(separate=base,joint=joint)
  print('seed',seed,'elapsed',round(time.time()-start,1),flush=True)
 with (R/'duty_tradeoff.csv').open('w',newline='') as f:
  out=csv.DictWriter(f,fieldnames=rows[0]);out.writeheader();out.writerows(rows)
 summary=[]
 for mode,_,_ in modes:
  rs=[r for r in rows if r['mode']==mode]
  s=dict(mode=mode)
  for name in ['separate','joint']:
   a=[r for r in rs if r['method']==name]
   s[name]={k:statistics.mean(r[k] for r in a) for k in ['km','duty_minutes','extra_delivery_minutes','max_delivery_extra','collector_duty_minutes','matched','collector_trips']}
  s['mean_pct_km_saving']=statistics.mean(100*(a['km']-b['km'])/a['km'] for a,b in zip(rs[::2],rs[1::2]))
  s['mean_pct_duty_saving']=statistics.mean(100*(a['duty_minutes']-b['duty_minutes'])/a['duty_minutes'] for a,b in zip(rs[::2],rs[1::2]))
  s['joint_increases_duty_worlds']=sum(b['duty_minutes']>a['duty_minutes']+1e-8 for a,b in zip(rs[::2],rs[1::2]))
  summary.append(s)
 (R/'duty_tradeoff_summary.json').write_text(json.dumps(summary,indent=2)+'\n')
 (R/'duty_tradeoff_seed0.json').write_text(json.dumps(examples,indent=2)+'\n')
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
