"""Stage 5: build the methodology report PDF.
Usage: python -I stage5_report.py <out_dir> <pdf_path>"""
import sys
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak, PageTemplate,
                                Paragraph, Spacer, Table, TableStyle)

OUT, PDF = sys.argv[1], sys.argv[2]
MY_VIEW = sys.argv[3] if len(sys.argv) > 3 else None   # optional: the author's own one-page note (markdown-lite)
import os
exec(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "trades.py")).read())   # TRADES, AS_OF
FIG = f"{OUT}/fig"
PINK, NAVY, INK, INK2, RULE, TINT = (colors.HexColor(h) for h in ("#E4087C", "#14254F", "#0b0b0b", "#52514e", "#dddcd6", "#f5f4f0"))
BLUE = colors.HexColor("#2a78d6")
DASH_URL = "https://rr-pressure-index-xi.vercel.app"
CODE_URL = "https://github.com/Margesh06/RR"
W, H = A4
M = 16 * mm

st = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=16, leading=20, textColor=NAVY, spaceBefore=4, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=NAVY, spaceBefore=8, spaceAfter=4),
    "kick": ParagraphStyle("kick", fontName="Helvetica-Bold", fontSize=8, leading=10, textColor=PINK, spaceAfter=2),
    "p": ParagraphStyle("p", fontName="Helvetica", fontSize=9, leading=13, textColor=INK, spaceAfter=5),
    "small": ParagraphStyle("small", fontName="Helvetica", fontSize=7.5, leading=10, textColor=INK2, spaceAfter=3),
    "cell": ParagraphStyle("cell", fontName="Helvetica", fontSize=7.4, leading=9.2, textColor=INK),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=7.4, leading=9.2, textColor=INK),
    "cellh": ParagraphStyle("cellh", fontName="Helvetica-Bold", fontSize=7.2, leading=9, textColor=colors.white),
    "bullet": ParagraphStyle("bullet", fontName="Helvetica", fontSize=9, leading=13, textColor=INK, leftIndent=10,
                             bulletIndent=0, spaceAfter=3),
    "formula": ParagraphStyle("formula", fontName="Courier", fontSize=8.2, leading=11.5, textColor=NAVY,
                              backColor=TINT, borderPadding=(5, 6, 5, 6), spaceBefore=3, spaceAfter=8),
}


def P(t, s="p"):
    return Paragraph(t, st[s])


def bullets(items, small=False):
    sty = ParagraphStyle("bs", parent=st["bullet"], fontSize=7.6, leading=9.6, spaceAfter=1) if small else st["bullet"]
    return [Paragraph(t, sty, bulletText="•") for t in items]


def fig(name, width_mm=178):
    img = Image(f"{FIG}/{name}.png")
    r = img.imageHeight / img.imageWidth
    img.drawWidth = width_mm * mm
    img.drawHeight = width_mm * mm * r
    return img


def table(rows, widths, header=True, zebra=True, bold_first_col=False, align_right_from=None):
    data = []
    for i, row in enumerate(rows):
        cells = []
        for j, c in enumerate(row):
            style = "cellh" if (header and i == 0) else ("cellb" if (bold_first_col and j <= 1) else "cell")
            cells.append(c if not isinstance(c, str) else Paragraph(c, st[style]))
        data.append(cells)
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if header else 0)
    cmds = [("VALIGN", (0, 0), (-1, -1), "MIDDLE"), ("TOPPADDING", (0, 0), (-1, -1), 2.5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5), ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3), ("LINEBELOW", (0, 0), (-1, -1), 0.3, RULE)]
    if header:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), NAVY))
    if zebra:
        for i in range(1 if header else 0, len(rows)):
            if i % 2 == 0:
                cmds.append(("BACKGROUND", (0, i), (-1, i), TINT))
    t.setStyle(TableStyle(cmds))
    return t


# ------------------------------------------------------------------ data
NATION_FIX = {781: "West Indies", 4219: "India", 88: "South Africa"}
bat = pd.read_pickle(f"{OUT}/ratings_bat.pkl")
bowl = pd.read_pickle(f"{OUT}/ratings_bowl.pkl")
for R in (bat, bowl):
    for pid, n in NATION_FIX.items():
        if pid in R.index:
            R.loc[pid, "nation"] = n
tb = pd.read_csv(f"{OUT}/top_bat.csv", index_col=0)
tw = pd.read_csv(f"{OUT}/top_bowl.csv", index_col=0)
cons = {r: pd.read_csv(f"{OUT}/consensus_{r}.csv", index_col=0) for r in ("bat", "bowl")}                # every eligible player
cons_auc = {r: pd.read_csv(f"{OUT}/consensus_auction_{r}.csv", index_col=0) for r in ("bat", "bowl")}  # IPL 2027 auction pool
fswing = pd.read_csv(f"{OUT}/factor_swing.csv", index_col=0)
closers = pd.read_csv(f"{OUT}/closers.csv", index_col=0)
N_SPECS = 73
rel = pd.read_csv(f"{OUT}/reliability.csv")
tv = pd.read_csv(f"{OUT}/temporal_validation.csv")
wpv = pd.read_csv(f"{OUT}/wp_validation.csv")
pb = pd.read_csv(f"{OUT}/params_bat.csv", index_col=0).iloc[:, 0]
pw = pd.read_csv(f"{OUT}/params_bowl.csv", index_col=0).iloc[:, 0]
top_bat = bat.loc[cons["bat"].index[:10]].join(cons["bat"][["consensus_PRI", "consensus_rank", "top10_share", "median_rank", "tied"]])
REL = {(r.role, r.metric): r.full_sample_reliability for r in rel.itertuples()}
rel_pq_b, rel_pq_w = REL[("bat", "Pressure Quality (PRI core)")], REL[("bowl", "Pressure Quality (PRI core)")]
rel_wpa_b, rel_rv_b = REL[("bat", "Raw pressure WPA")], REL[("bat", "Raw pressure run value")]
top_bowl = bowl.loc[cons["bowl"].index[:10]].join(cons["bowl"][["consensus_PRI", "consensus_rank", "top10_share", "median_rank", "tied"]])
crank = {r: cons[r].consensus_rank for r in cons}
CG = pd.read_csv(f"{OUT}/close_games.csv").reset_index(drop=True)
CG["pos"] = range(1, len(CG) + 1)
cg_rr = CG[CG.team == "Rajasthan Royals"].iloc[0]
cg_top = CG.iloc[0]
imp = pd.read_csv(f"{OUT}/rr_impact.csv").set_index("pid")
cards = pd.read_csv(f"{OUT}/cards.csv")
CTX = pd.read_csv(f"{OUT}/context_summary.csv", index_col=0).value      # ground and opponent effect sizes
ctxc = pd.read_csv(f"{OUT}/ctx_compare.csv")                              # Test 8
ctxm = pd.read_csv(f"{OUT}/ctx_moves.csv")
_ro = pd.read_csv(f"{OUT}/reliability_without_context.csv")
REL_OLD = _ro[_ro.metric == "Pressure Quality (PRI core)"].set_index("role").full_sample_reliability
tier_s = pd.read_csv(f"{OUT}/tier_check.csv")
pak = pd.read_csv(f"{OUT}/consensus_bowl_incl_pak.csv", index_col=0)
pak_bat = pd.read_csv(f"{OUT}/consensus_bat_incl_pak.csv", index_col=0)
NAWAZ_RANK = int(pak.loc[2490, "consensus_rank"])
PAK_DROPS = [n for n in cons["bowl"].name.head(10) if n not in set(pak.name.head(10))]
BAT_SAME = list(pak_bat.name.head(10)) == list(cons["bat"].name.head(10))
best_trio = imp.loc[[imp[imp.slot == s].wins.idxmax() for s in ("middle / finish", "pace", "spin")]]
AUC = pd.read_csv(f"{OUT}/rr_auction.csv").set_index("pid")
# best auction buy per gap; the three gaps use exactly RR's three overseas slots if all are overseas
free_trio = AUC.loc[[AUC[AUC.slot == s].wins.idxmax() for s in ("middle / finish", "pace", "spin")]]
n_os = int((free_trio.nation != "India").sum())
gems_all = pd.read_csv(f"{OUT}/extra_gems.csv")
LAST_FEE = {"Matheesha Pathirana": "Rs 18 Cr (KKR, 2026 auction)", "Wanindu Hasaranga": "Rs 2 Cr base (LSG, 2026 auction)",
            "Tushar Deshpande": "Rs 6.5 Cr (RR)", "Daryl Mitchell": "unsold in 2026", "Mujeeb Ur Rahman": "unsold in 2026",
            "Maheesh Theekshana": "unsold in 2026", "Mark Adair": "never played IPL"}
TEAM_ABBR = {"Royal Challengers Bengaluru": "RCB", "Sunrisers Hyderabad": "SRH", "Lucknow Super Giants": "LSG",
             "Kolkata Knight Riders": "KKR", "Chennai Super Kings": "CSK", "Rajasthan Royals": "RR",
             "Mumbai Indians": "MI", "Delhi Capitals": "DC", "Punjab Kings": "PBKS", "Gujarat Titans": "GT", "-": "Not in an IPL 2026 squad"}


def team(x):
    return TEAM_ABBR.get(x, x)


SHORT = {"Rashid Khan": "Rashid", "Krunal Pandya": "Krunal", "Namboori Tilak Varma": "Tilak Varma",
         "Varun Chakravarthy": "Varun", "Kuldeep Yadav": "Kuldeep"}


def short_name(n):
    return SHORT.get(n, n.split()[-1])


def and_list(xs):
    xs = list(xs)
    return xs[0] if len(xs) == 1 else ", ".join(xs[:-1]) + " and " + xs[-1]


def _every(role):
    """Players top 10 in every specification, as a sentence subject."""
    n = [short_name(x) for x in cons[role][cons[role].top10_share >= 1].name]
    return and_list(n) + (" is" if role == "bat" and len(n) == 1 else "")


_out_ = ctxm[ctxm.rank_with > 10].sort_values(["role", "rank_without"])
_in_ = ctxm[ctxm.rank_with <= 10].sort_values(["role", "rank_with"])
_moves_txt = (and_list([f"{r['name']} ({'batter' if r.role == 'bat' else 'bowler'} #{r.rank_without} to #{r.rank_with})" for _, r in _out_.iterrows()])
              + " drop out, and " + and_list([f"{r['name']} (#{r.rank_without} to #{r.rank_with})" for _, r in _in_.iterrows()]) + " come in")


# ------------------------------------------------------------------ page furniture
def on_page(c, doc):
    c.saveState()
    c.setFillColor(PINK)
    c.rect(0, H - 4 * mm, W, 4 * mm, stroke=0, fill=1)
    c.setFont("Helvetica", 7)
    c.setFillColor(INK2)
    c.drawString(M, 9 * mm, "SupeRR Selector Season 2  |  Pressure Reliability Index (PRI)  |  Methodology report")
    c.drawRightString(W - M, 9 * mm, f"{doc.page}")
    c.restoreState()


def on_cover(c, doc):
    c.saveState()
    c.setFillColor(NAVY)
    c.rect(0, H - 92 * mm, W, 92 * mm, stroke=0, fill=1)
    c.setFillColor(PINK)
    c.rect(0, H - 94 * mm, W, 2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, H - 20 * mm, "SUPERR SELECTOR SEASON 2  •  ROUND 1  •  RAJASTHAN ROYALS")
    c.setFont("Helvetica-Bold", 30)
    c.drawString(M, H - 40 * mm, "Who delivers when")
    c.drawString(M, H - 52 * mm, "the game is on the line?")
    c.setFont("Helvetica", 11)
    c.drawString(M, H - 64 * mm, "The Pressure Reliability Index (PRI): a win-probability definition of pressure,")
    c.drawString(M, H - 70 * mm, "a context-adjusted rating, and tested top-10 lists, with an IPL 2027 auction lens.")
    c.setFont("Helvetica", 8.5)
    c.setFillColor(colors.HexColor("#c9d3ea"))
    c.drawString(M, H - 82 * mm, "818 matches  •  195,124 deliveries  •  IPL 2022-26 + T20Is 2022-26  •  code: " + CODE_URL.replace("https://", ""))
    c.linkURL(CODE_URL, (M, H - 84 * mm, W - M, H - 79 * mm), relative=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 10)
    c.drawRightString(W - M, H - 20 * mm, "Prepared by Margesh")
    # interactive dashboard link (clickable)
    c.setFillColor(PINK)
    c.roundRect(W - M - 74 * mm, H - 33 * mm, 74 * mm, 8.5 * mm, 2 * mm, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(W - M - 37 * mm, H - 29.6 * mm, "Open the interactive dashboard  >")
    c.setFont("Helvetica", 7.5)
    c.drawRightString(W - M, H - 37 * mm, DASH_URL.replace("https://", ""))
    c.linkURL(DASH_URL, (W - M - 74 * mm, H - 38.5 * mm, W - M, H - 24.5 * mm), relative=0)
    c.restoreState()
    on_page(c, doc)


doc = BaseDocTemplate(PDF, pagesize=A4, leftMargin=M, rightMargin=M, topMargin=14 * mm, bottomMargin=16 * mm,
                      title="Pressure Reliability Index - SupeRR Selector Season 2", author="Margesh")
frame = Frame(M, 16 * mm, W - 2 * M, H - 30 * mm, id="f")
cover_frame = Frame(M, 16 * mm, W - 2 * M, H - 112 * mm, id="c")
doc.addPageTemplates([PageTemplate("cover", [cover_frame], onPage=on_cover), PageTemplate("body", [frame], onPage=on_page)])

S = []
# ------------------------------------------------------------------ cover: the answer first
S.append(NextPageTemplate("body"))
S.append(P("THE ANSWER", "kick"))
S.append(P("Final rankings (as submitted on Unstop)", "h1"))


def cover_list(top, extra):
    rows = [["#", "Player", "Lift", "Cons.", "Score", "Top-10 in specs"]]
    for i, (pid, r) in enumerate(top.iterrows(), 1):
        rows.append([f"{i}{'†' if r.tied else ''}", f"<b>{r['name']}</b>", f"{r.lift:+.1f}", f"{r.succ_raw*100:.0f}%",
                     f"{r.consensus_PRI:+.2f}", f"{r.top10_share*100:.0f}%"])
    return table(rows, [7, 34, 11, 12, 11, 13])


lists = Table([[P("<b>Top 10 batters under pressure</b>", "h2"), P("<b>Top 10 bowlers under pressure</b>", "h2")],
               [cover_list(top_bat, None), cover_list(top_bowl, None)]], colWidths=[89 * mm, 89 * mm])
lists.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
S.append(lists)
S.append(Spacer(1, 4))
n_lift = {r: int(((bat if r == "bat" else bowl).loc[cons[r].index[:10]].lift > 0).sum()) for r in cons}
_kept = {r: sum(route(x["name"], x.ipl_2026_team)[0] == "Under contract" for _, x in T.iterrows())
         for r, T in (("bat", top_bat), ("bowl", top_bowl))}
_at_rr = sum(route(x["name"], x.ipl_2026_team)[0] == "Already at RR" for T in (top_bat, top_bowl) for _, x in T.iterrows())
_words = {2: "Two", 3: "Three", 5: "Five", 6: "Six", 7: "Seven", 8: "Eight", 9: "Nine"}
S.append(P(f"Score = consensus PRI: performance on pressure balls vs an average player in the same situations (same ground, "
           f"same opponent), plus Lift (vs the player's own normal level, runs per 100 balls), consistency across pressure "
           f"matches and win impact, averaged over {N_SPECS} model specifications (0 = average eligible player). Cons. = share "
           f"of pressure matches beating expectation. {n_lift['bat']} of our batters and {n_lift['bowl']} of our bowlers have "
           "positive Lift (Sooryavanshi and Pathirana roughly neutral; Abhishek Sharma the one dip). † Dead heat (score gap "
           "< 0.01, chained), ordered by share of specifications in the top 10, then pressure matches. "
           f"<b>{_words.get(_kept['bat'], _kept['bat'])} batters and {_words.get(_kept['bowl'], _kept['bowl']).lower()} bowlers "
           f"here were kept by other IPL teams for 2027 ({_words.get(_at_rr, _at_rr).lower()} more batters are already at RR), so RR cannot buy them: page 2 "
           "ranks the players RR can buy, with a backup order.</b>", "small"))
S.append(Spacer(1, 6))
S.append(P("FOUR THINGS RR SHOULD KNOW", "kick"))
S += bullets([
    "<b>Pressure is measurable, and it is not the same as \"death overs\".</b> We define it as the expected swing in "
    "win probability on the next ball. Only 18% of deliveries qualify; the other 82% are 'normal' balls, the baseline for "
    "each player's usual level. Even in chase death overs only about a third of balls are high-pressure.",
    f"<b>Raw \"clutch\" stats are mostly noise.</b> Raw pressure win-probability-added has a reliability of only {rel_wpa_b:.2f} for "
    "batters, so one set of matches barely predicts the next. Our shrunk Pressure Quality, judged against the same "
    f"situation, ground and opponent, reaches {rel_pq_b:.2f} for batters and {rel_pq_w:.2f} for bowlers, and predicts "
    "later seasons better than leaving grounds and opponents out (Section 7).",
    f"<b>The lists do not hinge on our assumptions.</b> We re-ran the full pipeline under {N_SPECS} combinations of "
    "pressure threshold, weights, priors, recency, knockout and opposition settings, and rank on the average. "
    + _every("bowl") + " are top 10 in every specification; " + _every("bat") + " the only batter who is.",
    f"<b>RR's gap is the middle order and the bowling under pressure.</b> In the tensest third of games RR won "
    f"{int(cg_rr.close_wins)} of {int(cg_rr.close_games)} in 2025-26 (30%), the lowest win rate of the 10 teams. The best auction buys for those "
    f"gaps ({', '.join(free_trio.name)}) add about <b>{free_trio.wins.round(2).sum():.2f} wins a season</b> (Section 8).",
])
S.append(PageBreak())

# ------------------------------------------------------------------ the backup order: top 20 in the auction pool
def role_of(role, r):
    if role == "bat":
        n = r.bat_pos
        return "opener" if n <= 2 else "top order" if n <= 3 else "middle order" if n <= 5 else "finisher"
    t = r.bowl_type.lower()
    return ("wrist spin" if "chinaman" in t else "leg-spin" if "leg" in t else "off-spin" if "offbreak" in t else
            "left-arm spin" if "orthodox" in t else "pace")


def broad(role, w):
    return ("top" if w in ("opener", "top order") else "middle") if role == "bat" else ("pace" if w == "pace" else "spin")


def sure_word(x):
    return "Very sure" if x >= .9 else "Sure" if x >= .6 else "Borderline" if x >= .3 else "Unlikely"


def top20(role):
    R = bat if role == "bat" else bowl
    C = cons_auc[role].head(20)
    roles = {pid: role_of(role, R.loc[pid]) for pid in C.index}
    rows = [["#", "Player", "Overall", "Role", "Place", "Why he is free", "Score", "Top 10 of pool"]]
    for pid, c in C.iterrows():
        r = R.loc[pid]
        rb = released_by(c["name"], r.ipl_2026_team)
        why = (f"Released ({team(rb)})" if rb else "Unsold in 2026" if c["name"] in UNSOLD_2026 else "No IPL squad")
        rows.append([f"{int(c.consensus_rank)}{'†' if c.tied else ''}", f"<b>{c['name']}</b>" if c.consensus_rank <= 10 else c["name"],
                     f"#{int(c.overall_rank)}", roles[pid], "Indian" if r.nation == "India" else "Overseas", why, f"{c.consensus_PRI:+.2f}",
                     sure_word(c.top10_share)])
    t = table(rows, [9, 44, 15, 24, 18, 30, 16, 22])
    t.setStyle(TableStyle([("LINEBELOW", (0, 10), (-1, 10), 1.4, PINK),
                           ("BACKGROUND", (0, 11), (-1, 20), colors.HexColor("#F3F4F8")),
                           ("TOPPADDING", (0, 1), (-1, -1), 0.9), ("BOTTOMPADDING", (0, 1), (-1, -1), 0.9)]))
    # backups by role: ranks 11-20 grouped, so a missed pick is replaced like with like
    groups = {}
    for pid, c in C[C.consensus_rank > 10].iterrows():
        groups.setdefault(broad(role, roles[pid]), []).append(f"{c['name']} (#{int(c.consensus_rank)})")
    lab = {"top": "Top-order backups", "middle": "Middle-order backups", "pace": "Pace backups", "spin": "Spin backups"}
    line = P("  ·  ".join(f"<b>{lab[k]}:</b> {', '.join(v)}" for k, v in groups.items()), "small")
    return [t, Spacer(1, 2), line]


neg = {r: int(cons_auc[r][cons_auc[r].consensus_PRI < 0].consensus_rank.min()) for r in cons_auc}
ind = [f"{c['name']} (bowler #{int(c.consensus_rank)})" for pid, c in cons_auc["bowl"].head(20).iterrows() if bowl.nation[pid] == "India"]
S.append(P("RR AUCTION BOARD", "kick"))
S.append(P("The 20 best players RR can actually buy, and who to take if a pick is missed", "h1"))
S.append(P(f"Our top 10s rank every IPL-eligible player, as the brief asks; players kept by their teams ({AS_OF}) cannot be "
           "bought. This board ranks only the 16 Dec auction pool on the same scores ('Overall' = rank in the full lists). "
           "If a pick is missed, take the next name:", "small"))
S += bullets([
    "<b>Replace like with like.</b> Under each table, ranks 11-20 are grouped by role: a missed spinner is replaced by the "
    "first spin backup, a missed opener by the first top-order backup.",
    f"<b>Watch the overseas places.</b> RR have {RR_OVERSEAS_SLOTS} overseas places. Indian players need none: "
    + ", ".join(ind) + ".",
    f"<b>Ranks 11-20 are the best of what is left, not equals.</b> Scores fall below the average of all rated players from "
    f"batter #{neg['bat']} and bowler #{neg['bowl']}. For batting, check the hidden gems in Section 10 (such as M Shahrukh "
    "Khan) before going far down.",
], small=True)
S.append(Spacer(1, 3))
S.append(P("<b>Batters</b>", "p"))
S += top20("bat")
S.append(P("<b>Bowlers</b>", "p"))
S += top20("bowl")
S.append(P(f"Top 10 of pool: Very sure = 90%+ of {N_SPECS} specifications, Sure 60%+, Borderline 30%+, Unlikely below 30%. Harry "
           f"Brook (#{crank['bat'][6280]} overall) is not on the board: he is banned from the IPL until the 2028 auction. "
           "Bangladesh players: registered by the BCB, but KKR released Mustafizur in Jan 2026 on BCCI instructions, so "
           "treat them as a risk.", "small"))
S.append(PageBreak())

# ------------------------------------------------------------------ the author's own note (only if written)
if MY_VIEW and os.path.exists(MY_VIEW):
    lines = [l.rstrip() for l in open(MY_VIEW, encoding="utf-8") if not l.lstrip().startswith("<!--")]
    body = [l for l in lines if l.strip() and not l.startswith("# ")]
    if body:
        S.append(P("MY VIEW", "kick"))
        S.append(P(next((l[2:] for l in lines if l.startswith("# ")), "In my own words"), "h1"))
        para = []
        for l in lines + [""]:
            if l.startswith("# "):
                continue
            if l.startswith("## "):
                if para: S.append(P(" ".join(para))); para = []
                S.append(P(l[3:], "h2"))
            elif l.startswith("- "):
                if para: S.append(P(" ".join(para))); para = []
                S += bullets([l[2:]])
            elif l.strip():
                para.append(l.strip())
            elif para:
                S.append(P(" ".join(para))); para = []
        S.append(Spacer(1, 6))
        S.append(P("<b>Margesh</b>"))
        S.append(PageBreak())

# ------------------------------------------------------------------ read this first: plain-English glossary
S.append(P("READ THIS FIRST", "kick"))
S.append(P("The key terms in plain English", "h1"))
S.append(P("No statistics background is needed to read this report. Every number in it is one of the terms below. "
           f"The same explanations appear as tooltips in the interactive dashboard: <link href='{DASH_URL}' color='#E4087C'><u>{DASH_URL.replace('https://', '')}</u></link>."))
G = [
    ("Pressure ball", "A ball where the match could swing either way. We measure how much the next ball can change each "
     "team's chance of winning; if it can change it a lot, it is a pressure ball. About 1 ball in 5 qualifies.",
     "Needing 12 off the last over with 2 wickets left is huge pressure; 12 off 6 overs with 8 wickets left is none."),
    ("Pressure Index (PI)", "How tense a ball is. 1 = an average ball; 1.5 or more = a pressure ball; famous last-ball "
     "finishes reach 14 to 28.", "Rinku Singh's five sixes: the first came at 0.5 (game nearly lost), the last at 28."),
    ("Expected", "What an average player would have done in exactly the same situation (same over, score, wickets, "
     "target), at the same ground and against the same opponent. Beating 'expected' is what counts, so openers and "
     "finishers, and players from strong and weak teams, are judged fairly.",
     f"Strike rate {tb.SR_p[6396]:.0f} vs {tb.xSR_p[6396]:.0f} expected = {tb.SR_p[6396] - tb.xSR_p[6396]:.0f} more runs "
     "per 100 balls than an average batter in the same spots."),
    ("Ground and opponent", "Some grounds are easier to score at, and facing Bumrah is harder than facing an average "
     "bowler. Each ball's 'expected' is raised or lowered for both, so nobody gains from a small ground or a weak "
     "opponent.", f"Facing Bumrah, an average batter is expected to score {-CTX['bumrah']:.0f} fewer runs per 100 balls."),
    ("Score (PRI)", "One number for performance under pressure. It combines four parts: Pressure Quality (beating "
     "expected), Consistency (doing it often), Lift (rising above his own normal level) and Win Impact (changing results).",
     "0 = an average eligible player; +1 or more = elite; below 0 = below average."),
    ("Consistency", "The share of a player's tense matches in which he beat what an average player would have done.",
     "Rinku Singh: 18 of 20 tense matches (90%)."),
    ("Lift", "How much better (or worse) he is under pressure than in his own normal games, in runs per 100 balls. "
     "A wicket counts as the runs it costs the team.", "Positive = rises to the occasion; negative = dips."),
    ("Top 10 in specs", "We ran the whole analysis 73 different reasonable ways (different pressure cut-offs, weightings "
     "and so on). This is the share of those runs that put the player in the top 10.",
     "100% = top 10 however you measure it; under 50% = borderline."),
    ("Reliability", "Skill or luck? We split each player's matches into two random halves and check whether a measure "
     "gives the same answer in both. 1 = perfectly consistent, 0 = pure luck.",
     "Our measure: about 0.5. The usual 'clutch' statistics: about 0.05, i.e. mostly luck."),
    ("Wins added", "If a player had taken the pressure balls RR gave to its below-average players in his role in 2026, "
     "how many more matches RR would have expected to win that season.",
     "+0.4 sounds small, but RR finished one win short of the top two in 2026."),
    ("80% range", "The range we are 80% confident contains the true value. Wider = less certain, usually because "
     "the player has fewer pressure balls.", None),
    ("† Dead heat", "Scores within 0.01 of each other are a statistical tie. The player who is top 10 in more of the 73 "
     "versions of the analysis is placed first (robustness), then the one with more pressure matches.", None),
    ("Auction", f"In no IPL 2027 squad after the official retention lists ({AS_OF}), so RR can bid for him at the "
     "16 Dec auction if he registers.", "Pathirana: released by KKR, now in the auction."),
]
rows = [["Term", "What it means", "Example"]]
for t, m, e in G:
    rows.append([f"<b>{t}</b>", m, e or ""])
S.append(table(rows, [30, 88, 60]))
S.append(Spacer(1, 6))
S.append(P("Where each part of the brief is answered", "h2"))
S.append(table([["The brief asks for", "Where"],
                ["Pressure definition, and why it is meaningful", "Section 2 (with proof it tracks real swings in the result)"],
                ["Batting and bowling metrics, player baselines, scoring logic", "Section 3"],
                ["Fair comparisons: sample size, eligibility, contexts, IPL and T20I", "Section 4"],
                ["Evidence for the top 10 and their order", "Sections 5, 6 and 9 (player cards)"],
                ["Reliability, consistency across matches, limitations", "Section 7 (ten tests)"],
                ["Reproducibility", "Appendix B and the public code"],
                ["How each player could strengthen the RR squad", "Section 8 and page 2"]], [100, 78]))
S.append(PageBreak())

# ------------------------------------------------------------------ 1. approach
S.append(P("1  OVERVIEW", "kick"))
S.append(P("How the system works", "h1"))
S.append(P("Every delivery in the data pack is replayed through a match-state engine. Each ball receives a "
           "<b>Pressure Index</b> (how much the match can swing on it) and an <b>expected outcome</b> (what an average "
           "player would produce in exactly that context). Players are then rated on how far they beat expectation when "
           "pressure is high, relative to how they perform normally, and every estimate is shrunk in proportion to how much "
           "evidence supports it."))
flow = [["Step", "What happens", "Output"],
        ["1  State engine", "Rebuild score, wickets, legal balls left, target and required rate before every ball. "
         "Decode extras (wides and no-balls are not legal balls; byes and leg-byes are not charged to the bowler).", "195,124 ball states"],
        ["2  Win-probability model", "Gradient-boosted classifiers (monotonic constraints) for each innings, trained on "
         "this data, validated with 5-fold match-grouped CV.", "WP before and after each ball"],
        ["3  Pressure Index", "Leverage = expected |change in WP| over the league outcome distribution for the phase, "
         "scaled so the league average = 1; x1.25 in knockouts. Pressure ball = PI >= 1.5.", "PI per ball; 18.3% are pressure"],
        ["4  Expectation model", "League-expected runs, dismissal, boundary and dot probability given innings, over, "
         "wickets, required rate, scoring environment; then adjusted for the ground and the exact opponent on that ball.",
         "Context-neutral residuals"],
        ["5  Player rating", "Component-wise empirical-Bayes shrinkage; pressure evidence shrunk toward the player's own "
         "baseline; four components combined into the PRI.", "PRI per batter and bowler"],
        ["6  Model averaging", f"Re-run steps 3-5 under {N_SPECS} specifications (thresholds, weights, priors, recency, "
         "knockout, opposition); final score = average PRI.", "Consensus ranking"],
        ["7  Validation", "Split-half reliability, out-of-time test (2022-24 to 2025-26), 1,000-sample match "
         "bootstrap, face-validity check on famous moments.", "Confidence for every rank"]]
S.append(table(flow, [32, 112, 34], bold_first_col=False))
S.append(Spacer(1, 6))
S.append(P("Data used", "h2"))
S.append(P("The pack contains 883 matches. We drop 40 abandoned or no-result games and 34 rain-reduced games, where "
           "DLS targets break the state model; the two sets overlap, so 65 matches are removed in total. That leaves "
           "<b>818 matches</b>: 357 IPL (2022-26), 431 T20Is and 30 A-team fixtures (Emerging Asia Cup 2024, Rising "
           "Stars 2025). Super overs are excluded from ratings. Every number in this report is reproduced by the "
           f"Python scripts listed in Appendix B, published at <link href='{CODE_URL}' color='#E4087C'><u>{CODE_URL.replace('https://', '')}</u></link>."))

# ------------------------------------------------------------------ 2. pressure definition
S.append(PageBreak())
S.append(P("2  PRESSURE DEFINITION", "kick"))
S.append(P("Pressure = how much the next ball can change who wins", "h1"))
S.append(P("Required rate, wickets in hand, balls left, the closeness of the contest and the stage of the innings all "
           "matter, but only in combination. Needing 30 off 18 is enormous pressure with 4 wickets left and a formality "
           "with 8 left. Rather than hand-weighting these signals, we let a <b>win-probability model</b> combine them, then "
           "measure pressure as <b>leverage</b>: the expected absolute change in win probability that the next delivery "
           "will cause."))
S.append(P("LI(ball)  = SUM over outcomes o in {0,1,2,3,4,6,W,wide}  P(o | phase, competition) x |WP(state after o) - WP(state now)|<br/>"
           "PI(ball)  = LI / mean(LI)  x 1.25 if knockout (final / qualifier / eliminator / semi-final)<br/>"
           "Pressure ball  :=  PI >= 1.5   (18.3% of all deliveries)", "formula"))
S.append(P("<b>Why this definition is meaningful.</b> (1) It works identically for batting and bowling, because the same ball is "
           "high-pressure for both players. (2) It covers both innings: a first-innings collapse at 40/4 scores high, while "
           "a chase that is already won or already lost scores near zero. (3) It is continuous and calibrated, so no "
           "arbitrary over cut-offs are needed. (4) It is learned from this data, so it reflects the modern "
           "impact-player scoring environment."))
CHK = pd.read_csv(f"{OUT}/check_summary.csv", index_col=0).iloc[:, 0]
DEC = pd.read_csv(f"{OUT}/check_deciles.csv")
S.append(P(f"<b>Proof that it measures real pressure.</b> Split every ball into ten equal groups by Pressure Index. The actual "
           f"swing in win probability on the ball rises in every step, from {DEC.swing.iloc[0]:.2f}% in the calmest tenth to "
           f"{DEC.swing.iloc[-1]:.1f}% in the tensest ({CHK['top_vs_bottom']:.0f} times as much). The {CHK['ball_share_pressure']*100:.0f}% "
           f"of balls we call pressure carry {CHK['wp_share_pressure']*100:.0f}% of all the win-probability movement in the data.", "p"))
S.append(fig("f1_pressure_map", 118))
S.append(P("Figure 1. Mean Pressure Index in chases. Pressure runs along a diagonal ridge where the required rate is "
           "achievable but uncertain. The bottom-left corner (few runs, few balls) and the top-left (impossible asks) both "
           "carry low pressure.", "small"))
S.append(fig("f2_tiers", 128))
S.append(P("Figure 2. The definition separates genuinely different situations. In Extreme-pressure balls (PI 3+) the "
           "league scores 15% faster and loses wickets 52% more often than in Low-pressure balls: the risk-reward trade-off "
           "changes, which is exactly where reliable players separate from the rest.", "small"))

S.append(P("Face validity: the model finds the moments everyone remembers", "h2"))
S.append(table([["Match", "Moment", "Pressure Index", "Win-prob. swing"],
                ["IPL 2024, SRH v RR", "Bhuvneshwar traps Rovman Powell lbw, last ball, 2 to win (SRH won by 1 run)", "28.4", "-92%"],
                ["IPL 2024, KKR v RCB", "Karn Sharma hits Starc for six (9 off 3), then is caught next ball (KKR won by 1 run)", "7.7 / 16.4", "+85% / -84%"],
                ["IPL 2022, PBKS v GT", "Rahul Tewatia's last-ball six off Odean Smith, 6 to win", "14.3", "+83%"],
                ["IPL 2024, PBKS v RR", "Shimron Hetmyer hits Arshdeep for six, 10 off 4 (RR won by 3 wickets)", "8.6", "+83%"],
                ["IPL 2023, GT v KKR", "Rinku Singh's five sixes: the first three barely move WP (still about 5%); the 4th and 5th swing +38% and +57%", "0.5 to 28.0", "+38% / +58%"],
                ["Asia Cup 2022, PAK v AFG", "Naseem Shah hits Farooqi for a second straight six, 5 off 5, one wicket left", "15.6", "+69%"]],
               [36, 96, 22, 24]))
S.append(Spacer(1, 3))
S.append(P("All six are among the largest single-ball swings in the 195k-ball data set. The Rinku sequence shows the "
           "index behaving like cricket intuition: pressure is low while the chase is near-impossible and spikes "
           "the moment it becomes live.", "small"))
S.append(P("Win-probability model validation", "h2"))
w1, w2 = wpv.iloc[0], wpv.iloc[1]
S.append(table([["Model", "Balls", "Brier", "Brier (naive)", "Log-loss", "AUC"],
                ["1st innings (P batting side wins)", f"{int(w1.n_balls):,}", f"{w1.brier:.3f}", f"{w1.brier_naive:.3f}", f"{w1.logloss:.3f}", f"{w1.auc:.3f}"],
                ["2nd innings (P chasing side wins)", f"{int(w2.n_balls):,}", f"{w2.brier:.3f}", f"{w2.brier_naive:.3f}", f"{w2.logloss:.3f}", f"{w2.auc:.3f}"]],
               [60, 22, 20, 24, 22, 20]))
S.append(Spacer(1, 3))
S.append(P("Out-of-fold predictions, using 5 folds grouped by match so no match leaks between train and test. Monotonic "
           "constraints keep the model sensible: more runs needed never raises the chaser's win probability. The "
           "first-innings model is weaker by nature, because the target is still unknown. Feature set: balls left, "
           "wickets in hand, runs (or runs needed and required rate), and the competition-season scoring environment. "
           "Calibration curves are in Appendix A.", "small"))

# ------------------------------------------------------------------ 3. performance measurement
S.append(Spacer(1, 10))
S.append(P("3  PERFORMANCE MEASUREMENT", "kick"))
S.append(P("Rating players against the situation, not the scorecard", "h1"))
S.append(P("Raw strike rate and economy under pressure are biased by role. A finisher facing balls at the death will "
           "out-score an opener rebuilding after a collapse. So every ball is compared with a <b>league expectation "
           "model</b> (gradient-boosted, trained on all 195k balls) that predicts expected runs, dismissal, boundary and "
           "dot probability from the innings, over, wickets down, required rate and scoring environment. The player's "
           "contribution on that ball is actual minus expected."))
S.append(P("Adjusting for the ground and the opponent", "h2"))
S.append(P("The situation is not the whole story. A batter who faces Bumrah and Narine has a harder job than one facing "
           "an associate attack, and some grounds are simply easier to score at. So each ball's expectation is adjusted "
           "twice more, using the data itself: <b>a ground effect</b> (how many more or fewer runs and wickets that venue "
           "gives than average) and <b>an opponent effect</b> (how many more or fewer runs and wickets the bowler a batter "
           "faced, or the batter a bowler bowled at, gives or takes than average). The ground, the opponent and the player "
           "himself are fitted together, so a good batter is not mistaken for a flat pitch. Every effect is shrunk toward "
           "zero in proportion to its evidence, so a ground with three matches or an opponent with a few overs barely "
           f"moves anything. Sizes in this data: among the {int(CTX['bat_grounds_10plus'])} grounds with 10 or more matches "
           f"(of {int(CTX['bat_grounds'])}), the most and least batting-friendly differ by about "
           f"<b>{CTX['bat_ground_spread_rpo']:.1f} runs an over</b>. Opponents matter more: an average batter facing Bumrah is "
           f"expected to score <b>{-CTX['bumrah']:.0f} fewer runs per 100 balls</b> (Narine {-CTX['narine']:.0f} fewer), and an "
           f"average bowler bowling at Sooryavanshi is expected to concede <b>{CTX['sooryavanshi']:.0f} more</b> (Abhishek "
           f"Sharma {CTX['abhishek']:.0f} more)."))
S.append(P("xRuns(ball) = league expectation(situation) + ground effect + opponent effect     (same for wickets, boundaries, dots)<br/>"
           "effects fitted jointly with each player's own effect; each shrunk by n / (n + k), k from the data", "formula"))
S.append(P(f"Quality per ball  Q = (runs - xRuns) - (dismissal - xDismissal) x WV        [batters]<br/>"
           f"Q (bowlers)       = -(runs conceded - xRuns) + (wicket - xWicket) x WV<br/>"
           f"WV = run value of a wicket in pressure states, from the expected-runs model = {pb['WV_True']:.1f} runs<br/>"
           f"Reported per 100 balls: 'runs above expectation per 100 balls'", "formula"))
S.append(P("Separating signal from noise: component-wise shrinkage", "h2"))
S.append(P("Runs and dismissals stabilise at very different rates. Dismissals are rare and close to random over a few "
           "hundred balls. We therefore shrink each component separately toward its prior using <b>empirical-Bayes "
           "stabilisation constants k = noise variance / true-skill variance</b>, estimated from the data by "
           "method of moments. A player with n balls keeps n/(n+k) of their observed edge."))
S.append(table([["Component", "Batters k (weighted balls)", "Bowlers k (weighted balls)", "Read as"],
                ["Runs vs expectation, normal balls", f"{pb['r_np']:,.0f}", f"{pw['r_np']:,.0f}", "Scoring skill shows fast"],
                ["Dismissals vs expectation, normal", f"{pb['out_np']:,.0f}", f"{pw['out_np']:,.0f}", "Wicket luck dominates"],
                ["Runs vs expectation, pressure", f"{pb['r_p']:,.0f}", f"{pw['r_p']:,.0f}", "Pressure samples are small"],
                ["Dismissals vs expectation, pressure", f"{pb['out_p']:,.0f}", f"{pw['out_p']:,.0f}", ""],
                ["Win-prob. added, pressure", f"{pb['wpa_p']:,.0f}", f"{pw['wpa_p']:,.0f}", "Heavily luck-driven"]],
               [54, 36, 36, 52]))
S.append(Spacer(1, 6))
S.append(P("The four components of the PRI", "h2"))
S.append(table([["Component", "Weight", "Definition", "Why it is in the index"],
                ["<b>Pressure Quality (PQ)</b>", "45%", "Pressure-ball quality shrunk toward the player's <i>own</i> "
                 "baseline: PQ = (n<sub>P</sub>·Q<sub>P</sub> + 500·Q<sub>base</sub>) / (n<sub>P</sub> + 500)",
                 "Best estimate of true ability under pressure. The out-of-time test showed that shrinking toward the "
                 "player's own baseline predicts future pressure output better than raw pressure numbers."],
                ["<b>Consistency</b>", "20%", "Share of pressure matches (>=4 balls faced / >=6 bowled) in which the player "
                 "beat expectation, shrunk toward the league rate with a prior of 12 matches.",
                 "\"Reliable\" means delivering repeatedly, not one famous night."],
                ["<b>Pressure Lift</b>", "20%", "PQ - Q<sub>base</sub>: how far pressure evidence moves the player above "
                 "or below their own normal level.", "The brief: performance under pressure <i>compared with their usual "
                 "level</i>. Already shrunk by construction."],
                ["<b>Win Impact</b>", "15%", "Win-probability added above league average per 100 pressure balls, "
                 "shrunk to 0 with the k above.", "The bottom line (did it move the result?), but weighted low because "
                 "it is the noisiest signal."]],
               [30, 14, 62, 72]))
S.append(Spacer(1, 3))
S.append(P("PRI = 0.45 z(PQ) + 0.20 z(Consistency) + 0.20 z(Lift) + 0.15 z(Win Impact), with z-scores taken across the "
           "eligible pool. Q<sub>base</sub> is the player's normal-situation quality, component-shrunk toward the league mean. "
           "The baseline prior of 500 balls was chosen on the 2022-24 / 2025-26 out-of-time test; it is one of the "
           "choices averaged over below, and Section 7 quantifies how much each choice matters.", "small"))
S.append(P("Model averaging: no single assumption decides the list", "h2"))
S.append(P("Every modelling choice above is defensible, but none is uniquely right. Rather than pick one, we ran the "
           f"entire rating pipeline under <b>{N_SPECS} specifications</b>: the base case plus 72 drawn at random from a "
           "288-cell grid (pressure threshold 1.25 / 1.5 / 2.0; baseline prior 200 / 500 / 1,000 balls; four weighting "
           "schemes; recency on or off; knockout multiplier on or off; opposition weighting on or off). As in Bayesian "
           "model averaging, the final score is the mean PRI across specifications. Scores within 0.01 are a dead heat "
           "and go to the player who is top 10 in more specifications (the more robust result), then to the one with more "
           "pressure matches.", "p"))
S.append(P(f"Final score(player) = (1/{N_SPECS}) x SUM over specs s of PRI<sub>s</sub>(player)", "formula"))
# ---- worked example: one player from raw balls to score
_r = bat.loc[6396]
_pool = bat[bat.eligible]
_z = {c: (_r[c] - _pool[c].mean()) / _pool[c].std() for c in ("pq", "succ_s", "lift", "wpa_s")}
we = [["Step", f"Tim David (batter #{crank['bat'][6396]})", "What it means"],
      ["1. Pressure balls", f"{int(_r.n_p)} balls in {int(_r.p_matches)} tense matches", "Balls with Pressure Index 1.5 or more"],
      ["2. Raw level under pressure", f"{_r.q_p_raw:+.1f} runs per 100 balls", "vs an average batter in the same situations, at the same grounds, against the same bowlers; each dismissal counts as runs lost"],
      ["3. Usual level (normal balls)", f"{_r.q_base:+.1f}", "his normal-ball level, shrunk toward the league average"],
      ["4. Level under pressure, as used", f"{_r.pq:+.1f} = ({_r.q_p_raw:.1f} x {int(_r.n_p)} + {_r.q_base:.1f} x 500) / ({int(_r.n_p)} + 500)",
       "pressure evidence weighed against his usual level (500-ball prior)"],
      ["5. Lift", f"{_r.lift:+.1f}", "step 4 minus step 3: better under pressure than usual"],
      ["6. Consistency and win impact", f"{_r.succ_raw*100:.0f}% of tense games (shrunk {_r.succ_s*100:.0f}%); {_r.wpa_s:+.1f}", "share of tense games beating expectation; win probability added"],
      ["7. Score (one specification)", f"0.45 x {_z['pq']:.2f} + 0.20 x {_z['succ_s']:.2f} + 0.20 x {_z['lift']:.2f} + 0.15 x {_z['wpa_s']:.2f} = {_r.PRI:+.2f}",
       "each part as a z-score against all eligible batters"],
      ["8. Final score", f"{cons['bat'].consensus_PRI[6396]:+.2f}", f"the average of the step-7 score over all {N_SPECS} specifications"]]
S.append(KeepTogether([P("Worked example: from raw balls to a final score", "h2"), table(we, [40, 72, 66])]))

# ------------------------------------------------------------------ 4. fair comparisons
S.append(Spacer(1, 10))
S.append(P("4  FAIR COMPARISONS", "kick"))
S.append(P("Sample size, eligibility, context and competition", "h1"))
S.append(table([["Issue", "How we handle it"],
                ["<b>Small samples</b>", "Empirical-Bayes shrinkage on every component (Section 3). Eligibility needs >= 100 "
                 "pressure balls faced or bowled and >= 10 matches with meaningful pressure exposure. Every rank carries "
                 "a bootstrap interval (Section 7)."],
                ["<b>Recency</b>", "Balls weighted by a 2.5-year half-life anchored at the last match (IPL 2026 final). "
                 "2026 counts at 1.0 and 2022 at about 0.33. This is a 2027 auction, so current form matters, but older "
                 "evidence still informs. Recency on/off is one of the settings averaged over (Section 7)."],
                ["<b>Active and IPL-eligible</b>", "Must have played in 2025 or 2026. Pakistan nationals are excluded because no "
                 "Pakistan player has been available to IPL teams since 2009, so they cannot be part of an IPL ranking. "
                 "Availability for 2027 (retained, released, banned) is not used in the ranking; it is reported separately "
                 "(page 2, Section 8). "
                 f"Transparency: re-running all {N_SPECS} specifications with them included puts Mohammad Nawaz at "
                 f"#{NAWAZ_RANK} among bowlers ({', '.join(PAK_DROPS)} would drop out)"
                 + ("; the batting top 10 is unchanged." if BAT_SAME else ".")],
                ["<b>IPL vs T20I scoring environments</b>", "The win-probability, expected-runs and expectation models all "
                 "include a scoring-environment feature (runs per over by competition type and year: IPL 2026 = 9.85, "
                 "T20I 2024 = 8.47). Beating expectation in a 9.9-RPO league is judged against 9.9, not 8.5."],
                ["<b>Opposition quality</b>", "Two layers. (1) Every ball's expectation is adjusted for the exact opponent: the "
                 "bowler a batter faced, the batter a bowler bowled at (Section 3). So runs off a weak attack count for less "
                 "and wickets of tail-enders are expected anyway. (2) On top, balls are weighted by the opposing team: IPL "
                 "franchises and the top-10 full members = 1.0; Zimbabwe and Ireland = 0.75; associates and A-teams = 0.5."],
                ["<b>Ground</b>", f"A ground effect for each of the {int(CTX['bat_grounds'])} venues, shrunk toward average by "
                 "how many matches it has hosted, so a few freak games at one ground cannot move a rating (Section 3)."],
                ["<b>Role and phase</b>", "Handled by the expectation model (over, wickets, required rate), so openers and "
                 "finishers are each compared with what is normal for their situation."],
                ["<b>Attribution</b>", "Batters are credited with runs off the bat and their own dismissal only (a "
                 "non-striker run-out is not charged to the striker). Bowlers are charged bat runs, wides and no-balls, "
                 "and credited with wickets except run-outs."],
                ["<b>Excluded data</b>", "Rain-reduced (DLS) matches, abandoned and no-result games, and super overs."],
                ["<b>Data checks</b>", "Extras are counted with their real runs (wides, no-balls, byes, leg-byes). Rebuilt totals "
                 "reproduce the winner of 99.6% of the 747 decided matches and the exact winning margin in 99.5% of matches won "
                 "by runs; no duplicate deliveries; A-team fixtures are their own tier, not IPL; players are matched by ID, "
                 "so the two Rashid Khans stay separate."]],
               [36, 142]))
S.append(Spacer(1, 6))
S.append(P("Who is in the eligible pool", "h2"))
comp = [["Pool", "Players", "Median pressure balls", "Median IPL share of pressure balls", "Mostly-IPL players (>50%)",
         "Top-10 IPL share"]]
for lab, R in (("Batters", bat), ("Bowlers", bowl)):
    E = R[R.eligible]
    comp.append([lab, str(len(E)), f"{E.n_p.median():.0f}", f"{E.ipl_share_p.median()*100:.0f}%",
                 f"{(E.ipl_share_p > 0.5).sum()}", f"{E.head(10).ipl_share_p.mean()*100:.0f}%"])
S.append(table(comp, [24, 20, 30, 42, 32, 30]))
S.append(Spacer(1, 4))
S.append(P("IPL vs T20I: does the ranking depend on the competition?", "h2"))
S.append(P("We re-rated every player on IPL balls only and on T20I balls only (same model, same eligibility rules) and "
           "compared the results with the combined rating. If combining the two competitions were distorting the ranks, "
           "the three versions would disagree.", "p"))
trow = [["Rated on", "Role", "Eligible players", "Rank corr. with combined", "Final top 10 with enough data",
         "...of whom in that competition's top 10"]]
for r in tier_s.itertuples():
    trow.append([r.tier, "Batters" if r.role == "bat" else "Bowlers", str(r.eligible), f"{r.spearman:.2f}",
                 str(r.final_top10_eligible), str(r.final_top10_in_tier_top10)])
S.append(table(trow, [24, 20, 26, 34, 38, 36]))
S.append(Spacer(1, 3))
_t20i_led = list(cards[cards.ipl_rank.isna() & (cards.ipl_share < 0.5)].name)
ipl_b = tier_s[(tier_s.role == "bat") & (tier_s.tier == "IPL only")].iloc[0]
ipl_w = tier_s[(tier_s.role == "bowl") & (tier_s.tier == "IPL only")].iloc[0]
S.append(P(f"The competition-specific ratings agree closely with the combined one (rank correlation "
           f"{tier_s.spearman.min():.2f} to {tier_s.spearman.max():.2f}). Of the final top 10s, "
           f"{ipl_b.final_top10_in_tier_top10} of {ipl_b.final_top10_eligible} batters and {ipl_w.final_top10_in_tier_top10} "
           f"of {ipl_w.final_top10_eligible} bowlers with enough IPL pressure balls are also top 10 on IPL evidence alone. "
           f"{and_list(_t20i_led)} rest{'s' if len(_t20i_led) == 1 else ''} mainly on T20I evidence (flagged on the player "
           f"cards), as does Sooryavanshi's small sample: fewer than 100 pressure balls in either competition alone. "
           "Combining the competitions mainly adds sample size, which is why we keep both.", "small"))
S.append(P("Why level and lift, not lift alone", "h2"))
S.append(P("The brief asks how players perform under pressure compared with their usual level. We measure that as Lift "
           "(pressure quality minus the player's normal-ball quality). But Lift alone ranks badly: for bowlers 'pressure minus "
           "normal' does not agree with itself across two halves of the data, and for batters it mostly rewards finishers "
           "(Test 5). So the score combines level under pressure (45%), consistency (20%), Lift (20%) and win impact (15%): "
           "a dip is penalised, but an elite player is not punished for being elite all the time.", "p"))

# ------------------------------------------------------------------ 5. batters
S.append(PageBreak())
S.append(P("5  EVIDENCE: TOP 10 BATTERS", "kick"))
S.append(P("The best batters under pressure: level, lift and consistency", "h1"))
rows = [["#", "Batter", "IPL 2026 team", "Press. balls / matches", "SR (exp.)", "Outs (exp.)", "Avg", "Lift", "Cons.", "Score", "Specs top-10"]]
for i, (pid, r) in enumerate(tb.head(10).iterrows(), 1):
    rows.append([f"{i}{'†' if r.tied else ''}", f"<b>{r['name']}</b>", team(r.ipl_2026_team).replace("Not in an IPL 2026 squad", "-"),
                 f"{int(r.n_p)} / {int(r.p_matches)}", f"{r.SR_p:.0f} ({r.xSR_p:.0f})", f"{int(r.outs_p)} ({r.exp_outs_p:.1f})",
                 f"{r.avg_p:.1f}", f"{r.lift:+.1f}", f"{r.succ_raw*100:.0f}%", f"{r.consensus_PRI:+.2f}", f"{r.top10_share*100:.0f}%"])
S.append(table(rows, [8, 31, 14, 22, 17, 18, 12, 13, 14, 13, 16]))
S.append(P("SR (exp.) = strike rate under pressure vs what an average batter would score in exactly those situations, grounds and match-ups. "
           "Outs (exp.) = dismissals vs the expected number. Lift = runs above own baseline per 100 pressure balls. "
           "Consist. = share of pressure matches beating expectation. † dead heat, ordered by share of specifications in the top 10, then pressure matches. "
           "IPL 2026 team = team in the data pack; 2027 status is on page 2 and in Section 8.", "small"))
S.append(fig("f12_bat_dumbbell", 160))
S.append(fig("f10_bat_strip", 168))
S.append(P("Figure: every pressure match each batter played (at least 4 pressure balls faced). This is the "
           "consistency-across-matches check the brief asks for: Rinku beat expectation in 18 of 20.", "small"))

S.append(PageBreak())
S.append(P("Why each batter ranks where they do", "h2"))
cl = closers
def _sr(pid):
    return f"strike rate {tb.SR_p[pid]:.0f} vs {tb.xSR_p[pid]:.0f} expected"


def _out(pid):
    return f"out {int(tb.outs_p[pid])} times vs {tb.exp_outs_p[pid]:.1f} expected"


def _t10(pid, R=None):
    return f"top 10 in {(cons['bat'] if R is None else R).top10_share[pid]*100:.0f}% of specifications"


bat_notes = [
    ("Vaibhav Sooryavanshi (RR)", f"{_sr(50284).capitalize()}: the most explosive pressure output in the data, and "
     f"{_t10(50284)}. <b>Smallest sample in the top 10</b> ({int(tb.n_p[50284])} balls, {int(tb.p_matches[50284])} matches); "
     f"lift is near neutral ({tb.lift[50284]:+.1f}), so he plays the same way under pressure. Aged 15, he became India's "
     "youngest international debutant (T20I, 4 Jul 2026). Core RR asset."),
    ("Tim David", f"{_sr(6396).capitalize()}; {tb.death_share_p[6396]*100:.0f}% of his pressure balls come at the death. "
     f"Hit the winning runs in <b>{int(cl.loc[6396, 'hit_winning_runs'])} chases that reached extreme pressure</b>, the "
     f"most of anyone in our top 10. {_t10(6396).capitalize()}."),
    ("Tilak Varma", f"The largest pressure sample in the pool ({int(tb.n_p[7897])} balls, {int(tb.p_matches[7897])} matches). "
     f"Dismissed {int(tb.outs_p[7897])} times vs {tb.exp_outs_p[7897]:.0f} expected (pressure average {tb.avg_p[7897]:.1f}). "
     f"Ordinary in normal situations, so his <b>{tb.lift[7897]:+.1f} lift is the biggest of any batter</b>: the purest "
     "pressure riser in the data."),
    ("Yashasvi Jaiswal (RR)", f"<b>The only batter in the top 10 under all {N_SPECS} specifications.</b> "
     f"{_sr(6819).capitalize()}, lift {tb.lift[6819]:+.1f}, {int(tb.ko_balls_p[6819])} knockout pressure balls."),
    ("Shreyas Iyer", f"{_sr(3647).capitalize()}, lift {tb.lift[3647]:+.1f}; hit the winning runs in "
     f"{int(cl.loc[3647, 'hit_winning_runs'])} extreme-pressure chases; {int(tb.ko_balls_p[3647])} knockout pressure balls. "
     f"Depends on the pressure threshold: near the top at the strictest setting, outside the top 20 at the loosest "
     f"({_t10(3647)})."),
    ("Suryakumar Yadav", f"The most pressure matches in the pool ({int(tb.p_matches[1699])}). {_sr(1699).capitalize()}, "
     f"dismissed less often than expected ({int(tb.outs_p[1699])} vs {tb.exp_outs_p[1699]:.1f})."),
    ("Abhishek Sharma", f"The highest normal-situation level in the pool, but he <b>dips under pressure</b> (lift "
     f"{tb.lift[6281]:+.1f}, {tb.succ_raw[6281]*100:.0f}% consistency). He stays top 10 because even his dipped level is "
     "elite."),
    ("Phil Salt", f"{_sr(5553).capitalize()}, bought at a price: {_out(5553)}. A high-variance attacking profile "
     f"({tb.succ_raw[5553]*100:.0f}% consistency) that is still {_t10(5553)}."),
    ("Rinku Singh", f"Dismissed only <b>{int(tb.outs_p[4708])} times in {int(tb.n_p[4708])} pressure balls against "
     f"{tb.exp_outs_p[4708]:.1f} expected</b> (average {tb.avg_p[4708]:.1f}). Beat expectation in <b>18 of 20 pressure "
     "matches (90%)</b>, the best consistency in the pool on more than 10 matches, and hit the winning runs in "
     f"{int(cl.loc[4708, 'hit_winning_runs'])} extreme-pressure chases."),
    ("Daryl Mitchell", f"{_sr(4106).capitalize()} and {_out(4106)} (pressure average {tb.avg_p[4106]:.1f}), batting at "
     f"No. 4. Mostly T20I evidence for New Zealand ({tb.ipl_share_p[4106]*100:.0f}% of his pressure balls in the IPL), "
     f"and the lowest-conviction pick ({_t10(4106)}): Dasun Shanaka (#{crank['bat'][2436]}) and Harry Brook "
     f"(#{crank['bat'][6280]}) are close behind. Went unsold at the 2026 auction, so he is in the 2027 auction: "
     "RR's best middle-order buy (Section 8)."),
]
for n, t in bat_notes:
    S.append(Paragraph(f"<b>{n}.</b> {t}", st["bullet"], bulletText="\u2022"))
S.append(fig("f4_bat_scatter", 150))
S.append(fig("f14_bat_specs", 150))
S.append(P(f"Grey = rank in each of the {N_SPECS} specifications; blue = mean rank. The final order uses the mean score, not the "
           "mean rank, so a few very low ranks under the strictest settings can pull the blue dot below the final position "
           f"(Abhishek Sharma: final #{crank['bat'][6281]}, median rank {cons['bat'].median_rank[6281]:.0f}, mean rank "
           f"{cons['bat'].mean_rank[6281]:.0f}).", "small"))

# ------------------------------------------------------------------ 6. bowlers
S.append(PageBreak())
S.append(P("6  EVIDENCE: TOP 10 BOWLERS", "kick"))
S.append(P("The best bowlers under pressure: level, lift and consistency", "h1"))
rows = [["#", "Bowler", "IPL 2026 team", "Type", "Legal balls / matches", "Econ (exp.)", "Wkts (exp.)", "Dot %", "Lift", "Cons.", "Score", "Specs top-10"]]
for i, (pid, r) in enumerate(tw.head(10).iterrows(), 1):
    rows.append([f"{i}{'†' if r.tied else ''}", f"<b>{r['name']}</b>", team(r.ipl_2026_team).replace("Not in an IPL 2026 squad", "-"),
                 r.bowl_type.replace("Right-arm ", "RA ").replace("Left-arm ", "LA ").replace("Slow left-arm orthodox", "SLA").replace("Chinaman", "wrist spin"),
                 f"{int(r.legal_p)} / {int(r.p_matches)}", f"{r.econ_p:.2f} ({r.xecon_p:.2f})", f"{int(r.outs_p)} ({r.exp_outs_p:.1f})",
                 f"{r.dotpct_p:.0f}%", f"{r.lift:+.1f}", f"{r.succ_raw*100:.0f}%", f"{r.consensus_PRI:+.2f}", f"{r.top10_share*100:.0f}%"])
S.append(table(rows, [7, 27, 13, 20, 17, 19, 16, 10, 11, 12, 12, 14]))
S.append(P("Econ (exp.) = runs conceded per over under pressure vs the expected economy for those exact situations, grounds and batters. "
           "Wkts (exp.) = wickets vs expected. Consist. = share of pressure matches beating expectation. Legal balls exclude "
           "wides and no-balls; the player cards count all pressure deliveries.", "small"))
S.append(fig("f13_bowl_dumbbell", 160))
S.append(fig("f11_bowl_strip", 168))
S.append(P("Figure: every pressure match each bowler played (at least 6 pressure balls bowled).", "small"))

S.append(PageBreak())
S.append(P("Why each bowler ranks where they do", "h2"))
def _ec(pid):
    return f"economy {tw.econ_p[pid]:.2f} vs {tw.xecon_p[pid]:.2f} expected"


def _wk(pid):
    return f"{int(tw.outs_p[pid])} wickets vs {tw.exp_outs_p[pid]:.1f} expected"


def _t10w(pid):
    return f"top 10 in {cons['bowl'].top10_share[pid]*100:.0f}% of specifications"


bowl_notes = [
    ("Josh Hazlewood", f"<b>{_wk(830)}</b> in {int(tw.legal_p[830])} pressure balls, {_ec(830)}. Ordinary in normal "
     f"situations, so his <b>{tw.lift[830]:+.1f} lift is the largest of any player</b>. Never worse than "
     f"#{int(cons['bowl'].worst_rank[830])} in any specification; {int(tw.ko_balls_p[830])} knockout pressure balls."),
    ("Rashid Khan", f"The biggest bowling sample among our top 10 ({int(tw.legal_p[4722])} legal balls, "
     f"{int(tw.p_matches[4722])} matches): {_wk(4722)}, {_ec(4722)}. Top 10 in every specification and never worse than "
     f"#{int(cons['bowl'].worst_rank[4722])}. In a dead heat with Narine (scores {cons['bowl'].consensus_PRI[4722]:.2f} and "
     f"{cons['bowl'].consensus_PRI[781]:.2f}); placed first on more pressure matches."),
    ("Sunil Narine", f"{_ec(781).capitalize()}, {tw.succ_raw[781]*100:.0f}% consistency, all IPL evidence. Elite normally "
     f"and still lifts {tw.lift[781]:+.1f}. Age (38 in 2026) is the auction risk, not performance."),
    ("Krunal Pandya", f"{_ec(4219).capitalize()}, {_wk(4219)}, {int(tw.ko_balls_p[4219])} knockout pressure balls. Top 10 "
     "in every specification, all on IPL evidence."),
    ("Varun Chakravarthy", f"{_ec(6256).capitalize()} across {int(tw.legal_p[6256])} pressure balls; lift "
     f"{tw.lift[6256]:+.1f}. {_t10w(6256).capitalize()}."),
    ("Kuldeep Yadav", f"{_wk(3644)}, {_ec(3644)}, lift {tw.lift[3644]:+.1f}. <b>The most stable score among top-10 "
     f"bowlers</b> across specifications."),
    ("Jasprit Bumrah", f"The biggest economy gap in the top 10: {tw.econ_p[2933]:.2f} vs {tw.xecon_p[2933]:.2f} expected. "
     f"Wickets are below expectation ({int(tw.outs_p[2933])} vs {tw.exp_outs_p[2933]:.1f}), so his pressure value is run "
     "suppression. He is top 10 in every specification at pressure thresholds 1.25 and 1.5, and in only a third of "
     "those at the strictest 2.0 threshold."),
    ("Mitchell Santner", f"{_ec(4101).capitalize()}, {_wk(4101)}, lift {tw.lift[4101]:+.1f}. Most of his pressure overs "
     f"came in T20Is for New Zealand ({tw.ipl_share_p[4101]*100:.0f}% in the IPL), often against strong batting: he rises "
     f"from #13 to #{crank['bowl'][4101]} once each ball is judged against the batter faced (Test 8). "
     f"{_t10w(4101).capitalize()}."),
    ("Matheesha Pathirana", f"A pure death specialist ({tw.death_share_p[8661]*100:.0f}% of pressure balls at the death): "
     f"{tw.econ_p[8661]:.2f} an over where {tw.xecon_p[8661]:.2f} is expected, in the hardest overs to bowl. "
     f"{_t10w(8661).capitalize()}. <b>Released by KKR on 17 Nov 2026</b>, so he is in the 2027 auction."),
    ("Wanindu Hasaranga", f"{_wk(4900)}, {_ec(4900)}, lift {tw.lift[4900]:+.1f}, {int(tw.ko_balls_p[4900])} knockout "
     f"pressure balls. A three-way dead heat for 9th to 11th with Pathirana and Lockie Ferguson (scores "
     f"{cons['bowl'].consensus_PRI[8661]:.2f}, {cons['bowl'].consensus_PRI[4900]:.2f}, {cons['bowl'].consensus_PRI[4692]:.2f}), "
     f"ordered by share of specifications in the top 10. <b>Released by LSG</b>, so he is in the 2027 auction."),
]
for n, t in bowl_notes:
    S.append(Paragraph(f"<b>{n}.</b> {t}", st["bullet"], bulletText="\u2022"))
S.append(fig("f5_bowl_scatter", 150))
S.append(fig("f15_bowl_specs", 150))
S.append(P(f"Grey = rank in each of the {N_SPECS} specifications; blue = mean rank. The final order uses the mean score, not the "
           "mean rank, so a few very low ranks under the strictest settings can pull the blue dot below the final position "
           f"(Bumrah: final #{crank['bowl'][2933]}, median rank {cons['bowl'].median_rank[2933]:.0f}, mean rank "
           f"{cons['bowl'].mean_rank[2933]:.1f}).", "small"))

# ------------------------------------------------------------------ 7. reliability
S.append(PageBreak())
S.append(P("7  RELIABILITY AND LIMITATIONS", "kick"))
S.append(P("Is the ranking signal or noise? We tested it ten ways", "h1"))
S.append(P("<b>Test 1: split-half reliability.</b> Matches were randomly split into two halves 40 times; we correlated "
           "each player's metric across halves (Spearman-Brown corrected to the full sample). A metric that cannot "
           "agree with itself cannot rank players."))
S.append(fig("f3_reliability", 86))
S.append(P("Raw pressure run value and raw win-probability added, the usual \"clutch\" statistics, barely agree with "
           f"themselves for batters ({rel_rv_b:.2f} and {rel_wpa_b:.2f}). Component shrinkage toward the player's own baseline lifts "
           f"reliability to {rel_pq_b:.2f} (batters) and {rel_pq_w:.2f} (bowlers).", "small"))
CC = pd.read_csv(f"{OUT}/check_components.csv").set_index(["role", "part"]).reliability
S.append(P("<b>Each part of the score on its own.</b> The level under pressure, as used, is the stable part (batters "
           f"{CC[('bat', 'Level under pressure (as used)')]:.2f}, bowlers {CC[('bowl', 'Level under pressure (as used)')]:.2f}). "
           f"Lift and consistency barely repeat on their own (Lift {CC[('bat', 'Lift (as used)')]:.2f} and "
           f"{CC[('bowl', 'Lift (as used)')]:.2f}; consistency {CC[('bat', 'Consistency (share of tense games won)')]:.2f} and "
           f"{CC[('bowl', 'Consistency (share of tense games won)')]:.2f}). We keep them because the brief asks for both "
           "'compared with their usual level' and 'consistently', at 20% each so they adjust the ranking rather than drive "
           "it; Test 7 shows these weights predict later seasons at least as well as weights tuned on the data.", "small"))
S.append(P("<b>Test 2: out-of-time prediction.</b> We rebuilt every rating using only 2022-24 data and asked how well it "
           "ranks players' actual pressure performance in 2025-26 (players with 60+ pressure balls in both windows).", "p"))
tvr = [["Estimator built on 2022-24", "Batters: rank corr. with 2025-26 pressure quality", "Bowlers"]]
for est in ["PRI consensus (73 specs, final method)", "PRI single base specification", "Pressure Quality (PRI core)", "Raw pressure WPA (naive clutch)", "Raw pressure run value",
            "Normal-situation quality only"]:
    a = tv[(tv.role == "bat") & (tv.estimator == est)].r_future_pressure_quality.iat[0]
    bb = tv[(tv.role == "bowl") & (tv.estimator == est)].r_future_pressure_quality.iat[0]
    tvr.append([est, f"{a:+.2f}", f"{bb:+.2f}"])
for lab in ("consensus", "base spec"):
    hb = tv[(tv.role == "bat") & (tv.estimator == f"Top-quartile hit rate ({lab})")].r_future_pressure_quality.iat[0]
    hw = tv[(tv.role == "bowl") & (tv.estimator == f"Top-quartile hit rate ({lab})")].r_future_pressure_quality.iat[0]
    tvr.append([f"<b>Top-quartile hit rate*, {lab}</b>", f"<b>{hb*100:.0f}%</b>", f"<b>{hw*100:.0f}%</b>"])
S.append(table(tvr, [92, 50, 36]))
S.append(Spacer(1, 3))
S.append(P("*Share of the top-quartile players (by 2022-24 index) who were above median under pressure in 2025-26; a coin flip gives 50%. "
           "Honest reading: future pressure performance in T20 is hard to predict for every method (about 50 players, "
           "so the standard error is about 0.14). PRI is competitive with the best single metric while being far more "
           "stable, and <b>roughly two-thirds to seven in ten of its top-quartile players stayed above median under "
           "pressure</b> in the following seasons. Model averaging neither helps nor hurts prediction (all differences are "
           "within noise); we adopt it for robustness, not accuracy.", "small"))
nb, nw = int((top_bat.top10_prob > 0.5).sum()), int((top_bowl.top10_prob > 0.5).sum())
S.append(P("<b>Test 3: bootstrap.</b> Each eligible player's pressure matches were resampled 1,000 times and the full "
           f"index recomputed (base specification). {nb} of the 10 final batters and {nw} of the 10 final bowlers stay "
           "top 10 in a majority of resamples. The rest form the tier near the cut-off: "
           + ", ".join(pd.concat([top_bat, top_bowl])[lambda d: d.top10_prob <= 0.5]["name"]) + ". The two tests answer "
           "different questions: the specifications test our modelling choices, the bootstrap tests match-to-match luck. "
           "Jaiswal is top 10 under every modelling choice but near the cut-off on luck; Sooryavanshi survives resampling "
           "because much of his score rests on his normal-situation level, which is why we flag him as the biggest risk.", "p"))
S.append(P(f"<b>Test 4: specification robustness.</b> Across the {N_SPECS}-specification ensemble, how much does each "
           "assumption move the ranks? Each value is the average swing in rank, for the top 20 players, between that factor's "
           "settings:", "p"))
frows = [["Assumption", "Batters: avg rank swing", "Bowlers: avg rank swing", "Verdict"]]
verdict = {"Pressure threshold": "Most influential, hence averaged over", "Component weights": "Moderate",
           "Recency weighting": "Moderate", "Baseline prior": "Moderate", "Knockout multiplier": "Negligible",
           "Opposition weighting": "Negligible"}
for f, r in fswing.iterrows():
    frows.append([f, f"{r.bat:.1f}", f"{r.bowl:.1f}", verdict.get(f, "")])
S.append(table(frows, [48, 38, 38, 54]))
S.append(Spacer(1, 4))
# ---- Test 5: head-to-head with the approaches most analyses use
cm = pd.read_csv(f"{OUT}/compare_methods.csv")
t5 = []
t5.append(P("<b>Test 5: head-to-head with the usual approaches.</b> The two most common ways to answer this brief are (A) "
           "call the death overs or a 10+ required rate 'pressure' and rank by raw strike rate or economy, and (B) the same "
           "pressure, ranked by 'under pressure minus normal', which is how most analyses answer 'compared with their usual "
           "level'. We scored all three methods on the same players with three neutral tests:", "p"))
cr = [["Method", "Role", "Skill, not luck (reliability)", "Predicts 2025-26 (from 2022-24)", "Role bias (lower = fairer)"]]
short = {"Common: death overs / high required rate + raw strike rate": "A: death overs + raw strike rate",
         "Common: same pressure, strike rate under pressure minus normal": "B: pressure minus normal SR",
         "Common: death overs / high required rate + raw economy": "A: death overs + raw economy",
         "Common: same pressure, economy under pressure minus normal": "B: pressure minus normal economy",
         "Ours: win-probability pressure + context-adjusted, shrunk rating": "<b>Ours</b>"}
for r in cm.itertuples():
    cr.append([short.get(r.method, r.method), "Batters" if r.role == "bat" else "Bowlers", f"{r.reliability:.2f}",
               f"{r.next_seasons:+.2f}", f"{r.role_bias:.2f}"])
t5.append(table(cr, [58, 20, 34, 36, 30]))
t5.append(Spacer(1, 3))
cb = cm.set_index(["role", "method"])
t5.append(P("Role bias = how strongly a ranking simply follows the share of a player's pressure balls bowled or faced at the "
           "death; a fair pressure ranking should not just reward finishers or punish death bowlers. <b>Reading:</b> for "
           "batters our method is best on reliability and prediction, while simple death-over strike rate (A) is less "
           "role-biased. For bowlers, raw economy (A) is more stable mostly because "
           "it measures role: death overs are always expensive, so it ranks death bowlers low whatever their skill (bias "
           f"{cb.loc[('bowl', 'Common: death overs / high required rate + raw economy'), 'role_bias']:.2f}). The usual way to "
           "compare with a player's normal level (B) is pure noise for bowlers (reliability "
           f"{cb.loc[('bowl', 'Common: same pressure, economy under pressure minus normal'), 'reliability']:.2f}) and mostly "
           "rewards finishers for batters (bias "
           f"{cb.loc[('bat', 'Common: same pressure, strike rate under pressure minus normal'), 'role_bias']:.2f}). Ours is the "
           "only one of the three that answers 'compared with their usual level' while staying reliable and fair. With about "
           "50 players per test, prediction differences under about 0.15 are within noise.", "small"))
S.append(KeepTogether(t5))
# ---- Test 6: known-answer simulation
sim = pd.read_csv(f"{OUT}/simulation.csv")
sim = sim[~sim.scenario.str.startswith("As the data")]
t6 = [P("<b>Test 6: a known-answer test.</b> We simulated players whose true pressure skill we set ourselves. Every "
        "eligible player keeps his real deliveries (same matches, same pressure balls); we give him a true normal level and "
        "a true pressure lift, simulate each ball as truth plus noise drawn from the real per-ball variation, re-rate "
        "everyone and check which method finds the truth. 200 runs per scenario.", "p")]
sr = [["True pressure skill", "Role", "Raw pressure average", "Pressure minus normal", "<b>Ours</b>", "True top 10 found (raw / ours)", "80% range holds the truth"]]
for r in sim.itertuples():
    sr.append([{"No pressure skill": "None", "Half of normal skill": "Half of normal skill",
                "Equal to normal skill": "Equal to normal skill"}[r.scenario], "Batters" if r.role == "bat" else "Bowlers",
               f"{r.raw:.2f}", f"{r.minus:.2f}", f"<b>{r.ours:.2f}</b>", f"{r.top10_raw:.1f} / <b>{r.top10_ours:.1f}</b>",
               f"{r.coverage80*100:.0f}%"])
t6.append(table(sr, [34, 18, 26, 26, 16, 34, 24]))
t6.append(Spacer(1, 3))
t6.append(P("Values are rank correlations with the true pressure quality (1 = perfect). <b>Ours recovers the truth best in every "
            "scenario, for batters and bowlers</b>; 'pressure minus normal' is close to useless, as Test 5 found on the real "
            f"data. Our 80% ranges are cautious (they hold the truth {sim.coverage80.min()*100:.0f}-{sim.coverage80.max()*100:.0f}% of the time). Even a perfect method finds only "
            "about three of the true top 10, because pressure samples are small: this is why ranks 6-10 are a tier, not an "
            "exact order. The real data's own variation implies pressure-specific skill close to zero, matching Test 2.", "small"))
S.append(KeepTogether(t6))
# ---- Test 7: weights chosen on held-out seasons
hw = pd.read_csv(f"{OUT}/heldout_weights.csv").set_index("role")
t7 = [P("<b>Test 7: are our weights any good?</b> The score's weights (45% pressure quality, 20% consistency, 20% Lift, "
        "15% win impact) were set by hand to match the brief. We let the data choose instead: every weighting on a 5% grid "
        "(1,771 options) was built on 2022-24 and scored on how well it ranks the same players in 2025-26. Picking the "
        "best of 1,771 options on about 50 players flatters the winner, so the fair test chooses the weights on a random "
        "half of the players and scores them on the other half, 1,000 times.", "p")]
wr = [["Role", "Data's best weights (in sample)", "Cross-validated: data-chosen weights", "Cross-validated: <b>our weights</b>", "Ours as good or better", "Top 10 kept"]]
for role, lab in (("bat", "Batters"), ("bowl", "Bowlers")):
    r = hw.loc[role]
    wr.append([lab, r.best_weights, f"{r.cv_chosen:.2f}", f"<b>{r.cv_ours:.2f}</b>", f"{r.cv_ours_wins*100:.0f}% of splits",
               f"{int(r.top10_overlap)} of 10"])
t7.append(table(wr, [18, 34, 36, 34, 28, 22]))
t7.append(Spacer(1, 3))
t7.append(P(f"<b>On new players our fixed weights predict at least as well as data-chosen ones</b> ({hw.loc['bat', 'cv_ours']:.2f} vs "
            f"{hw.loc['bat', 'cv_chosen']:.2f} for batters, a tie within noise; {hw.loc['bowl', 'cv_ours']:.2f} vs {hw.loc['bowl', 'cv_chosen']:.2f} "
            f"for bowlers, better in {hw.loc['bowl', 'cv_ours_wins']*100:.0f}% of splits): tuned weights only look better on the players they were tuned on. For bowlers the data's own best "
            f"weighting ({hw.loc['bowl', 'best_weights']}) is close to ours. For batters it puts everything on win impact, "
            "which ignores the brief's 'compared with their usual level'; applying it would keep "
            f"{int(hw.loc['bat', 'top10_overlap'])} of our 10 batters. We keep the brief-driven weights.", "small"))
S.append(KeepTogether(t7))
# ---- Test 8: the ground and opponent adjustment
t8 = [P("<b>Test 8: does adjusting for the ground and the opponent help?</b> We ran the whole pipeline (all "
        f"{N_SPECS} specifications, both time windows) twice: with the adjustment (our method) and without it. Both were "
        "built on 2022-24 and scored on how well they rank the same players' pressure performance in 2025-26, against "
        "three targets: future pressure quality measured without the adjustment, with it, and future win impact.", "p")]
c8 = [["Built on 2022-24", "Role", "Future pressure quality (unadjusted)", "Future pressure quality (adjusted)", "Future win impact"]]
for r in ctxc.itertuples():
    fin = "final" in r.method
    lab = "<b>With ground and opponent (ours)</b>" if fin else "Without"
    f = (lambda x: f"<b>{x:+.3f}</b>") if fin else (lambda x: f"{x:+.3f}")
    c8.append([lab, "Batters" if r.role == "bat" else "Bowlers", f(r.future_q_unadjusted), f(r.future_q_adjusted), f(r.future_wpa)])
t8.append(table(c8, [50, 18, 38, 38, 34]))
t8.append(Spacer(1, 3))
_w8 = ctxc.pivot(index="role", columns="method")
_better = sum((ctxc[ctxc.method.str.contains("final")].set_index("role")[c] > ctxc[~ctxc.method.str.contains("final")].set_index("role")[c]).sum()
              for c in ("future_q_unadjusted", "future_q_adjusted", "future_wpa"))
t8.append(P(f"Values are rank correlations (1 = perfect). <b>The adjusted ratings predict the future better in {_better} of the 6 "
            "comparisons</b> (the other is a tie), including against the unadjusted target, which the adjustment does not touch. "
            "The gains are small (about 50 players per test), but they all point the same way, and split-half "
            f"reliability rises for bowlers (from {REL_OLD['bowl']:.2f} to {rel_pq_w:.2f}; batters {REL_OLD['bat']:.2f} to "
            f"{rel_pq_b:.2f}; Test 9 checks this without leakage). So we adopted it. <b>What it changed:</b> " + _moves_txt + ".", "small"))
S.append(KeepTogether(t8))
# ---- Test 9: leak-free reliability; Test 10: permutation test for Lift
LF = pd.read_csv(f"{OUT}/leakfree_reliability.csv").set_index(["role", "version"]).reliability
PM = pd.read_csv(f"{OUT}/permutation_lift.csv").set_index("role")
_v = ["No ground/opponent adjustment", "Adjustment fitted on all matches", "Adjustment refitted on each half (leak-free)"]
t9 = [P("<b>Test 9: is the reliability gain real, or leakage?</b> In Test 1 the ground and opponent effects were fitted on all "
        "matches, so each half has 'seen' the other. Here they are refitted on each random half alone (20 splits).", "p")]
r9 = [["Pressure Quality, split-half reliability", "Batters", "Bowlers"]]
for v in _v:
    lab = "<b>Refitted on each half (leak-free)</b>" if "leak-free" in v else v.replace("No ground", "No ground")
    f = (lambda x: f"<b>{x:.2f}</b>") if "leak-free" in v else (lambda x: f"{x:.2f}")
    r9.append([lab, f(LF[("bat", v)]), f(LF[("bowl", v)])])
t9.append(table(r9, [90, 44, 44]))
t9.append(Spacer(1, 3))
t9.append(P(f"For bowlers the gain survives without leakage ({LF[('bowl', _v[0])]:.2f} to {LF[('bowl', _v[2])]:.2f}). For batters "
            f"the adjustment costs a little consistency ({LF[('bat', _v[0])]:.2f} to {LF[('bat', _v[2])]:.2f}) while predicting "
            "later seasons better (Test 8): some of what looked like batting skill was easy bowling. We keep the adjustment, "
            "because predicting the future is the job.", "small"))
S.append(KeepTogether(t9))
t10 = [P("<b>Test 10: is 'rising under pressure' a real skill?</b> If Lift (pressure level minus normal level) were pure "
         "chance, shuffling which of a player's own balls count as 'pressure' would produce the same spread of Lifts as the "
         f"real data. We shuffled each eligible player's labels {500} times, keeping his number of pressure balls.", "p")]
r10 = [["Role", "Players", "Real spread of Lift", "Spread if pure chance (95th pct)", "p-value"]]
for role, lab in (("bat", "Batters"), ("bowl", "Bowlers")):
    r = PM.loc[role]
    r10.append([lab, str(int(r.players)), f"{r.observed_sd:.1f}", f"{r.null_mean_sd:.1f} ({r.null_p95_sd:.1f})", f"{r.p_value:.2f}"])
t10.append(table(r10, [24, 20, 40, 54, 40]))
t10.append(Spacer(1, 3))
t10.append(P("Honest reading: with 100-500 pressure balls per player, differences in Lift cannot be told apart from chance "
             f"(p = {PM.loc['bat', 'p_value']:.2f} batters, {PM.loc['bowl', 'p_value']:.2f} bowlers), as Test 6 also found. So the "
             "score is led by <b>level under pressure</b> (45%), which is repeatable (Test 1); Lift stays at 20% because the "
             "brief asks for the comparison with a player's usual level.", "small"))
S.append(KeepTogether(t10))
# ---- the questions a sceptical judge will ask, answered from the data
_E = bowl[bowl.eligible]
_ps = _E.groupby("pace_spin").pq.mean()
_n_spin = int((bowl.loc[cons["bowl"].index[:10]].pace_spin == "Spin").sum())
_tvx = tv.set_index(["role", "estimator"]).r_future_pressure_quality
_bb = pd.read_pickle(f"{OUT}/balls.pkl")
_mt = pd.read_pickle(f"{OUT}/matches.pkl")
_tn = pd.concat([_mt.set_index("home_team_id").home_team, _mt.set_index("away_team_id").away_team])
_tn = _tn[~_tn.index.duplicated()]
_ad = _bb[(_bb.bowler_id == 5379) & (_bb.PI >= 1.5)].batting_team_id.map(_tn)
_full = {"Afghanistan", "Australia", "Bangladesh", "England", "India", "New Zealand", "Pakistan", "South Africa",
         "Sri Lanka", "West Indies"}
_ad_full = _ad.isin(_full).mean()
_C = pd.read_pickle(f"{OUT}/context_bowl_9999.pkl")
_rb = pd.read_pickle(f"{OUT}/resid_bowl.pkl")
_mu_idx = _rb[(_rb.pid == 6450) & _rb.P].index
_mu_uae = int((_rb.loc[_mu_idx, "match_id"].map(_mt.set_index("match_id").venue_country) == "United Arab Emirates").sum())
_ctx_mu = {"v": _C.loc[_mu_idx, "v_r"].mean() * 100, "o": _C.loc[_mu_idx, "o_r"].mean() * 100}
sq = [P("Questions a sceptic will ask", "h2")]
sq += bullets([
    f"<b>Home bias? Two RR batters are in the top 4.</b> The same rules rate every player; team and availability play no "
    f"part in any rank. The same rules put RR's Sandeep Sharma #{crank['bowl'][2411]} of {int(bowl.eligible.sum())} bowlers "
    f"and Ravi Bishnoi #{crank['bowl'][7503]}.",
    f"<b>Why {_n_spin} spinners in the bowling top 10?</b> Across the whole pool, spinners beat expectation under pressure "
    f"far more than pacers (average Pressure Quality {_ps['Spin']:+.1f} vs {_ps['Pace']:+.1f} runs per 100 balls). It is "
    "not a role artefact: the ranking is only weakly tied to death-over share (Test 5).",
    "<b>Did anyone get in by playing weak teams or on slow grounds?</b> We checked by judging every ball against its "
    "ground and its exact opponent: three picks dropped out (Test 8). Mujeeb's figures were helped "
    f"mostly by low-scoring grounds (his pressure balls came at grounds worth {-_ctx_mu['v']:.1f} fewer runs per 100 balls "
    f"than average; {_mu_uae} of his {len(_mu_idx)} came in the UAE), not by weak batting; Santner rose because he bowled "
    "at above-average batters.",
    f"<b>Where are Klaasen and Buttler?</b> Klaasen is clearly worse than his own normal level under pressure (Lift "
    f"{bat.lift[4260]:+.1f}, #{crank['bat'][4260]}); Buttler is #{crank['bat'][813]}, scoring only a little above an average "
    "batter in the same spots (Section 10).",
    f"<b>Is pressure skill even real?</b> Partly, and we say so. For bowlers, the pressure rating predicts later seasons' "
    f"pressure performance better than normal form alone ({_tvx[('bowl', 'Pressure Quality (PRI core)')]:.2f} vs "
    f"{_tvx[('bowl', 'Normal-situation quality only')]:.2f}). For batters it barely does "
    f"({_tvx[('bat', 'Pressure Quality (PRI core)')]:.2f} vs {_tvx[('bat', 'Normal-situation quality only')]:.2f}): a batter "
    "who is good under pressure is mostly a good batter. That is why the score leans on level under pressure, not on "
    "Lift alone.",
], small=True)
S.append(KeepTogether(sq))
S.append(P("Where the model is less certain", "h2"))
S += bullets([
    "<b>Pressure skill is only partly persistent.</b> Our best metric has a reliability of about 0.5 and Lift alone is not "
    "distinguishable from chance (Test 10). Treat ranks 6-10 as a tier; the bootstrap intervals overlap.",
    "<b>Near the cut-off.</b> Sooryavanshi (119 pressure balls, 15 of them from A-team matches weighted at 0.5) is the "
    "biggest single risk in the lists: much of his score is his normal-situation level. "
    + and_list(list(pd.concat([cons["bat"].head(10), cons["bowl"].head(10)])[lambda d: d.top10_share < 0.6].name))
    + " are top 10 in fewer than 60% of specifications. Bowlers 9 to 11 (Pathirana, Hasaranga, Ferguson) are a "
    "statistical dead heat.",
    "<b>Model and data gaps.</b> The win-probability model that defines pressure ignores team strength, venue and toss "
    "(first-innings AUC 0.69). Grounds are known only by an ID and rarely-used ones stay near average by design. No "
    "fielding data or T20 World Cups; 2027 auction prices are unknown.",
])

# ------------------------------------------------------------------ 8. RR lens
S.append(PageBreak())
S.append(P("8  RAJASTHAN ROYALS AUCTION LENS", "kick"))
S.append(P("Where RR loses close games, and who fixes it", "h1"))
S.append(fig("f8_rr_profile", 178))
S.append(P("Same PRI machinery applied at team level, IPL 2025-26. Close game = the tensest third of matches (peak "
           "Pressure Index 8 or more).", "small"))
S.append(P("Diagnosis from the data", "h2"))
_tpb = pd.read_csv(f"{OUT}/team_profile_bat.csv").set_index("team").loc["Rajasthan Royals"]
_tpw = pd.read_csv(f"{OUT}/team_profile_bowl.csv").set_index("team").loc["Rajasthan Royals"]
_ord = lambda n: f"{n}{'th' if 10 <= n % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')}"
S += bullets([
    f"<b>Close games are the leak.</b> In the tensest third of games RR won {int(cg_rr.close_wins)} of {int(cg_rr.close_games)}, "
    f"the lowest win rate of the 10 teams ({cg_rr.win_pct:.0f}%); RCB won {int(cg_top.close_wins)} of {int(cg_top.close_games)} (small samples). In 2026 RR finished 4th "
    "on 16 points while RCB, SRH and GT tied on 18 for the top two places, which bring a second chance at the final. "
    "In 2025 RR were 9th. One more win a season is the difference that matters.",
    f"<b>Pressure batting at the death: {_tpb.Death:+.0f} runs per 100 balls vs expectation.</b> RR's top order is strong under "
    f"pressure (Sooryavanshi #{crank['bat'][50284]}, Jaiswal #{crank['bat'][6819]}), but the finishing core does not lift: "
    f"Hetmyer ranks {_ord(crank['bat'][3297])} (lift {bat.lift[3297]:+.1f}; released on 17 Nov) and Jurel {_ord(crank['bat'][7260])} "
    f"(lift {bat.lift[7260]:+.1f}).",
    f"<b>Pressure bowling ranks {_ord(int(_tpw['rank']))} of 10, and three frontline bowlers dip.</b> Sandeep Sharma (lift "
    f"{bowl.lift[2411]:+.1f}, rank {crank['bowl'][2411]} of {int(bowl.eligible.sum())}), Sam Curran ({bowl.lift[4409]:+.1f}, rank "
    f"{crank['bowl'][4409]}) and Ravi Bishnoi ({bowl.lift[7503]:+.1f}, rank {crank['bowl'][7503]}) all perform clearly worse under "
    f"pressure than in normal play. Archer is about neutral (lift {bowl.lift[3298]:+.1f}, rank {crank['bowl'][3298]}). Tushar "
    f"Deshpande ({bowl.lift[6806]:+.1f}, rank {crank['bowl'][6806]}) was RR's best pressure bowler.",
    "<b>What changed on 17 Nov 2026 (official).</b> RR released Hetmyer and Deshpande, traded Curran to LSG, and brought in "
    f"Mohammed Shami and Manimaran Siddharth from LSG. Our data supports letting Curran go; it flags Shami (lift "
    f"{bowl.lift[1566]:+.1f}, rank {crank['bowl'][1566]}) as another bowler who dips under pressure, so his best use is the "
    "powerplay rather than the tense death overs. RR go into the auction with Rs 27.05 Cr, 6 slots and 3 overseas places.",
])
S.append(P("What each pick is worth to RR, in wins", "h2"))
S.append(P("For every pick we replay RR's IPL 2026 season. We take the pressure balls RR gave to players whose Pressure "
           "Quality is below league average, matched by role (pace for pace, spin for spin, top order or middle order "
           "for batters), and ask what the pick would have added on those exact balls. The gain in runs is converted "
           "to wins using the win-probability value of a run at each ball's pressure level, which the data puts at "
           f"about 1.1% of a win per run at moderate pressure and 4.3% at the most extreme.", "p"))
S.append(P("wins added = SUM over replaced balls (PQ<sub>pick</sub> - PQ<sub>incumbent</sub>) / 100 x "
           "WinProb-per-run(Pressure Index band)", "formula"))
S.append(fig("f16_wins_added", 132))
mid_bal = int(imp[imp.slot == "middle / finish"].slot_balls.iloc[0])
_bw = imp[imp.slot.isin(["pace", "spin"])].groupby("slot").wins.max()
pace_bal = int(imp[imp.slot == "pace"].slot_balls.iloc[0])
spin_bal = int(imp[imp.slot == "spin"].slot_balls.iloc[0])
S.append(P(f"Below-par pressure balls in 2026: {mid_bal} in the middle order, {pace_bal} for pace and {spin_bal} for spin, but "
           "almost none in the top order. That gives the auction its shape. <b>A top-order pick (Salt, Abhishek) adds "
           "almost nothing to RR</b>, because Jaiswal and Sooryavanshi already win those balls. <b>Bowling is where the wins "
           f"are:</b> the best pace and spin picks add {_bw.min():.1f}-{_bw.max():.1f} wins each. The three slots are independent, so the gains "
           f"add up: {', '.join(best_trio.name)} together are worth about {best_trio.wins.round(2).sum():.2f} wins a season. Bars "
           "show an 80% range from the uncertainty in each player's rating. The chart covers our top 10s; the auction plan "
           "below applies the same replay to the players who are actually in the 2027 auction.", "small"))
S.append(P("2027 auction plan: the best buys RR can actually make", "h2"))
S.append(P(f"Built on the official retention lists ({AS_OF}). RR have <b>Rs {RR_PURSE} Cr, {RR_SLOTS} slots and {RR_OVERSEAS_SLOTS} "
           "overseas places</b>. Every player below is in the 16 Dec auction pool. Wins added = the same 2026 replay as the chart "
           "above; a second player for the same gap adds little, because the gains come from the same balls.", "small"))


_mu_e = (tw.econ_p[6450], tw.xecon_p[6450])


def arow(name, note):
    r = AUC[AUC.name == name].iloc[0]
    role = "bat" if r.role == "bat" else "bowl"
    lo, hi = max(0, r.wins_lo), r.wins_hi
    return [f"<b>{name}</b> ({role} #{int(r['rank'])})", "Indian place" if r.nation == "India" else "Overseas place",
            f"<b>+{r.wins:.2f}</b> ({lo:.2f}-{hi:.2f})", note, LAST_FEE.get(name, "-")]


plan = [["", "Player", "Uses", "Wins added", "Why", "Last IPL fee"]]
first = [arow(n, w) for n, w in (
    ("Tushar Deshpande", f"Best pace buy, and Indian, so no overseas place: RR's best pressure bowler in 2026 (lift "
     f"{bowl.lift[6806]:+.1f}). Released by RR on 17 Nov; worth buying back at auction prices."),
    ("Mujeeb Ur Rahman", f"Best spin buy for RR: economy {_mu_e[0]:.2f} vs {_mu_e[1]:.2f} expected. Takes Bishnoi's tense "
     f"overs. Outside the overall top 10 (#{crank['bowl'][6450]}) once grounds are allowed for, but RR's spin gap is big."),
    ("Daryl Mitchell", f"Best middle-order buy and #{crank['bat'][4106]} overall: out {int(tb.outs_p[4106])} times vs "
     f"{tb.exp_outs_p[4106]:.1f} expected; fills the gap Hetmyer leaves."))]
alts = [arow(n, w) for n, w in (
    ("Lockie Ferguson", f"Overseas pace option (#{crank['bowl'][4692]}, level with #9-#10); released by PBKS."),
    ("Wanindu Hasaranga", f"Top 10 overall (#{crank['bowl'][4900]}); spin back-up to Mujeeb; released by LSG."),
    ("Matheesha Pathirana", "Top 10 overall, but his gain for RR is lower than Deshpande's, and his last fee was two-thirds of RR's purse."),
    ("Mark Adair", f"Death-overs pace (#{crank['bowl'][5379]}); in no IPL squad, so likely cheap."))]
for i, r in enumerate(first):
    plan.append(["<b>1. Bid first</b>" if i == 0 else ""] + r)
for i, r in enumerate(alts):
    plan.append(["<b>2. Backups</b>" if i == 0 else ""] + r)
S.append(table(plan, [17, 34, 15, 21, 68, 23]))
S.append(Spacer(1, 3))
S.append(P(f"<b>Plan 1 adds about +{free_trio.wins.round(2).sum():.2f} wins a season</b> ({free_trio.wins.round(2).sum() / best_trio.wins.round(2).sum() * 100:.0f}% "
           f"of the best possible trio, whose members were all retained), using {n_os} of RR's {RR_OVERSEAS_SLOTS} overseas places "
           "(Deshpande is Indian), which leaves one for a back-up. Mitchell and Mujeeb went unsold at the 2026 auction, so the "
           "market has passed on them. "
           f"Keep: Sooryavanshi (#{crank['bat'][50284]}) and Jaiswal (#{crank['bat'][6819]}). Use carefully: Sandeep Sharma, Ravi "
           "Bishnoi and Shami in lower-leverage overs. Watch list: M Shahrukh Khan, an uncapped finisher released by GT, whose "
           f"small sample would rank about #{int(gems_all[gems_all.pid == 3782].would_rank.iloc[0])} (Section 10).", "small"))
S.append(P(f"Not available: Harry Brook (#{crank['bat'][6280]}) is banned from the IPL until the 2028 auction. Most of the top 10s "
           "were retained by their teams (see below), so only a trade could bring them to RR.", "small"))

# ---- can RR actually get them?
route_head = [P("Can RR actually get them? The route to each pick", "h2"),
              P("The rankings answer the brief: who performs best under pressure. Under IPL rules a player under contract with "
                f"another team is not in the auction unless his team releases him. This uses the official retention lists of {AS_OF} "
                "(franchise announcements, e.g. rajasthanroyals.com, and the released lists reported by national media on 17 Nov). 'Unsold in 2026' = went unsold at the "
                "IPL 2026 auction. A player in no 2027 squad goes into the auction if he registers.", "small")]


def route_rows(top, role_lbl):
    rows = [["#", role_lbl, "Route to RR"]]
    for i, (pid, r) in enumerate(top.iterrows(), 1):
        lab, why = route(r["name"], r.ipl_2026_team)
        t = team27(r["name"], r.ipl_2026_team)
        rb = released_by(r["name"], r.ipl_2026_team)
        short = {"Under contract": f"Retained · {team(t)}" + (" (traded in)" if r["name"] in TRADES else ""),
                 "Already at RR": "Already at RR",
                 "Auction": "Auction · " + ("unsold in 2026" if r["name"] in UNSOLD_2026 else
                                            f"released by {team(rb)}" if rb else "if he registers"),
                 "Not available": "Not available"}[lab]
        rows.append([str(i), f"<b>{r['name']}</b>", short])
    return table(rows, [7, 40, 42])


rt = Table([[route_rows(top_bat, "Batter"), route_rows(top_bowl, "Bowler")]], colWidths=[89 * mm, 89 * mm])
rt.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 2)]))
S.append(KeepTogether(route_head + [rt]))
S.append(Spacer(1, 4))
n_auc = sum(route(r["name"], r.ipl_2026_team)[0] == "Auction" for T in (top_bat, top_bowl) for _, r in T.iterrows())
short = {k: ", ".join(f"{r['name']} (#{int(r['rank'])})" for _, r in AUC[AUC.role == k].sort_values("rank").iterrows() if r["rank"] <= 16)
         for k in ("bat", "bowl")}
S.append(P(f"<b>Auction-ready shortlist</b> (players in the 16 Dec auction pool with an overall rank of 16 or better): batters {short['bat']}; "
           f"bowlers {short['bowl']}. "
           f"{n_auc} of our 20 picks are in the auction; {sum(route(r['name'], r.ipl_2026_team)[0] == 'Already at RR' for T in (top_bat, top_bowl) for _, r in T.iterrows())} "
           "are already at RR; the rest were retained by their teams.", "small"))

# ------------------------------------------------------------------ 9. player cards
NATION = {**bat.nation.to_dict(), **bowl.nation.to_dict()}


def card(c):
    is_bat = c.role == "bat"
    lab = route(c["name"], c.team26)[0]
    t = team27(c["name"], c.team26)
    rb = released_by(c["name"], c.team26)
    avail = ("RR: core" if lab == "Already at RR" else f"Released by {team(rb)}: in the auction" if rb else
             "In the auction" if lab == "Auction" else f"Retained by {team(t)} for 2027")
    overseas = NATION.get(c.pid, "") not in ("India",)
    head = Table([[Paragraph(f"<font color='#E4087C'>#{c['rank']}{'†' if c.tied else ''}</font>  {c['name']}",
                             ParagraphStyle("ch", fontName="Helvetica-Bold", fontSize=9.5, leading=11, textColor=colors.white)),
                   Paragraph(f"{avail}{'  ·  overseas' if overseas else ''}",
                             ParagraphStyle("ca", fontName="Helvetica", fontSize=6.6, leading=8, textColor=colors.HexColor("#c9d3ea"),
                                            alignment=2))]], colWidths=[44 * mm, 41 * mm])
    head.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), NAVY), ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                              ("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                              ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]))
    if is_bat:
        key = (f"Pressure SR <b>{c.sr:.0f}</b> vs {c.xsr:.0f} expected  ·  out {int(c.outs)} times vs {c.xouts:.1f} expected")
    else:
        key = (f"Pressure economy <b>{c.econ:.2f}</b> vs {c.xecon:.2f} expected  ·  {int(c.outs)} wickets vs {c.xouts:.1f}")
    fmt = lambda x: "n/a" if pd.isna(x) else f"#{int(x)}"
    ev = []
    if pd.isna(c.ipl_rank):
        ev.append("rated mainly on T20I evidence" if c.ipl_share < 0.5 else "under 100 pressure balls in either competition alone")
    elif pd.isna(c.t20i_rank) and c.ipl_share >= 0.5:
        ev.append("rated mainly on IPL evidence")
    ss = ParagraphStyle("cs", fontName="Helvetica", fontSize=6.9, leading=8.6, textColor=INK)
    if c.slot == "top order":
        fit = (f"RR's top order already wins its pressure balls, so marginal value to RR is low "
               f"(+{c.wins:.2f} wins). " + ("Retain." if t == "Rajasthan Royals" else "Insurance, not a priority."))
    else:
        fit = (f"Takes the {c.slot} pressure balls of {c.replaces}: <b>+{c.wins:.2f} wins a season</b> "
               f"(80% range {max(c.wins_lo, 0):.2f}-{c.wins_hi:.2f}).")
    lines = [
        f"<font color='#52514e'>{c['style'].replace('Chinaman', 'wrist spin')}  ·  {c.n_p} pressure balls, {c.p_matches} matches  ·  "
        f"{c.death*100:.0f}% at the death</font>",
        key,
        f"Beat expectation in <b>{c.n_succ} of {c.p_matches}</b> pressure matches  ·  lift {c.lift:+.1f}  ·  "
        f"top 10 in {c.specs_top10*100:.0f}% of specs",
        f"IPL-only rank {fmt(c.ipl_rank)}  ·  T20I-only rank {fmt(c.t20i_rank)}" + (f"  ·  {ev[0]}" if ev else ""),
        f"<b>Biggest moment:</b> {c.moment} (<b>+{c.moment_swing:.0f}%</b> win prob.)"
        + (" (A-team match; his case rests on sustained output, not one ball)" if "Rising Stars" in c.moment or "Emerging" in c.moment else ""),
        f"<b>RR fit:</b> {fit}",
    ]
    body = Table([[Paragraph(l, ss)] for l in lines], colWidths=[85 * mm])
    body.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 4), ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                              ("TOPPADDING", (0, 0), (-1, -1), 1.2), ("BOTTOMPADDING", (0, 0), (-1, -1), 1.2),
                              ("BACKGROUND", (0, 0), (-1, -1), TINT)]))
    outer = Table([[head], [body]], colWidths=[85 * mm])
    outer.setStyle(TableStyle([("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                               ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 0)]))
    return outer


for role, title in (("bat", "Batters"), ("bowl", "Bowlers")):
    S.append(PageBreak())
    S.append(P("9  PLAYER CARDS" if role == "bat" else "9  PLAYER CARDS (CONTINUED)", "kick"))
    S.append(P(f"{title}: the case for each pick on one card", "h1"))
    cc = cards[cards.role == role].sort_values("rank")
    rows_ = [r for _, r in cc.iterrows()]
    grid = [[card(rows_[i]), card(rows_[i + 1])] for i in range(0, len(rows_), 2)]
    g = Table(grid, colWidths=[89 * mm, 89 * mm])
    g.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0),
                           ("RIGHTPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 5)]))
    S.append(g)
    S.append(Spacer(1, 2))
    S.append(P("Biggest moment = the single pressure ball with the largest win-probability swing in the player's favour. "
               "Lift = runs above own normal level per 100 pressure balls. Overseas status matters for RR's XI (four "
               "overseas players at most).", "small"))

# ------------------------------------------------------------------ 10. beyond the top 10
gems = pd.read_csv(f"{OUT}/extra_gems.csv")
gems = gems[gems.matches >= 5].sort_values(["role", "would_rank"]).head(6)
dips = pd.read_csv(f"{OUT}/extra_dippers.csv")
fam = pd.read_csv(f"{OUT}/extra_famous.csv")
TOP_IDS = set(top_bat.index) | set(top_bowl.index)


def team_label(name, t):
    t = t if isinstance(t, str) else "-"
    rb = released_by(name, t)
    if rb:
        return f"Auction (released by {team(rb)})"
    t27 = team27(name, t)
    if t27 is None:
        return "Auction"
    return team(t27) + (" (traded)" if name in TRADES else "")


def rec(r):
    if r.role == "bat":
        return f"{r.rate:.0f} vs {r.xrate:.0f} runs / 100 balls"
    return f"{r.rate:.2f} vs {r.xrate:.2f} runs / over"


S.append(PageBreak())
S.append(P("10  BEYOND THE TOP 10", "kick"))
S.append(P("Hidden gems, expensive reputations, and famous absences", "h1"))
S.append(P("The ranking answers 'who is most reliable under pressure'. An auction also needs to know who is about to "
           "become reliable and cheap, and whose reputation costs more than his pressure record is worth."))
S.append(P("Hidden gems: a watch list for the auction", "h2"))
S.append(P("These active players in the auction pool are below our eligibility floor (fewer than 100 pressure balls or 10 pressure matches), "
           "so they are not in the submitted top 10. Their ratings are already pulled strongly toward their normal level, "
           "so the 'would rank' column is a conservative estimate.", "small"))
gr = [["Player", "Role", "IPL 2027", "Under pressure (vs average)", "Out / wickets (vs avg)", "Pressure balls / matches", "Would rank"]]
for r in gems.itertuples():
    gr.append([f"<b>{r.name}</b>" + (" (uncapped)" if r.uncapped else ""), r.style, team_label(r.name, r.team), rec(r),
               f"{r.outs} ({r.xouts:.1f})", f"{r.n_p} / {r.matches}", f"~#{r.would_rank}"])
S.append(table(gr, [36, 24, 20, 36, 22, 22, 18]))
S.append(Spacer(1, 3))
_sk = gems_all[gems_all.pid == 3782].iloc[0]
S.append(P("<b>Why it matters for RR:</b> every gem here is in the 2027 auction pool. M Shahrukh Khan is an uncapped Indian "
           f"finisher released by GT: out {_sk.outs} times against {_sk.xouts:.1f} expected, in the middle-order slot where RR lose wins, and he "
           "needs no overseas place. Uncapped players have a much lower base price than established stars. Like Season 1's "
           "Vignesh Puthur, these are worth tracking now; the evidence will firm up with one more season.", "small"))

S.append(P("Don't pay for a pressure reputation", "h2"))
S.append(P("Strong players in normal conditions whose output clearly falls under pressure (Lift of -5 or worse, with at least 200 pressure balls of evidence). A "
           "franchise paying for their reputation in tense moments would be overpaying. Abhishek Sharma is the one top-10 "
           "player with a dip: he ranks because his normal level is the highest in the pool.", "small"))
_ar = dips[dips.pid == 6464].iloc[0]
dd = pd.concat([dips, fam[fam.reason.str.startswith("clearly worse")]]).drop_duplicates("name")
dd = dd[~dd.pid.isin(TOP_IDS) & (dd.team != "Rajasthan Royals") & (dd.n_p >= 200)].sort_values("lift")
dr_ = [["Player", "IPL 2027", "Under pressure (vs average)", "vs his own normal level", "Delivered in", "Our rank"]]
for r in dd.itertuples():
    dr_.append([f"<b>{r.name}</b>", team_label(r.name, r.team), rec(r), f"{r.lift:+.1f} runs / 100 balls",
                f"{r.succ*100:.0f}% of {r.matches} games", f"{int(r.crank)} of {int(r.n_pool)}"])
S.append(table(dr_, [36, 26, 40, 30, 26, 20]))
S.append(Spacer(1, 3))
S.append(P("A player here can still beat the average player (Klaasen does); the point is that he is clearly worse than "
           f"his own normal level. Arshdeep Singh has the largest pressure sample in the data ({int(_ar.n_p)} balls): he is a "
           f"little better than average under pressure ({_ar.rate:.2f} vs {_ar.xrate:.2f} expected) but far below his normal "
           f"level (Lift {_ar.lift:+.1f}), and delivers in only {_ar.succ*100:.0f}% of tense games.", "small"))

S.append(PageBreak())
S.append(P("Why isn't he in our top 10?", "h2"))
S.append(P("The first question any reader asks. The answer for each well-known name, from the data:", "small"))
fr = [["Player", "Our rank", "Under pressure (vs average)", "The reason"]]
ff = fam[~fam.name.isin(dd.name)].sort_values(["role", "crank"]).groupby("role").head(7)
for r in ff.itertuples():
    fr.append([f"<b>{r.name}</b>", f"{int(r.crank)} of {int(r.n_pool)}", rec(r), r.reason[0].upper() + r.reason[1:]])
S.append(table(fr, [36, 20, 42, 80]))

# ---- young and uncapped (confirmed ages and cap status only)
yg = pd.read_csv(f"{OUT}/extra_young.csv")
_su = yg[yg.name == "Suyash Sharma"].iloc[0]
yb = []
yb.append(P("Young and uncapped: who already handles pressure?", "h2"))
yb.append(P("The contest terms (Round 1, clause 5) ask entrants to identify the youngest uncapped player. <b>Our answer: Ayush "
            "Mhatre (19, CSK), the youngest uncapped Indian in the data with at least 40 pressure balls</b> (only 3 tense "
            "games, so an early signal). The table lists the uncapped "
            "Indian players aged 25 or under (confirmed ages and cap status, 17 Nov 2026) with at least 40 pressure balls. The "
            "samples are small, so read them as early signals, not rankings. The youngest player in our top 10, Vaibhav "
            "Sooryavanshi (15), is already capped and already at RR.", "small"))
yr = [["Player", "Age", "Role", "IPL 2027", "Under pressure (vs average)", "Out / wickets (vs avg)", "Tense games"]]
for r in yg.itertuples():
    yr.append([f"<b>{r.name}</b>", str(r.age), r.style, team_label(r.name, r.team), rec(r), f"{r.outs} ({r.xouts:.1f})", str(r.matches)])
yb.append(table(yr, [34, 10, 30, 18, 38, 26, 18]))
yb.append(Spacer(1, 3))
yb.append(P(f"<b>Reading:</b> Suyash Sharma (23, leg-spinner) gives away about {_su.xrate - _su.rate:.1f} runs an over fewer than expected under "
            "pressure; Abdul Samad (25) and Abishek Porel (24) score clearly faster than an average batter in the same spots. "
            "None has enough evidence for the top 10 yet.", "small"))
S.append(KeepTogether(yb))

# ------------------------------------------------------------------ appendices
S.append(PageBreak())
S.append(P("APPENDIX", "kick"))
S.append(P("A. Win-probability calibration", "h2"))
S.append(fig("f9_calibration", 60))
S.append(P(f"B. Reproducibility: code and run steps at <link href='{CODE_URL}' color='#E4087C'><u>{CODE_URL.replace('https://', '')}</u></link>", "h2"))
S.append(P("Verified: a fresh copy of the public code, run only with the README steps, rebuilt the full ranking with every "
           "score identical (largest difference 0.000).", "small"))
S.append(table([["Script", "What it does"],
                ["stage1_models.py", "State engine, WP models (CV-validated), expected-runs model, attribution of WPA and run value, Leverage and Pressure Index"],
                ["stage2_ratings.py", "Expectation models, component shrinkage, PRI, eligibility, split-half reliability, bootstrap. Optional window and parameter overrides for validation and sensitivity runs"],
                ["ensemble_specs.py, run_ens.sh, consensus.py", "73-specification ensemble and consensus ranking (also re-run on the 2022-24 window)"],
                ["validate.py, closers.py", "Out-of-time test (2022-24 to 2025-26); extreme-pressure chase closers"],
                ["extras.py, trades.py", "Hidden gems, players who dip under pressure, famous absences, young uncapped; confirmed trades, availability, caps and ages"],
                ["compare.py, simulate.py, heldout_weights.py, checks.py", "Head-to-head (Test 5), known-answer simulation (Test 6), held-out weights (Test 7), pressure-decile and per-component checks"],
                ["tier_check.py, rr_impact.py, cards.py", "IPL-only and T20I-only re-ratings; wins added for RR; player-card data"],
                ["ctx_compare.py, factor_swing.py, robust_tests.py", "Ground and opponent adjustment vs none (Test 8); rank swing per choice (Test 4); leak-free reliability and Lift permutation test (Tests 9-10)"],
                ["stage3_tables.py, stage4_figures.py, stage4b_figures.py, stage5_report.py", "Team profiles, figures, this report"]],
               [52, 126]))
S.append(Spacer(1, 3))
S.append(P("Key parameters: pressure threshold PI >= 1.5; knockout multiplier 1.25; recency half-life 2.5 years; baseline "
           "prior K = 500 pressure balls; consistency prior 12 matches; eligibility >= 100 pressure balls and >= 10 "
           "pressure matches, active 2025+; ground and opponent adjustment on (CONTEXT_ADJ = True). Models: scikit-learn "
           "HistGradientBoosting with fixed random seeds. Python 3, pandas, scikit-learn, matplotlib, reportlab.", "small"))
S.append(P("C. Next 12 and excluded players (transparency)", "h2"))


def ext_rows(role):
    E = cons[role].iloc[10:22]
    rows = [["#", "Player", "Score", "Specs top-10"]]
    for pid, r in E.iterrows():
        rows.append([f"{int(r.consensus_rank)}{'†' if r.tied else ''}", r["name"], f"{r.consensus_PRI:+.2f}", f"{r.top10_share*100:.0f}%"])
    return table(rows, [8, 46, 14, 18])


ext = Table([[P("<b>Batters 11-22</b>", "p"), P("<b>Bowlers 11-22</b>", "p")], [ext_rows("bat"), ext_rows("bowl")]],
            colWidths=[89 * mm, 89 * mm])
ext.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
S.append(ext)
S.append(Spacer(1, 4))
# consensus rank each excluded player would hold if Pakistan nationals were included (same 73 specifications)
exc_b = bowl[bowl.sample_ok & ~bowl.eligible].index.intersection(pak.index)
exc_t = bat[bat.sample_ok & ~bat.eligible].index.intersection(pak_bat.index)
eb = pak.loc[exc_b].sort_values("consensus_rank").head(3)
et = pak_bat.loc[exc_t].sort_values("consensus_rank").head(3)
S.append(P("Excluded as unavailable at the IPL auction (Pakistan nationals), with the consensus rank they would hold if "
           "included: bowlers " + ", ".join(f"{r['name']} (#{int(r.consensus_rank)})" for _, r in eb.iterrows())
           + "; batters " + ", ".join(f"{r['name']} (#{int(r.consensus_rank)})" for _, r in et.iterrows()) + ".", "small"))

doc.build(S)
print("wrote", PDF)
