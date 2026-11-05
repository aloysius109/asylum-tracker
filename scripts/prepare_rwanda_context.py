"""Rwanda's own UNHCR asylum activity, distinct from the former UK partnership."""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
import numpy as np
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/"quarto-preview"
OUTCOMES=["Recognized decisions","Complementary protection","Rejected decisions","Otherwise closed"]


def prepare_origins(frame):
    import pycountry
    from html import escape
    groups={}
    for key,subset in [("all",frame)]+[(str(year),part) for year,part in frame.groupby("Year")]:
        counts=subset.groupby(["Country of origin (ISO)","Country of origin"]).applied.sum(min_count=1).dropna()
        counts=counts[counts>0].sort_values(ascending=False,kind="stable")
        total=int(subset.applied.sum(min_count=1))
        rows=[]
        for (code,name),value in counts.items():
            country=pycountry.countries.get(alpha_3=code)
            flag=country.alpha_2.lower() if country else None
            if flag and not (DEST/f"assets/flags/{flag}.svg").exists():
                flag=None
            rows.append({"code":code,"name":name,"applications":int(value),"share":float(value/total) if total else None,"flag":flag})
        if sum(r["applications"] for r in rows)!=total:
            raise ValueError("Rwanda origin counts do not reconcile")
        groups[key]={"total":total,"rows":rows}
    (DEST/"data/uk/rwanda-origins.json").write_text(json.dumps(groups,allow_nan=False),encoding="utf-8")
    frame.groupby(["Year","Country of origin (ISO)","Country of origin"]).applied.sum(min_count=1).to_csv(DEST/"data/uk/rwanda-origins.csv")
    print("Rwanda latest application origins:", [(r["name"],r["applications"]) for r in groups["2025"]["rows"][:5]])


def main():
    lock=json.loads((DEST/"_inputs.json").read_text(encoding="utf-8"))
    frames={}
    for filename in ["asylum-applications.csv","asylum-decisions.csv"]:
        source=ROOT/filename
        if hashlib.sha256(source.read_bytes()).hexdigest()!=lock["inputs"][filename]:
            raise ValueError(f"Rwanda input changed: {filename}")
        frame=pd.read_csv(source)
        frames[filename]=frame.loc[frame["Country of asylum (ISO)"].eq("RWA")]
    years=np.arange(2000,2026)
    apps=frames["asylum-applications.csv"].groupby("Year").applied.sum(min_count=1).reindex(years)
    decs=frames["asylum-decisions.csv"].groupby("Year")[OUTCOMES+["Total decisions"]].sum(min_count=1).reindex(years)
    valid=decs[OUTCOMES].notna().all(axis=1)&decs[OUTCOMES].sum(axis=1).eq(decs["Total decisions"])&decs["Total decisions"].gt(0)
    result=decs.copy()
    result["applications"]=apps
    result["decisions_per_100_applications"]=decs["Total decisions"]/apps.where(apps>0)*100
    for column in OUTCOMES:
        result[column+" share"]=decs[column].div(decs["Total decisions"]).where(valid)
    folder=DEST/"assets/uk";folder.mkdir(exist_ok=True)
    with plt.rc_context({"font.family":"DejaVu Sans","font.size":11,"text.color":"#20383b"}):
        fig,(ax,detail)=plt.subplots(1,2,figsize=(13,5.8),gridspec_kw={"width_ratios":[3.5,1.25]})
        fig.subplots_adjust(left=.07,right=.97,bottom=.17,top=.73,wspace=.27)
        fig.text(.07,.94,"Rwanda's own asylum system",fontsize=23,fontweight="bold",color="#20383b")
        fig.text(.07,.86,"Reported applications and recorded decisions | 2000-2025",fontsize=12,color="#526767")
        ax.bar(years,apps,color="#087f75",alpha=.85,width=.72,label="Applications",zorder=3)
        ax.plot(years,decs["Total decisions"],color="#8060a9",linewidth=2.7,marker="o",markersize=3.5,label="Decisions",zorder=4)
        ax.legend(loc="lower left",bbox_to_anchor=(0,1.01),frameon=False,ncol=2)
        ax.set(xlim=(1999.2,2025.8),ylim=(0,max(apps.max(),decs["Total decisions"].max())*1.12),xticks=[2000,2005,2010,2015,2020,2025])
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value,_:f"{value:,.0f}"))
        latest_counts=[apps.loc[2025],decs.loc[2025,"Total decisions"]]
        detail.barh([1,0],latest_counts,color=["#087f75","#8060a9"],height=.36,zorder=3)
        for y,value,label in zip([1,0],latest_counts,["Applications","Decisions"]):
            detail.text(0,y+.27,label,fontsize=11,color="#526767")
            detail.text(value+max(latest_counts)*.04,y,f"{value:,.0f}",va="center",fontsize=15,fontweight="bold")
        detail.set(xlim=(0,max(latest_counts)*1.65),ylim=(-.5,1.8),xticks=[],yticks=[])
        detail.set_title("2025 at a glance",loc="left",fontsize=14,fontweight="bold",pad=20)
        detail.spines[:].set_visible(False)
        ax.spines[["top","right","left"]].set_visible(False)
        ax.spines["bottom"].set_color("#dce5df")
        ax.tick_params(length=0,pad=9,colors="#526767")
        ax.grid(axis="y",color="#e0e8e3",linewidth=.8);ax.set_axisbelow(True)
        fig.text(.07,.035,"UNHCR reported activity. Applications and decisions are different flows, not matched claims.",fontsize=10,color="#526767")
        fig.savefig(folder/"rwanda-flows.png",dpi=170,facecolor="white");plt.close(fig)
        fig,ax=plt.subplots(figsize=(12,5.5),layout="constrained")
        bottom=np.zeros(len(years))
        for key,label,colour in zip(OUTCOMES,["Refugee status","Other protection","Rejected","Otherwise closed"],["#00a98f","#f4c542","#ef6655","#8574bd"]):
            values=result[key+" share"]
            ax.bar(years,values,bottom=bottom,color=colour,width=.85,label=label)
            bottom+=values.fillna(0).to_numpy()
        ax.set_title("Rwanda: how recorded decision outcomes changed",loc="left",fontsize=18,pad=40)
        ax.legend(loc="lower left",bbox_to_anchor=(0,1.01),ncol=4,frameon=False,fontsize=10)
        ax.set(xlim=(1999.3,2025.7),ylim=(0,1),xticks=[2000,2005,2010,2015,2020,2025],ylabel="Share of all recorded decisions")
        ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
        ax.spines[["top","right","left"]].set_visible(False);ax.tick_params(length=0,pad=8,colors="#526767")
        ax.grid(axis="y",color="#e0e8e3",linewidth=.7);ax.set_axisbelow(True)
        fig.savefig(folder/"rwanda-outcomes.png",dpi=150,facecolor="white");plt.close(fig)
    (DEST/"data/uk").mkdir(exist_ok=True)
    result.to_csv(DEST/"data/uk/rwanda-annual.csv",index_label="year")
    prepare_origins(frames["asylum-applications.csv"])
    latest=result.loc[2025]
    (DEST/"_rwanda-headlines.qmd").write_text(f'''::: {{.snapshot}}
<div><span class="value">{int(latest.applications):,}</span><span class="label">reported applications in Rwanda<br>2025 · all procedures</span></div>
<div><span class="value">{int(latest['Total decisions']):,}</span><span class="label">recorded decisions in Rwanda<br>2025 · all outcomes</span></div>
<div><span class="value">{latest.decisions_per_100_applications:.0f}</span><span class="label">decisions per 100 applications<br>Rwanda · 2025 recorded flows</span></div>
:::
''',encoding="utf-8")
    print(f"Prepared Rwanda's own system: {int(latest.applications):,} applications and {int(latest['Total decisions']):,} decisions in 2025; annual outcomes reconciled.")


if __name__=="__main__":
    main()
