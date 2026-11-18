"""Stage 1: rebuild ball-level match state, fit win-probability (WP) and expected-runs (ER)
models, and compute the Leverage Index (pressure) for every delivery.

Usage: python -I stage1_models.py <data_dir> <out_dir>
"""
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor
from sklearn.model_selection import GroupKFold
from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

D, OUT = sys.argv[1], sys.argv[2]
rng = np.random.default_rng(7)

b = pd.read_csv(f"{D}/ball_by_ball.csv", low_memory=False)
m = pd.read_csv(f"{D}/matches.csv")
c = pd.read_csv(f"{D}/competitions.csv")
m = m.merge(c, on="comp_id", how="left")
m["match_date"] = pd.to_datetime(m["match_date"])
m["year"] = m.match_date.dt.year

# ---------------------------------------------------------------- match filters
bad_result = m.result.str.contains("Abandon|No Result|no result", case=False, na=True)
reduced = m.first_inn_revised_overs.notna() | m.second_inn_revised_overs.notna() | m.revised_target.notna()
m["is_tie"] = m.result.str.contains("Tie|Super Over", case=False, na=False)
keep = m[~bad_result & ~reduced & m.win_team_id.notna()].copy()
print(f"matches: total={len(m)} abandoned/NR={bad_result.sum()} rain-reduced={reduced.sum()} kept={len(keep)}")

# competition tier
def comp_tier(r):
    if str(r.comp_name).startswith("IPL"):
        return "IPL"
    if r.match_format == "T20I":
        return "T20I"
    return "A-team"
keep["tier"] = keep.apply(comp_tier, axis=1)

b = b[b.match_id.isin(keep.match_id) & (b.innings <= 2)].copy()
b = b.sort_values(["match_id", "innings", "overid", "over_ball_num"]).reset_index(drop=True)

# ---------------------------------------------------------------- ball semantics
b["extras_type"] = b.extras_type.fillna("None")
b["legal"] = ~b.extras_type.isin(["wide", "Overstep", "other"])
b["total_runs"] = b.runs + b.extras1_runs + b.extras_2_runs
# bowler is charged bat runs + wides + no-balls; not byes / leg-byes / penalty
b["bowler_extras"] = np.where(b.extras_type.isin(["wide", "Overstep", "other"]), b.extras1_runs + b.extras_2_runs, 0)
b["bowler_runs"] = b.runs + b.bowler_extras
b["is_wicket"] = b.is_wicket.astype(str).str.lower().eq("true")
non_bowler_dis = {"RunOut", "Retire Out", "Obstracting the field", "Obstructing the field"}
b["bowler_wkt"] = b.is_wicket & ~b.dismissal_type.isin(non_bowler_dis)
b["striker_out"] = b.is_wicket & (b.dismissed_player_id.fillna(-1).astype(int) == b.striker_id)
b["is_four"] = b.is_four.astype(str).str.lower().eq("true")
b["is_six"] = b.is_six.astype(str).str.lower().eq("true")

g = b.groupby(["match_id", "innings"], sort=False)
b["runs_before"] = g.total_runs.cumsum() - b.total_runs
b["wkts_before"] = g.is_wicket.cumsum() - b.is_wicket.astype(int)
b["legal_before"] = g.legal.cumsum() - b.legal.astype(int)
b["balls_left"] = (120 - b.legal_before).clip(lower=0)
b["wkts_in_hand"] = (10 - b.wkts_before).clip(lower=0)

inn_tot = b.groupby(["match_id", "innings"]).total_runs.sum().unstack()
b = b.merge(inn_tot[1].rename("first_inn_total"), left_on="match_id", right_index=True, how="left")
b["target"] = b.first_inn_total + 1
b["runs_needed"] = np.where(b.innings == 2, b.target - b.runs_before, np.nan)

b = b.merge(keep[["match_id", "win_team_id", "is_tie", "tier", "year", "match_date", "stage", "knock_out",
                  "comp_name", "match_format"]], on="match_id", how="left")
b["bat_won"] = (b.win_team_id == b.batting_team_id).astype(int)

# scoring environment: average runs per over for each competition-tier x year
env = (b.groupby(["tier", "year"]).agg(r=("total_runs", "sum"), l=("legal", "sum")))
env["env_rpo"] = env.r / env.l * 6
b = b.merge(env[["env_rpo"]], left_on=["tier", "year"], right_index=True, how="left")
print(env)

# ---------------------------------------------------------------- expected-runs model (context-neutral run value)
# fit on first innings only (second innings is truncated by the chase)
inn1 = b[b.innings == 1]
inn1 = inn1.assign(runs_rest=inn1.first_inn_total - inn1.runs_before)
XR = ["balls_left", "wkts_in_hand", "env_rpo"]
er = HistGradientBoostingRegressor(max_iter=300, learning_rate=0.05, min_samples_leaf=200,
                                   monotonic_cst=[1, 1, 1], random_state=0)
er.fit(inn1[XR], inn1.runs_rest)

def ER(balls_left, wkts_in_hand, env_rpo):
    X = pd.DataFrame({"balls_left": balls_left, "wkts_in_hand": wkts_in_hand, "env_rpo": env_rpo})
    out = er.predict(X)
    return np.where((np.asarray(balls_left) <= 0) | (np.asarray(wkts_in_hand) <= 0), 0.0, out)

# ---------------------------------------------------------------- win-probability models
trainable = b[~b.is_tie]
X1 = ["balls_left", "wkts_in_hand", "runs_before", "env_rpo"]
X2 = ["balls_left", "wkts_in_hand", "runs_needed", "rrr", "env_rpo"]
b["rrr"] = np.where(b.innings == 2, b.runs_needed / np.maximum(b.balls_left, 1) * 6, np.nan)
trainable = b[~b.is_tie]
t1, t2 = trainable[trainable.innings == 1], trainable[trainable.innings == 2]

def make_clf(cst):
    return HistGradientBoostingClassifier(max_iter=400, learning_rate=0.04, min_samples_leaf=300,
                                          max_leaf_nodes=24, l2_regularization=1.0,
                                          monotonic_cst=cst, random_state=0)
CST1 = [1, 1, 1, -1]        # more balls left / wickets / runs -> batting-first team better; higher-scoring env -> worse
CST2 = [1, 1, -1, -1, 1]

def cv_eval(df, feats, cst, name):
    gkf = GroupKFold(n_splits=5)
    oof = np.zeros(len(df))
    for tr, te in gkf.split(df, df.bat_won, df.match_id):
        mdl = make_clf(cst).fit(df.iloc[tr][feats], df.iloc[tr].bat_won)
        oof[te] = mdl.predict_proba(df.iloc[te][feats])[:, 1]
    y = df.bat_won.values
    base = np.full(len(y), y.mean())
    res = dict(model=name, n_balls=len(df), brier=brier_score_loss(y, oof), brier_naive=brier_score_loss(y, base),
               logloss=log_loss(y, oof), auc=roc_auc_score(y, oof))
    calib = pd.DataFrame({"p": oof, "y": y}).assign(bin=lambda d: pd.cut(d.p, np.linspace(0, 1, 11)))
    calib = calib.groupby("bin", observed=True).agg(pred=("p", "mean"), obs=("y", "mean"), n=("y", "size")).reset_index()
    calib["model"] = name
    return res, calib

r1, c1 = cv_eval(t1, X1, CST1, "1st innings WP")
r2, c2 = cv_eval(t2, X2, CST2, "2nd innings WP")
print(pd.DataFrame([r1, r2]))
pd.DataFrame([r1, r2]).to_csv(f"{OUT}/wp_validation.csv", index=False)
pd.concat([c1, c2]).to_csv(f"{OUT}/wp_calibration.csv", index=False)

wp1_m = make_clf(CST1).fit(t1[X1], t1.bat_won)
wp2_m = make_clf(CST2).fit(t2[X2], t2.bat_won)

def WP2(runs_needed, balls_left, wkts_in_hand, env_rpo):
    """P(chasing side wins)."""
    rn = np.asarray(runs_needed, float); bl = np.asarray(balls_left, float); wk = np.asarray(wkts_in_hand, float)
    X = pd.DataFrame({"balls_left": bl, "wkts_in_hand": wk, "runs_needed": rn,
                      "rrr": rn / np.maximum(bl, 1) * 6, "env_rpo": env_rpo})
    p = wp2_m.predict_proba(X)[:, 1]
    done = (bl <= 0) | (wk <= 0)
    p = np.where(rn <= 0, 1.0, p)
    p = np.where((rn > 0) & done, np.where(rn == 1, 0.5, 0.0), p)
    return p

def WP1(runs, balls_left, wkts_in_hand, env_rpo):
    """P(batting-first side wins). Terminal states hand over to the chase model."""
    rr = np.asarray(runs, float); bl = np.asarray(balls_left, float); wk = np.asarray(wkts_in_hand, float)
    X = pd.DataFrame({"balls_left": bl, "wkts_in_hand": wk, "runs_before": rr, "env_rpo": env_rpo})
    p = wp1_m.predict_proba(X)[:, 1]
    done = (bl <= 0) | (wk <= 0)
    if done.any():
        envd = np.asarray(env_rpo, float)[done] if np.ndim(env_rpo) else env_rpo
        p[done] = 1 - WP2(rr[done] + 1, np.full(done.sum(), 120), np.full(done.sum(), 10), envd)
    return p

def wp_batting(innings, runs_before, balls_left, wkts_in_hand, target, env_rpo):
    """WP of the batting side for a vector of states (innings 1 or 2)."""
    innings = np.asarray(innings)
    out = np.empty(len(innings))
    i1, i2 = innings == 1, innings == 2
    out[i1] = WP1(np.asarray(runs_before)[i1], np.asarray(balls_left)[i1], np.asarray(wkts_in_hand)[i1], np.asarray(env_rpo)[i1])
    rn = np.asarray(target)[i2] - np.asarray(runs_before)[i2]
    out[i2] = WP2(rn, np.asarray(balls_left)[i2], np.asarray(wkts_in_hand)[i2], np.asarray(env_rpo)[i2])
    return out

S = dict(innings=b.innings.values, target=b.target.values, env=b.env_rpo.values,
         r0=b.runs_before.values, bl0=b.balls_left.values, wk0=b.wkts_in_hand.values)
b["wp_before"] = wp_batting(S["innings"], S["r0"], S["bl0"], S["wk0"], S["target"], S["env"])

def state_after(runs_add, wkt_add, legal):
    return (S["r0"] + runs_add, S["bl0"] - legal.astype(int), S["wk0"] - wkt_add.astype(int))

def wp_after(runs_add, wkt_add, legal):
    r, bl, wk = state_after(np.asarray(runs_add), np.asarray(wkt_add), np.asarray(legal))
    return wp_batting(S["innings"], r, bl, wk, S["target"], S["env"])

def er_after(wkt_add, legal):
    bl = S["bl0"] - np.asarray(legal).astype(int); wk = S["wk0"] - np.asarray(wkt_add).astype(int)
    return ER(bl, wk, S["env"])

er0 = ER(S["bl0"], S["wk0"], S["env"])
b["er_before"] = er0

# actual team-level WP change (for diagnostics)
b["wp_after_team"] = wp_after(b.total_runs.values, b.is_wicket.values, b.legal.values)

# ---- attribution
# batter: credited with runs off the bat and own dismissal; ball counts if not a wide
bat_runs = b.runs.values
b["bat_wpa"] = wp_after(bat_runs, b.striker_out.values, b.legal.values) - b.wp_before
b["bat_rv"] = bat_runs + er_after(b.striker_out.values, b.legal.values) - er0
# bowler: charged with bat runs + wides/no-balls, credited with bowler wickets
b["bowl_wpa"] = -(wp_after(b.bowler_runs.values, b.bowler_wkt.values, b.legal.values) - b.wp_before)
b["bowl_rv"] = -(b.bowler_runs.values + er_after(b.bowler_wkt.values, b.legal.values) - er0)

# ---------------------------------------------------------------- Leverage Index
# expected absolute WP swing of the next delivery, using league outcome frequencies for the phase
b["phase"] = pd.cut(120 - b.balls_left, [-1, 35, 89, 120], labels=["PP", "Middle", "Death"]).astype(str)
def outcome(r):
    if r.extras_type == "wide":
        return "WD"
    if r.is_wicket:
        return "W"
    return str(min(int(r.runs), 6)) if r.runs in (0, 1, 2, 3, 4, 6) else "1"
b["outcome"] = [("WD" if e == "wide" else "W" if w else (str(int(x)) if x in (0, 1, 2, 3, 4, 6) else "1"))
                for e, w, x in zip(b.extras_type.values, b.is_wicket.values, b.runs.values)]
freq = b.groupby(["tier", "phase"]).outcome.value_counts(normalize=True).rename("p").reset_index()
OUTCOMES = {"0": (0, 0, 1), "1": (1, 0, 1), "2": (2, 0, 1), "3": (3, 0, 1), "4": (4, 0, 1), "6": (6, 0, 1),
            "W": (0, 1, 1), "WD": (1, 0, 0)}
lev = np.zeros(len(b))
for o, (ra, wa, lg) in OUTCOMES.items():
    swing = np.abs(wp_after(np.full(len(b), ra), np.full(len(b), wa), np.full(len(b), lg)) - b.wp_before.values)
    p = b[["tier", "phase"]].merge(freq[freq.outcome == o], on=["tier", "phase"], how="left").p.fillna(0).values
    lev += p * swing
b["leverage"] = lev
b["LI"] = b.leverage / b.leverage.mean()

# big-match multiplier: knockouts carry extra stakes beyond the scoreboard
b["is_knockout"] = (b.knock_out == 1) | b.stage.isin(["Final", "Qualifier", "Eliminator", "Semi Final"])
b["PI"] = b.LI * np.where(b.is_knockout, 1.25, 1.0)

print(b.LI.describe(percentiles=[.5, .75, .8, .9, .95, .99]))
print("share PI>=1.5:", (b.PI >= 1.5).mean())
cols = ["match_id", "innings", "overid", "over_ball_num", "batting_team_id", "bowling_team_id", "striker_id",
        "striker_name", "bowler_id", "bowler_name", "batting_type", "bowling_type", "pace_or_spin", "batting_order",
        "runs", "total_runs", "bowler_runs", "extras_type", "legal", "is_wicket", "bowler_wkt", "striker_out",
        "is_four", "is_six", "dismissal_type", "runs_before", "wkts_before", "balls_left", "wkts_in_hand", "target",
        "runs_needed", "rrr", "env_rpo", "tier", "year", "match_date", "stage", "is_knockout", "comp_name", "phase",
        "bat_won", "wp_before", "wp_after_team", "er_before", "bat_wpa", "bat_rv", "bowl_wpa", "bowl_rv",
        "leverage", "LI", "PI", "outcome"]
b[cols].to_pickle(f"{OUT}/balls.pkl")
keep.to_pickle(f"{OUT}/matches.pkl")
print("saved", len(b))
