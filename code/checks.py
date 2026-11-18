"""Two further checks for the report.
  1 does the Pressure Index measure real swings? actual win-probability movement on each ball, by Pressure Index decile
  2 how repeatable is each part of the score? split-half reliability (40 random match halves, Spearman-Brown) of the
    pressure-quality level, Lift and consistency, raw and as used (shrunk)
Usage: python -I checks.py <out_dir>"""
import sys
import numpy as np
import pandas as pd

OUT = sys.argv[1]
K_BASE = 500
b = pd.read_pickle(f"{OUT}/balls.pkl")
b["swing"] = b.bat_wpa.abs() * 100
b["dec"] = pd.qcut(b.PI.rank(method="first"), 10, labels=range(1, 11))
dec = b.groupby("dec", observed=True).agg(pi_lo=("PI", "min"), pi_hi=("PI", "max"), swing=("swing", "mean"))
share = b.loc[b.PI >= 1.5, "swing"].sum() / b.swing.sum()
dec.to_csv(f"{OUT}/check_deciles.csv")
print(dec.round(3), "\nshare of all win-probability movement on pressure balls:", round(share, 3),
      "share of balls:", round((b.PI >= 1.5).mean(), 3))
pd.Series({"wp_share_pressure": share, "ball_share_pressure": (b.PI >= 1.5).mean(),
           "top_vs_bottom": dec.swing.iloc[-1] / dec.swing.iloc[0]}).to_csv(f"{OUT}/check_summary.csv")


def shrink(x, n, k, prior=0.0):
    return (x * n + prior * k) / (n + k)


rows = []
rng = np.random.default_rng(5)
CMIN = {"bat": 4, "bowl": 6}
for role in ("bat", "bowl"):
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    pool = R.index[R.eligible]
    r = pd.read_pickle(f"{OUT}/resid_{role}.pkl")
    r = r[r.pid.isin(pool)].assign(qw=lambda d: d.q * d.w)
    mids = r.match_id.unique()
    k_n = float(np.median(R.loc[pool, "n_np"]))      # rough baseline prior for the halves (league-average shrink)

    def metrics(d):
        g = d.groupby(["pid", "P"]).agg(qw=("qw", "sum"), w=("w", "sum")).unstack("P")
        qp = g[("qw", True)] / g[("w", True)]
        qn = g[("qw", False)] / g[("w", False)]
        n_p, n_n = g[("w", True)], g[("w", False)]
        base = shrink(qn, n_n, k_n)
        pq = shrink(qp, n_p, K_BASE, base)
        pm = d[d.P].groupby(["pid", "match_id"]).agg(n=("q", "size"), qw=("qw", "sum"))
        pm = pm[pm.n >= CMIN[role]]
        succ = (pm.qw > 0).groupby("pid").mean()
        return pd.DataFrame({"Level under pressure (raw)": qp, "Level under pressure (as used)": pq,
                             "Lift (raw: pressure minus normal)": qp - qn, "Lift (as used)": pq - base,
                             "Consistency (share of tense games won)": succ})
    halves = []
    for _ in range(40):
        h = pd.Series(rng.integers(0, 2, len(mids)), index=mids)
        a, c = metrics(r[r.match_id.map(h) == 0]), metrics(r[r.match_id.map(h) == 1])
        halves.append({m: a[m].corr(c[m], method="spearman") for m in a.columns})
    mean = pd.DataFrame(halves).mean()
    for m, v in mean.items():
        rows.append(dict(role=role, part=m, split_half=v, reliability=2 * v / (1 + v)))
out = pd.DataFrame(rows)
out.to_csv(f"{OUT}/check_components.csv", index=False)
print(out.round(3).to_string(index=False))
