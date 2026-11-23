import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"scripts"))
from run_nf_shift import FEATURES, main, sample

def native_file(path, start):
    records=[]
    for i in range(start,start+200):
        values={f:i*2+j for j,f in enumerate(FEATURES)}
        records.append({**values,"Label":i%2})
    pd.DataFrame(records).to_csv(path,index=False)

def test_excludes_conflicts_and_overlap(tmp_path):
    a,b=tmp_path/"a.csv",tmp_path/"b.csv"
    native_file(a,0)
    native_file(b,150)
    frame=pd.read_csv(a)
    row=frame.iloc[0].copy()
    row["Label"]=1
    pd.concat([frame,row.to_frame().T]).to_csv(a,index=False)
    _,counts,_=sample(a,1000,8)
    assert counts["contradictory_vectors"]==1
    out=tmp_path/"run"
    main(a,b,out)
    import json
    result=json.loads((out/"metrics.json").read_text())
    assert result["target_overlap_removed"]==50
    assert result["external"]["n"]==150
    with pytest.raises(FileExistsError):
        main(a,b,out)
    with pytest.raises(ValueError):
        main(a,a,tmp_path/"other")

def test_invalid_flow_values(tmp_path):
    path=tmp_path/"bad.csv"
    native_file(path,0)
    frame=pd.read_csv(path)
    frame.loc[4,"IN_PKTS"]=-1
    frame.to_csv(path,index=False)
    with pytest.raises(ValueError):
        sample(path,30,7)
