# Synthetic backhaul distance/duty audit

Can a delivery truck pick up waste on its way back and save distance? Yes. Does that
guarantee less work for drivers? No. This repository contains a small, exact,
fully reproducible study that makes that gap visible: a distance-minimizing plan
is compared against plans that also respect counted driver duty.

Every input is invented by a seeded generator. Nothing here is measured road data,
and no percentage in the outputs describes a real region, company or market.

## Layout

- `project/` - the main distance/duty audit
- `baseline-study/` - the earlier distance-only sensitivity work the audit compares against

## Reproduce

Python 3.10 or later. Install dependencies once:

    pip install -r requirements.txt

Then, from `project/`:

    python duty_tradeoff.py          # distance-only vs duty-aware plans, 20 base seeds
    python pareto_duty.py            # exact distance/duty frontiers
    python verify_pareto.py          # 550 independent LP checks, 60 exhaustive small checks,
                                     # 40 full-size regressions, then 40 complete frontier comparisons
    python test_boundaries.py        # 11 deterministic contract tests
    python audit_claims.py           # re-checks every headline number against the outputs
    python make_figure.py            # rebuilds counterexample.png from the seed-1 ledger

An additional fixed-seed run (seeds 100-199, used earlier in the project - an extra
check, not an untouched holdout):

    python -c "import pareto_duty as p; p.main(range(100,200),'pareto_holdout')"

The baseline study, from `baseline-study/`:

    python experiment.py             # 420 synthetic instances, scenario grid
    python validate.py               # independent reconstruction of all 1,260 results
    python quality_checks.py
    python structural_checks.py
    python stronger_baseline.py
    python metamorphic_checks.py
    python speed_stress.py
    python check_claims.py

All outputs are deterministic for the listed seeds and regenerate the files in each folder.

## What to know before reading the numbers

- Locations, weights, capacities, time windows and speeds are assumptions, not measurements.
- Counted duty is driving + pickup handling + recycler unloading + waiting after departure.
  It is not payroll, shift length, headcount or a fairness measure.
- The 60-minute per-driver added-duty allowance is illustrative. No driver agreed to it.
- Main statistics are mean within-instance percentages on the same 20 paired seeds,
  not estimates for any population of operators.
- These checks test implementation consistency. They are not empirical validation.

## Provenance

Research design, code, tests, analysis and text were produced with extensive AI
assistance. Human review and understanding of the method and claims are required
before this work is presented as anyone's own.

## License

MIT, see `LICENSE`.
