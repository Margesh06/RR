"""Two further tests for the report.
  Test 9  leak-free split-half reliability: the ground and opponent effects are refitted on each random half of the
          matches alone, so neither half's rating has seen the other half. Compared with the same splits using effects
          fitted on all matches, and with no adjustment.
  Test 10 permutation test for Lift: is the spread of players' pressure-minus-normal gaps bigger than chance? Within
          each eligible player, the pressure / normal labels are shuffled across his own balls (same counts), which
          keeps his level but destroys any real pressure effect.
Usage: python -I robust_tests.py <data_dir> <out_dir>"""
import sys
import numpy as np
import pandas as pd

D, OUT = sys.argv[1], sys.argv[2]
K_BASE, REPS, PERMS = 500, 20, 500
rng = np.random.default_rng(17)
b = pd.read_pickle(f"{OUT}/balls.pkl")
venue = b.match_id.map(pd.read_csv(f"{D}/matches.csv").set_index("match_id").venue_id)


def shrink(x, n, k, prior=0.0):
    return (x * n + prior * k) / (n + k)


def shrunk_mean(y, key):
    g = y.groupby(key)
    m, n = g.mean(), g.size()
    noise = (y.var() / n).mean()
    tau2 = max(m.var() - noise, m.var() * 0.05)
    return shrink(m, n, y.var() / tau2).reindex(key).to_numpy()


def context(df, opp):
    """Same two-way fit as stage2_ratings.add_context, on whatever balls it is given."""
    out = {}
    for comp in ("r", "out"):
        y = df[comp] - df[f"e_{comp}"]
        own = ven = op = np.zeros(len(df))
        for _ in range(5):
            ven = shrunk_mean(y - own - op, df.venue)
            op = shrunk_mean(y - own - ven, opp)
            own = shrunk_mean(y - ven - op, df.pid)
        out[comp] = ven + op
    return out


def wavg(v, w, key):
    return (v * w).groupby(key).sum() / w.groupby(key).sum()


def pq_of(df, adj, sign, ks, WV):
    d_r = df.r - (df.e_r + adj["r"])
    d_out = df.out - (df.e_out + adj["out"]).clip(0.001, 0.999)
    P = df.P.to_numpy()
    q = sign * (d_r - d_out * np.where(P, WV[True], WV[False])) * 100
    sp, sn = df[P], df[~P]
    w_n = sn.w.groupby(sn.pid).sum()
    base = sign * (shrink(wavg(d_r[~P], sn.w, sn.pid), w_n, ks["r_np"])
                   - shrink(wavg(d_out[~P], sn.w, sn.pid), w_n, ks["out_np"]) * WV[False]) * 100
    n_p = sp.groupby("pid").size()
    return shrink(wavg(q[P], sp.w, sp.pid), n_p, K_BASE, base.reindex(n_p.index).fillna(0)), q


rel_rows, perm_rows = [], []
for role, opp_col in (("bat", "bowler_id"), ("bowl", "striker_id")):
    sign = 1 if role == "bat" else -1
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    pool = R.index[R.eligible]
    prm = pd.read_csv(f"{OUT}/params_{role}.csv", index_col=0).iloc[:, 0]
    ks, WV = {"r_np": prm["r_np"], "out_np": prm["out_np"]}, {True: prm["WV_True"], False: prm["WV_False"]}
    res = pd.read_pickle(f"{OUT}/resid_{role}.pkl")
    E = pd.read_pickle(f"{OUT}/expect_{role}_9999.pkl").reindex(res.index)
    df = pd.DataFrame({"match_id": res.match_id, "pid": res.pid, "P": res.P, "w": res.w, "r": res.r,
                       "out": res.out.astype(float), "e_r": E.e_r, "e_out": E.e_out,
                       "venue": venue.reindex(res.index), "opp": b[opp_col].reindex(res.index)})
    full_adj = context(df, df.opp)
    zero = {"r": np.zeros(len(df)), "out": np.zeros(len(df))}
    mids = df.match_id.unique()
    cors = {"No ground/opponent adjustment": [], "Adjustment fitted on all matches": [], "Adjustment refitted on each half (leak-free)": []}
    for _ in range(REPS):
        h = pd.Series(rng.integers(0, 2, len(mids)), index=mids)
        halves = {k: [] for k in cors}
        for side in (0, 1):
            m = (df.match_id.map(h) == side).to_numpy()
            s = df[m]
            halves["No ground/opponent adjustment"].append(pq_of(s, {"r": zero["r"][m], "out": zero["out"][m]}, sign, ks, WV)[0])
            halves["Adjustment fitted on all matches"].append(pq_of(s, {"r": full_adj["r"][m], "out": full_adj["out"][m]}, sign, ks, WV)[0])
            halves["Adjustment refitted on each half (leak-free)"].append(pq_of(s, context(s, s.opp), sign, ks, WV)[0])
        for k, (a, c) in halves.items():
            idx = a.index.intersection(c.index).intersection(pool)
            cors[k].append(a[idx].corr(c[idx], method="spearman"))
    for k, v in cors.items():
        r_ = float(np.mean(v))
        rel_rows.append(dict(role=role, version=k, split_half=r_, reliability=2 * r_ / (1 + r_)))

    # Test 10: permutation test for Lift, on the final per-ball quality
    _, q = pq_of(df, full_adj, sign, ks, WV)
    sub = pd.DataFrame({"pid": df.pid, "P": df.P, "q": q})
    sub = sub[sub.pid.isin(pool)].sort_values("pid", kind="stable")
    pid = sub.pid.to_numpy()
    lab = sub.P.to_numpy()
    qq = sub.q.to_numpy()
    codes, inv = np.unique(pid, return_inverse=True)
    n = len(codes)

    def lift_sd(p):
        sp = np.bincount(inv, qq * p, n) / np.maximum(np.bincount(inv, p.astype(float), n), 1)
        sn = np.bincount(inv, qq * ~p, n) / np.maximum(np.bincount(inv, (~p).astype(float), n), 1)
        return np.std(sp - sn)
    obs = lift_sd(lab)
    null = []
    for _ in range(PERMS):
        order = np.lexsort((rng.random(len(pid)), inv))     # shuffle within player
        null.append(lift_sd(lab[order]))
    null = np.array(null)
    perm_rows.append(dict(role=role, players=n, observed_sd=obs, null_mean_sd=null.mean(), null_p95_sd=np.percentile(null, 95),
                          p_value=(np.sum(null >= obs) + 1) / (PERMS + 1),
                          real_share_of_spread=max(0.0, 1 - (null ** 2).mean() / obs ** 2)))
    print(role, rel_rows[-3:], perm_rows[-1])

pd.DataFrame(rel_rows).to_csv(f"{OUT}/leakfree_reliability.csv", index=False)
pd.DataFrame(perm_rows).to_csv(f"{OUT}/permutation_lift.csv", index=False)
print(pd.DataFrame(rel_rows).round(3).to_string(index=False))
print(pd.DataFrame(perm_rows).round(3).to_string(index=False))
