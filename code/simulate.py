"""Known-answer test: simulated players with a pressure skill we set ourselves.

Every eligible player keeps his real deliveries (same matches, same pressure balls, same weights). We give each one a
true normal-situation quality T_n and a true pressure lift L, so his true pressure quality is T_p = T_n + L. Each ball's
quality is then simulated as the true value plus noise resampled from the real per-ball residuals (heavy tails kept).
We re-estimate everyone and ask which method recovers the truth best:
  raw      pressure-ball average only (the usual "clutch" number)
  minus    pressure average minus normal average (the usual "compared with his normal level")
  ours     Pressure Quality: normal level shrunk to league average, pressure evidence shrunk toward it (K_BASE balls)
Scenarios set how big true pressure skill is relative to normal skill (sd of L / sd of T_n): none, half, equal, and
the size the data itself implies (method of moments on the real data).
Usage: python -I simulate.py <out_dir>"""
import sys
import numpy as np
import pandas as pd

OUT = sys.argv[1]
K_BASE, REPS, Z80 = 500, 200, 1.2816
rng = np.random.default_rng(7)


def wmean(v, w, idx, n):
    return np.bincount(idx, v * w, n) / np.maximum(np.bincount(idx, w, n), 1e-9)


def mom_k(q, w, idx, n, keep):
    """Method-of-moments shrinkage constant, as in stage2: k = per-ball variance / between-player variance."""
    m = wmean(q, w, idx, n)[keep]
    sw = np.bincount(idx, w, n)[keep]
    s2 = q.var()
    noise = (s2 / sw).mean()
    tau2 = max(m.var() - noise, m.var() * 0.05)
    return s2 / tau2


rows, recov = [], []
for role in ("bat", "bowl"):
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    pool = R.index[R.eligible]
    r = pd.read_pickle(f"{OUT}/resid_{role}.pkl")
    r = r[r.pid.isin(pool)]
    code = {p: i for i, p in enumerate(pool)}
    idx = r.pid.map(code).to_numpy()
    n = len(pool)
    P = r.P.to_numpy()
    w = r.w.to_numpy()
    q = r.q.to_numpy()
    # noise pools: real per-ball residuals with each player's own mean removed (skill taken out, noise kept)
    centred = q - np.where(P, wmean(q * P, w * P, idx, n)[idx], wmean(q * ~P, w * ~P, idx, n)[idx])
    noise_p, noise_n = centred[P], centred[~P]
    n_p = np.bincount(idx[P], w[P], n)
    n_n = np.bincount(idx[~P], w[~P], n)
    keep = (n_p > 0) & (n_n > 0)
    sd_n = R.loc[pool, "q_base"].std()
    # pressure-skill size implied by the real data: var(pressure - normal) minus its sampling noise
    raw_diff = (R.loc[pool, "q_p_raw"] - R.loc[pool, "q_np_raw"]).to_numpy()
    samp = (noise_p.var() / np.maximum(n_p, 1) + noise_n.var() / np.maximum(n_n, 1))
    implied = np.sqrt(max(raw_diff.var() - samp.mean(), 0)) / sd_n
    scen = {"No pressure skill": 0.0, f"As the data implies ({implied:.2f})": implied, "Half of normal skill": 0.5,
            "Equal to normal skill": 1.0}
    for sname, ratio in scen.items():
        acc = {m: [] for m in ("raw", "minus", "ours")}
        top = {m: [] for m in ("raw", "ours")}
        lift_acc = {m: [] for m in ("minus", "ours")}
        cover = []
        for _ in range(REPS):
            Tn = rng.normal(0, sd_n, n)
            L = rng.normal(0, ratio * sd_n, n)
            Tp = Tn + L
            e = np.empty(len(q))
            e[P] = rng.choice(noise_p, P.sum())
            e[~P] = rng.choice(noise_n, (~P).sum())
            qs = np.where(P, Tp[idx], Tn[idx]) + e
            raw_p = wmean(qs * P, w * P, idx, n)
            raw_n = wmean(qs * ~P, w * ~P, idx, n)
            k_n = mom_k(qs[~P], w[~P], idx[~P], n, keep)
            base = raw_n * n_n / (n_n + k_n)                       # normal level, shrunk to league average
            pq = (raw_p * n_p + base * K_BASE) / (n_p + K_BASE)     # pressure evidence, shrunk to own baseline
            est = {"raw": raw_p, "minus": raw_p - raw_n, "ours": pq}
            for m in acc:
                acc[m].append(pd.Series(est[m][keep]).corr(pd.Series(Tp[keep]), method="spearman"))
            true10 = set(np.argsort(-Tp[keep])[:10])
            for m in top:
                top[m].append(len(true10 & set(np.argsort(-est[m][keep])[:10])))
            if ratio > 0:
                for m, v in (("minus", raw_p - raw_n), ("ours", pq - base)):
                    lift_acc[m].append(pd.Series(v[keep]).corr(pd.Series(L[keep]), method="spearman"))
            se = noise_p.std() / np.sqrt(n_p + K_BASE)
            cover.append(np.mean(np.abs(pq - Tp)[keep] <= Z80 * se[keep]))
        rows.append(dict(role=role, scenario=sname, ratio=ratio,
                         raw=np.mean(acc["raw"]), minus=np.mean(acc["minus"]), ours=np.mean(acc["ours"]),
                         top10_raw=np.mean(top["raw"]), top10_ours=np.mean(top["ours"]),
                         lift_minus=(np.mean(lift_acc["minus"]) if lift_acc["minus"] else np.nan),
                         lift_ours=(np.mean(lift_acc["ours"]) if lift_acc["ours"] else np.nan),
                         coverage80=np.mean(cover)))
        print(role, sname, {k: round(v, 3) for k, v in rows[-1].items() if isinstance(v, float)})
out = pd.DataFrame(rows)
out.to_csv(f"{OUT}/simulation.csv", index=False)
print(out.round(3).to_string(index=False))
