"""Stage 2: Pressure Reliability Index (PRI) for batters and bowlers.

Pipeline per role:
  1. league expectation model -> expected runs / dismissal / boundary / dot for every ball in its context
  2. per-player residuals (actual - expected) on pressure and normal balls
  3. Baseline quality: normal-situation residuals, component-wise empirical-Bayes shrinkage to league
  4. Pressure Quality: pressure residuals shrunk toward the player's OWN baseline (K_BASE balls)
  5. PRI = 45% Pressure Quality + 20% Consistency + 20% Pressure Lift + 15% Win Impact (z-scores)
  6. split-half reliability + match-level bootstrap of the final ranking

Usage: python -I stage2_ratings.py <data_dir> <out_dir> [max_year] [tag]
"""
import sys
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor

D, OUT = sys.argv[1], sys.argv[2]
MAX_YEAR = int(sys.argv[3]) if len(sys.argv) > 3 else 9999
TAG = sys.argv[4] if len(sys.argv) > 4 else ""
b = pd.read_pickle(f"{OUT}/balls.pkl")
b = b[b.year <= MAX_YEAR].copy()
mp = pd.read_csv(f"{D}/competition_team_player_mapping.csv")

PRESSURE = 1.5          # Pressure Index threshold (~top 18% of deliveries)
HALF_LIFE_YRS = 2.5     # recency half-life, anchored at the last match in the window
K_BASE = 500            # pressure balls needed before pressure evidence outweighs a player's own baseline
K_SUCC = 12             # pressure matches needed before success rate outweighs the league rate
REF_DATE = b.match_date.max()
ACTIVE_FROM = REF_DATE.year - 1
TIER1 = {"India", "Pakistan", "Australia", "England", "New Zealand", "South Africa", "West Indies", "Sri Lanka",
         "Bangladesh", "Afghanistan"}
TIER2 = {"Zimbabwe", "Ireland"}
W = {"pq": 0.45, "succ": 0.20, "lift": 0.20, "wpa": 0.15}
ELIG = {"bat": dict(n_p=100, p_matches=10), "bowl": dict(n_p=100, p_matches=10)}
CONSIST_MIN = {"bat": 4, "bowl": 6}      # pressure balls in a match for it to count toward consistency
EXCLUDE_NATIONS = {"Pakistan"}           # not available at the IPL auction
KO_MULT = 1.25          # big-match multiplier on leverage in knockouts
OPP_WEIGHTING = True    # down-weight balls against associate / A-team opposition
TIER_KEEP = None        # sensitivity: rate on one competition tier only, e.g. ["IPL"]

# sensitivity runs override the constants above, e.g. RR_OVERRIDES='{"PRESSURE": 2.0}'
import json, os
for _k, _v in json.loads(os.environ.get("RR_OVERRIDES", "{}")).items():
    globals()[_k] = _v
if TIER_KEEP:
    b = b[b.tier.isin(TIER_KEEP)].copy()

comps = pd.read_csv(f"{D}/competitions.csv")
mpf = mp.merge(comps[["comp_id", "match_format"]], on="comp_id")
NATION = mpf[mpf.match_format == "T20I"].groupby("player_id").team_name.agg(lambda s: s.mode().iat[0])
IPL26 = mp[mp.comp_name == "IPL 2026"].drop_duplicates("player_id").set_index("player_id").team_name

# ---------------------------------------------------------------- weights
teams = pd.read_csv(f"{D}/teams.csv").drop_duplicates("team_id").set_index("team_id").team_name
ipl_ids = set(mp[mp.comp_name.str.startswith("IPL")].team_id)
def opp_weight(tid):
    if tid in ipl_ids or teams.get(tid) in TIER1:
        return 1.0
    return 0.75 if teams.get(tid) in TIER2 else 0.5
if not OPP_WEIGHTING:
    opp_weight = lambda tid: 1.0
ow = {t: opp_weight(t) for t in set(b.batting_team_id) | set(b.bowling_team_id)}
b["w_rec"] = 0.5 ** ((REF_DATE - b.match_date).dt.days / 365.25 / HALF_LIFE_YRS)
b["PI"] = b.LI * np.where(b.is_knockout, KO_MULT, 1.0)
b["P"] = b.PI >= PRESSURE
b["over"] = (120 - b.balls_left) // 6 + 1
b["rrr_f"] = b.rrr.fillna(-1).clip(upper=36)

# ---------------------------------------------------------------- role tables
bat = b[b.extras_type != "wide"].assign(
    pid=b.striker_id, name=b.striker_name, w=b.w_rec * b.bowling_team_id.map(ow),
    rv=b.bat_rv, wpa=b.bat_wpa, r=b.runs, out=b.striker_out.astype(float),
    bnd=(b.is_four | b.is_six).astype(float), dot=((b.runs == 0) & ~b.striker_out).astype(float))
bowl = b.assign(
    pid=b.bowler_id, name=b.bowler_name, w=b.w_rec * b.batting_team_id.map(ow),
    rv=b.bowl_rv, wpa=b.bowl_wpa, r=b.bowler_runs, out=b.bowler_wkt.astype(float),
    bnd=(b.is_four | b.is_six).astype(float), dot=(b.total_runs == 0).astype(float))

FEATS = ["innings", "over", "wkts_before", "rrr_f", "env_rpo", "balls_left"]


def add_expectations(df, role):
    """League expectation for each component given the exact match context of the ball.
    The models do not depend on any rating parameter, so fits are cached per data window and reused."""
    df = df.copy()
    cache = f"{OUT}/expect_{role}_{MAX_YEAR}.pkl"
    if os.path.exists(cache):
        E = pd.read_pickle(cache)
        df[E.columns] = E.reindex(df.index)
    else:
        X = df[FEATS]
        df["e_r"] = HistGradientBoostingRegressor(max_iter=200, min_samples_leaf=300, random_state=0).fit(X, df.r).predict(X)
        for comp in ("out", "bnd", "dot"):
            clf = HistGradientBoostingClassifier(max_iter=200, min_samples_leaf=300, random_state=0).fit(X, df[comp])
            df[f"e_{comp}"] = clf.predict_proba(X)[:, 1]
        df[["e_r", "e_out", "e_bnd", "e_dot"]].to_pickle(cache)
    for comp in ("r", "out", "bnd", "dot"):
        df[f"d_{comp}"] = df[comp] - df[f"e_{comp}"]
    return df


def wavg(df, col):
    return (df[col] * df.w).groupby(df.pid).sum() / df.w.groupby(df.pid).sum()


def mom_k(per_ball_resid, player_means, player_w):
    """Method-of-moments stabilisation constant: k = sigma^2 / tau^2 (in weighted balls)."""
    sigma2 = per_ball_resid.var()
    noise = (sigma2 / player_w).mean()
    tau2 = max(player_means.var() - noise, player_means.var() * 0.05)
    return sigma2 / tau2


def shrink(x, n, k, prior=0.0):
    return (x * n + prior * k) / (n + k)


def rate(df, role):
    sign = 1 if role == "bat" else -1     # bowlers: fewer runs / more wickets is good
    df = add_expectations(df, role)
    # wicket value in runs: average run-value cost of a dismissal in each pressure state
    WV = {p: abs(df[(df.P == p) & (df.out == 1)].rv.mean()) for p in (True, False)}
    df["q"] = sign * (df.d_r - df.d_out * df.P.map(WV)) * 100      # per-ball quality, runs per 100 balls
    P, NP = df[df.P], df[~df.P]

    R = pd.DataFrame({"name": df.groupby("pid").name.agg(lambda s: s.mode().iat[0])})
    rough = P.groupby("pid").size()
    rough = rough[rough >= 60].index
    ks = {}
    for tag, sub in (("p", P), ("np", NP)):
        R[f"n_{tag}"] = sub.groupby("pid").size()
        R[f"w_{tag}"] = sub.groupby("pid").w.sum()
        for comp in ("r", "out", "bnd", "dot"):
            raw = wavg(sub, f"d_{comp}")
            ks[f"{comp}_{tag}"] = mom_k(sub[f"d_{comp}"], raw.reindex(rough).dropna(), R.loc[rough, f"w_{tag}"].dropna())
            R[f"d{comp}_{tag}"] = raw
            R[f"d{comp}_{tag}_s"] = shrink(raw, R[f"w_{tag}"], ks[f"{comp}_{tag}"])
        R[f"q_{tag}_raw"] = wavg(sub, "q")
        # traditional splits for the report
        R[f"runs_{tag}"] = sub.groupby("pid").r.sum()
        R[f"exp_runs_{tag}"] = sub.groupby("pid").e_r.sum()
        R[f"outs_{tag}"] = sub.groupby("pid").out.sum()
        R[f"exp_outs_{tag}"] = sub.groupby("pid").e_out.sum()
        R[f"legal_{tag}"] = sub[sub.legal].groupby("pid").size()
        R[f"bndpct_{tag}"] = sub.groupby("pid").bnd.mean() * 100
        R[f"dotpct_{tag}"] = sub.groupby("pid").dot.mean() * 100
    R = R.fillna({"n_p": 0, "w_p": 0, "n_np": 0, "w_np": 0})

    # 1) Baseline (normal-situation) quality, component-shrunk toward league average
    R["q_base"] = sign * (R.dr_np_s.fillna(0) - R.dout_np_s.fillna(0) * WV[False]) * 100
    # 2) Pressure Quality: pressure evidence shrunk toward the player's own baseline
    R["pq"] = shrink(R.q_p_raw.fillna(0), R.n_p, K_BASE, R.q_base)
    # 3) Pressure Lift: how far the evidence moves the player above / below their own baseline
    R["lift"] = R.pq - R.q_base

    # 4) Win Impact: WPA above league average under pressure (win-% points per 100 balls), shrunk to 0
    lgw = (P.wpa * P.w).sum() / P.w.sum()
    P = P.assign(wpa_rel=(P.wpa - lgw) * 1e4)
    R["wpa_raw"] = wavg(P, "wpa_rel")
    ks["wpa_p"] = mom_k(P.wpa_rel, R.loc[rough, "wpa_raw"], R.loc[rough, "w_p"])
    R["wpa_s"] = shrink(R.wpa_raw.fillna(0), R.w_p, ks["wpa_p"])
    R["wpa_total_p"] = P.groupby("pid").wpa.sum() * 100           # cumulative win-% added under pressure

    # 5) Consistency: share of pressure matches in which the player beat league expectation
    pm = (P.assign(qw=P.q * P.w, ww=P.wpa_rel * P.w)
          .groupby(["pid", "match_id"]).agg(n=("q", "size"), w=("w", "sum"), qw=("qw", "sum"), ww=("ww", "sum"))
          .reset_index())
    pm["qualifies"] = pm.n >= CONSIST_MIN[role]
    pm["success"] = (pm.qw > 0).astype(int)
    lg_succ = pm[pm.qualifies].success.mean()
    R["p_matches"] = pm[pm.qualifies].groupby("pid").size()
    R["succ_raw"] = pm[pm.qualifies].groupby("pid").success.mean()
    R = R.fillna({"p_matches": 0})
    R["succ_s"] = shrink(R.succ_raw.fillna(lg_succ), R.p_matches, K_SUCC, lg_succ)

    # context for the report / squad fit
    R["matches"] = df.groupby("pid").match_id.nunique()
    R["last_year"] = df.groupby("pid").year.max()
    R["ipl_share_p"] = P.groupby("pid").tier.agg(lambda s: (s == "IPL").mean())
    R["death_share_p"] = P.groupby("pid").phase.agg(lambda s: (s == "Death").mean())
    R["pp_share_p"] = P.groupby("pid").phase.agg(lambda s: (s == "PP").mean())
    R["chase_share_p"] = P.groupby("pid").innings.agg(lambda s: (s == 2).mean())
    R["ko_balls_p"] = P[P.is_knockout].groupby("pid").size()
    R["avg_PI_p"] = P.groupby("pid").PI.mean()
    if role == "bat":
        R["bat_pos"] = df.groupby("pid").batting_order.median()
        R["hand"] = df.groupby("pid").batting_type.agg(lambda s: s.mode().iat[0])
    else:
        R["bowl_type"] = df.groupby("pid").bowling_type.agg(lambda s: s.mode().iat[0])
        R["pace_spin"] = df.groupby("pid").pace_or_spin.agg(lambda s: s.mode().iat[0])
    R = R.fillna({"ko_balls_p": 0})
    meta = dict(ks=ks, WV=WV, lg_succ=lg_succ)
    print(role, "k:", {k: round(v) for k, v in ks.items()}, "WV:", {k: round(v, 2) for k, v in WV.items()},
          "lg_succ:", round(lg_succ, 3))
    return R, pm, df, meta


COLS = {"pq": "pq", "succ": "succ_s", "lift": "lift", "wpa": "wpa_s"}


def composite(R, pool_mask):
    mu = {k: R.loc[pool_mask, v].mean() for k, v in COLS.items()}
    sd = {k: R.loc[pool_mask, v].std() for k, v in COLS.items()}
    z = pd.DataFrame({k: (R[v] - mu[k]) / sd[k] for k, v in COLS.items()})
    return z, sum(W[k] * z[k] for k in W), mu, sd


def split_half(df, role, pool, meta, reps=40, seed=3):
    """Random match halves; Spearman correlation of each per-player metric between halves (Spearman-Brown)."""
    rng = np.random.default_rng(seed)
    mids = df.match_id.unique()
    sign = 1 if role == "bat" else -1
    names = ["Pressure Quality (PRI core)", "Raw pressure run value", "Raw pressure WPA", "Raw pressure SR / economy"]
    out = {n: [] for n in names}
    for _ in range(reps):
        h = pd.Series(rng.integers(0, 2, len(mids)), index=mids)
        halves = []
        for k in (0, 1):
            s = df[df.match_id.map(h) == k]
            sp, sn = s[s.P], s[~s.P]
            n_p, w_n = sp.groupby("pid").size(), sn.groupby("pid").w.sum()
            base = sign * (shrink(wavg(sn, "d_r"), w_n, meta["ks"]["r_np"])
                           - shrink(wavg(sn, "d_out"), w_n, meta["ks"]["out_np"]) * meta["WV"][False]) * 100
            pq = shrink(wavg(sp, "q"), n_p, K_BASE, base.reindex(n_p.index).fillna(0))
            halves.append(pd.DataFrame({names[0]: pq, names[1]: wavg(sp, "rv"), names[2]: wavg(sp, "wpa"),
                                        names[3]: sign * wavg(sp, "r")}))
        a, c = halves
        idx = a.index.intersection(c.index).intersection(pool)
        for n in names:
            out[n].append(a.loc[idx, n].corr(c.loc[idx, n], method="spearman"))
    r = {n: np.mean(v) for n, v in out.items()}
    return pd.DataFrame({"role": role, "metric": list(r), "split_half_r": list(r.values()),
                         "full_sample_reliability": [2 * x / (1 + x) for x in r.values()]})


def bootstrap(R, pm, pool, mu, sd, meta, n_boot=1000, seed=11):
    """Resample each eligible player's pressure matches with replacement; re-score everything; re-rank."""
    rng = np.random.default_rng(seed)
    base = R.loc[pool]
    groups = {pid: g[["n", "w", "qw", "ww", "success", "qualifies"]].to_numpy(float) for pid, g in pm[pm.pid.isin(pool)].groupby("pid")}
    kw, lg = meta["ks"]["wpa_p"], meta["lg_succ"]
    ranks, boot_scores, top10 = [], [], pd.Series(0.0, index=pool)
    for _ in range(n_boot):
        rec = {}
        for pid in pool:
            g = groups[pid]
            s = g[rng.integers(0, len(g), len(g))]
            n, w = s[:, 0].sum(), s[:, 1].sum()
            pq = shrink(s[:, 2].sum() / w, n, K_BASE, base.q_base[pid])
            wpa = shrink(s[:, 3].sum() / w, w, kw)
            qual = s[s[:, 5] == 1]
            succ = shrink(qual[:, 4].mean() if len(qual) else lg, len(qual), K_SUCC, lg)
            rec[pid] = (pq, succ, pq - base.q_base[pid], wpa)
        t = pd.DataFrame(rec, index=["pq", "succ", "lift", "wpa"]).T
        sc = sum(W[k] * (t[k] - mu[k]) / sd[k] for k in W)
        rk = sc.rank(ascending=False)
        top10 += rk <= 10
        ranks.append(rk)
        boot_scores.append(sc)
    ranks = pd.concat(ranks, axis=1)
    boot_scores = pd.concat(boot_scores, axis=1)
    return pd.DataFrame({"top10_prob": top10 / n_boot, "PRI_boot_sd": boot_scores.std(axis=1),
                         "rank_p10": ranks.quantile(0.1, axis=1),
                         "rank_med": ranks.median(axis=1), "rank_p90": ranks.quantile(0.9, axis=1)})


rel_all = []
for role, df in (("bat", bat), ("bowl", bowl)):
    R, pm, dfx, meta = rate(df, role)
    e = ELIG[role]
    R["nation"] = R.index.map(NATION).fillna("No T20I in window")
    R["ipl_2026_team"] = R.index.map(IPL26).fillna("-")
    sample_ok = (R.n_p >= e["n_p"]) & (R.p_matches >= e["p_matches"]) & (R.last_year >= ACTIVE_FROM)
    pool_mask = sample_ok & ~R.nation.isin(EXCLUDE_NATIONS)
    R["eligible"] = pool_mask
    R["sample_ok"] = sample_ok
    pool = R.index[pool_mask]
    z, R["PRI"], mu, sd = composite(R, pool_mask)
    for k in W:
        R[f"z_{k}"] = z[k]
    R["rank"] = R.PRI.where(pool_mask).rank(ascending=False)
    R["rank_incl_excluded"] = R.PRI.where(sample_ok).rank(ascending=False)
    if not TAG:
        R = R.join(bootstrap(R, pm, pool, mu, sd, meta))
        rel = split_half(dfx, role, pool, meta)
        rel_all.append(rel)
        print(rel.round(3).to_string(index=False))
        dfx[["match_id", "pid", "P", "PI", "w", "d_r", "d_out", "e_r", "r", "out", "q", "rv", "wpa", "innings",
             "phase", "year", "tier", "is_knockout"]].to_pickle(f"{OUT}/resid_{role}.pkl")
        pm.to_pickle(f"{OUT}/pmatch_{role}.pkl")
        pd.Series({**meta["ks"], **{f"WV_{k}": v for k, v in meta["WV"].items()}, "lg_succ": meta["lg_succ"]}).to_csv(
            f"{OUT}/params_{role}.csv")
    print(role, "eligible:", pool_mask.sum())
    R.sort_values("PRI", ascending=False).to_pickle(f"{OUT}/ratings_{role}{TAG}.pkl")

if rel_all:
    pd.concat(rel_all).to_csv(f"{OUT}/reliability.csv", index=False)

pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
show = ["name", "n_p", "p_matches", "q_p_raw", "q_base", "pq", "lift", "succ_s", "wpa_s", "PRI"] + \
       (["top10_prob", "rank_p10", "rank_p90"] if not TAG else []) + ["ipl_share_p", "last_year"]
for role in ("bat", "bowl"):
    R = pd.read_pickle(f"{OUT}/ratings_{role}{TAG}.pkl")
    print(f"\n==== {role} top 25")
    print(R[R.eligible][show].head(25).round(2).to_string())
