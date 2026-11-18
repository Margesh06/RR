"""Beyond the top 10:
  gems      - active players below the eligibility floor whose (heavily shrunk) rating would still place them high
  dippers   - eligible players with a strong normal level who are clearly worse under pressure (negative Lift)
  famous    - well-known names outside the top 10 (including the best performers RR cannot buy), with the data reason
The top 10s are ranked within the IPL 2027 auction pool; gems are auction-pool players too.
Usage: python -I extras.py <out_dir>"""
import os
import sys
import pandas as pd

OUT = sys.argv[1]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.py")).read())   # NOT_AVAILABLE
FAMOUS = {"bat": ["Heinrich Klaasen", "Nicholas Pooran", "Jos Buttler", "Travis Head", "Hardik Pandya", "Virat Kohli",
                  "Shubman Gill", "Lokesh Rahul", "Rishabh Pant", "Glenn Maxwell", "David Miller", "Andre Russell"],
          "bowl": ["Arshdeep Singh", "Mohammed Siraj", "Bhuvneshwar Kumar", "Pat Cummins", "Trent Boult",
                   "Yuzvendra Chahal", "Axar Patel", "Harshal Patel", "Mitchell Starc", "Wanindu Hasaranga"]}
rows = {"gems": [], "dippers": [], "famous": [], "young": []}
for role in ("bat", "bowl"):
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    C = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0)          # auction pool
    CA = pd.read_csv(f"{OUT}/consensus_all_{role}.csv", index_col=0)    # every eligible player
    R["crank"] = CA.consensus_rank
    R["route"] = [route(n, t)[0] for n, t in zip(R["name"], R.ipl_2026_team)]
    R["top10"] = C.top10_share
    if role == "bat":
        R["rate"], R["xrate"] = R.runs_p / R.n_p * 100, R.exp_runs_p / R.n_p * 100
    else:
        R["rate"], R["xrate"] = R.runs_p / R.legal_p * 6, R.exp_runs_p / R.legal_p * 6
    pool = R[R.eligible]
    n_pool = len(pool)

    def style(r):
        if role == "bowl":
            t = r.bowl_type.lower()
            return ("left-arm wrist spinner" if "chinaman" in t else "leg-spinner" if "leg" in t else
                    "off-spinner" if "offbreak" in t else "left-arm spinner" if "orthodox" in t else "pace bowler")
        n = r.bat_pos
        return "opener" if n <= 2 else "top-order batter" if n <= 3 else "middle-order batter" if n <= 5 else "finisher"
    base = dict(role=role)

    # Bangladesh players: only the seven the BCB registered for the 2027 auction can be bought
    bd_out = (R.nation == "Bangladesh") & ~R["name"].isin(BD_REGISTERED)
    g = R[~R.sample_ok & (R.n_p >= 40) & (R.last_year >= 2025) & ~R.nation.isin(["Pakistan"]) & ~bd_out
          & ~R["name"].isin(list(NOT_AVAILABLE)) & (R.route == "Auction")].copy()
    apool = R.loc[C.index]      # rated against the full eligible pool, like the main ranking
    g["would_rank"] = g.PRI.apply(lambda v: int((apool.PRI > v).sum() + 1))
    g = g[g.would_rank <= 20].sort_values("PRI", ascending=False).head(6)
    for pid, r in g.iterrows():
        rows["gems"].append(dict(base, pid=pid, name=r["name"], team=r.ipl_2026_team, style=style(r),
                                 uncapped=r["name"] in UNCAPPED, nation=r.nation, n_p=int(r.n_p),
                                 matches=int(r.p_matches), rate=r.rate, xrate=r.xrate, outs=int(r.outs_p),
                                 xouts=r.exp_outs_p, would_rank=int(r.would_rank), last_year=int(r.last_year)))

    y = R[R["name"].isin([n for n in UNCAPPED if AGE.get(n, 99) <= 25]) & (R.n_p >= 40)].copy()
    y["would_rank"] = y.PRI.apply(lambda v: int((pool.PRI > v).sum() + 1))
    for pid, r in y.sort_values("PRI", ascending=False).iterrows():
        rows["young"].append(dict(base, pid=pid, name=r["name"], age=AGE[r["name"]], team=r.ipl_2026_team, style=style(r),
                                  n_p=int(r.n_p), matches=int(r.p_matches), rate=r.rate, xrate=r.xrate, outs=int(r.outs_p),
                                  xouts=r.exp_outs_p, would_rank=int(r.would_rank)))

    d = pool[(pool.q_base > pool.q_base.median()) & (pool.lift <= -5)].sort_values("lift").head(5)
    for pid, r in d.iterrows():
        rows["dippers"].append(dict(base, pid=pid, name=r["name"], team=r.ipl_2026_team, n_p=int(r.n_p),
                                    matches=int(r.p_matches), lift=r.lift, rate=r.rate, xrate=r.xrate,
                                    succ=r.succ_raw, crank=int(r.crank), n_pool=n_pool))

    for name in FAMOUS[role]:
        m = R[R["name"] == name]
        if m.empty:
            continue
        pid, r = m.index[0], m.iloc[0]
        if pid in C.index and C.loc[pid, "consensus_rank"] <= 10:
            continue
        # share by which he beats the average player in the same spots (positive = better, both roles)
        gap = (r.rate - r.xrate) / r.xrate if role == "bat" else (r.xrate - r.rate) / r.xrate
        rank = C.loc[pid, "consensus_rank"] if pid in C.index else None
        orank = int(CA.loc[pid, "consensus_rank"]) if pid in CA.index else None
        t27 = team27(name, r.ipl_2026_team)
        if name in NOT_AVAILABLE and not r.sample_ok:
            reason = NOT_AVAILABLE[name]
        elif not r.sample_ok:
            reason = "not enough pressure balls to rate fairly"
        elif r.lift <= -5:
            reason = "clearly worse under pressure than in his normal games"
        elif gap < -0.03:
            reason = ("scores slower than an average batter would in the same spots" if role == "bat"
                      else "concedes more than an average bowler would in the same spots")
        elif rank is not None and rank <= 16:
            reason = f"good under pressure, just outside the top 10 (#{int(rank)})"
        elif abs(gap) <= 0.03:
            reason = "about average under pressure"
        elif r.lift < 0:
            reason = (f"above average under pressure, but below his own normal level (Lift {r.lift:+.1f}), "
                      "which the score counts against him")
        elif r.n_p < 200:
            reason = f"strong numbers, but only {int(r.n_p)} pressure balls, so his rating is pulled toward his normal level"
        elif (r.succ_raw or 0) < 0.6:
            reason = "good on average, but delivers in fewer tense games"
        else:
            reason = "good under pressure, but behind the top 10"
        if name in NOT_AVAILABLE and r.sample_ok and not reason.startswith(NOT_AVAILABLE[name]):
            reason = f"{reason}; also {NOT_AVAILABLE[name]}"
        rows["famous"].append(dict(base, pid=pid, name=name, team=r.ipl_2026_team,
                                   crank=(int(r.crank) if pd.notna(r.crank) else None), n_pool=n_pool,
                                   n_p=int(r.n_p), rate=r.rate, xrate=r.xrate, lift=r.lift, succ=r.succ_raw,
                                   matches=int(r.p_matches), reason=reason))
for k, v in rows.items():
    pd.DataFrame(v).to_csv(f"{OUT}/extra_{k}.csv", index=False)
    print(f"== {k}")
    print(pd.DataFrame(v).drop(columns=["pid"]).round(2).to_string(index=False))
