"""Scouting-card data for the final top 10s: headline pressure numbers, competition split, RR fit, wins added,
and each player's biggest single pressure moment (largest win-probability swing in his favour).
Usage: python -I cards.py <data_dir> <out_dir>"""
import sys
import pandas as pd

D, OUT = sys.argv[1], sys.argv[2]
b = pd.read_pickle(f"{OUT}/balls.pkl")
teams = pd.read_csv(f"{D}/teams.csv").drop_duplicates("team_id").set_index("team_id").team_name
imp = pd.read_csv(f"{OUT}/rr_impact.csv").set_index("pid")
tier = pd.read_csv(f"{OUT}/tier_check_top10.csv", header=[0, 1], index_col=[0, 1, 2])
tier.columns = [f"{a}|{c}" for a, c in tier.columns]
tier = tier.reset_index().set_index("name")


def moment(row, role):
    team = teams.get(row.bowling_team_id if role == "bat" else row.batting_team_id, "?")
    if row.bowler_wkt and role == "bowl":
        what = f"took the wicket ({row.dismissal_type.lower()})"
    elif row.striker_out and role == "bat":
        what = "was dismissed"
    elif row.is_six:
        what = "hit a six" if role == "bat" else "conceded a six"
    elif row.is_four:
        what = "hit a four" if role == "bat" else "conceded a four"
    else:
        n = int(row.runs if role == "bat" else row.total_runs)
        what = (f"took {n} run{'s' if n != 1 else ''}" if role == "bat"
                else ("bowled a dot" if n == 0 else f"conceded {n}"))
    if row.innings == 2:
        sit = f"{int(row.runs_needed)} needed off {int(row.balls_left)}"
    else:
        sit = f"{int(row.runs_before)}/{int(row.wkts_before)} after {int((120 - row.balls_left) // 6)}.{int((120 - row.balls_left) % 6)} overs"
    return f"{row.comp_name} v {team}: {what} with {sit}"


rows = []
for role, wcol, pcol in (("bat", "bat_wpa", "striker_id"), ("bowl", "bowl_wpa", "bowler_id")):
    top = pd.read_csv(f"{OUT}/top_{role}.csv", index_col=0).head(10)
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    for i, (pid, r) in enumerate(top.iterrows(), 1):
        mine = b[(b[pcol] == pid) & (b.PI >= 1.5)]
        best = mine.loc[mine[wcol].idxmax()]
        t = tier.loc[r["name"]]
        im = imp.loc[pid]
        rows.append(dict(
            role=role, rank=i, pid=pid, name=r["name"], team26=r.ipl_2026_team, tied=r.tied,
            score=r.consensus_PRI, specs_top10=r.top10_share, n_p=int(r.n_p), p_matches=int(r.p_matches),
            succ=r.succ_raw, n_succ=int(round(r.succ_raw * r.p_matches)), lift=r.lift,
            sr=r.get("SR_p"), xsr=r.get("xSR_p"), econ=r.get("econ_p"), xecon=r.get("xecon_p"),
            outs=r.outs_p, xouts=r.exp_outs_p, death=R.death_share_p[pid], pp=R.pp_share_p[pid],
            ko_balls=int(R.ko_balls_p[pid]), ipl_share=R.ipl_share_p[pid],
            style=(R.bowl_type[pid] if role == "bowl" else f"{R.hand[pid]}, usually no. {R.bat_pos[pid]:.0f}"),
            ipl_rank=t.get("tier_rank|IPL only"), t20i_rank=t.get("tier_rank|T20I only"),
            slot=im.slot, replaces=im.replaces, wins=im.wins, wins_lo=im.wins_lo, wins_hi=im.wins_hi,
            moment=moment(best, role), moment_swing=best[wcol] * 100, moment_year=int(best.year)))
C = pd.DataFrame(rows)
C.to_csv(f"{OUT}/cards.csv", index=False)
print(C[["role", "rank", "name", "style", "ipl_rank", "t20i_rank", "wins", "moment", "moment_swing"]].round(2).to_string(index=False))
