"""A ranked origin-volume chart with compact names and aligned exact totals."""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"


def main():
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    source = ROOT / "asylum-applications.csv"
    if hashlib.sha256(source.read_bytes()).hexdigest() != lock["inputs"][source.name]:
        raise ValueError("Origin-volume inputs differ from the pinned edition.")
    summary = pd.read_csv(DEST / "assets/origins/application-volumes.csv")
    raw = pd.read_csv(source).groupby("Country of origin (ISO)").applied.sum().nlargest(20)
    if summary.origin.tolist() != raw.index.tolist() or summary.applications.tolist() != raw.tolist():
        raise ValueError("The origin ranking or totals differ from source records.")
    short = {"VEN":"Venezuela", "SYR":"Syria", "COD":"DR Congo", "RUS":"Russia", "IRN":"Iran", "UNK":"Unknown origin"}
    labels = [f"{i:02d}   {short.get(row.origin,row['name'])}" for i,(_,row) in enumerate(summary.iterrows(),1)]
    maximum = summary.applications.max()
    with plt.rc_context({"font.family":"DejaVu Sans", "font.size":11, "text.color":"#20383b"}):
        fig, ax = plt.subplots(figsize=(11.8,9.8),layout="constrained")
        for i in range(20):
            if i%2==0:
                ax.axhspan(i-.48,i+.48,color="#f6f8f5",zorder=0)
        colours = ["#8574bd" if code=="UNK" else "#256f68" if i<3 else "#58a99c" for i,code in enumerate(summary.origin)]
        ax.barh(range(20),summary.applications,height=.54,color=colours,zorder=3)
        for i,count in enumerate(summary.applications):
            ax.text(maximum*1.20,i,f"{count:,}",ha="right",va="center",fontsize=11,color="#20383b")
        ax.set(yticks=range(20),yticklabels=labels,xlim=(0,maximum*1.23),ylim=(19.7,-.7),
               xticks=[0,500000,1000000,1500000,2000000,2500000],
               xlabel="Reported applications · 2000–2025")
        ax.xaxis.set_major_formatter(FuncFormatter(lambda value,_: "0" if value==0 else f"{value/1e6:.1f}m"))
        ax.set_title("Application volumes: Top 20 reported origins",loc="left",fontsize=19,pad=42)
        ax.text(0,1.025,"Ranked by period total · Persons and cases combined without conversion",transform=ax.transAxes,fontsize=10,color="#526767")
        ax.spines[["top","right","left"]].set_visible(False)
        ax.spines["bottom"].set_color("#d4dfd9")
        ax.tick_params(length=0,pad=10,colors="#526767")
        ax.grid(axis="x",color="#e1e8e3",linewidth=.6)
        ax.set_axisbelow(True)
        fig.savefig(DEST / "assets/origins/application-volumes.png",dpi=165,facecolor="white")
        plt.close(fig)
    print("Restyled all 20 origins; exact totals and ranking match the pinned application input.")


if __name__ == "__main__":
    main()
