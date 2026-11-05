"""Explain reporting coverage as country-code presence, not application volume."""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"


def main():
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    series = []
    for filename in ["asylum-applications.csv", "asylum-decisions.csv"]:
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != lock["inputs"][filename]:
            raise ValueError(f"Pinned input changed: {filename}")
        frame = pd.read_csv(ROOT / filename)
        series.append(frame.groupby("Year")["Country of asylum (ISO)"].nunique())
    apps, decs = series
    year = min(int(apps.index.max()), int(decs.index.max()))
    with plt.rc_context({"font.family":"DejaVu Sans", "font.size":11, "text.color":"#20383b"}):
        fig, axes = plt.subplots(1,2,figsize=(12,5.2),sharey=True)
        fig.set_facecolor("#ffffff")
        fig.subplots_adjust(top=.58,bottom=.14,left=.06,right=.98,wspace=.12)
        fig.text(.06,.94,"Who is represented in the data?",fontsize=22,color="#20383b")
        fig.text(.06,.875,"Receiving countries with records, 2000-2025 | Each country code counted once per year",fontsize=10,color="#526767")
        for ax, values, label, colour in zip(axes,[apps,decs],["APPLICATION RECORDS","DECISION RECORDS"],["#256f68","#8574bd"]):
            latest = int(values.loc[year])
            change = latest-int(values.loc[year-1])
            direction = "fewer" if change<0 else "more" if change>0 else "unchanged"
            comparison = f"{abs(change)} {direction} than {year-1}" if change else f"Unchanged from {year-1}"
            ax.text(0,1.52,label,transform=ax.transAxes,fontsize=10,color=colour)
            ax.text(0,1.24,str(latest),transform=ax.transAxes,fontsize=38,color="#20383b")
            ax.text(.24,1.29,f"receiving countries\nin {year}",transform=ax.transAxes,fontsize=11,color="#526767",linespacing=1.5)
            ax.text(0,1.10,comparison,transform=ax.transAxes,fontsize=10,color="#526767")
            ax.fill_between(values.index,values.values,color=colour,alpha=.07)
            ax.plot(values.index,values.values,color=colour,linewidth=2.4)
            ax.scatter([year],[latest],s=55,color=colour,zorder=3,edgecolor="white",linewidth=1.5)
            ax.set(xlim=(1999.5,2026),ylim=(0,180),xticks=[2000,2010,2020,2025],yticks=[0,50,100,150])
            ax.spines[["top","right","left"]].set_visible(False)
            ax.spines["bottom"].set_color("#d6e1dc")
            ax.tick_params(length=0,pad=8,colors="#526767",labelsize=9)
            ax.grid(axis="y",color="#e3eae6",linewidth=.7)
            ax.set_axisbelow(True)
        fig.savefig(DEST/"assets/reporting-coverage.png",dpi=170,facecolor="white");plt.close(fig)
    (DEST/"_coverage-reading.qmd").write_text(
        f"In **{year}**, the saved application data includes **{apps.loc[year]} receiving-country codes**, "
        f"compared with **{apps.loc[year-1]}** in {year-1}. Decision data includes **{decs.loc[year]}**, "
        f"compared with **{decs.loc[year-1]}**. Each code is counted once per year in each file, "
        "regardless of application volume or whether the record uses persons or cases. "
        "A record with zero reported volume still counts as reporting presence. These panels show "
        "**how widely the data covers receiving countries**, not how many applications were received.\n",
        encoding="utf-8")
    print(f"Coverage counts verified: {apps.loc[year]} application and {decs.loc[year]} decision country codes in {year}.")


if __name__ == "__main__":
    main()
