"""Out-of-time validation: indices built on 2022-24 vs pressure performance in 2025-26.

Usage: python -I validate.py <out_dir>
"""
import sys
import numpy as np
import pandas as pd

OUT = sys.argv[1]
rows = []
for role in ("bat", "bowl"):
    sign = 1 if role == "bat" else -1
    old = pd.read_pickle(f"{OUT}/ratings_{role}_to2024.pkl")
    df = pd.read_pickle(f"{OUT}/resid_{role}.pkl")
    te = df[(df.year >= 2025) & df.P]
    tr = df[(df.year <= 2024) & df.P]
    n_te = te.groupby("pid").size()
    tgt_q = te.groupby("pid").q.mean()
    tgt_wpa = te.groupby("pid").wpa.mean()
    pool = old.index[(old.n_p >= 60)].intersection(n_te[n_te >= 60].index)
    tags = [l.split("\t")[0] for l in open(f"{OUT}/ensemble_specs.jsonl")]
    ens = pd.concat([old.PRI] + [pd.read_pickle(f"{OUT}/ratings_{role}_to2024{t}.pkl").PRI for t in tags], axis=1)
    cands = {
        "PRI consensus (73 specs, final method)": ens.mean(axis=1),
        "PRI single base specification": old.PRI,
        "Pressure Quality (PRI core)": old.pq,
        "Raw pressure WPA (naive clutch)": tr.groupby("pid").wpa.mean(),
        "Raw pressure run value": tr.groupby("pid").rv.mean(),
        "Raw pressure SR / economy": sign * tr.groupby("pid").r.mean(),
        "Normal-situation quality only": old.q_base,
    }
    for name, est in cands.items():
        e = est.reindex(pool)
        rows.append(dict(role=role, estimator=name, n_players=len(pool),
                         r_future_pressure_quality=e.corr(tgt_q.reindex(pool), method="spearman"),
                         r_future_pressure_wpa=e.corr(tgt_wpa.reindex(pool), method="spearman")))
    # top-quartile hit rate: of the top 25% by PRI in 2022-24, what share were above median under pressure in 2025-26?
    for lab, sc in (("consensus", ens.mean(axis=1)), ("base spec", old.PRI)):
        e = sc.reindex(pool)
        top = e[e >= e.quantile(0.75)].index
        hit = (tgt_q.reindex(top) > tgt_q.reindex(pool).median()).mean()
        rows.append(dict(role=role, estimator=f"Top-quartile hit rate ({lab})", n_players=len(top),
                         r_future_pressure_quality=hit, r_future_pressure_wpa=np.nan))
    continue
    e = old.PRI.reindex(pool)
    top = e[e >= e.quantile(0.75)].index
    hit = (tgt_q.reindex(top) > tgt_q.reindex(pool).median()).mean()
    rows.append(dict(role=role, estimator="Top-quartile PRI -> above-median 2025-26 (hit rate)", n_players=len(top),
                     r_future_pressure_quality=hit, r_future_pressure_wpa=np.nan))
res = pd.DataFrame(rows)
print(res.round(3).to_string(index=False))
res.to_csv(f"{OUT}/temporal_validation.csv", index=False)
