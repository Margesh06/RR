"""Stage 3: team pressure profiles (RR vs IPL) and detail tables for the report.
Usage: python -I stage3_tables.py <data_dir> <out_dir>"""
import sys, pandas as pd, numpy as np
D, OUT = sys.argv[1], sys.argv[2]
b = pd.read_pickle(f"{OUT}/balls.pkl")
tn = pd.read_csv(f"{D}/teams.csv").drop_duplicates("team_id").set_index("team_id").team_name
pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
prof = {}
for role, team_col in (("bat", "batting_team_id"), ("bowl", "bowling_team_id")):
    r = pd.read_pickle(f"{OUT}/resid_{role}.pkl").join(b[[team_col]])
    r = r[(r.tier == "IPL") & (r.year >= 2025)]
    r["team"] = r[team_col].map(tn)
    g = r[r.P].groupby("team").q.mean().rename("pressure_q")
    gn = r[~r.P].groupby("team").q.mean().rename("normal_q")
    ph = r[r.P].pivot_table(index="team", columns="phase", values="q", aggfunc="mean")
    t = pd.concat([g, gn, ph], axis=1).sort_values("pressure_q", ascending=False)
    t["rank"] = range(1, len(t) + 1)
    prof[role] = t
    print(role); print(t.round(1))
    t.to_csv(f"{OUT}/team_profile_{role}.csv")

# RR close-game record 2025-26: the tensest third of matches (peak pressure index >= 8)
m = b[(b.tier == "IPL") & (b.year >= 2025)].groupby("match_id").agg(peak=("PI", "max"), bt1=("batting_team_id", "first"))
mm = pd.read_pickle(f"{OUT}/matches.pkl").set_index("match_id")
m = m.join(mm[["home_team_id", "away_team_id", "win_team_id"]])
close = m[m.peak >= 8]
rows = []
for tid, name in tn.items():
    s = close[(close.home_team_id == tid) | (close.away_team_id == tid)]
    if len(s) >= 5 and tid in set(m.home_team_id):
        rows.append(dict(team=name, close_games=len(s), close_wins=(s.win_team_id == tid).sum()))
cg = pd.DataFrame(rows).assign(win_pct=lambda d: d.close_wins / d.close_games * 100).sort_values("win_pct", ascending=False)
print(cg); cg.to_csv(f"{OUT}/close_games.csv", index=False)

# RR squad ratings
for role in ("bat", "bowl"):
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    rr = R[R.ipl_2026_team == "Rajasthan Royals"]
    print(role, "RR players"); print(rr[["name", "n_p", "pq", "q_base", "lift", "PRI", "rank", "eligible"]].round(2).to_string())
