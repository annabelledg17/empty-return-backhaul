"""Rebuild counterexample.png from the seed-1 ledger. Run after duty_tradeoff.py and the counterexample export."""
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ex = json.loads(open('driver-duty-counterexample-seed1.json').read())
b, a = ex['baseline'], ex['distance_only']
plt.rcParams.update({'font.family': 'Noto Sans', 'font.size': 8})
fig, axes = plt.subplots(1, 2, figsize=(6.6, 1.75))
data = [
    ('System distance (toy km)', [b['km'], a['km']], ['%.2f' % b['km'], '%.2f' % a['km']], (0, 550), range(0, 501, 100)),
    ('Counted duty (minutes)', [b['duty_minutes'], a['duty_minutes']], ['{:,.2f}'.format(b['duty_minutes']), '{:,.2f}'.format(a['duty_minutes'])], (0, 1400), range(0, 1251, 250)),
]
cats = ['Separate collection', 'Distance-only match']
colors = ['#808080', '#5e9c78']
for ax, (title, vals, labels, xlim, ticks) in zip(axes, data):
    y = [1, 0]
    ax.barh(y, vals, height=0.55, color=colors)
    ax.set_yticks(y); ax.set_yticklabels(cats)
    ax.set_xlim(*xlim); ax.set_xticks(list(ticks))
    ax.set_title(title, loc='left', fontsize=8.5, pad=6)
    ax.grid(axis='x', color='#e0e0e0', linewidth=0.6)
    ax.set_axisbelow(True)
    for sp in ['top', 'right', 'left']: ax.spines[sp].set_visible(False)
    ax.spines['bottom'].set_color('#999999')
    ax.tick_params(length=0, labelsize=7.5, colors='#333333')
    for yi, v, lab in zip(y, vals, labels):
        ax.text(v + xlim[1] * 0.012, yi, lab, va='center', fontsize=7.5, color='#333333')
fig.tight_layout(w_pad=3.0)
fig.savefig('counterexample.png', dpi=200, bbox_inches='tight', facecolor='white')
print('figure saved')
