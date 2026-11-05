"""Origin-specific outcomes and illustrative processing balances from pinned inputs."""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter, PercentFormatter
import numpy as np
import pandas as pd
import pycountry

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"
YEARS = np.arange(2000, 2026)
OUTCOMES = ["Recognized decisions", "Complementary protection", "Rejected decisions", "Otherwise closed"]
COLOURS = ["#00a98f", "#f4c542", "#ef6655", "#8574bd"]


def name(code):
    country = pycountry.countries.get(alpha_3=code)
    return country.name if country else code


def tidy(ax):
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.tick_params(length=0, pad=7, colors="#45605b")
    ax.grid(axis="x", color="#e4ebe7", linewidth=.6)
    ax.set_axisbelow(True)


def outcome_chart(ax, values, title):
    bottom = np.zeros(len(values))
    for key, label, colour in zip(OUTCOMES, ["Refugee status", "Other protection", "Rejected", "Closed"], COLOURS):
        share = values[key].div(values["Total decisions"].where(values["Total decisions"].gt(0)))
        ax.barh(np.arange(len(values)), share, left=bottom, color=colour, label=label)
        bottom += share.fillna(0).to_numpy()
    for i, row in enumerate(values.itertuples(index=False)):
        if not np.isfinite(values["Total decisions"].iloc[i]) or values["Total decisions"].iloc[i] <= 0:
            ax.text(.02,i,"Unavailable",va="center",fontsize=9)
    ax.set(yticks=np.arange(len(values)), yticklabels=values.index, xlim=(0,1), title=title)
    ax.xaxis.set_major_formatter(PercentFormatter(1))
    ax.invert_yaxis(); tidy(ax)


def main():
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    for filename, digest in lock["inputs"].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Input changed: {filename}")
    apps = pd.read_csv(ROOT / "asylum-applications.csv")
    decs = pd.read_csv(ROOT / "asylum-decisions.csv")
    codes = apps.groupby("Country of asylum (ISO)").applied.sum().nlargest(20).index
    assets = DEST / "assets/detail"
    assets.mkdir(parents=True, exist_ok=True)
    origin_parts, gap_parts, exports, gap_exports = [], [], [], []
    with plt.rc_context({"font.family":"DejaVu Sans", "font.size":10, "text.color":"#20383b"}):
        for code in codes:
            a = apps.loc[apps["Country of asylum (ISO)"].eq(code)]
            d = decs.loc[decs["Country of asylum (ISO)"].eq(code)]
            origins = a.groupby("Country of origin (ISO)").applied.sum().nlargest(10).index
            sums = d.groupby("Country of origin (ISO)")[OUTCOMES+["Total decisions"]].sum(min_count=1).reindex(origins)
            yearly = d.groupby(["Country of origin (ISO)","Year"])[["Recognized decisions","Total decisions"]].sum(min_count=1)
            rates = yearly["Recognized decisions"].div(yearly["Total decisions"].where(yearly["Total decisions"].gt(0))).unstack().reindex(index=origins,columns=YEARS)
            fig, axes = plt.subplots(1,2,figsize=(15,6),gridspec_kw={"width_ratios":[1,1.7]},layout="constrained")
            outcome_chart(axes[0],sums,"Overall outcomes · 2000–2025")
            cmap = plt.get_cmap("viridis").copy(); cmap.set_bad("#ededeb")
            image = axes[1].imshow(np.ma.masked_invalid(rates),aspect="auto",vmin=0,vmax=1,cmap=cmap)
            axes[1].set(yticks=np.arange(len(origins)),yticklabels=origins,
                        xticks=[0,5,10,15,20,25],xticklabels=[2000,2005,2010,2015,2020,2025],title="Refugee-status share by origin and year")
            fig.colorbar(image,ax=axes[1],format=PercentFormatter(1),shrink=.8,label="Share of all recorded decisions")
            axes[0].legend(loc="upper left",bbox_to_anchor=(0,-.12),ncol=2,frameon=False)
            fig.suptitle(f"{name(code)} · Origin and time both matter",fontsize=18)
            fig.savefig(assets/f"{code.lower()}-origins.png",dpi=130,facecolor="white");plt.close(fig)
            latest_origins = a.loc[a.Year.eq(2025)].groupby("Country of origin (ISO)").applied.sum().nlargest(10)
            latest = d.loc[d.Year.eq(2025)].groupby("Country of origin (ISO)")[OUTCOMES+["Total decisions"]].sum(min_count=1).reindex(latest_origins.index)
            fig, axes = plt.subplots(1,2,figsize=(13,5.5),layout="constrained")
            bars = axes[0].barh(np.arange(len(latest_origins)),latest_origins,color="#256f68")
            axes[0].bar_label(bars,labels=[f"{v:,}" for v in latest_origins],padding=4,fontsize=8)
            axes[0].set(yticks=np.arange(len(latest_origins)),yticklabels=latest_origins.index,title="Reported applications · 2025")
            axes[0].invert_yaxis();axes[0].margins(x=.3);tidy(axes[0])
            axes[0].xaxis.set_major_formatter(FuncFormatter(lambda v,_:f"{v/1000:g}k"))
            outcome_chart(axes[1],latest,"Recorded decision outcomes · 2025")
            axes[1].legend(loc="upper left",bbox_to_anchor=(0,-.12),ncol=2,frameon=False)
            fig.suptitle(f"{name(code)} · Applications and outcomes by origin",fontsize=17)
            fig.savefig(assets/f"{code.lower()}-2025.png",dpi=130,facecolor="white");plt.close(fig)
            for period, table in [("2000–2025",sums),("2025",latest)]:
                for origin, row in table.iterrows():
                    exports.append({"destination":code,"origin":origin,"period":period,**row.to_dict()})
            for origin, values in rates.iterrows():
                for year, rate in values.items():
                    exports.append({"destination":code,"origin":origin,"period":str(year),"recognised_share":rate})
            origin_parts.append(f'''::: {{.origin-card}}
### {name(code)} ({code})

![{name(code)}: overall outcomes for its Top 10 application origins and annual refugee-status shares.](assets/detail/{code.lower()}-origins.png){{loading="lazy"}}

![{name(code)}: 2025 application volumes alongside decision outcomes for its Top 10 application origins.](assets/detail/{code.lower()}-2025.png){{loading="lazy"}}
:::
''')
            av = a.groupby("Year").applied.sum(min_count=1).reindex(YEARS)
            dv = d.groupby("Year")["Total decisions"].sum(min_count=1).reindex(YEARS)
            gap = av-dv
            # Resume neither cumulative series after an unknown annual flow.
            cumulative = gap.cumsum(skipna=False)
            floor, balance = [], 0.0
            for value in gap:
                balance = max(0,balance+value) if np.isfinite(balance) and np.isfinite(value) else np.nan
                floor.append(balance)
            fig, axes = plt.subplots(3,1,figsize=(12,9),layout="constrained",sharex=True)
            colours=np.where(gap>=0,"#ef6655","#00a98f")
            axes[0].bar(YEARS,gap,color=colours,width=.8)
            axes[0].set_title("Annual shortfall: applications minus decisions",loc="left")
            previous=cumulative-gap
            axes[1].bar(YEARS,gap,bottom=previous,color=colours,width=.8)
            axes[1].step(YEARS,cumulative,where="mid",color="#526767",linewidth=.8)
            axes[1].set_title("Waterfall: cumulative recorded flow difference (zero opening)",loc="left")
            axes[2].fill_between(YEARS,floor,color="#eee9f4")
            axes[2].plot(YEARS,floor,color="#8574bd",linewidth=2.5)
            axes[2].set_title("Illustrative zero-opening balance, floored at zero",loc="left")
            for ax in axes:
                tidy(ax);ax.grid(axis="y",color="#e4ebe7",linewidth=.6);ax.axhline(0,color="#526767",linewidth=.7)
                ax.yaxis.set_major_formatter(FuncFormatter(lambda v,_:f"{v/1e6:g}m" if abs(v)>=1e6 else f"{v/1000:g}k"))
            axes[-1].set(xticks=[2000,2005,2010,2015,2020,2025],xlabel="Year")
            fig.suptitle(f"{name(code)} · Processing pressure",fontsize=18)
            fig.savefig(assets/f"{code.lower()}-pressure.png",dpi=130,facecolor="white");plt.close(fig)
            for i, year in enumerate(YEARS):
                gap_exports.append({"country":code,"year":year,"applications":av.loc[year],"decisions":dv.loc[year],"annual_gap":gap.loc[year],"cumulative_flow_difference":cumulative.loc[year],"illustrative_zero_opening_balance":floor[i]})
            gap_parts.append(f'''::: {{.origin-card}}
### {name(code)} ({code})

![{name(code)}: annual shortfalls, cumulative flow waterfall, and illustrative zero-opening balance.](assets/detail/{code.lower()}-pressure.png){{loading="lazy"}}
:::
''')
            print(f"Prepared outcome and pressure details: {code}",flush=True)
    pd.DataFrame(exports).to_csv(DEST/"data/origin-outcome-detail.csv",index=False)
    pd.DataFrame(gap_exports).to_csv(DEST/"data/processing-gap-detail.csv",index=False)
    intro='''## Different origins, different outcomes, different years {#origin-outcomes}

These profiles replace the original destination/origin grant-rate and 2025 applications-and-grant-rates figures. Each receiving country shows its **Top 10 origins by reported application volume**, selected separately for the full period and for 2025. Receiving countries use the same period-wide Top 20 selection as elsewhere.

The stacked bars show all four outcomes. The heatmaps compare the **recognised refugee-status share of all recorded decisions**, including closures in the denominator, on a common 0–100% colour scale. Grey means unavailable, not zero. These are outcome shares, not cohort success rates or the substantive recognition rates above. Changes across origin, destination, and year do not by themselves establish discrimination or policy effects: procedure, case mix, reporting units, and coverage also vary.

The 2025 panels place application volumes beside decision outcomes on separate axes, avoiding the original overlapping scales. Decisions need not concern the applications recorded in that year. Period rates use summed decision counts, not averages of annual percentages. Persons and cases are combined without conversion. Fixed 2000–2025 inputs; the dropdown above uses its own dated snapshot.

[Download underlying counts and annual recognised shares (CSV)](data/origin-outcome-detail.csv). Origin labels are ISO codes; UNK denotes unknown origin.

:::: {.origin-gallery}
'''
    (DEST/"_origin-outcome-detail.qmd").write_text(intro+"\n".join(origin_parts)+"\n::::\n",encoding="utf-8")
    intro='''## Annual shortfalls and country waterfalls {#processing-gaps}

**Coral:** applications exceed decisions. **Teal:** decisions exceed applications. The first panel shows each annual difference; the waterfall adds these differences from a zero opening balance in 2000. Missing annual reports remain gaps and stop cumulative calculations.

### About the old “minimum backlog” figures

The final panel is explicitly **illustrative**, not an observed backlog or a defensible lower bound on it. It follows balance[t] = max(0, balance[t−1] + applications[t] − decisions[t]), starting at zero. It assumes compatible flow units, scope, and timing and no other entries, exits, transfers, or reporting adjustments. The combined persons/cases records do not establish those assumptions. Compare actual unresolved caseloads using the separately observed UNHCR stocks on the front page.

### What if the gap persists?

If reported applications continue to exceed comparable recorded decisions, processing pressure will persist unless inflows fall or output rises. This is a conditional scenario, not a prediction that every country will worsen. The record includes years and countries where decisions exceeded applications. Resource needs, future inflows, and policy changes are not modelled here.

[Download all annual flows and illustrative balances (CSV)](data/processing-gap-detail.csv). Fixed 2000–2025 inputs; persons and cases combined without conversion. Each panel uses its own scale to reveal its pattern.

:::: {.origin-gallery}
'''
    (DEST/"_processing-gap-detail.qmd").write_text(intro+"\n".join(gap_parts)+"\n::::\n",encoding="utf-8")


if __name__ == "__main__":
    main()
