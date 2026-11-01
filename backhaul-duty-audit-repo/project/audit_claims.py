"""Audit numerical manuscript claims against retained experiment outputs."""
from pathlib import Path
import json,math
P=Path(__file__).parent;B=P.parent/'baseline-study'
def near(a,b):assert math.isclose(a,b,abs_tol=0.005),(a,b)
d=json.loads((P/'duty_tradeoff_summary.json').read_text());p=json.loads((P/'pareto_duty_summary.json').read_text());h=json.loads((P/'pareto_holdout_summary.json').read_text());ex=json.loads((P/'driver-duty-counterexample-seed1.json').read_text())
q=next(v for v in d if v['mode']=='distance');near(q['mean_pct_km_saving'],3.94);near(q['mean_pct_duty_saving'],1.79);assert q['joint_increases_duty_worlds']==3
for q,km,du,pos in zip(p,[3.74,1.74],[2.35,1.36],[8,4]):near(q['mean_pct_km_saving'],km);near(q['mean_pct_duty_saving'],du);assert q['positive_worlds']==pos
for q,km,pos in zip(h,[3.97,2.25],[38,21]):near(q['mean_pct_km_saving'],km);assert q['positive_worlds']==pos
for k,km,du in [('baseline',496.28,1187.55),('distance_only',487.56,1237.68)]:near(ex[k]['km'],km);near(ex[k]['duty_minutes'],du)
near(ex['extra_delivery_minutes'],110.80);near(ex['collector_minutes_avoided'],60.67);near(ex['distance_only']['duty_minutes']-ex['baseline']['duty_minutes'],50.13)
assert ex['no_duty_increase']['assignments']==[]
a=json.loads((B/'summary.json').read_text());b=json.loads((B/'stronger_baseline.json').read_text());s=json.loads((B/'structural_checks.json').read_text())
for cap,val in [(1,10.26),(2,4.33),(3,9.26)]:
 r=next(x for x in a if x['scenario']=='base' and x['method']=='joint' and x['collector_baseline']==f'up_to_{cap}');near(r['mean_saving_pct'],val)
near(next(x for x in b if x['cap']==6 and x['method']=='joint')['mean_saving_pct'],3.94)
for n,vs in [(9,[9.63,2.49,5.98]),(11,[9.13,4.16,3.49])]:
 for cap,val in zip([2,3,4],vs):near(next(x for x in s if x['test']=='job_count' and x['value']==f'{n}:{cap}')['mean_saving_pct'],val)
near(next(x for x in s if x['test']=='return_pickup_count' and x['value']==6)['mean_saving_pct'],6.28)
import experiment as e
for seed in range(20):
 _,j,_=e.generate(seed,20,120,20);assert sum(sorted(x['weight'] for x in j)[:7])>6
print('PASS headline, example, baseline and structural numbers; 20-seed payload certificate')