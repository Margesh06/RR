"""IPL vs T20I: re-rate on each competition alone (base specification, same eligibility rules) and compare
with the combined rating. Usage: python -I tier_check.py <out_dir>"""
import sys
import pandas as pd

OUT = sys.argv[1]
summ, detail = [], []
for role in ("bat", "bowl"):
    full = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    top = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0).head(10)
    for tier, tag in (("IPL only", "_ipl"), ("T20I only", "_t20i")):
        R = pd.read_pickle(f"{OUT}/ratings_{role}{tag}.pkl")
        both = full.index[full.eligible].intersection(R.index[R.eligible])
        rho = full.loc[both, "PRI"].corr(R.loc[both, "PRI"], method="spearman")
        tier_top = set(R[R.eligible].nlargest(10, "PRI").index)
        in_tier = [p for p in top.index if p in R.index and R.eligible.get(p, False)]
        summ.append(dict(role=role, tier=tier, eligible=int(R.eligible.sum()), overlap_players=len(both),
                         spearman=rho, final_top10_eligible=len(in_tier),
                         final_top10_in_tier_top10=len(tier_top & set(top.index)),
                         final_top10_in_tier_top20=sum(R["rank"].get(p, 99) <= 20 for p in in_tier)))
        for pid in top.index:
            detail.append(dict(role=role, pid=pid, name=top.loc[pid, "name"], final_rank=top.loc[pid, "consensus_rank"],
                               tier=tier, tier_rank=R["rank"].get(pid) if R.eligible.get(pid, False) else None,
                               tier_balls=int(R.n_p.get(pid, 0))))
S = pd.DataFrame(summ)
Dt = pd.DataFrame(detail).pivot_table(index=["role", "final_rank", "name"], columns="tier",
                                      values=["tier_rank", "tier_balls"], aggfunc="first")
S.to_csv(f"{OUT}/tier_check.csv", index=False)
Dt.to_csv(f"{OUT}/tier_check_top10.csv")
print(S.round(2).to_string(index=False))
print(Dt.to_string())
