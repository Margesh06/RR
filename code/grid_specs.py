"""Write the full 288-cell specification grid (for the dashboard's model lab). Usage: python -I grid_specs.py <out_dir>"""
import itertools, json, sys
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
with open(f"{OUT}/grid_specs.jsonl", "w") as f:
    for i, v in enumerate(itertools.product(*grid.values())):
        f.write(f"_g{i:03d}\t{json.dumps(dict(zip(grid, v)))}\n")
