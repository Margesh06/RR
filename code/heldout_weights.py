"""Are the hand-set PRI weights (45/20/20/15) any good? Choose the weights on held-out seasons and compare.

Components are built on 2022-24 only (the out-of-time ratings). Every weighting on a 5% grid (1,771 combinations of
pressure quality, consistency, lift and win impact, summing to 100%) is scored by how well it ranks the same players'
2025-26 pressure quality (Spearman), the target used in validate.py. A player bootstrap (1,000 resamples) gives the
noise. Because picking the best of 1,771 weightings on ~50 players flatters the winner, the fair comparison is
cross-validated: choose the weights on a random half of the players, score them on the other half, 1,000 times.
Finally the held-out-best weights are applied to the full data to see how much the top 10 would change.
Usage: python -I heldout_weights.py <out_dir>"""
import itertools
import sys
import numpy as np
import pandas as pd

OUT = sys.argv[1]
COLS = ["pq", "succ_s", "lift", "wpa_s"]
OURS = np.array([0.45, 0.20, 0.20, 0.15])
grid = np.array([c for c in itertools.product(range(21), repeat=4) if sum(c) == 20]) / 20
rng = np.random.default_rng(11)


def zs(df, pool):
    return (df.loc[pool, COLS] - df.loc[pool, COLS].mean()) / df.loc[pool, COLS].std()


def rank_corr(scores, target):
    """Spearman of every column of scores (players x weights) with target."""
    a = pd.DataFrame(scores).rank().to_numpy()
    b = pd.Series(target).rank().to_numpy()
    a = (a - a.mean(0)) / a.std(0)
    b = (b - b.mean()) / b.std()
    return (a * b[:, None]).mean(0)


rows, tops = [], []
for role in ("bat", "bowl"):
    old = pd.read_pickle(f"{OUT}/ratings_{role}_to2024.pkl")
    res = pd.read_pickle(f"{OUT}/resid_{role}.pkl")
    te = res[(res.year >= 2025) & res.P]
    n_te = te.groupby("pid").size()
    tgt = te.groupby("pid").q.mean()
    pool = old.index[old.n_p >= 60].intersection(n_te[n_te >= 60].index)
    Z = zs(old, pool).to_numpy()
    y = tgt.reindex(pool).to_numpy()
    allc = rank_corr(Z @ grid.T, y)
    ours_c = rank_corr((Z @ OURS)[:, None], y)[0]
    best = grid[allc.argmax()]
    # bootstrap the players: gap between the best grid weights (re-chosen each time) and ours
    gaps, pct = [], []
    for _ in range(1000):
        i = rng.integers(0, len(pool), len(pool))
        c = rank_corr(Z[i] @ grid.T, y[i])
        o = rank_corr((Z[i] @ OURS)[:, None], y[i])[0]
        gaps.append(c.max() - o)
        pct.append((c > o).mean())
    # cross-validated: choose on half the players, score on the other half
    cv_best, cv_ours = [], []
    for _ in range(1000):
        perm = rng.permutation(len(pool))
        a, b = perm[: len(pool) // 2], perm[len(pool) // 2:]
        wa = grid[rank_corr(Z[a] @ grid.T, y[a]).argmax()]
        cv_best.append(rank_corr((Z[b] @ wa)[:, None], y[b])[0])
        cv_ours.append(rank_corr((Z[b] @ OURS)[:, None], y[b])[0])
    cv_best, cv_ours = np.array(cv_best), np.array(cv_ours)
    # apply the held-out-best weights to the full data and compare top 10s
    full = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    fpool = full.index[full.eligible]
    zf = zs(full, fpool)
    cons = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0)
    ours10 = list(cons.index[:10])
    alt10 = list((zf @ best).sort_values(ascending=False).index[:10])
    rows.append(dict(role=role, players=len(pool), best_weights="/".join(f"{x*100:.0f}" for x in best),
                     best_corr=allc.max(), ours_corr=ours_c, gap=allc.max() - ours_c,
                     gap_lo=np.percentile(gaps, 5), gap_hi=np.percentile(gaps, 95),
                     ours_better_than_share=1 - np.mean(pct), cv_chosen=cv_best.mean(), cv_ours=cv_ours.mean(),
                     cv_ours_wins=(cv_ours >= cv_best).mean(), top10_overlap=len(set(ours10) & set(alt10)),
                     dropped=", ".join(full.name[p] for p in ours10 if p not in alt10),
                     added=", ".join(full.name[p] for p in alt10 if p not in ours10)))
    print(rows[-1])
out = pd.DataFrame(rows)
out.to_csv(f"{OUT}/heldout_weights.csv", index=False)
print(out.round(3).to_string(index=False))
