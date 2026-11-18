"""Model averaging: score the base eligible pool under every ensemble specification, then build a consensus.

Final score = mean PRI (a z-score composite) across all specifications, base included -- averaging the model
outputs, as in Bayesian model averaging. Dead heats (gap < TIE) go to the player with more pressure matches.
Rank statistics across specifications are reported alongside.
consensus_{role}.csv ranks the whole eligible pool (the submitted top 10s, as the brief asks). For the auction lens,
consensus_auction_{role}.csv re-ranks every specification within the IPL 2027 auction pool (official retention lists,
trades.py), with the overall rank alongside. consensus_all_{role}.csv is a copy of the full ranking.
Usage: python -I consensus.py <out_dir>
"""
import os
import sys
import numpy as np
import pandas as pd

OUT = sys.argv[1]
TIE = 0.01      # consensus-score gap below which two players are a statistical dead heat
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.py")).read())   # route()
specs = [line.rstrip("\n").split("\t") for line in open(f"{OUT}/ensemble_specs.jsonl")]
for role in ("bat", "bowl"):
    base = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    pool = base.index[base.eligible]
    ranks = {"base": base.loc[pool, "PRI"].rank(ascending=False)}
    scores = {"base": base.loc[pool, "PRI"]}
    for tag, js in specs:
        try:
            R = pd.read_pickle(f"{OUT}/ratings_{role}{tag}.pkl")
        except FileNotFoundError:
            continue
        ranks[tag] = R.loc[pool, "PRI"].rank(ascending=False)
        scores[tag] = R.loc[pool, "PRI"]
    M_all = pd.DataFrame(ranks)
    Sc = pd.DataFrame(scores)

    def build(M):
        idx = M.index
        C = pd.DataFrame({
            "name": base.loc[idx, "name"],
            "consensus_PRI": Sc.loc[idx].mean(axis=1),
            "PRI_sd": Sc.loc[idx].std(axis=1),
            "mean_rank": M.mean(axis=1),
            "median_rank": M.median(axis=1),
            "best_rank": M.min(axis=1),
            "worst_rank": M.max(axis=1),
            "top10_share": (M <= 10).mean(axis=1),
            "base_rank": M["base"],
            "base_PRI": base.loc[idx, "PRI"],
        })
        # dead heats: scores within TIE of a neighbour (chained) form a cluster ordered by pressure-match evidence
        C["p_matches"] = base.loc[idx, "p_matches"]
        C = C.sort_values("consensus_PRI", ascending=False)
        C["tie_group"] = (C.consensus_PRI.diff().abs().fillna(np.inf) >= TIE).cumsum()
        C = C.sort_values(["tie_group", "p_matches"], ascending=[True, False])
        C["consensus_rank"] = np.arange(1, len(C) + 1)
        C["tied"] = C.groupby("tie_group").name.transform("size") > 1
        return C

    C_all = build(M_all)
    C_all.to_csv(f"{OUT}/consensus_{role}.csv")
    C_all.to_csv(f"{OUT}/consensus_all_{role}.csv")
    M_all.to_pickle(f"{OUT}/ensemble_ranks_{role}.pkl")
    # auction pool: players in no IPL 2027 squad who can be bought on 16 Dec; every specification re-ranked within it
    auc = [p for p in pool if route(base.name[p], base.ipl_2026_team[p])[0] == "Auction"]
    M = M_all.loc[auc].rank(axis=0)
    C = build(M)
    C["overall_rank"] = C_all.consensus_rank.reindex(C.index)
    C.to_csv(f"{OUT}/consensus_auction_{role}.csv")
    M.to_pickle(f"{OUT}/ensemble_ranks_auction_{role}.pkl")
    print(f"\n==== {role}: {M.shape[1]} specifications, auction pool {len(auc)} of {len(pool)}")
    print(C.head(12).round(2).to_string())
