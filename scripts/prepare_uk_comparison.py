"""Reproducible Home Office summary-table comparison, without rerunning the notebook."""
import hashlib
import json
import os
import re
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"
DATA = DEST / "data/uk"
FIELDS = {"People claiming asylum":"ho_claimants_people","People receiving initial decisions":"ho_initial_decisions_people",
          "Grants of protection or other leave":"ho_grants_people","Refusals":"ho_refusals_people",
          "Withdrawals":"ho_withdrawals_people","Grant rate at initial decision":"ho_published_grant_rate_main_applicants",
          "People awaiting an initial decision":"ho_pending_initial_people","Cases awaiting an initial decision":"ho_pending_initial_cases"}


def tidy(ax):
    ax.spines[["top","right","left"]].set_visible(False)
    ax.tick_params(length=0,pad=8,colors="#526767")
    ax.grid(axis="y",color="#e0e8e3",linewidth=.7);ax.set_axisbelow(True)
    ax.set_xlim(2009.5,2025.5);ax.set_xticks([2010,2015,2020,2025])


def main():
    meta=json.loads((DATA/"source.json").read_text(encoding="utf-8"))
    path=DATA/"asylum-summary-jun-2026.ods"
    if hashlib.sha256(path.read_bytes()).hexdigest()!=meta["sha256"]:
        raise ValueError("Home Office source hash differs from the saved download.")
    raw=pd.read_excel(path,sheet_name="Asy_00a",header=None,engine="odf")
    header=next(i for i,row in raw.iterrows() if str(row.iloc[0]).startswith("Date / As at"))
    source_rows={str(row.iloc[0]):row for _,row in raw.iterrows()}
    records=[]
    for col,label in enumerate(raw.iloc[header]):
        label=str(label)
        if re.fullmatch(r"20\d{2}(?:\.0)?",label) and 2010<=int(float(label))<=2025:
            records.append({"year":int(float(label)),**{target:float(source_rows[name].iloc[col]) for name,target in FIELDS.items()}})
    official=pd.DataFrame(records).set_index("year").sort_index()
    if official.index.tolist()!=list(range(2010,2026)):
        raise ValueError("Expected complete calendar-year coverage from 2010 through 2025.")
    if not np.array_equal(official.ho_grants_people+official.ho_refusals_people,official.ho_initial_decisions_people):
        raise ValueError("Official grants and refusals must reconcile to initial decisions.")
    lock=json.loads((DEST/"_inputs.json").read_text(encoding="utf-8"))
    frames={}
    for filename in ["asylum-applications.csv","asylum-decisions.csv"]:
        if hashlib.sha256((ROOT/filename).read_bytes()).hexdigest()!=lock["inputs"][filename]:
            raise ValueError(f"UNHCR snapshot changed: {filename}")
        frame=pd.read_csv(ROOT/filename)
        frames[filename]=frame.loc[frame["Country of asylum (ISO)"].eq("GBR") & frame["Cases / Persons"].eq("P") & frame["Stage of procedure"].eq("FI")]
    applications=frames["asylum-applications.csv"].groupby("Year").applied.sum(min_count=1).rename("unhcr_first_instance_applications_persons")
    decs=frames["asylum-decisions.csv"].groupby("Year")[["Recognized decisions","Complementary protection","Rejected decisions","Otherwise closed","Total decisions"]].sum(min_count=1)
    substantive=decs[["Recognized decisions","Complementary protection","Rejected decisions"]].sum(axis=1,min_count=3)
    derived=pd.DataFrame({"unhcr_fi_substantive_decisions_persons":substantive,
                          "unhcr_fi_protection_share_persons":(decs["Recognized decisions"]+decs["Complementary protection"])/substantive.where(substantive>0),
                          "unhcr_fi_otherwise_closed_persons":decs["Otherwise closed"]})
    result=official.join(applications).join(derived)
    if not result.ho_published_grant_rate_main_applicants.between(0,1).all():
        raise ValueError("Published official rates must be fractions between zero and one.")
    result.to_csv(DATA/"annual-comparison.csv",index_label="year")
    latest_col=next(i for i,label in enumerate(raw.iloc[header]) if str(label)=="Year ending June 2026")
    latest={target:float(source_rows[name].iloc[latest_col]) for name,target in FIELDS.items()}
    comparison={"source":meta,"table":"Asy_00a","release":"year ending June 2026","published":"2026-08-27","latest_year_ending_june_2026":latest,"calendar_years":result.reset_index().replace({np.nan:None}).to_dict(orient="records")}
    (DATA/"comparison.json").write_text(json.dumps(comparison,indent=2,allow_nan=False)+"\n",encoding="utf-8")
    assets=DEST/"assets/uk";assets.mkdir(parents=True,exist_ok=True)
    with plt.rc_context({"font.family":"DejaVu Sans","font.size":11,"text.color":"#20383b"}):
        fig,axes=plt.subplots(2,1,figsize=(12,8),layout="constrained")
        for ax,ho,un,title in [(axes[0],"ho_claimants_people","unhcr_first_instance_applications_persons","Asylum inflows: people, calendar years"),
                               (axes[1],"ho_initial_decisions_people","unhcr_fi_substantive_decisions_persons","Substantive initial decisions: people, calendar years")]:
            ax.plot(result.index,result[ho],color="#256f68",linewidth=2.6,marker="o",markersize=3,label="Home Office · main applicants + dependants")
            ax.plot(result.index,result[un],color="#8574bd",linewidth=2.6,linestyle="--",label="UNHCR · first-instance persons records")
            tidy(ax);ax.set_title(title,loc="left",fontsize=15,pad=15)
            ax.yaxis.set_major_formatter(FuncFormatter(lambda value,_:f"{value/1000:g}k"));ax.set_ylim(bottom=0)
            ax.legend(frameon=False,fontsize=9,loc="upper left")
        fig.suptitle("UK asylum: two sources, aligned calendar years",fontsize=19)
        fig.savefig(assets/"flows.png",dpi=150,facecolor="white");plt.close(fig)
        fig,ax=plt.subplots(figsize=(12,5.5),layout="constrained")
        ax.plot(result.index,result.ho_published_grant_rate_main_applicants,color="#256f68",linewidth=2.6,marker="o",markersize=3,label="Home Office published grant rate · main applicants")
        ax.plot(result.index,result.unhcr_fi_protection_share_persons,color="#8574bd",linewidth=2.6,linestyle="--",label="UNHCR protection share · first-instance persons")
        tidy(ax);ax.set_ylim(0,1);ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0))
        ax.set_title("Initial-decision grant measures: related, not identical",loc="left",fontsize=18,pad=40)
        ax.legend(loc="lower left",bbox_to_anchor=(0,1.01),frameon=False,fontsize=9)
        fig.savefig(assets/"rates.png",dpi=150,facecolor="white");plt.close(fig)
    year2025=result.loc[2025]
    text=f'''::: {{.snapshot}}
<div><span class="value">{int(year2025.ho_claimants_people):,}</span><span class="label">people claiming asylum<br>Calendar year 2025</span></div>
<div><span class="value">{year2025.ho_published_grant_rate_main_applicants:.0%}</span><span class="label">published initial grant rate<br>Main applicants · 2025</span></div>
<div><span class="value">{int(year2025.ho_pending_initial_people):,}</span><span class="label">people awaiting an initial decision<br>At end-2025</span></div>
:::

**Newer UK-only context:** in the year ending June 2026, the published main-applicant grant rate was **{latest['ho_published_grant_rate_main_applicants']:.0%}**, and **{int(latest['ho_pending_initial_people']):,} people** awaited an initial decision at the end of June. These rolling-year figures are not plotted as calendar 2026 or compared with UNHCR 2025.
'''
    (DEST/"_uk-headlines.qmd").write_text(text,encoding="utf-8")
    print("Parsed 16 official calendar years; grants/refusals reconcile; UK/UNHCR first-instance scopes kept explicit.")


if __name__=="__main__":
    main()
