"""Deterministic contracts, not empirical waste-market validation. Run directly."""
import unittest, math, copy
import experiment as e
import duty_tradeoff as x
import pareto_duty as p

class BoundaryTests(unittest.TestCase):
 def job(self,**kw):
  return dict(dict(pos=e.COLLECTOR_DEPOT,weight=1,ready=100,due=200),**kw)
 def truck(self,**kw):
  return dict(dict(end=e.COLLECTOR_DEPOT,depot=e.COLLECTOR_DEPOT,available=0,capacity=1,compatible=True),**kw)
 def test_wait_is_before_departure(self):
  r=x.collector([self.job()],[0]);self.assertAlmostEqual(r['start'],100);self.assertAlmostEqual(r['duty'],150)
 def test_intraroute_wait_cannot_all_be_removed(self):
  jobs=[self.job(due=10,ready=0),self.job(ready=100,due=100)]
  r=x.collector(jobs,[0,1]);self.assertAlmostEqual(r['start'],10);self.assertAlmostEqual(r['duty'],240)
 def test_collector_exact_payload_and_window(self):
  self.assertIsNotNone(x.collector([self.job(weight=6,ready=0,due=0)],[0]))
  self.assertIsNone(x.collector([self.job(weight=6.001,ready=0,due=0)],[0]))
  self.assertIsNone(x.collector([self.job(pos=(6,5),ready=0,due=1.99)],[0]))
 def test_collector_horizon(self):
  self.assertIsNotNone(x.collector([self.job(ready=330,due=330)],[0]))
  self.assertIsNone(x.collector([self.job(ready=330.01,due=330.01)],[0]))
 def test_backhaul_detour_and_time(self):
  t=self.truck();j=self.job(ready=0,due=0)
  r=e.backhaul(t,j,60);self.assertIsNotNone(r);self.assertAlmostEqual(r['extra_minutes'],150)
  self.assertIsNone(e.backhaul(t,j,59.99))
  self.assertIsNone(e.backhaul(self.truck(compatible=False),j,60))
  self.assertIsNone(e.backhaul(self.truck(capacity=.99),j,60))
 def test_backhaul_horizon(self):
  self.assertIsNotNone(e.backhaul(self.truck(available=330),self.job(ready=330,due=330),60))
  self.assertIsNone(e.backhaul(self.truck(available=330.01),self.job(ready=330.01,due=330.01),60))
 def test_no_matches_keeps_reference(self):
  jobs=[self.job()];opts=x.all_routes(jobs,1)
  b,f=p.frontier([self.truck(compatible=False)],jobs,60,opts)
  self.assertEqual(len(f),1);self.assertAlmostEqual(b['km'],f[0]['km']);self.assertAlmostEqual(b['duty_minutes'],f[0]['duty_minutes'])
 def test_individual_cap_is_inclusive(self):
  jobs=[self.job(ready=0,due=0)];opts=x.all_routes(jobs,1)
  # At equal complete-system cost, inspect assignment labels before final pruning
  # by scalar duty filtering: a prohibited transition must not appear.
  b,r=x.solve([self.truck()],jobs,60,opts,0,149.99);self.assertEqual(r['assignments'],[])
  # Direct pair has exactly 150 added minutes, so threshold itself is feasible.
  self.assertAlmostEqual(e.backhaul(self.truck(),jobs[0],60)['extra_minutes'],150)
 def test_dominance_is_two_dimensional(self):
  self.assertEqual([v[:2] for v in p.prune([(10,50,None),(11,40,None),(12,60,None),(10,55,None)])],[(10,50),(11,40)])
 def test_empty_problem(self):
  b,f=p.frontier([],[],20,{})
  self.assertEqual(b['km'],0);self.assertEqual(f[0]['duty_minutes'],0)
 def test_verifier_rejects_duplicate_job(self):
  jobs=[self.job()];opts=x.all_routes(jobs,1);b,_=x.solve([],jobs,20,opts,0)
  b=copy.deepcopy(b);b['routes'].append(b['routes'][0])
  with self.assertRaises(AssertionError):x.verify([],jobs,20,b,None)

if __name__=='__main__':unittest.main(verbosity=2)