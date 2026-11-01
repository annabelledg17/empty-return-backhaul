"""Checks invariants without relying on expected numerical answers."""
import experiment as e
import copy,random,math
for seed in range(20):
 t,j,d=e.generate(seed,20,120,20)
 base=e.evaluate(t,j,d,max_jobs=3)['joint']['total_km']
 # Relabeling all trucks/jobs cannot change optimum.
 rng=random.Random(seed+999);tt=copy.deepcopy(t);jj=copy.deepcopy(j);rng.shuffle(tt);rng.shuffle(jj)
 assert abs(e.evaluate(tt,jj,d,max_jobs=3)['joint']['total_km']-base)<1e-8
 # Euclidean translation/reflection of all geometry cannot change optimum.
 old=(e.RECYCLER,e.COLLECTOR_DEPOT)
 f=lambda x:(100-x[0],x[1]+200)
 tt=copy.deepcopy(t);jj=copy.deepcopy(j)
 for x in tt:x['end']=f(x['end']);x['depot']=f(x['depot'])
 for x in jj:x['pos']=f(x['pos'])
 e.RECYCLER,e.COLLECTOR_DEPOT=f(old[0]),f(old[1])
 assert abs(e.evaluate(tt,jj,d,max_jobs=3)['joint']['total_km']-base)<1e-8
 e.RECYCLER,e.COLLECTOR_DEPOT=old
 # No compatible truck must reproduce collection baseline.
 tt=copy.deepcopy(t)
 for x in tt:x['compatible']=False
 r=e.evaluate(tt,j,d,max_jobs=3);assert abs(r['joint']['total_km']-r['separate']['total_km'])<1e-8
 # More eligible return pairs can never worsen exact joint objective.
 tt=copy.deepcopy(t)
 for x in tt:x['compatible']=True
 assert e.evaluate(tt,j,d,max_jobs=3)['joint']['total_km']<=base+1e-8
 assert e.evaluate(t,j,d+20,max_jobs=3)['joint']['total_km']<=base+1e-8
print('PASS 20 seeds x5 metamorphic checks: relabeling, geometry symmetry, no compatibility, increased compatibility, detour relaxation.')