import experiment as e
import json,csv,statistics,itertools

def brute_collect(mask,opts):
 if mask==0:return 0
 bit=mask&-mask
 return min(route['km']+brute_collect(mask^part,opts) for part,route in opts.items() if part&bit and part&mask==part)
for cap in [1,2,3]:
 for seed in range(10):
  ts,js,d=e.generate(seed,20,120,20)
  cost,choice,opts=e.collector_tables(js[:6],max_jobs=cap)
  for mask in range(64):assert abs(cost[mask]-brute_collect(mask,opts))<1e-8
rows=list(csv.DictReader((e.ROOT/'results.csv').open()))
assert len(rows)==1260
summary=json.loads((e.ROOT/'summary.json').read_text())
for x in summary:
 rs=[r for r in rows if all(r[k]==x[k] for k in ['scenario','collector_baseline','method'])]
 assert len(rs)==20
 assert abs(statistics.mean(float(r['saving_pct']) for r in rs)-x['mean_saving_pct'])<1e-8
# Independently reconstruct all routes and service coverage in every setting.
inputs=[]
for scenario,spread,window,detour in [('base',20,120,20),('spread_10',10,120,20),('spread_40',40,120,20),('window_60',20,60,20),('window_240',20,240,20),('detour_0',20,120,0),('detour_40',20,120,40)]:
 for seed in range(20):
  ts,js,d=e.generate(seed,spread,window,detour);inputs.append(dict(scenario=scenario,seed=seed,trucks=ts,jobs=js,max_detour=d))
  for cap in [1,2,3]:
   cost,choice,opts=e.collector_tables(js,max_jobs=cap)
   result=e.evaluate(ts,js,d,max_jobs=cap)
   for method,res in result.items():
    direct=sum(e.dist(t['end'],t['depot']) for t in ts)
    truck=direct;seen=set();used=set()
    for i,j in res['assignment']:
     assert i not in used and j not in seen;used.add(i);seen.add(j)
     p=e.backhaul(ts[i],js[j],d);assert p is not None
     truck+=p['km']-e.dist(ts[i]['end'],ts[i]['depot'])
    collector=0
    for route in res['collector_routes']:
     assert len(route['order'])<=cap
     fresh=e.collection_route(js,route['order']);assert fresh is not None
     assert abs(fresh['km']-route['km'])<1e-8;collector+=fresh['km']
     for j in route['order']:assert j not in seen;seen.add(j)
    assert len(seen)==10 and abs(truck+collector-res['total_km'])<1e-8
    row=next(r for r in rows if r['scenario']==scenario and r['seed']==str(seed) and r['collector_baseline']==f'up_to_{cap}' and r['method']==method)
    assert abs(float(row['total_km'])-res['total_km'])<1e-8
(e.ROOT/'synthetic_inputs.json').write_text(json.dumps(inputs,indent=2))
with (e.ROOT/'tests.txt').open('a') as f:f.write('PASS: generalized collection partitions vs enumeration (3 caps x10 seeds x64 subsets); raw summary aggregation; all 1260 results independently route-reconstructed with service conservation; deterministic rerun; 140 input worlds exported.\
')
print((e.ROOT/'tests.txt').read_text())