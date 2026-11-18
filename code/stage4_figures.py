"""Stage 4: report figures (static PNG, print / light surface).
Usage: python -I stage4_figures.py <out_dir>"""
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

OUT = sys.argv[1]
FIG = f"{OUT}/fig"
import os; os.makedirs(FIG, exist_ok=True)

TEXT, TEXT2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8983", "#e6e5e0", "#ffffff"
BLUE, ORANGE, GRAY = "#2a78d6", "#eb6834", "#c9c8c1"
SEQ = ["#cde2fb", "#9ec5f4", "#6da7ec", "#3987e5", "#256abf", "#184f95", "#0d366b"]
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "text.color": TEXT, "axes.labelcolor": TEXT2,
    "axes.edgecolor": GRID, "axes.linewidth": 0.8, "xtick.color": TEXT2, "ytick.color": TEXT2,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "figure.facecolor": SURF, "axes.facecolor": SURF,
    "axes.titlesize": 10, "axes.titleweight": "bold", "axes.titlelocation": "left", "savefig.dpi": 200,
})


def save(fig, name):
    fig.savefig(f"{FIG}/{name}.png", bbox_inches="tight", facecolor=SURF)
    plt.close(fig)


b = pd.read_pickle(f"{OUT}/balls.pkl")

# F1 -- where pressure lives in a chase (empirical mean Pressure Index)
c = b[(b.innings == 2) & (b.runs_needed > 0)].copy()
c["bl_bin"] = pd.cut(c.balls_left, np.arange(0, 121, 12), labels=[f"{i+1}-{i+12}" for i in range(0, 120, 12)])
c["rn_bin"] = pd.cut(c.runs_needed, [0, 10, 20, 30, 40, 50, 60, 80, 100, 130, 300],
                     labels=["1-10", "11-20", "21-30", "31-40", "41-50", "51-60", "61-80", "81-100", "101-130", "131+"])
hm = c.pivot_table(index="rn_bin", columns="bl_bin", values="PI", aggfunc="mean", observed=False)
cnt = c.pivot_table(index="rn_bin", columns="bl_bin", values="PI", aggfunc="size", observed=False)
hm = hm.where(cnt >= 40)
fig, ax = plt.subplots(figsize=(7.2, 3.6))
cmap = LinearSegmentedColormap.from_list("seq", SEQ)
cmap.set_bad("#f4f3ef")
im = ax.imshow(hm.values, aspect="auto", cmap=cmap, origin="lower", vmin=0, vmax=4)
ax.set_xticks(range(len(hm.columns)), hm.columns, rotation=0, fontsize=7)
ax.set_yticks(range(len(hm.index)), hm.index, fontsize=7)
ax.set_xlabel("Balls remaining in the chase")
ax.set_ylabel("Runs still needed")
ax.grid(False)
for i in range(hm.shape[0]):
    for j in range(hm.shape[1]):
        v = hm.values[i, j]
        if not np.isnan(v):
            ax.text(j, i, f"{v:.1f}", ha="center", va="center", fontsize=6.5, color="white" if v > 2.2 else TEXT)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("Mean Pressure Index (league avg = 1)", fontsize=7)
cb.outline.set_visible(False)
ax.set_title("Pressure concentrates where the chase is still alive, late")
save(fig, "f1_pressure_map")

# F2 -- league behaviour by pressure tier
b["ptier"] = pd.cut(b.PI, [0, 0.75, 1.5, 3, 1e9], labels=["Low\n<0.75", "Medium\n0.75-1.5", "High\n1.5-3", "Extreme\n3+"])
fb = b[b.extras_type != "wide"]
lg = fb.groupby("ptier", observed=True).agg(SR=("runs", lambda x: x.mean() * 100), wkt=("is_wicket", lambda x: x.mean() * 100),
                                            dot=("runs", lambda x: (x == 0).mean() * 100), share=("runs", "size"))
lg["share"] = lg.share / lg.share.sum() * 100
fig, axes = plt.subplots(1, 4, figsize=(7.4, 2.5))
for ax, (col, title) in zip(axes, [("share", "Share of balls (%)"), ("SR", "Strike rate"), ("wkt", "Wicket per ball (%)"), ("dot", "Dot-ball (%)")]):
    cols = [GRAY, GRAY, BLUE, BLUE]
    ax.bar(range(4), lg[col], color=cols, width=0.62)
    ax.set_xticks(range(4), lg.index, fontsize=6.5)
    ax.set_title(title, fontsize=8.5)
    for i, v in enumerate(lg[col]):
        ax.text(i, v, f"{v:.0f}" if col != "wkt" else f"{v:.1f}", ha="center", va="bottom", fontsize=7, color=TEXT)
    ax.grid(axis="x", visible=False)
    ax.set_ylim(0, lg[col].max() * 1.18)
fig.suptitle("Under extreme pressure the league takes more risk: faster scoring, more wickets", x=0.01, ha="left",
             fontsize=10, fontweight="bold", y=1.04)
fig.tight_layout()
save(fig, "f2_tiers")

# F3 -- reliability of competing metrics
rel = pd.read_csv(f"{OUT}/reliability.csv")
order = ["Raw pressure WPA", "Raw pressure run value", "Raw pressure SR / economy", "Pressure Quality (PRI core)"]
fig, axes = plt.subplots(1, 2, figsize=(7.4, 2.4), sharex=True)
for ax, role, title in zip(axes, ["bat", "bowl"], ["Batters", "Bowlers"]):
    r = rel[rel.role == role].set_index("metric").loc[order]
    cols = [GRAY] * 3 + [BLUE]
    ax.barh(range(4), r.full_sample_reliability.clip(lower=0), color=cols, height=0.6)
    ax.set_yticks(range(4), [o.replace("Pressure Quality (PRI core)", "PRI Pressure Quality") for o in order], fontsize=7.5)
    for i, v in enumerate(r.full_sample_reliability):
        ax.text(max(v, 0) + 0.01, i, f"{v:.2f}", va="center", fontsize=7.5)
    ax.set_title(title, fontsize=9)
    ax.set_xlim(0, 0.65)
    ax.grid(axis="y", visible=False)
    ax.set_xlabel("Split-half reliability (Spearman-Brown)", fontsize=7.5)
axes[1].set_yticklabels([])
fig.suptitle("Our metric is signal; raw 'clutch' stats are mostly noise", x=0.01, ha="left", fontsize=10,
             fontweight="bold", y=1.05)
fig.tight_layout()
save(fig, "f3_reliability")


# F4/F5 -- baseline vs pressure scatter
def scatter(role, title, fname):
    R = pd.read_pickle(f"{OUT}/ratings_{role}.pkl")
    R = R[R.eligible]
    cons = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0).head(10)
    top = R.loc[cons.index].assign(rank=cons.consensus_rank)          # final (consensus) top 10
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    rest = R.drop(top.index)
    ax.scatter(rest.q_base, rest.pq, s=22, color=GRAY, edgecolor="white", linewidth=0.8, zorder=2, label="Eligible pool")
    ax.scatter(top.q_base, top.pq, s=150, color=BLUE, edgecolor="white", linewidth=1.2, zorder=3, label="Top 10 (PRI)")
    for _, r in top.iterrows():   # rank number inside each marker; names in the key on the right
        ax.text(r.q_base, r.pq, str(int(r["rank"])), ha="center", va="center", fontsize=6.5, color="white",
                fontweight="bold", zorder=4)
    lim = [min(R.q_base.min(), R.pq.min()) - 3, max(R.q_base.max(), R.pq.max()) + 3]
    ax.plot(lim, lim, color=MUTED, lw=1, ls="--", zorder=1)
    ax.text(lim[1], lim[1] - 1, "pressure = normal ", fontsize=7, color=MUTED, va="top", ha="right")
    ax.axhline(0, color=GRID, lw=1); ax.axvline(0, color=GRID, lw=1)
    key = "\n".join(f"{int(r['rank']):>2}  {r['name']}" for _, r in top.iterrows())
    ax.text(1.02, 1.0, key, transform=ax.transAxes, fontsize=7.2, va="top", ha="left", color=TEXT, linespacing=1.55)
    ax.set_xlabel("Normal-situation quality (runs above expectation per 100 balls)")
    ax.set_ylabel("Pressure Quality (runs above exp. / 100 balls)")
    ax.set_title(title)
    ax.legend(frameon=False, fontsize=7.5, loc="lower right", markerscale=0.6)
    save(fig, fname)


scatter("bat", "Batters: above the dashed line = raises their game under pressure", "f4_bat_scatter")
scatter("bowl", "Bowlers: above the dashed line = raises their game under pressure", "f5_bowl_scatter")


# F8 -- RR team pressure profile vs IPL 2025-26
ABBR = {"Royal Challengers Bengaluru": "RCB", "Sunrisers Hyderabad": "SRH", "Lucknow Super Giants": "LSG",
        "Kolkata Knight Riders": "KKR", "Chennai Super Kings": "CSK", "Rajasthan Royals": "RR", "Mumbai Indians": "MI",
        "Delhi Capitals": "DC", "Punjab Kings": "PBKS", "Gujarat Titans": "GT"}
fig, axes = plt.subplots(1, 3, figsize=(7.6, 2.9))
for ax, role, title in zip(axes[:2], ["bat", "bowl"], ["Pressure batting", "Pressure bowling"]):
    t = pd.read_csv(f"{OUT}/team_profile_{role}.csv", index_col=0).sort_values("pressure_q")
    cols = [BLUE if n == "Rajasthan Royals" else GRAY for n in t.index]
    ax.barh(range(len(t)), t.pressure_q, color=cols, height=0.62)
    ax.set_yticks(range(len(t)), [n.replace("Royal Challengers Bengaluru", "RCB").replace("Sunrisers Hyderabad", "SRH")
                                  .replace("Lucknow Super Giants", "LSG").replace("Kolkata Knight Riders", "KKR")
                                  .replace("Chennai Super Kings", "CSK").replace("Rajasthan Royals", "RR")
                                  .replace("Mumbai Indians", "MI").replace("Delhi Capitals", "DC")
                                  .replace("Punjab Kings", "PBKS").replace("Gujarat Titans", "GT") for n in t.index], fontsize=7.5)
    ax.axvline(0, color=MUTED, lw=0.8)
    ax.set_title(title, fontsize=9)
    ax.set_xlabel("Runs vs exp. / 100 pressure balls", fontsize=7)
    ax.grid(axis="y", visible=False)
cg = pd.read_csv(f"{OUT}/close_games.csv").sort_values("win_pct")
ax = axes[2]
cols = [BLUE if n == "Rajasthan Royals" else GRAY for n in cg.team]
ax.barh(range(len(cg)), cg.win_pct, color=cols, height=0.62)
ax.set_yticks(range(len(cg)), [f"{ABBR[n]} {w}/{g}" for n, w, g in zip(cg.team, cg.close_wins, cg.close_games)], fontsize=7)
ax.set_title("Close-game wins", fontsize=9)
ax.set_xlabel("Win % (tensest third of games, peak PI >= 8)", fontsize=7)
ax.axvline(50, color=MUTED, lw=0.8, ls=":")
ax.grid(axis="y", visible=False)
for i, (n, v) in enumerate(zip(cg.team, cg.win_pct)):
    short = "RR" if n == "Rajasthan Royals" else ""
    if short:
        ax.text(v + 1, i, f"RR {v:.0f}%", va="center", fontsize=7, color=TEXT, fontweight="bold")
fig.suptitle("Rajasthan Royals under pressure, IPL 2025-26", x=0.01, ha="left", fontsize=10, fontweight="bold", y=1.03)
fig.tight_layout()
save(fig, "f8_rr_profile")

# F9 -- WP model calibration
cal = pd.read_csv(f"{OUT}/wp_calibration.csv")
fig, ax = plt.subplots(figsize=(3.6, 3.2))
for (name, g), col in zip(cal.groupby("model"), [BLUE, ORANGE]):
    ax.plot(g.pred, g.obs, marker="o", ms=4, lw=2, color=col, label=name)
ax.plot([0, 1], [0, 1], color=MUTED, ls="--", lw=1)
ax.set_xlabel("Predicted win probability"); ax.set_ylabel("Observed win rate")
ax.set_title("Win-probability model calibration\n(5-fold, grouped by match)", fontsize=9)
ax.legend(frameon=False, fontsize=7)
save(fig, "f9_calibration")
print("figures written to", FIG)
