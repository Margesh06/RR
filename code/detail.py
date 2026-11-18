import pandas as pd, numpy as np
pd.set_option("display.width",300); pd.set_option("display.max_columns",40)
for role in ("bat","bowl"):
    R=pd.read_pickle(f"out/ratings_{role}.pkl")
    C=pd.read_csv(f"out/consensus_{role}.csv",index_col=0)
    E=R.loc[C.index[:15]].join(C[["consensus_PRI","consensus_rank","top10_share","median_rank","tied"]])
    if role=="bat":
        E["SR_p"]=E.runs_p/E.n_p*100; E["xSR_p"]=E.exp_runs_p/E.n_p*100; E["SR_np"]=E.runs_np/E.n_np*100
        E["avg_p"]=E.runs_p/E.outs_p.replace(0,np.nan)
        cols=["name","nation","ipl_2026_team","n_p","p_matches","runs_p","SR_p","xSR_p","outs_p","exp_outs_p","avg_p","SR_np","bndpct_p","dotpct_p","pq","q_base","lift","succ_raw","succ_s","wpa_s","wpa_total_p","PRI","consensus_PRI","consensus_rank","top10_share","median_rank","tied","top10_prob","rank_p10","rank_p90","bat_pos","hand","death_share_p","chase_share_p","ko_balls_p","ipl_share_p"]
    else:
        E["econ_p"]=E.runs_p/E.legal_p*6; E["xecon_p"]=E.exp_runs_p/E.legal_p*6; E["econ_np"]=E.runs_np/E.legal_np*6
        cols=["name","nation","ipl_2026_team","n_p","legal_p","p_matches","econ_p","xecon_p","outs_p","exp_outs_p","econ_np","dotpct_p","bndpct_p","pq","q_base","lift","succ_raw","succ_s","wpa_s","wpa_total_p","PRI","consensus_PRI","consensus_rank","top10_share","median_rank","tied","top10_prob","rank_p10","rank_p90","bowl_type","death_share_p","pp_share_p","chase_share_p","ko_balls_p","ipl_share_p"]
    print(E[cols].round(2).to_string()); E[cols].to_csv(f"out/top_{role}.csv")
    S=R[R.sample_ok].sort_values("PRI",ascending=False)
    print("incl excluded:", S[["name","nation","rank_incl_excluded"]].head(12).to_string())
