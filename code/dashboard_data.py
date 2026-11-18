"""Export the dashboard data: derived ratings only (no ball-by-ball data leaves the pipeline).
  - every eligible player's headline numbers, consensus result and IPL-only / T20I-only rank
  - PRI under all 288 grid specifications (the model lab)
  - match-level success flags for the consistency strip
  - RR team profile, wins added and player-card extras
Usage: python -I dashboard_data.py <out_dir> <grid_dir> <json_path>"""
import json
import os
import sys
import numpy as np
import pandas as pd

OUT, GRID, DST = sys.argv[1:4]
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.py")).read())   # TRADES, AS_OF
NATION_FIX = {781: "West Indies", 4219: "India", 88: "South Africa"}
matches = pd.read_pickle(f"{OUT}/matches.pkl").set_index("match_id")
specs = [l.rstrip("\n").split("\t") for l in open(f"{GRID}/grid_specs.jsonl")]
grid_keys = ["PRESSURE", "K_BASE", "W", "HALF_LIFE_YRS", "KO_MULT", "OPP_WEIGHTING"]
spec_list = [json.loads(js) for _, js in specs]
W_OPTS = [{"pq": 0.45, "succ": 0.20, "lift": 0.20, "wpa": 0.15}, {"pq": 0.35, "succ": 0.35, "lift": 0.15, "wpa": 0.15},
          {"pq": 0.30, "succ": 0.20, "lift": 0.35, "wpa": 0.15}, {"pq": 0.25, "succ": 0.25, "lift": 0.25, "wpa": 0.25}]
spec_idx = [[[1.25, 1.5, 2.0].index(s["PRESSURE"]), [200, 500, 1000].index(s["K_BASE"]), W_OPTS.index(s["W"]),
             int(s["HALF_LIFE_YRS"] == 2.5), int(s["KO_MULT"] == 1.25), int(s["OPP_WEIGHTING"])] for s in spec_list]
cards = pd.read_csv(f"{OUT}/cards.csv").set_index("pid")
auc = pd.read_csv(f"{OUT}/rr_auction.csv").set_index("pid")


def r(x, d=2):
    return None if x is None or (isinstance(x, float) and np.isnan(x)) else round(float(x), d)


data = {"specs": spec_idx, "roles": {}}
for role in ("bat", "bowl"):
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    C = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0)          # every eligible player (the submitted ranking)
    CU = pd.read_csv(f"{OUT}/consensus_auction_{role}.csv", index_col=0)  # IPL 2027 auction pool
    CA = pd.read_csv(f"{OUT}/consensus_all_{role}.csv", index_col=0)    # every eligible player
    ipl = pd.read_pickle(f"{OUT}/ratings_{role}_ipl.pkl")
    t20 = pd.read_pickle(f"{OUT}/ratings_{role}_t20i.pkl")
    pm = pd.read_pickle(f"{OUT}/pmatch_{role}.pkl")
    pm = pm[pm.qualifies].join(matches[["match_date", "comp_name"]], on="match_id")
    pool = C.index
    G = np.array([pd.read_pickle(f"{GRID}/ratings_{role}{tag}.pkl").PRI.reindex(pool).to_numpy() for tag, _ in specs])
    players = []
    for j, pid in enumerate(pool):
        x, c = R.loc[pid], C.loc[pid]
        if role == "bat":
            stat = dict(rate=x.runs_p / x.n_p * 100, xrate=x.exp_runs_p / x.n_p * 100, rate_np=x.runs_np / x.n_np * 100)
            style = f"{x.hand}, usually no. {x.bat_pos:.0f}"
        else:
            stat = dict(rate=x.runs_p / x.legal_p * 6, xrate=x.exp_runs_p / x.legal_p * 6, rate_np=x.runs_np / x.legal_np * 6)
            style = x.bowl_type
        g = pm[pm.pid == pid].sort_values("match_date")
        p = dict(id=int(pid), name=x["name"], nation=NATION_FIX.get(pid, x.nation), team=x.ipl_2026_team, style=style,
                 score=r(c.consensus_PRI, 3), rank=int(c.consensus_rank), arank=(int(CU.consensus_rank[pid]) if pid in CU.index else None),
                 atop10=(r(CU.top10_share[pid]) if pid in CU.index else None), tied=bool(c.tied), top10=r(c.top10_share),
                 n_p=int(x.n_p), pm=int(x.p_matches), outs=int(x.outs_p), xouts=r(x.exp_outs_p, 1),
                 lift=r(x.lift, 1), pq=r(x.pq, 1), base=r(x.q_base, 1), succ=r(x.succ_raw), wpa=r(x.wpa_s, 2),
                 death=r(x.death_share_p), ipl_share=r(x.ipl_share_p), ko=int(x.ko_balls_p),
                 ipl_rank=(int(ipl["rank"][pid]) if pid in ipl.index and ipl.eligible[pid] else None),
                 t20_rank=(int(t20["rank"][pid]) if pid in t20.index and t20.eligible[pid] else None),
                 grid=[r(v, 3) for v in G[:, j]],
                 strip=[[d.strftime("%Y-%m-%d"), int(s), cn] for d, s, cn in zip(g.match_date, g.success, g.comp_name)],
                 **{k: r(v) for k, v in stat.items()})
        if ((cards.index == pid) & (cards.role == role)).any():
            k = cards[(cards.index == pid) & (cards.role == role)].iloc[0]
            p.update(moment=k.moment, moment_swing=r(k.moment_swing, 0), slot=k.slot, replaces=k.replaces,
                     wins=r(k.wins), wins_lo=r(k.wins_lo), wins_hi=r(k.wins_hi))
        elif ((auc.index == pid) & (auc.role == role)).any():
            k = auc[(auc.index == pid) & (auc.role == role)].iloc[0]
            p.update(slot=k.slot, replaces=k.replaces, wins=r(k.wins), wins_lo=r(k.wins_lo), wins_hi=r(k.wins_hi))
        # 2027 availability from the official retention lists
        p["team26"] = x.ipl_2026_team
        p["team"] = team27(x["name"], x.ipl_2026_team) or "-"
        p["route"] = list(route(x["name"], x.ipl_2026_team))
        rb = released_by(x["name"], x.ipl_2026_team)
        if rb:
            p["released_by"] = rb
        if p["name"] in TRADES:
            p["traded_from"] = TRADES[p["name"]][0]
        if p["name"] in NOT_AVAILABLE:
            p["na"] = NOT_AVAILABLE[p["name"]]
        if p["name"] in UNSOLD_2026:
            p["unsold26"] = True
        players.append(p)
    # closest players RR can buy: same broad role, nearest on the standardised playing profile
    feats = (["pq", "q_base", "death_share_p", "bat_pos"] if role == "bat" else ["pq", "q_base", "death_share_p", "pp_share_p"])
    Z = R.loc[pool, feats].astype(float)
    Z = (Z - Z.mean()) / Z.std()
    grp = (R.loc[pool, "bat_pos"] <= 3) if role == "bat" else (R.loc[pool, "pace_spin"] == "Spin")
    buyable = [q for q in pool if q in CU.index and route(R.name[q], R.ipl_2026_team[q])[0] == "Auction"]
    for p in players:
        q = p["id"]
        cand = [c for c in buyable if c != q and grp[c] == grp[q]]
        dist = ((Z.loc[cand] - Z.loc[q]) ** 2).sum(axis=1).sort_values()
        p["similar"] = [[int(c), R.name[c], int(C.consensus_rank[c])] for c in dist.index[:3]]
    data["roles"][role] = players
    data.setdefault("n_all", {})[role] = len(CA)
    RA = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    data.setdefault("overall", {})[role] = [
        dict(rank=int(c.consensus_rank), name=c["name"], route=route(c["name"], RA.ipl_2026_team[q])[0],
             team=team27(c["name"], RA.ipl_2026_team[q]) or "-",
             arank=(int(CU.consensus_rank[q]) if q in CU.index else None)) for q, c in CA.head(10).iterrows()]

tp = {role: pd.read_csv(f"{OUT}/team_profile_{role}.csv") for role in ("bat", "bowl")}
data["teams"] = {role: tp[role].round(2).to_dict(orient="records") for role in tp}
data["close"] = pd.read_csv(f"{OUT}/close_games.csv").round(3).to_dict(orient="records")
data["reliability"] = pd.read_csv(f"{OUT}/reliability.csv").round(3).to_dict(orient="records")
data["tier"] = pd.read_csv(f"{OUT}/tier_check.csv").round(3).to_dict(orient="records")
# beyond the top 10: same selection rules as the report (Section 10)
top_ids = {(r, p["id"]) for r in data["roles"] for p in data["roles"][r] if p["rank"] <= 10}
gems = pd.read_csv(f"{OUT}/extra_gems.csv")
gems = gems[gems.matches >= 5].sort_values(["role", "would_rank"]).head(6)
dips = pd.read_csv(f"{OUT}/extra_dippers.csv")
fam = pd.read_csv(f"{OUT}/extra_famous.csv")
dd = pd.concat([dips, fam[fam.reason.str.startswith("clearly worse")]]).drop_duplicates("name")
not_top = np.array([(r, i) not in top_ids for r, i in zip(dd.role, dd.pid)])
dd = dd[not_top & (dd.team != "Rajasthan Royals").to_numpy() & (dd.n_p >= 200).to_numpy()].sort_values("lift")
ff = fam[~fam.name.isin(dd.name)].sort_values(["role", "crank"]).groupby("role").head(7)
clean = lambda df, cols: [{k: (None if pd.isna(v) else (round(float(v), 2) if isinstance(v, float) else (int(v) if hasattr(v, "item") and not isinstance(v, (bool,)) else v))) for k, v in rec.items()} for rec in df[cols].to_dict(orient="records")]
def to27(df):
    df = df.copy()
    df["route"] = [route(n, t)[0] for n, t in zip(df.name, df.team)]
    df["released_by"] = [released_by(n, t) for n, t in zip(df.name, df.team)]
    df["team"] = [team27(n, t) or "-" for n, t in zip(df.name, df.team)]
    return df


gems = to27(gems)
data["gems"] = clean(gems, ["role", "name", "team", "route", "released_by", "style", "uncapped", "n_p", "matches", "rate", "xrate", "outs", "xouts", "would_rank"])
data["dippers"] = clean(dd, ["role", "pid", "name", "lift", "rate", "xrate", "succ", "matches", "crank", "n_pool"])
data["famous"] = clean(ff, ["role", "pid", "name", "crank", "n_pool", "rate", "xrate", "reason"])
data["trades_as_of"] = AS_OF
ia = pd.read_csv(f"{OUT}/rr_impact_all.csv")
data["ideal"] = [dict(name=ia.loc[ia[ia.slot == s_].wins.idxmax(), "name"], wins=r(ia[ia.slot == s_].wins.max()))
                 for s_ in ("middle / finish", "pace", "spin")]
data["rr27"] = dict(purse=RR_PURSE, slots=RR_SLOTS, overseas=RR_OVERSEAS_SLOTS,
                    first=["Tushar Deshpande", "Mujeeb Ur Rahman", "Daryl Mitchell"],
                    backup=["Lockie Ferguson", "Wanindu Hasaranga", "Matheesha Pathirana", "Mark Adair"],
                    fee={"Matheesha Pathirana": "Rs 18 Cr at the 2026 auction", "Wanindu Hasaranga": "Rs 2 Cr (base) at the 2026 auction",
                         "Tushar Deshpande": "Rs 6.5 Cr with RR", "Daryl Mitchell": "unsold at the 2026 auction",
                         "Mujeeb Ur Rahman": "unsold at the 2026 auction", "Mark Adair": "has never played in the IPL"})
data["young"] = clean(to27(pd.read_csv(f"{OUT}/extra_young.csv")), ["role", "name", "age", "team", "released_by", "style", "n_p", "matches", "rate", "xrate", "outs", "xouts"])
data["compare"] = pd.read_csv(f"{OUT}/compare_methods.csv").round(2).to_dict(orient="records")
sim = pd.read_csv(f"{OUT}/simulation.csv")
data["sim"] = sim[~sim.scenario.str.startswith("As the data")].round(3).to_dict(orient="records")
data["ctx"] = dict(rows=pd.read_csv(f"{OUT}/ctx_compare.csv").round(3).to_dict(orient="records"),
                   moves=pd.read_csv(f"{OUT}/ctx_moves.csv").to_dict(orient="records"),
                   size=pd.read_csv(f"{OUT}/context_summary.csv", index_col=0).value.round(2).to_dict(),
                   leakfree=pd.read_csv(f"{OUT}/leakfree_reliability.csv").round(3).to_dict(orient="records"),
                   perm=pd.read_csv(f"{OUT}/permutation_lift.csv").round(3).to_dict(orient="records"))
data["hw"] = pd.read_csv(f"{OUT}/heldout_weights.csv").round(3)[["role", "best_weights", "cv_chosen", "cv_ours", "cv_ours_wins", "top10_overlap"]].to_dict(orient="records")
with open(DST, "w") as f:
    json.dump(data, f, separators=(",", ":"))
print("players:", {k: len(v) for k, v in data["roles"].items()}, "bytes:", len(json.dumps(data, separators=(",", ":"))))
