"""Check every numerical headline used in the prose/guide against saved outputs."""
import csv,json,statistics
from pathlib import Path
r=Path(__file__).resolve().parent
rows=list(csv.DictReader((r/'results.csv').open()))
def select(cap,method):return [x for x in rows if x['scenario']=='base' and x['collector_baseline']==f'up_to_{cap}' and x['method']==method]
expected={1:(940.24,841.96,98.28,10.26),2:(585.86,559.47,26.40,4.33),3:(509.15,461.39,47.76,9.26)}
for cap,(a,b,c,d) in expected.items():
 ordinary=statistics.mean(float(x['total_km']) for x in select(cap,'separate'))
 joint=statistics.mean(float(x['total_km']) for x in select(cap,'joint'))
 saving=statistics.mean(float(x['saving_pct']) for x in select(cap,'joint'))
 assert all(abs(v-w)<.0051 for v,w in [(ordinary,a),(joint,b),(ordinary-joint,c),(saving,d)])
assert sum(float(x['saving_pct'])<1e-8 for x in select(2,'joint'))==9
assert sum(float(x['saving_pct'])<1e-8 for x in select(3,'joint'))==3
assert abs(statistics.mean(float(x['saving_pct']) for x in select(2,'greedy'))-1.70)<.0051
print('PASS: all guide numerical headlines agree with raw outputs and rounding.')