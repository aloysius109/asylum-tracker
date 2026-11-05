"""Build the local executive summary and processing assessment from pinned activity."""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "quarto-preview"


def n(value):
    return f"{value:,.0f}"


def display_ratio(value):
    return "Unavailable" if value is None else f"{value:.1f}" if 99 < value < 101 else f"{value:.0f}"


def ratio(frame, start, end):
    frame = frame.loc[frame.year.between(start, end)].dropna(subset=["applications", "decisions"])
    return (float(100 * frame.decisions.sum() / frame.applications.sum()) if frame.applications.sum() > 0 else None, len(frame))


def main():
    lock = json.loads((SITE / "_inputs.json").read_text(encoding="utf-8"))
    sources = []
    for filename in ["asylum-applications.csv", "asylum-decisions.csv"]:
        source = ROOT / filename
        if hashlib.sha256(source.read_bytes()).hexdigest() != lock["inputs"][filename]:
            raise ValueError(f"Changed summary source: {filename}")
        sources.append(pd.read_csv(source))
    apps, decs = sources
    frame = pd.read_csv(SITE / "data/processing-productivity.csv")
    # Check chart data against the source, not just its precomputed ratios.
    for column, source, field in [("applications", apps, "applied"), ("decisions", decs, "Total decisions")]:
        lookup = source.groupby(["Country of asylum (ISO)", "Year"])[field].sum(min_count=1)
        for row in frame.itertuples():
            actual = lookup.get((row.country, row.year), float("nan"))
            value = getattr(row, column)
            if not ((pd.isna(actual) and pd.isna(value)) or actual == value):
                raise ValueError(f"Summary/chart mismatch: {row.country}, {row.year}, {column}")
    rows = []
    for code, group in frame.groupby("country", sort=False):
        five, count = ratio(group, 2021, 2025)
        recent, recent_count = ratio(group, 2023, 2025)
        prior, prior_count = ratio(group, 2018, 2020)
        current = group.loc[group.year.eq(2025)].iloc[0]
        latest = float(current.decisions_per_100_applications) if pd.notna(current.decisions_per_100_applications) else None
        paired = group.loc[group.year.between(2021, 2025)].dropna(subset=["applications", "decisions"])
        deficits = int((paired.decisions < paired.applications).sum())
        if count < 5 or recent_count < 3:
            category = "Incomplete coverage"
        elif five >= 100 and recent >= 100 and latest is not None and latest >= 100 and deficits <= 2:
            category = "Stronger flow balance"
        elif abs(five-100) < 1 and abs(recent-100) < 1:
            category = "Close to balance"
        elif five < 100 and recent >= 100:
            category = "Recent catch-up"
        elif five < 100 and recent < 100 and deficits >= 4:
            category = "Repeated shortfalls"
        else:
            category = "Mixed annual pattern"
        rows.append({"country": code, "name": group['name'].iloc[0], "category": category,
                     "ratio_2021_2025": five, "paired_years": count, "shortfall_years": deficits,
                     "ratio_2023_2025": recent, "recent_paired_years": recent_count,
                     "ratio_2018_2020": prior, "prior_paired_years": prior_count,
                     "ratio_2025": latest, "recent_change": recent-prior if prior is not None and prior_count == 3 and recent_count == 3 else None})
    result = pd.DataFrame(rows)
    result.to_csv(SITE / "data/processing-assessment.csv", index=False)
    (SITE / "data/processing-assessment.json").write_text(json.dumps({"sources": lock["inputs"], "rows": rows}, allow_nan=False, indent=2), encoding="utf-8")
    def members(category):
        selected = [r for r in rows if r['category'] == category]
        return ", ".join(f"**{r['name']}** ({display_ratio(r['ratio_2021_2025'])})" for r in selected)
    stronger = members("Stronger flow balance")
    repeated = members("Repeated shortfalls")
    catchup = members("Recent catch-up")
    slipping = sorted([r for r in rows if r['recent_change'] is not None and r['recent_change'] <= -10 and r['ratio_2023_2025'] < 100 and r['paired_years'] == 5], key=lambda r:r['recent_change'])
    sliding = "; ".join(f"**{r['name']}**, {r['ratio_2018_2020']:.0f} → {r['ratio_2023_2025']:.0f}" for r in slipping)
    ordered = result.loc[result.paired_years.eq(5)].sort_values("ratio_2021_2025")
    palette = {"Stronger flow balance":"#087f75", "Recent catch-up":"#8060a9", "Repeated shortfalls":"#d46c51", "Mixed annual pattern":"#91a49e", "Close to balance":"#57737d"}
    with plt.rc_context({"font.family":"DejaVu Sans", "font.size":11, "text.color":"#20383b"}):
        fig, ax = plt.subplots(figsize=(12,9.3))
        fig.subplots_adjust(left=.23,right=.93,bottom=.21,top=.83)
        y = range(len(ordered))
        ax.barh(list(y), ordered.ratio_2021_2025, height=.58, color=[palette[c] for c in ordered.category], zorder=3)
        ax.axvline(100,color="#20383b",linewidth=1.1,linestyle=(0,(3,3)),zorder=4)
        for i, r in enumerate(ordered.itertuples()):
            ax.text(r.ratio_2021_2025+3,i,display_ratio(r.ratio_2021_2025),va="center",fontsize=11,fontweight="bold",bbox={"facecolor":"white","edgecolor":"none","pad":1})
        ax.set(yticks=list(y),yticklabels=ordered['name'],xlim=(0,max(ordered.ratio_2021_2025)*1.13),xlabel="Recorded decisions per 100 applications · period totals, 2021–2025")
        ax.grid(axis="x",color="#e5ebe6",linewidth=.7); ax.set_axisbelow(True)
        ax.tick_params(length=0,pad=9,colors="#526767");ax.spines[:].set_visible(False)
        fig.text(.04,.95,"Is recorded output keeping pace?",fontsize=24,fontweight="bold")
        fig.text(.04,.90,"Above 100: more decisions than applications. Closures are included.",fontsize=12,color="#526767")
        from matplotlib.patches import Patch
        fig.legend(handles=[Patch(color=c,label=k) for k,c in palette.items()],loc="lower center",bbox_to_anchor=(.5,.015),ncol=2,frameon=False,fontsize=10)
        (SITE / "assets/productivity").mkdir(exist_ok=True)
        fig.savefig(SITE / "assets/productivity/processing-balance.png",dpi=160,facecolor="white");plt.close(fig)
    table = ["| Receiving country | Assessment | 2021–2025 | 2023–2025 | 2025 | Shortfall years / paired years |", "|:--|:--|--:|--:|--:|--:|"]
    fmt = display_ratio
    def period_display(value, count, expected):
        return fmt(value) + (f" ({count}/{expected} years)" if count != expected else "")
    for r in rows:
        table.append(f"| {r['name']} | {r['category']} | {period_display(r['ratio_2021_2025'],r['paired_years'],5)} | {period_display(r['ratio_2023_2025'],r['recent_paired_years'],3)} | {fmt(r['ratio_2025'])} | {r['shortfall_years']} / {r['paired_years']} |")
    assessment = f"""## Who is keeping pace, and who is falling behind? {{#processing-assessment}}

**A stronger recorded flow balance is not the same as having everything under control.** These data show output relative to inflow, but not whether a country has cleared its pending caseload, shortened waits, or improved decision quality. All recorded decisions, including closures, count as output.

### Stronger flow balances

{stronger}. The figures in brackets are decisions per 100 applications across **2021–2025**, calculated from summed counts. Each of these countries also reached at least 100 across 2023–2025 and in 2025, with shortfalls in no more than two of the five years. That is evidence of a stronger recent balance in reported activity, rather than proof of an efficient or backlog-free system.

**France illustrates the difference between a period balance and the latest year:** it recorded 109 decisions per 100 applications over 2021–2025, but 98 in 2025. Its multi-year output exceeded inflow, while the latest year was slightly below balance.

### Repeated shortfalls

{repeated}. Each had applications exceeding decisions in at least four of the five years, and fewer than 100 decisions per 100 applications in both the five-year and recent three-year totals. Repeated imbalances suggest sustained processing pressure; the size of an actual pending caseload must be established from stock data.

### Which balances have deteriorated?

Comparing **2018–2020 with 2023–2025**, the following complete-coverage countries were below balance in the recent period and fell by at least 10 decisions per 100 applications: {sliding}. This is a deterioration in the output-to-inflow ratio, not evidence that staff became less productive: faster application growth can lower the ratio even when decision volumes increase.

The Netherlands and Mexico also have repeated shortfalls, but their recent ratios improved relative to 2018–2020. **Still behind** and **getting further behind** are different findings.

**The Russian Federation was close to balance**, rather than clearly in catch-up: 99.9 decisions per 100 applications in 2021?2025 and 100.4 in 2023?2025. The small difference should not be given more weight than reporting precision allows.

### Catch-up and misleading averages

{catchup} show recent catch-up: five-year output was below inflow, but 2023–2025 output exceeded inflow. For the UK this was **92 decisions per 100 applications across 2021–2025**, versus **116 across 2023–2025**. Recent output can be clearing older claims, so a favourable ratio does not establish that pending claims have disappeared.

**Peru needs particular care.** Its high five-year ratio is dominated by **136,383 recorded decisions in 2023**, followed by **1,318 in 2024 and 1,897 in 2025**. Across 2021–2025, approximately **95% of its recorded decisions were closures**. This is not evidence of consistently high substantive decision output; the table labels it a mixed annual pattern.

**Coverage prevents a confident classification for South Africa and Türkiye.** South Africa lacks application volume in 2021; Türkiye lacks decision volume in 2024 and 2025. Their available-year ratios are shown in the table, with the denominator's coverage, but excluded from the complete five-year chart. High output in the years available does not fill those gaps.

![Recorded decisions per 100 applications across 2021–2025 for the 18 Top 20 receiving countries with paired flows in all five years.](assets/productivity/processing-balance.png){{fig-alt="Horizontal bars compare five-year recorded decision output with application volume. A reference line marks 100 decisions per 100 applications; colours identify stronger balances, catch-up, repeated shortfalls and mixed patterns."}}

### The full comparison

All three numeric period columns show **decisions per 100 applications**. Values close to the threshold of 100 retain one decimal so rounding does not hide which side of balance they fall on. Period ratios divide summed decisions by summed applications for years with both flows available; they do not average annual ratios. A shortfall year has fewer recorded decisions than applications. Classification is descriptive, based on the explicit thresholds above, and is not a statistical test or an efficiency ranking.

""" + "\n".join(table) + "\n\nSource: the same pinned UNHCR mixed-unit, all-procedure extracts as the profiles below. Closures are included; persons and cases are added without conversion. Reporting coverage and procedures differ. The chart omits incomplete five-year coverage. [Download the unrounded assessment (CSV)](data/processing-assessment.csv).\n"
    (SITE / "_processing-assessment.qmd").write_text(assessment,encoding="utf-8")
    path = SITE / "productivity.qmd"; text = path.read_text(encoding="utf-8")
    include = "{{< include _processing-assessment.qmd >}}"
    if include not in text:
        text = text.replace("## Top 20 receiving-country profiles", include + "\n\n## Top 20 receiving-country profiles")
        path.write_text(text,encoding="utf-8")
    # One-time migration preserves the detailed worldwide chapter and its anchors.
    worldwide = SITE / "worldwide.qmd"
    if not worldwide.exists():
        text = (SITE / "index.qmd").read_text(encoding="utf-8").replace('title: "Asylum under pressure"','title: "Worldwide asylum trends"',1)
        worldwide.write_text(text,encoding="utf-8")
    totals = apps.groupby("Year").applied.sum(min_count=1)
    decision_totals = decs.groupby("Year")["Total decisions"].sum(min_count=1)
    stock = json.loads((SITE / "data/pending-stock-series.json").read_text(encoding="utf-8"))
    stocks = {int(r['year']):int(r['asylum_seekers']) for r in stock['response']['items']}
    gap = totals[2025]-decision_totals[2025]
    summary = f"""---
title: "Asylum under pressure"
subtitle: "The global picture, the processing gap, and the countries keeping pace."
author: Kathryn Hopkins
toc: false
---

::: {{.eyebrow}}
Report summary · Saved data through 2025
:::

::: {{.lead}}
The world recorded far more asylum applications in 2025 than in 2019, while the observed unresolved caseload more than doubled. Some receiving countries have recently matched incoming volume with decisions; others show repeated processing shortfalls.
:::

:::: {{.summary-headlines}}
::: {{.summary-metric .summary-metric-primary}}
<span class="summary-value">{stocks[2025]/1e6:.1f}m</span>
<span class="summary-label">asylum seekers pending at end-2025</span>
<span class="summary-detail">{n(stocks[2025])} persons · observed UNHCR stock</span>
:::
::: {{.summary-metric}}
<span class="summary-value">{totals[2025]/1e6:.1f}m</span>
<span class="summary-label">reported applications in 2025</span>
<span class="summary-detail">{n(totals[2025])} application events · mixed reporting units</span>
:::
::: {{.summary-metric}}
<span class="summary-value">{100*decision_totals[2025]/totals[2025]:.0f}</span>
<span class="summary-label">decisions per 100 applications in 2025</span>
<span class="summary-detail">{decision_totals[2025]/1e6:.1f}m recorded decisions · closures included</span>
:::
::::

**The recorded 2025 flow gap was {n(gap)}:** that many more applications than decisions were reported. This is an imbalance between annual flows, **not an estimate of the backlog**. The pending headline above comes from a separate observed population series.

## The main findings

1. **High demand, despite a retreat from the peak.** Applications in 2025 were **{100*(totals[2025]/totals[2019]-1):.0f}% above 2019**, but **{100*abs(totals[2025]/totals[2024]-1):.1f}% below 2024**. The recorded peak was **{totals.max()/1e6:.1f}m in {int(totals.idxmax())}**. Recent growth has not been uninterrupted. [Explore the worldwide trends](worldwide.qmd#worldwide-commentary).
2. **The unresolved stock has grown faster.** The observed asylum-seeker stock rose **{100*(stocks[2025]/stocks[2019]-1):.0f}% since 2019**, and **{100*(stocks[2025]/stocks[2024]-1):.1f}% from 2024 to 2025**. It is a persons-based population measure, distinct from mixed-unit application events. [See the stock series](worldwide.qmd#pending).
3. **Processing pressure is uneven.** Some receiving countries have recorded enough output to match recent inflow; others have repeated shortfalls. Period totals, annual variation and closures all matter. [Read the processing assessment](productivity.qmd#processing-assessment).
4. **Protection rates differ sharply.** The same recorded nationality can have very different aggregate outcomes in different receiving countries, and rates can change substantially over time. Different claim circumstances, procedures and timing prevent interpreting these as individual chances or isolated policy effects. [Compare grant rates and recent changes](grants.qmd#grant-commentary).

## Who appears to be keeping pace?

:::: {{.summary-findings}}
::: {{.summary-finding}}
### Stronger recorded flow balances

{stronger}.

The figures are decisions per 100 applications across 2021–2025. These countries also met or exceeded 100 in the recent three-year period and in 2025. This supports a finding of stronger recorded flow balance, not that their pending caseloads have been cleared.
:::
::: {{.summary-finding .summary-finding-pressure}}
### Repeated shortfalls

{repeated}.

Each had fewer decisions than applications in at least four of five years, with aggregate output also below inflow in 2021–2025 and 2023–2025. A shortfall signals pressure; it does not directly measure waiting time or backlog growth.
:::
::::

**Recent catch-up:** {catchup}. Their 2023–2025 output exceeded inflow, despite a five-year shortfall. **Close to balance:** the Russian Federation. **Mixed patterns:** France's period balance is stronger than its latest-year balance; Peru's high ratio is dominated by closures. South Africa and Türkiye have incomplete recent flow coverage. [See all 20 assessments and the comparison chart](productivity.qmd#processing-assessment).

{{{{< include _application-concentration.qmd >}}}}

## Explore the evidence

- [Worldwide trends](worldwide.qmd): applications, decision composition, unresolved stock and reporting coverage.
- [Country explorer](explore.qmd#top-20-gallery): Top 20 receiving-country profiles and commentary, plus an interactive selector.
- [Origins & destinations](origins.qmd): Top 20 origins, where applications were lodged, and how their patterns changed.
- [Processing assessment](productivity.qmd#processing-assessment): stronger balances, repeated shortfalls, recent catch-up and annual variation.
- [Grant rates](grants.qmd#grant-commentary): protection outcomes, closures, changes over time and same-origin comparisons.
- [Maps](maps.qmd) and [activity per population](population.qmd): geographical and population context.
- [UK and Rwanda](uk.qmd#uk-commentary): official UK statistics, small-boat arrivals and outcomes, and Rwanda's own system.

::: {{.reading-note}}
**Scope of this summary.** Application and decision counts describe the fixed 2000–2025 UNHCR extract, combining persons and cases without conversion, across reported procedures and application types. They are reported activities, not harmonised counts of unique people. Coverage can change. Latest-year figures need not be complete worldwide returns. Pending stock is reported separately in persons. The interactive explorers identify their own saved refresh dates. This report describes observed patterns; it does not predict inevitable future growth or establish policy causes. [Methods & sources](methods.qmd).
:::

An independent analysis by Kathryn Hopkins. Report edition · 5 November 2026.
"""
    (SITE / "index.qmd").write_text(summary,encoding="utf-8")
    print("Prepared executive summary and 20 processing assessments.")
    for row in rows:
        print(row['country'],row['category'],round(row['ratio_2021_2025']) if row['ratio_2021_2025'] is not None else None)


if __name__ == "__main__":
    main()
