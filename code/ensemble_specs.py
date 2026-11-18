"""Generate the specification grid for model averaging. Usage: python -I ensemble_specs.py <out_dir>"""
import itertools, json, random, sys
OUT = sys.argv[1]
grid = dict(
    PRESSURE=[1.25, 1.5, 2.0],
    K_BASE=[200, 500, 1000],
    W=[{"pq": 0.45, "succ": 0.20, "lift": 0.20, "wpa": 0.15},
       {"pq": 0.35, "succ": 0.35, "lift": 0.15, "wpa": 0.15},
       {"pq": 0.30, "succ": 0.20, "lift": 0.35, "wpa": 0.15},
       {"pq": 0.25, "succ": 0.25, "lift": 0.25, "wpa": 0.25}],
    HALF_LIFE_YRS=[2.5, 1000],
    KO_MULT=[1.25, 1.0],
    OPP_WEIGHTING=[True, False],
)
keys = list(grid)
allspecs = [dict(zip(keys, v)) for v in itertools.product(*grid.values())]
random.Random(2027).shuffle(allspecs)
specs = allspecs[:72]
with open(f"{OUT}/ensemble_specs.jsonl", "w") as f:
    for i, s in enumerate(specs):
        f.write(f"_e{i:02d}\t{json.dumps(s)}\n")
print(len(allspecs), "in grid;", len(specs), "sampled")
