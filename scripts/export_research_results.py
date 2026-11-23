"""Generate plots and a scalar summary using persisted evaluation results."""
import argparse
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

def export(folder, out):
    out.mkdir(parents=True,exist_ok=True)
    table=pd.read_csv(folder/"comparison.csv")
    table.to_csv(out/"model_comparison.csv",index=False)
    raw=table.loc[table.calibration=="raw"].set_index("model")
    ax=raw[["macro_f1","average_precision"]].plot.barh(figsize=(8,4),color=["#146c72","#efac48"])
    ax.set(xlim=(0,1),xlabel="Score",title="Held-out classification by model")
    ax.legend(["Macro-F1","Average precision"])
    def finish(name):
        plt.tight_layout()
        plt.savefig(out/(name+".png"),dpi=160)
        plt.close()
    finish("model_comparison")
    bins=pd.read_csv(folder/"reliability.csv")
    fig,ax=plt.subplots(figsize=(6,4))
    ax.plot([0,1],[0,1],"--",color="gray",label="Ideal")
    for tag,group in bins[bins.model=="logistic"].groupby("calibration"):
        group=group[group["count"]>0]
        ax.plot(group.mean_probability,group.observed_rate,".-",label=tag)
    ax.set(xlabel="Mean predicted attack probability",ylabel="Observed attack fraction",title="Logistic regression reliability")
    ax.legend()
    finish("calibration")
    cov=pd.read_csv(folder/"coverage.csv")
    fig,ax=plt.subplots(figsize=(6,4))
    for name,group in cov[cov.calibration=="platt"].groupby("model"):
        ax.plot(group.coverage,group.risk,".-",label=name)
    ax.set(xlabel="Fraction automatically accepted",ylabel="Error fraction among accepted",title="Platt-scaled selective decisions")
    ax.legend(fontsize=8)
    finish("selective_risk")
    text=["# "+folder.name,"","Raw held-out scores.","","| Model | Macro-F1 | AP | FPR |","|---|---:|---:|---:|"]
    for name,row in raw.iterrows():
        text.append(f"| {name} | {row.macro_f1:.3f} | {row.average_precision:.3f} | {row.fpr:.3f} |")
    (out/"summary.md").write_text("\n".join(text)+"\n")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root",type=Path,default=Path.cwd())
    p.add_argument("--run")
    a=p.parse_args()
    base=a.root/"results/v02"
    folders=[base/a.run] if a.run else sorted(f.parent for f in base.glob("*/registry.json"))
    if not folders:
        raise SystemExit("No completed runs")
    for folder in folders:
        export(folder,a.root/"reports/generated"/folder.name)
