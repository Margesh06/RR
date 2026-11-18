"""Test 4: how much does each modelling choice move the ranks? For every factor of the ensemble, average each top-20
player's rank over the specifications at each setting of that factor; the swing is the gap between the best and worst
setting, averaged over the top 20 (consensus order).
Usage: python -I factor_swing.py <out_dir>"""
import json
import sys
import pandas as pd

OUT = sys.argv[1]
BASE = {"PRESSURE": 1.5, "K_BASE": 500, "W": {"pq": 0.45, "succ": 0.2, "lift": 0.2, "wpa": 0.15}, "HALF_LIFE_YRS": 2.5,
        "KO_MULT": 1.25, "OPP_WEIGHTING": True}
spec = {"base": BASE} | {t: json.loads(j) for t, j in (l.rstrip("\n").split("\t") for l in open(f"{OUT}/ensemble_specs.jsonl"))}
FACTORS = {"Pressure threshold": "PRESSURE", "Component weights": "W", "Recency weighting": "HALF_LIFE_YRS",
           "Baseline prior": "K_BASE", "Knockout multiplier": "KO_MULT", "Opposition weighting": "OPP_WEIGHTING"}
out = {}
for role in ("bat", "bowl"):
    M = pd.read_pickle(f"{OUT}/ensemble_ranks_{role}.pkl")
    top = pd.read_csv(f"{OUT}/consensus_{role}.csv", index_col=0).index[:20]
    for lab, key in FACTORS.items():
        setting = pd.Series({t: json.dumps(spec[t][key], sort_keys=True) for t in M.columns})
        by = M.loc[top].T.groupby(setting).mean().T
        out.setdefault(lab, {})[role] = (by.max(axis=1) - by.min(axis=1)).mean()
res = pd.DataFrame(out).T.round(1)
res.index.name = "factor"
res.to_csv(f"{OUT}/factor_swing.csv")
print(res)
