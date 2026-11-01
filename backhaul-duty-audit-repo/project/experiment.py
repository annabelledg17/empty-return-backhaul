"""Synthetic backhaul experiment. All locations/times are invented, not French road data.
Run: python experiment.py. Python 3 standard library only.
"""
import math, random, json, csv, statistics, itertools
from pathlib import Path
ROOT=Path(__file__).resolve().parent
N=10
SPEED=30.0 # assumed km/h; straight-line toy geometry, not road routing
HANDLING=15.0 # assumed minutes per pickup
UNLOAD=15.0
HORIZON=480.0
COLLECTOR_DEPOT=(5.0,5.0)
RECYCLER=(35.0,5.0)
COLLECTOR_CAP=6.0 # assumed tonnes

def dist(a,b):return math.dist(a,b)
def minutes(km):return km/SPEED*60

def generate(seed,spread,window,detour):
 r=random.Random(seed)
 # Study square is arbitrary. It does not represent a mapped French region.
 trucks=[dict(end=(r.uniform(0,40),r.uniform(0,40)),depot=(r.uniform(0,40),r.uniform(0,40)),available=r.uniform(0,90),capacity=r.uniform(1,5),compatible=r.random()<.8) for _ in range(N)]
 jobs=[]
 for _ in range(N):
  ready=r.uniform(30,120)
  jobs.append(dict(pos=(20+r.uniform(-spread/2,spread/2),20+r.uniform(-spread/2,spread/2)),weight=r.uniform(.5,2.5),ready=ready,due=ready+window))
 return trucks,jobs,detour

def collection_route(jobs,order):
 """Independent collector starts at time 0, waits if early, and returns to depot.
 A bounded number of pickups per trip (set by collector_tables), then recycler. Unlimited identical collector trips
 may run in parallel. This is a controlled baseline, not a full fleet model.
 """
 if sum(jobs[j]['weight'] for j in order)>COLLECTOR_CAP+1e-9:return None
 pos=COLLECTOR_DEPOT;t=0;km=0;empty=0
 for k,j in enumerate(order):
  leg=dist(pos,jobs[j]['pos']);km+=leg
  if k==0:empty+=leg
  t=max(t+minutes(leg),jobs[j]['ready'])
  if t>jobs[j]['due']+1e-9:return None
  t+=HANDLING;pos=jobs[j]['pos']
 leg=dist(pos,RECYCLER);km+=leg;t+=minutes(leg)
 if t>HORIZON:return None
 t+=UNLOAD;leg=dist(RECYCLER,COLLECTOR_DEPOT);km+=leg;empty+=leg;t+=minutes(leg)
 if t>HORIZON:return None
 return dict(km=km,empty=empty,time=t,order=list(order))

def collector_tables(jobs,batch=True,max_jobs=None):
 n=len(jobs);opts={}
 if max_jobs is None:max_jobs=2 if batch else 1
 for k in range(1,max_jobs+1):
  for subset in itertools.combinations(range(n),k):
   routes=[r for order in itertools.permutations(subset) if (r:=collection_route(jobs,order)) is not None]
   if routes:opts[sum(1<<j for j in subset)]=min(routes,key=lambda x:x['km'])
 assert all(1<<j in opts for j in range(n)), 'single collection infeasible'
 cost=[0.0]*(1<<n);choice=[0]*(1<<n)
 for mask in range(1,1<<n):
  bit=mask & -mask
  options=[p for p in opts if p&bit and p&mask==p]
  pick=min(options,key=lambda m:opts[m]['km']+cost[mask^m])
  cost[mask]=opts[pick]['km']+cost[mask^pick];choice[mask]=pick
 return cost,choice,opts

def backhaul(t,j,max_detour):
 if not t['compatible'] or j['weight']>t['capacity']+1e-9:return None
 legs=[dist(t['end'],j['pos']),dist(j['pos'],RECYCLER),dist(RECYCLER,t['depot'])]
 direct=dist(t['end'],t['depot']);extra=sum(legs)-direct
 if extra>max_detour+1e-9:return None
 arrive=max(t['available']+minutes(legs[0]),j['ready'])
 if arrive>j['due']+1e-9:return None
 recycle=arrive+HANDLING+minutes(legs[1])
 if recycle>HORIZON:return None
 finish=recycle+UNLOAD+minutes(legs[2])
 if finish>HORIZON:return None
 return dict(km=sum(legs),delta=sum(legs)-direct,empty=legs[0]+legs[2],extra_minutes=finish-(t['available']+minutes(direct)))

def exact_assignment(pairs,fallback,njobs):
 """Exact dynamic programming over truck index and served-job bitmask.
 Objective = added truck km + optimal remaining collector km.
 No match is always an option. No job or truck can be used twice.
 """
 dp={0:0.0};parents=[]
 for i in range(len(pairs)):
  nxt=dict(dp);parent={m:(m,None) for m in dp}
  for m,v in dp.items():
   for j,p in enumerate(pairs[i]):
    if p is None or m&(1<<j):continue
    new=m|(1<<j);val=v+p['delta']
    if val<nxt.get(new,float('inf'))-1e-10:nxt[new]=val;parent[new]=(m,j)
  dp=nxt;parents.append(parent)
 full=(1<<njobs)-1
 mask=min(dp,key=lambda m:dp[m]+fallback[full^m]);value=dp[mask]+fallback[full^mask]
 assignment=[]
 for i in reversed(range(len(pairs))):
  previous,j=parents[i][mask]
  if j is not None:assignment.append((i,j))
  mask=previous
 return value,list(reversed(assignment))

def greedy_assignment(pairs,fallback,njobs):
 remaining=(1<<njobs)-1;used=set();chosen=[]
 while True:
  candidates=[]
  for i,row in enumerate(pairs):
   if i in used:continue
   for j,p in enumerate(row):
    if p is not None and remaining&(1<<j):
     saving=fallback[remaining]-fallback[remaining^(1<<j)]-p['delta']
     if saving>1e-9:candidates.append((saving,i,j))
  if not candidates:break
  _,i,j=max(candidates,key=lambda x:(x[0],-x[1],-x[2]))
  chosen.append((i,j));used.add(i);remaining^=1<<j
 value=sum(pairs[i][j]['delta'] for i,j in chosen)+fallback[remaining]
 return value,chosen

def evaluate(trucks,jobs,detour,batch=True,max_jobs=None):
 cost,choice,opts=collector_tables(jobs,batch,max_jobs)
 pairs=[[backhaul(t,j,detour) for j in jobs] for t in trucks]
 direct=sum(dist(t['end'],t['depot']) for t in trucks);full=(1<<len(jobs))-1
 result={}
 for name,(v,assignment) in [('separate',(cost[full],[])),('greedy',greedy_assignment(pairs,cost,len(jobs))),('joint',exact_assignment(pairs,cost,len(jobs)))]:
  assert len({i for i,j in assignment})==len(assignment)
  assert len({j for i,j in assignment})==len(assignment)
  remaining=full
  empty=direct;extra_minutes=0
  for i,j in assignment:
   assert pairs[i][j] is not None
   remaining^=1<<j;empty+=pairs[i][j]['empty']-dist(trucks[i]['end'],trucks[i]['depot']);extra_minutes+=pairs[i][j]['extra_minutes']
  routes=[];m=remaining
  while m:
   pick=choice[m];routes.append(opts[pick]);empty+=opts[pick]['empty'];m^=pick
  assert len(assignment)+sum(len(x['order']) for x in routes)==len(jobs)
  result[name]=dict(total_km=direct+v,empty_km=empty,matched=len(assignment),fallback_jobs=remaining.bit_count(),extra_truck_minutes=extra_minutes,assignment=assignment,collector_routes=routes)
 assert result['joint']['total_km']<=result['greedy']['total_km']+1e-8
 assert result['greedy']['total_km']<=result['separate']['total_km']+1e-8
 return result

def tests():
 # Assignment rule must beat a plausible greedy trap: truck0-job0 saving 9,
 # truck0-job1 saving 8, truck1-job0 saving 8; optimum chooses 8+8 instead of 9.
 fallback=[0,10,10,20]
 pairs=[[{'delta':1},{'delta':2}],[{'delta':2},None]]
 assert exact_assignment(pairs,fallback,2)[0]==4
 assert greedy_assignment(pairs,fallback,2)[0]==11
 # Compare exact solver with brute-force on many small random matrices.
 for seed in range(30):
  r=random.Random(seed);ps=[[None if r.random()<.3 else {'delta':r.randint(0,15)} for _ in range(4)] for _ in range(4)]
  fb=[10*m.bit_count() for m in range(16)];best=float('inf')
  for a in itertools.product(range(-1,4),repeat=4):
   chosen=[j for j in a if j>=0]
   if len(set(chosen))<len(chosen):continue
   if any(j>=0 and ps[i][j] is None for i,j in enumerate(a)):continue
   val=sum(ps[i][j]['delta'] for i,j in enumerate(a) if j>=0)+10*(4-len(chosen));best=min(best,val)
  assert abs(exact_assignment(ps,fb,4)[0]-best)<1e-8
 # Verify matching against non-additive fallback tables as residual collection
 # introduces interactions between jobs. Arbitrary costs also test solver logic.
 for seed in range(30):
  r=random.Random(1000+seed)
  ps=[[None if r.random()<.3 else {'delta':r.randint(0,15)} for _ in range(4)] for _ in range(4)]
  fb=[0]+[r.randint(5,50) for _ in range(15)];best=float('inf')
  for a in itertools.product(range(-1,4),repeat=4):
   chosen=[j for j in a if j>=0]
   if len(set(chosen))<len(chosen):continue
   if any(j>=0 and ps[i][j] is None for i,j in enumerate(a)):continue
   remaining=15
   for j in chosen:remaining^=1<<j
   val=sum(ps[i][j]['delta'] for i,j in enumerate(a) if j>=0)+fb[remaining]
   best=min(best,val)
  assert abs(exact_assignment(ps,fb,4)[0]-best)<1e-8
 # Simple hand calculation in a line: truck at 0, depot at 10, pickup at 2,
 # recycler at 8, collector depot at 0. Direct 10 + collector 16 = 26;
 # matched truck 2+6+2=10, saving 16. No extra distance allowed still feasible.
 global COLLECTOR_DEPOT,RECYCLER
 old=(COLLECTOR_DEPOT,RECYCLER);COLLECTOR_DEPOT=(0,0);RECYCLER=(8,0)
 ts=[dict(end=(0,0),depot=(10,0),available=0,capacity=3,compatible=True)]
 js=[dict(pos=(2,0),weight=1,ready=0,due=300)]
 x=evaluate(ts,js,0);assert x['separate']['total_km']==26 and x['joint']['total_km']==10
 assert backhaul(dict(ts[0],capacity=.1),js[0],100) is None
 assert backhaul(dict(ts[0],compatible=False),js[0],100) is None
 assert backhaul(ts[0],dict(js[0],due=0),100) is None
 COLLECTOR_DEPOT,RECYCLER=old
 return 'PASS: hand calculation; feasibility exclusions; 60 brute-force solver comparisons (30 additive and 30 non-additive residual costs); greedy-trap case; conservation/optimality assertions in every run.'

def main():
 status=tests();rows=[];examples={}
 # One-factor-at-a-time scenarios around spread 20km, window 120min, detour 20km.
 scenarios=[('base',20,120,20),('spread_10',10,120,20),('spread_40',40,120,20),('window_60',20,60,20),('window_240',20,240,20),('detour_0',20,120,0),('detour_40',20,120,40)]
 for scenario,spread,window,detour in scenarios:
  for seed in range(20):
   trucks,jobs,d=generate(seed,spread,window,detour)
   for cap in [1,2,3]:
    results=evaluate(trucks,jobs,d,max_jobs=cap)
    if scenario=='base' and seed==0 and cap==3:examples=dict(trucks=trucks,jobs=jobs,detour=d,results=results)
    baseline=results['separate']['total_km']
    for method,res in results.items():rows.append(dict(scenario=scenario,seed=seed,collector_baseline=f'up_to_{cap}',method=method,total_km=res['total_km'],empty_km=res['empty_km'],matched=res['matched'],fallback_jobs=res['fallback_jobs'],extra_truck_minutes=res['extra_truck_minutes'],saving_pct=100*(baseline-res['total_km'])/baseline))
 with (ROOT/'results.csv').open('w',newline='') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 summary=[]
 for scenario,*_ in scenarios:
  for baseline in ['up_to_1','up_to_2','up_to_3']:
   group=[x for x in rows if x['scenario']==scenario and x['collector_baseline']==baseline]
   for method in ['separate','greedy','joint']:
    rs=[x for x in group if x['method']==method]
    summary.append(dict(scenario=scenario,collector_baseline=baseline,method=method,mean_total_km=statistics.mean(x['total_km'] for x in rs),mean_saving_pct=statistics.mean(x['saving_pct'] for x in rs),min_saving_pct=min(x['saving_pct'] for x in rs),max_saving_pct=max(x['saving_pct'] for x in rs),mean_matches=statistics.mean(x['matched'] for x in rs)))
 (ROOT/'summary.json').write_text(json.dumps(summary,indent=2))
 (ROOT/'example_seed0.json').write_text(json.dumps(examples,indent=2))
 (ROOT/'tests.txt').write_text(status+'\
')
 print(status);print('Generated',len(rows),'method-results; 420 synthetic instances, 7 settings x 20 seeds x 3 collector baselines.')
 for x in summary:
  if x['scenario']=='base' or x['method']=='joint' and x['collector_baseline']=='up_to_3':print(x)
if __name__=='__main__':main()