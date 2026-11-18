"""Closers: in chases that reached extreme pressure (peak PI >= 3), who faced pressure balls and who hit the
winning runs. Usage: python -I closers.py <out_dir>"""
import sys
import pandas as pd

OUT = sys.argv[1]
b = pd.read_pickle(f"{OUT}/balls.pkl")
c = b[b.innings == 2]
hot = c.groupby("match_id").PI.max().loc[lambda s: s >= 3].index
c = c[c.match_id.isin(hot)]
won = c.groupby("match_id").tail(1).loc[lambda d: d.bat_won == 1]

featured = c[c.PI >= 1.5].groupby("striker_id").match_id.unique()
res = pd.DataFrame({
    "hot_chases": featured.apply(len),
    "hot_chases_won": featured.apply(lambda ms: int(pd.Index(ms).isin(won.match_id).sum())),
    "hit_winning_runs": won.groupby("striker_id").size(),
}).fillna(0).astype(int)
res["name"] = b.drop_duplicates("striker_id").set_index("striker_id").striker_name
res.to_csv(f"{OUT}/closers.csv")
print(res.sort_values("hit_winning_runs", ascending=False).head(15))
