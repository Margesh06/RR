"""Stage 4b: evidence figures for the final (consensus) top 10s.
  f10/f11  match-by-match consistency strips
  f12/f13  pressure vs normal vs expected (dumbbells)
  f14/f15  rank across all model specifications
Usage: python -I stage4b_figures.py <out_dir>"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

OUT = sys.argv[1]
FIG = f"{OUT}/fig"
TEXT, TEXT2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8983", "#e6e5e0", "#ffffff"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#c9c8c1"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "text.color": TEXT, "axes.labelcolor": TEXT2,
    "axes.edgecolor": GRID, "axes.linewidth": 0.8, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "savefig.dpi": 200,
})
matches = pd.read_pickle(f"{OUT}/matches.pkl").set_index("match_id")


def save(fig, name):
    fig.savefig(f"{FIG}/{name}.png", bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


def final_top(role):
    return pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0).head(10)


def strip(role, title, fname):
    top = final_top(role)
    pm = pd.read_pickle(f"{OUT}/pmatch_{role}.pkl")
    pm = pm[pm.qualifies & pm.pid.isin(top.index)].join(matches.match_date, on="match_id")
    fig, ax = plt.subplots(figsize=(7.4, 3.6))
    for i, (pid, r) in enumerate(top.iloc[::-1].iterrows()):
        g = pm[pm.pid == pid]
        ok, bad = g[g.success == 1], g[g.success == 0]
        ax.scatter(ok.match_date, np.full(len(ok), i), s=26, color=BLUE, edgecolor="white", linewidth=0.6, zorder=3)
        ax.scatter(bad.match_date, np.full(len(bad), i), s=22, facecolor="white", edgecolor=ORANGE, linewidth=1.1, zorder=3)
        ax.text(1.01, i, f"{len(ok)}/{len(g)}  ({len(ok)/max(len(g),1)*100:.0f}%)", transform=ax.get_yaxis_transform(),
                va="center", fontsize=7.2, color=TEXT)
    ax.set_yticks(range(len(top)), top.name.iloc[::-1], fontsize=7.8)
    ax.grid(axis="y", visible=False)
    ax.set_title(title)
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=BLUE, label="Beat expectation in that match's pressure balls"),
                       Line2D([], [], marker="o", ls="", mfc="white", mec=ORANGE, label="Fell short")],
              frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.08), ncol=2)
    save(fig, fname)


def dumbbell(role, fname):
    top = final_top(role)
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl").loc[top.index]
    if role == "bat":
        normal, exp, act = R.runs_np / R.n_np * 100, R.exp_runs_p / R.n_p * 100, R.runs_p / R.n_p * 100
        label, title, better = "Strike rate", "Batters: pressure strike rate vs what the situation demanded", "right"
    else:
        normal, exp, act = R.runs_np / R.legal_np * 6, R.exp_runs_p / R.legal_p * 6, R.runs_p / R.legal_p * 6
        label, title, better = "Economy (runs per over)", "Bowlers: pressure economy vs what the situation demanded", "left"
    fig, ax = plt.subplots(figsize=(7.2, 3.5))
    y = np.arange(len(top))[::-1]
    ax.hlines(y, exp, act, color="#9ec5f4", lw=3, zorder=2)
    ax.scatter(normal, y, s=30, marker="|", color=MUTED, linewidth=2, zorder=3, label="Normal situations")
    ax.scatter(exp, y, s=34, facecolor="white", edgecolor=TEXT2, linewidth=1.1, zorder=4, label="Expected under pressure")
    ax.scatter(act, y, s=42, color=BLUE, edgecolor="white", linewidth=0.8, zorder=5, label="Actual under pressure")
    for yi, a, e in zip(y, act, exp):
        d = a - e
        ax.text(max(a, e) + (2 if role == "bat" else 0.08), yi,
                f"{d:+.0f}" if role == "bat" else f"{d:+.2f}", va="center", fontsize=7, color=TEXT)
    ax.set_yticks(y, top.name, fontsize=7.8)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel(f"{label}  ({'higher' if better == 'right' else 'lower'} is better)")
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=7, loc="upper center", bbox_to_anchor=(0.5, -0.17), ncol=3)
    save(fig, fname)


def spec_ranks(role, title, fname):
    top = final_top(role)
    M = pd.read_pickle(f"{OUT}/ensemble_ranks_{role}.pkl").loc[top.index]
    fig, ax = plt.subplots(figsize=(7.2, 3.4))
    y = np.arange(len(top))[::-1]
    rng = np.random.default_rng(0)
    for yi, (pid, row) in zip(y, M.iterrows()):
        v = row.values
        ax.scatter(v, yi + rng.uniform(-0.18, 0.18, len(v)), s=7, color=GRAY, alpha=0.8, zorder=2, linewidth=0)
        ax.scatter(v.mean(), yi, s=46, color=BLUE, edgecolor="white", linewidth=1, zorder=3)
        ax.text(max(v.max(), 10) + 1, yi, f"top-10 in {(v <= 10).mean()*100:.0f}% of {len(v)} specs", va="center",
                fontsize=6.5, color=TEXT2)
    ax.axvline(10.5, color=MUTED, ls=":", lw=1)
    ax.set_yticks(y, top.name, fontsize=7.8)
    ax.set_xlim(0, max(M.values.max() + 30, 46))
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Rank under each model specification (grey) and consensus mean (blue)")
    ax.set_title(title)
    save(fig, fname)


def wins_added(fname):
    imp = pd.read_csv(f"{OUT}/rr_impact.csv")
    imp = imp[~imp.already_rr].sort_values("wins")
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    y = np.arange(len(imp))
    col = np.where(imp.role == "bat", BLUE, ORANGE)
    ax.hlines(y, imp.wins_lo, imp.wins_hi, color=GRAY, lw=2.2, zorder=2)
    ax.scatter(imp.wins, y, s=44, color=col, edgecolor="white", linewidth=0.8, zorder=3)
    for yi, (_, r) in zip(y, imp.iterrows()):
        ax.text(max(r.wins_hi, 0) + 0.02, yi, f"+{r.wins:.2f}   {r.slot}", va="center", fontsize=7, color=TEXT2)
    ax.set_yticks(y, [f"{n} ({'bat' if r == 'bat' else 'bowl'} #{k})" for n, r, k in zip(imp.name, imp.role, imp["rank"])],
                  fontsize=7.6)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_xlim(min(-0.1, imp.wins_lo.min() - 0.05), imp.wins_hi.max() + 0.42)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Extra wins per IPL season for RR (dot = estimate, bar = 80% range)")
    ax.set_title("Wins added if the pick took RR's below-par pressure balls (IPL 2026)")
    ax.legend(handles=[Line2D([], [], marker="o", ls="", color=BLUE, label="Batter"),
                       Line2D([], [], marker="o", ls="", color=ORANGE, label="Bowler")],
              frameon=False, fontsize=7, loc="lower right")
    save(fig, fname)


wins_added("f16_wins_added")
strip("bat", "Batters: every pressure match, 2022-2026", "f10_bat_strip")
strip("bowl", "Bowlers: every pressure match, 2022-2026", "f11_bowl_strip")
dumbbell("bat", "f12_bat_dumbbell")
dumbbell("bowl", "f13_bowl_dumbbell")
spec_ranks("bat", "Batters: rank under 73 model specifications", "f14_bat_specs")
spec_ranks("bowl", "Bowlers: rank under 73 model specifications", "f15_bowl_specs")
print("ok")
