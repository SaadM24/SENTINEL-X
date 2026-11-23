"""Render real held-out precision–recall and fusion workload curves from score tables."""
import argparse
import csv
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from sklearn.metrics import precision_recall_curve


def load(path):
    with path.open(encoding="utf-8",newline="") as f:
        return list(csv.DictReader(f))


def plot(sequence, fusion, out):
    primary=load(sequence/"scores.csv")
    paired=load(fusion/"scores.csv")
    fig, axes=plt.subplots(1,2,figsize=(10,4.3),layout="constrained")
    y=np.array([int(r["label"]) for r in primary])
    for col, name in [("unigram","Unigram"),("markov","Markov")]:
        precision, recall, _=precision_recall_curve(y,[float(r[col]) for r in primary])
        axes[0].plot(recall,precision,label=name,lw=1.6)
    axes[0].axhline(y.mean(),ls=":",color="#666",label="Prevalence")
    axes[0].set(title=f"Trace anomaly ranking · {len(y):,} test traces",xlabel="Recall",ylabel="Precision",
                xlim=(0,1),ylim=(0,1.02))
    y=np.array([int(r["label"]) for r in paired])
    for col, name in [("frequencies","Frequencies"),("frequencies_markov","Frequencies + Markov")]:
        p=np.array([float(r[col+"_calibrated"]) for r in paired])
        # Key includes a deterministic tie break; plotted operating points are descriptive.
        order=np.argsort(-np.maximum(p,1-p),kind="stable")
        errors=((p>=.5)!=y)[order]
        k=np.arange(1,len(y)+1)
        axes[1].plot(k/len(y),np.cumsum(errors)/k,label=name)
    axes[1].axvline(.80,ls=":",color="#666",label="20% review target")
    axes[1].set(title=f"Supervised fusion · {len(y):,} test traces",xlabel="Accepted fraction",
                ylabel="Error among accepted",xlim=(.5,1))
    for ax in axes:
        ax.spines[["top","right"]].set_visible(False)
        ax.grid(axis="y",alpha=.2)
        ax.legend(frameon=False,fontsize=9)
    out.parent.mkdir(parents=True,exist_ok=True)
    fig.savefig(out,dpi=165)
    plt.close(fig)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sequence",type=Path,default=Path("results/v03"))
    p.add_argument("--fusion",type=Path,default=Path("results/v03_fusion"))
    p.add_argument("--out",type=Path,default=Path("reports/sequence/sequence_fusion.png"))
    a=p.parse_args()
    plot(a.sequence,a.fusion,a.out)
