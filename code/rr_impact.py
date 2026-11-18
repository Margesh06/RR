"""Wins added for RR: if a candidate had taken the pressure balls RR gave to its below-par pressure performers
in IPL 2026, how many more games would RR expect to win per season?

  slot      = RR 2026 pressure balls by players whose Pressure Quality (PQ) is below league average,
              role-matched: pace for pace, spin for spin; top order (1-3) or middle / finish (4+) for batters
  gain/ball = (PQ_candidate - PQ_incumbent) / 100 runs
  wins      = sum over those balls of gain x (win probability per run at that ball's pressure level)
The win-per-run rate is estimated from the data in Pressure Index bands (no-intercept fit of WPA on run value).
Usage: python -I rr_impact.py <out_dir>"""
import os
import sys
import numpy as np
import pandas as pd

OUT = sys.argv[1]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.py")).read())   # route()
RR, SEASON = 3, "IPL 2026"
BANDS = [1.5, 2, 3, 5, np.inf]
b = pd.read_pickle(f"{OUT}/balls.pkl")
rows, auc, allp = [], [], []
for role, team_col in (("bat", "batting_team_id"), ("bowl", "bowling_team_id")):
    r = pd.read_pickle(f"{OUT}/resid_{role}.pkl").join(b[[team_col, "comp_name"]])
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    top = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0).head(10)
    P = r[r.P].copy()
    P["band"] = pd.cut(P.PI, BANDS, right=False)
    k = P.groupby("band", observed=True).apply(lambda d: (d.rv * d.wpa).sum() / (d.rv ** 2).sum())
    rr = P[(P[team_col] == RR) & (P.comp_name == SEASON)].copy()
    rr["k"] = rr.band.map(k).astype(float)
    rr["pq_inc"] = rr.pid.map(R.pq)
    if role == "bat":
        grp = lambda pid: "top order" if R.bat_pos.get(pid, 9) <= 3 else "middle / finish"
    else:
        grp = lambda pid: "spin" if R.pace_spin.get(pid) == "Spin" else "pace"
    rr["slot"] = rr.pid.map(grp)
    # below par = below the average player on an IPL 2026 pressure ball (ball-weighted), not below zero: with the
    # ground and opponent adjustment the zero point is the average T20 ball of the whole data set, not the IPL's
    lg_pq = P[P.comp_name == SEASON].pid.map(R.pq).mean()
    weak = rr[rr.pq_inc < lg_pq]
    # posterior sd of PQ: per-ball sd of quality / sqrt(pressure balls + prior balls)
    sd_q = r[r.P].q.std()
    C = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0)
    pool = pd.read_csv(f"{OUT}/consensus_auction_{role}.csv", index_col=0).head(20)
    pool = pool.assign(arank=pool.consensus_rank, consensus_rank=pool.overall_rank)
    CA = pd.read_csv(f"{OUT}/consensus_all_{role}.csv", index_col=0).head(10)   # best of all players, incl. retained
    for pid, c in pd.concat([top.assign(_set="top"), pool.assign(_set="auction"), CA.assign(_set="all")]).iterrows():
        slot = grp(pid)
        s = weak[weak.slot == slot]
        pq = R.pq[pid]
        se = sd_q / np.sqrt(R.n_p[pid] + 500)
        gain = ((pq - s.pq_inc) / 100 * s.k).sum()
        per_se = (s.k.sum() / 100) * se
        inc = s.groupby("pid").size().sort_values(ascending=False)
        {"top": rows, "auction": auc, "all": allp}[c._set].append(dict(role=role, pid=pid, name=c["name"], rank=c.consensus_rank, team26=R.ipl_2026_team[pid],
                         slot=slot, slot_balls=len(s), slot_pq=(s.pq_inc.mean() if len(s) else np.nan),
                         replaces=", ".join(R.name[i] for i in inc.index[:3]),
                         pq=pq, wins=gain, wins_lo=gain - 1.28 * per_se, wins_hi=gain + 1.28 * per_se,
                         already_rr=R.ipl_2026_team[pid] == "Rajasthan Royals", nation=R.nation[pid],
                         why=route(c["name"], R.ipl_2026_team[pid])[1],
                         arank=c.get("arank", np.nan)))
    print(role, "win-prob per run by PI band:", k.round(4).to_dict())
    print(role, "IPL 2026 average PQ:", round(lg_pq, 1), "RR 2026 below-par pressure balls by slot:", weak.groupby("slot").size().to_dict())
res = pd.DataFrame(rows)
res.to_csv(f"{OUT}/rr_impact.csv", index=False)
print(res.drop(columns=["pid", "why"]).round(2).to_string(index=False))
# 2027 auction pool (official retention lists): the best auction-available players by ranking, same wins-added replay
pd.DataFrame(allp).to_csv(f"{OUT}/rr_impact_all.csv", index=False)
A = pd.DataFrame(auc)
A.to_csv(f"{OUT}/rr_auction.csv", index=False)
print("== auction pool")
print(A.drop(columns=["pid", "why", "replaces"]).round(2).to_string(index=False))
