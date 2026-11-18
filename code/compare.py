"""Head-to-head: our method vs the approaches most entries use, on three neutral tests.
  common A  rule-based pressure (overs 16-20, or chasing at 10+ an over) + raw strike rate / economy
  common B  the same rule-based pressure, ranked on "pressure SR minus normal SR" (economy for bowlers)
Tests (same eligible pool for every method):
  1 skill-not-luck : split-half reliability (40 random match halves, Spearman-Brown)
  2 next seasons   : built on 2022-24, Spearman with 2025-26 pressure quality (same target as validate.py)
  3 fairness       : |Spearman| between the ranking and the share of a player's pressure balls at the death
                     (a fair ranking should not simply reward finishers / death bowlers)
Usage: python -I compare.py <out_dir>"""
import sys
import numpy as np
import pandas as pd

OUT = sys.argv[1]
b = pd.read_pickle(f"{OUT}/balls.pkl")
b["over"] = (120 - b.balls_left) // 6 + 1
b["RULE"] = (b.over >= 16) | ((b.innings == 2) & (b.rrr >= 10))
rel = pd.read_csv(f"{OUT}/reliability.csv")
tv = pd.read_csv(f"{OUT}/temporal_validation.csv")
rows = []
for role in ("bat", "bowl"):
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    C = pd.read_csv(f"{OUT}/consensus_all_{role}.csv", index_col=0)
    pool = R.index[R.eligible]
    if role == "bat":
        d = b[b.extras_type != "wide"].assign(pid=b.striker_id, r=b.runs, n=1.0)
    else:
        d = b.assign(pid=b.bowler_id, r=b.bowler_runs, n=b.legal.astype(float))
    d = d[["pid", "match_id", "year", "RULE", "r", "n"]]
    sign = 1 if role == "bat" else -1
    scale = 100 if role == "bat" else 6

    def metrics(x):
        g = x.groupby(["pid", "RULE"])[["r", "n"]].sum().unstack("RULE")
        rate_p = g[("r", True)] / g[("n", True)] * scale
        rate_n = g[("r", False)] / g[("n", False)] * scale
        return {"A": sign * rate_p, "B": sign * (rate_p - rate_n)}

    # 1 split-half reliability
    rng = np.random.default_rng(3)
    mids = d.match_id.unique()
    sh = {"A": [], "B": []}
    for _ in range(40):
        h = pd.Series(rng.integers(0, 2, len(mids)), index=mids)
        m0, m1 = metrics(d[d.match_id.map(h) == 0]), metrics(d[d.match_id.map(h) == 1])
        for k in sh:
            a, c = m0[k].reindex(pool), m1[k].reindex(pool)
            ok = a.notna() & c.notna()
            sh[k].append(a[ok].corr(c[ok], method="spearman"))
    sb = {k: 2 * np.mean(v) / (1 + np.mean(v)) for k, v in sh.items()}

    # 2 next seasons (same pool and target as validate.py)
    old = pd.read_pickle(f"{OUT}/ratings_{role}_to2024.pkl")
    res = pd.read_pickle(f"{OUT}/resid_{role}.pkl")
    te = res[(res.year >= 2025) & res.P]
    n_te = te.groupby("pid").size()
    tgt = te.groupby("pid").q.mean()
    tpool = old.index[old.n_p >= 60].intersection(n_te[n_te >= 60].index)
    mo = metrics(d[d.year <= 2024])
    fut = {k: mo[k].reindex(tpool).corr(tgt.reindex(tpool), method="spearman") for k in mo}

    # 3 fairness: how much the ranking just follows death-over exposure
    death = R.death_share_p.reindex(pool)
    full = metrics(d)
    fair = {k: abs(full[k].reindex(pool).corr(death, method="spearman")) for k in full}
    ours_fair = abs(C.consensus_PRI.reindex(pool).corr(death, method="spearman"))

    our_rel = rel[(rel.role == role) & (rel.metric == "Pressure Quality (PRI core)")].full_sample_reliability.iat[0]
    our_fut = tv[(tv.role == role) & (tv.estimator == "PRI consensus (73 specs, final method)")].r_future_pressure_quality.iat[0]
    lab = "strike rate" if role == "bat" else "economy"
    rows += [dict(role=role, method=f"Common: death overs / high required rate + raw {lab}", reliability=sb["A"], next_seasons=fut["A"], role_bias=fair["A"]),
             dict(role=role, method=f"Common: same pressure, {lab} under pressure minus normal", reliability=sb["B"], next_seasons=fut["B"], role_bias=fair["B"]),
             dict(role=role, method="Ours: win-probability pressure + context-adjusted, shrunk rating", reliability=our_rel, next_seasons=our_fut, role_bias=ours_fair)]
out = pd.DataFrame(rows)
out.to_csv(f"{OUT}/compare_methods.csv", index=False)
print(out.round(3).to_string(index=False))
print("rule-based pressure share of balls:", round(b.RULE.mean() * 100, 1), "%")
