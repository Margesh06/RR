"""Test 8: the ground and opponent adjustment. Compares the final method with the same 73-specification pipeline run
without it (CONTEXT_ADJ = False, in a separate output folder):
  1 prediction: indices built on 2022-24 by each method, scored against the same 2025-26 targets
  2 how big the effects are: spread of ground effects, examples of opponent effects
  3 what it changes in the top 10s
Usage: python -I ctx_compare.py <out_without_adjustment> <out_final>"""
import sys
import pandas as pd

OLD, NEW = sys.argv[1], sys.argv[2]
rows, moves = [], []
for role in ("bat", "bowl"):
    tags = [l.split("\t")[0] for l in open(f"{OLD}/ensemble_specs.jsonl")]

    def ens(o):
        return pd.concat([pd.read_pickle(f"{o}/ratings_{role}_to2024{t}.pkl").PRI for t in [""] + tags], axis=1).mean(axis=1)
    pred = {"Without ground/opponent adjustment": ens(OLD), "With ground/opponent adjustment (final)": ens(NEW)}
    res_o, res_n = pd.read_pickle(f"{OLD}/resid_{role}.pkl"), pd.read_pickle(f"{NEW}/resid_{role}.pkl")
    te_o, te_n = res_o[(res_o.year >= 2025) & res_o.P], res_n[(res_n.year >= 2025) & res_n.P]
    n_te = te_o.groupby("pid").size()
    old24 = pd.read_pickle(f"{OLD}/ratings_{role}_to2024.pkl")
    pool = old24.index[old24.n_p >= 60].intersection(n_te[n_te >= 60].index)
    tg = {"future_q_unadjusted": te_o.groupby("pid").q.mean(), "future_q_adjusted": te_n.groupby("pid").q.mean(),
          "future_wpa": te_o.groupby("pid").wpa.mean()}
    for pn, p in pred.items():
        r = dict(role=role, method=pn, players=len(pool))
        for tn, t in tg.items():
            r[tn] = p.reindex(pool).corr(t.reindex(pool), method="spearman")
        rows.append(r)
    # what changes in the top 10s
    co = pd.read_csv(f"{OLD}/consensus_{role}.csv", index_col=0)
    cn = pd.read_csv(f"{NEW}/consensus_{role}.csv", index_col=0)
    for pid in co.index[:10].union(cn.index[:10]):
        ro, rn = int(co.consensus_rank.get(pid, 999)), int(cn.consensus_rank.get(pid, 999))
        if (ro <= 10) != (rn <= 10):
            moves.append(dict(role=role, pid=pid, name=cn.name.get(pid, co.name.get(pid)), rank_without=ro, rank_with=rn))
out = pd.DataFrame(rows)
out.to_csv(f"{NEW}/ctx_compare.csv", index=False)
pd.DataFrame(moves).to_csv(f"{NEW}/ctx_moves.csv", index=False)
pd.read_csv(f"{OLD}/reliability.csv").to_csv(f"{NEW}/reliability_without_context.csv", index=False)
print(out.round(3).to_string(index=False))
print(pd.DataFrame(moves).to_string(index=False))

# effect sizes (final run)
b = pd.read_pickle(f"{NEW}/balls.pkl")
mt = pd.read_pickle(f"{NEW}/matches.pkl").set_index("match_id")
summ = {}
for role, opp in (("bat", "bowler_id"), ("bowl", "striker_id")):
    C = pd.read_pickle(f"{NEW}/context_{role}_9999.pkl")
    s = b.loc[C.index]
    v = pd.DataFrame({"v": C.v_r, "venue": s.match_id.map(mt.venue_id), "m": s.match_id}).groupby("venue").agg(
        v=("v", "first"), n=("m", "nunique"))
    big = v[v.n >= 10]
    summ[f"{role}_grounds"] = len(v)
    summ[f"{role}_grounds_10plus"] = len(big)
    summ[f"{role}_ground_spread_rpo"] = (big.v.max() - big.v.min()) * 6
    o = pd.DataFrame({"o": C.o_r, "opp": s[opp]}).groupby("opp").o.first() * 100
    summ[f"{role}_opp_sd_per100"] = o.std()
    if role == "bat":
        summ["bumrah"], summ["narine"] = o[2933], o[781]
    else:
        summ["sooryavanshi"], summ["abhishek"] = o[50284], o[6281]
pd.Series(summ).to_csv(f"{NEW}/context_summary.csv", header=["value"])
print(pd.Series(summ).round(2))
