"""Assumption stress: fixed geometry, slower/faster constant toy travel speed.
Not a traffic model or calibrated French speed estimate.
"""
import experiment as e
import json,statistics
rows=[]
for speed in [15.,30.,45.]:
 e.SPEED=speed
 for seed in range(20):
  ts,js,d=e.generate(seed,20,120,20)
  try:r=e.evaluate(ts,js,d,max_jobs=3)
  except AssertionError as err:
   if str(err)=='single collection infeasible':rows.append(dict(speed=speed,seed=seed,infeasible=True));continue
   raise
  base=r['separate']['total_km']
  rows.append(dict(speed=speed,seed=seed,infeasible=False,base_km=base,joint_km=r['joint']['total_km'],saving_pct=100*(base-r['joint']['total_km'])/base,matched=r['joint']['matched'],extra_truck_minutes=r['joint']['extra_truck_minutes']))
summary=[]
for speed in [15.,30.,45.]:
 group=[x for x in rows if x['speed']==speed];valid=[x for x in group if not x['infeasible']]
 summary.append(dict(speed=speed,valid=len(valid),excluded=len(group)-len(valid),mean_saving_pct=statistics.mean(x['saving_pct'] for x in valid) if valid else None,mean_extra_delivery_truck_minutes=statistics.mean(x['extra_truck_minutes'] for x in valid) if valid else None))
(e.ROOT/'speed_stress.json').write_text(json.dumps(dict(rows=rows,summary=summary),indent=2))
print(summary)