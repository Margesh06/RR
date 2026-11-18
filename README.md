# Pressure Reliability Index (PRI)

**SupeRR Selector Season 2 (Rajasthan Royals), Round 1.** Prepared by Margesh.

A data-driven system that measures how batters and bowlers perform in high-pressure match situations compared with
their usual level, and ranks the players who deliver most consistently when it matters.

- **Live dashboard:** https://rr-pressure-index-xi.vercel.app
- **Pressure** = the expected swing in win probability on the next ball (Pressure Index >= 1.5, about 18% of deliveries),
  from win-probability models fitted on IPL and T20I data, 2022-2026.
- **Rating** = context-adjusted pressure quality (vs an average player in the same situation), Lift (vs the player's own
  normal level), consistency across pressure matches and win impact, with empirical-Bayes shrinkage, averaged over 73
  model specifications.
- **Checks:** split-half reliability, bootstrap, out-of-time test (2022-24 -> 2025-26), IPL-only / T20I-only re-ratings,
  a head-to-head test against common approaches, a known-answer simulation and weights chosen on held-out seasons.
- **RR lens:** wins added for Rajasthan Royals and an auction board built on the official IPL 2027 retention lists.

## Data

The competition data pack is **not** included (it may not be shared). Put its CSV files in a folder, for example
`Data Pack/`, and set `DATA` to that path. Every output is rebuilt from those files.

## Code

| Script | What it does |
|---|---|
| `stage1_models.py` | Match-state engine, win-probability and expected-runs models, Leverage and Pressure Index |
| `stage2_ratings.py` | Expectation models, component shrinkage, PRI, eligibility, reliability, bootstrap |
| `ensemble_specs.py`, `run_ens.sh`, `run_ens24.sh`, `consensus.py` | 73-specification ensemble and consensus ranking; auction-pool ranking |
| `validate.py`, `closers.py`, `compare.py` | Out-of-time test, extreme-pressure chase closers, head-to-head with common approaches |
| `simulate.py`, `heldout_weights.py` | Known-answer simulation (players with a known true skill) and weights chosen on held-out seasons |
| `tier_check.py`, `rr_impact.py`, `cards.py`, `extras.py`, `trades.py` | IPL-only / T20I-only checks, wins added for RR, player cards, beyond-the-top-10 lists, 2027 availability |
| `stage3_tables.py`, `stage4_figures.py`, `stage4b_figures.py`, `stage5_report.py` | Team profiles, figures, the PDF report |
| `grid_specs.py`, `dashboard_data.py`, `dashboard_template.html` | 288-cell model lab and the interactive dashboard |

## Reproduce (about 10 minutes on 8 cores)
```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # tested on Python 3.14
export DATA="Data Pack"; D="$DATA"; mkdir -p out   # folder holding the competition CSVs
PY=".venv/bin/python -I"

# 1. models and base ratings
$PY code/stage1_models.py "$D" out                 # state engine, WP models, Pressure Index
$PY code/stage2_ratings.py "$D" out                # base-spec PRI + bootstrap + reliability
$PY code/stage2_ratings.py "$D" out 2024 _to2024   # 2022-24 window for the out-of-time test

# 2. 73-specification consensus (base + 72 random cells of the 288-cell grid)
$PY code/ensemble_specs.py out
cp code/run_ens*.sh code/stage2_ratings.py .       # runners expect to sit next to stage2 and out/
while IFS=$'\t' read -r t j; do printf '%s\0%s\0' "$t" "$j"; done < out/ensemble_specs.jsonl | OMP_NUM_THREADS=1 xargs -0 -n 2 -P 6 ./run_ens.sh
while IFS=$'\t' read -r t j; do printf '%s\0%s\0' "$t" "$j"; done < out/ensemble_specs.jsonl | OMP_NUM_THREADS=1 xargs -0 -n 2 -P 6 ./run_ens24.sh
$PY code/consensus.py out && $PY code/validate.py out && $PY code/closers.py out

# 3. transparency run: the same consensus with Pakistan nationals included
mkdir -p out_pk && for f in balls.pkl matches.pkl expect_bat_9999.pkl expect_bowl_9999.pkl ensemble_specs.jsonl; do ln -sf ../out/$f out_pk/$f; done
RR_OVERRIDES='{"EXCLUDE_NATIONS": []}' $PY code/stage2_ratings.py "$D" out_pk
while IFS=$'\t' read -r t j; do printf '%s\0%s\0' "$t" "$(echo "$j" | sed 's/}$/, "EXCLUDE_NATIONS": []}/')"; done < out/ensemble_specs.jsonl \
  | OMP_NUM_THREADS=1 xargs -0 -n 2 -P 6 sh -c 'RR_OVERRIDES="$1" .venv/bin/python -I code/stage2_ratings.py "$DATA" out_pk 9999 "$0" > /dev/null'
$PY code/consensus.py out_pk && cp out_pk/consensus_bat.csv out/consensus_bat_incl_pak.csv && cp out_pk/consensus_bowl.csv out/consensus_bowl_incl_pak.csv

# 4. IPL-only / T20I-only check, RR wins added, player cards
RR_OVERRIDES='{"TIER_KEEP": ["IPL"]}'  $PY code/stage2_ratings.py "$D" out 9999 _ipl
RR_OVERRIDES='{"TIER_KEEP": ["T20I"]}' $PY code/stage2_ratings.py "$D" out 9999 _t20i
$PY code/stage3_tables.py "$D" out && $PY code/detail.py
$PY code/tier_check.py out && $PY code/compare.py out && $PY code/simulate.py out && $PY code/heldout_weights.py out && $PY code/rr_impact.py out && $PY code/cards.py "$D" out && $PY code/extras.py out

# 5. figures and report
$PY code/stage4_figures.py out && $PY code/stage4b_figures.py out
$PY code/stage5_report.py out out/report.pdf MY_VIEW.md   # trades.py: official 2027 retention lists, trades, RR purse and slots

# 6. dashboard: all 288 grid cells, then inline the derived data into the template
mkdir -p out_grid && for f in balls.pkl matches.pkl expect_bat_9999.pkl expect_bowl_9999.pkl; do ln -sf ../out/$f out_grid/$f; done
$PY code/grid_specs.py out_grid
while IFS=$'\t' read -r t j; do printf '%s\0%s\0' "$t" "$j"; done < out_grid/grid_specs.jsonl \
  | OMP_NUM_THREADS=1 xargs -0 -n 2 -P 6 sh -c 'RR_OVERRIDES="$1" .venv/bin/python -I code/stage2_ratings.py "$DATA" out_grid 9999 "$0" > /dev/null'
$PY code/dashboard_data.py out out_grid out/data.json
python3 -c "t=open('code/dashboard_template.html').read(); open('out/index.html','w').write(t.replace('/*DATA*/null', open('out/data.json').read()))"
```
