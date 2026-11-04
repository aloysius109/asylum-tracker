"""Shared publication styling and fixed-edition receiving-country gallery."""
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
OUTCOMES = ["Recognized decisions", "Complementary protection", "Rejected decisions", "Otherwise closed"]
LABELS = ["Refugee status", "Other protection", "Rejected", "Otherwise closed"]
COLOURS = ["#00a98f", "#f4c542", "#ef6655", "#8574bd"]
YEARS = np.arange(2000, 2026)


def decorate(ax, label):
    ax.set_facecolor("#ffffff")
    ax.spines[["top", "right", "left"]].set_visible(False)
    ax.spines["bottom"].set_color("#cbd7d3")
    ax.grid(axis="y", color="#dce4e1", linewidth=.7)
    ax.set_axisbelow(True)
    ax.tick_params(length=0, labelcolor="#45605b", pad=8)
    ax.set(xlim=(1999.3, 2025.7), xticks=[2000, 2005, 2010, 2015, 2020, 2025], ylabel=label)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v/1e6:g}m" if abs(v)>=1e6 else f"{v/1000:g}k" if abs(v)>=1000 else f"{v:g}"))


def annual(frame, columns):
    return frame.groupby("Year")[columns].sum(min_count=1).reindex(YEARS)


def flows(ax, apps, decs, unit):
    values = annual(decs, OUTCOMES)
    bottom = np.zeros(len(YEARS))
    for key, label, colour in zip(OUTCOMES, LABELS, COLOURS):
        v = values[key].to_numpy()
        ax.bar(YEARS, v, bottom=bottom, color=colour, width=.78, label=label)
        bottom += v
    a = annual(apps, ["applied"])["applied"]
    ax.plot(YEARS, a, color="#164b63", linewidth=2.3, marker="o", markersize=3, label="Applications")
    decorate(ax, f"Reported {unit}")
    ax.set_ylim(bottom=0)


def productivity(apps, decs, ranking):
    """Annual flow ratios, preserving missing observations and zero denominators."""
    assets = DEST / "assets/productivity"
    assets.mkdir(parents=True, exist_ok=True)
    records, cards = [], []
    for code in ranking.index:
        country = pycountry.countries.get(alpha_3=code)
        name = country.name if country else code
        a = annual(apps.loc[apps["Country of asylum (ISO)"].eq(code)], ["applied"])["applied"]
        d = annual(decs.loc[decs["Country of asylum (ISO)"].eq(code)], ["Total decisions"])["Total decisions"]
        ratio = d.div(a.where(a.gt(0)))
        smooth = ratio.rolling(3, center=True, min_periods=1).mean().where(ratio.notna())
        records.extend({"country": code, "name": name, "year": int(year),
                        "applications": a.loc[year], "decisions": d.loc[year],
                        "decisions_per_100_applications": ratio.loc[year]*100,
                        "centred_three_year_mean": smooth.loc[year]*100} for year in YEARS)
        fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
        ax.plot(YEARS, ratio*100, color="#bedbd5", marker="o", markersize=4, linewidth=1.5, label="Annual ratio")
        ax.plot(YEARS, smooth*100, color="#008f83", linewidth=2.8, label="3-year centred mean")
        ax.axhline(100, color="#d8634c", linestyle="--", linewidth=1.3, label="100 decisions per 100 applications")
        decorate(ax, "Decisions per 100 applications")
        ax.yaxis.set_major_formatter(FuncFormatter(lambda value, _: f"{value:,.0f}"))
        ax.set_ylim(bottom=0)
        ax.set_title(f"{name} · {code}", loc="left", fontsize=18, pad=40)
        ax.legend(loc="lower left", bbox_to_anchor=(0,1.01), frameon=False, fontsize=9, ncol=3)
        filename = f"assets/productivity/{code.lower()}.png"
        fig.savefig(DEST / filename, dpi=135, facecolor="white")
        plt.close(fig)
        cards.append(f"""::: {{.origin-card}}
### {name}

![{name}: annual decisions per 100 applications and a three-year centred mean, 2000–2025.]({filename}){{loading="lazy"}}

[Open full-size chart]({filename})
:::
""")
    frame = pd.DataFrame(records)
    (DEST / "data").mkdir(exist_ok=True)
    frame.to_csv(DEST / "data/processing-productivity.csv", index=False)
    page = """---
title: "Processing Productivity"
subtitle: "Decisions relative to applications in the Top 20 receiving countries, 2000–2025."
toc: false
page-layout: full
---

How does recorded decision output compare with incoming application volume? These charts use the notebook's **decision-to-application ratio**, expressed as **decisions per 100 applications**.

::: {.reading-note}
**A measure of processing flows.** This ratio does not measure staff productivity, processing speed, waiting times, or decision quality: those require information about resources and individual cases. Decisions can concern applications from earlier years. Administrative closures are included in recorded decisions.
:::

## How to read the charts

**100** means as many decisions as applications were recorded in that year. **Above 100** means decisions exceeded applications; **below 100** means applications exceeded decisions. These comparisons alone do not establish whether a backlog grew or fell.

The pale line shows each annual ratio; the teal line is a **three-year centred mean** of annual ratios, using available values at the ends. A missing annual ratio remains a gap. This is an average of ratios, not a ratio of three-year totals. No ratio is calculated when applications are zero or either flow is unavailable.

**Reporting units:** original persons- and case-reported values are added without conversion in both flows. These exploratory ratios can be affected by different unit mixes and reporting coverage; they are not harmonised comparisons of people or a league table of national efficiency.

**Selection:** the same Top 20 receiving countries as the Country Explorer gallery, ranked by combined reported application volume across **2000–2025**. This is the fixed notebook edition, rather than the explorer's refreshed dataset.

[Download all chart values (CSV)](data/processing-productivity.csv) · [Methods and source definitions](methods.qmd)

## Top 20 receiving-country profiles

:::: {.origin-gallery .productivity-gallery}
"""
    (DEST / "productivity.qmd").write_text(page + "\n".join(cards) + "\n::::\n", encoding="utf-8")


def main():
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    for filename, digest in lock["inputs"].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != digest:
            raise ValueError(f"Fixed-edition input changed: {filename}")
    apps = pd.read_csv(ROOT / "asylum-applications.csv")
    decs = pd.read_csv(ROOT / "asylum-decisions.csv")
    receiving = DEST / "assets/receiving"
    receiving.mkdir(parents=True, exist_ok=True)
    ranking = apps.groupby("Country of asylum (ISO)")["applied"].sum().nlargest(20)
    parts = ["""## Gallery: Top 20 receiving countries {#top-20-gallery}

The 20 receiving countries with the largest **combined reported application volume, 2000–2025**, in the fixed notebook edition. Reported applications and decisions combine persons and cases without conversion; they are **not counts of unique people**. The dropdown above uses its own dated, refreshed dataset and lets you examine units separately.

**Colours show decision outcomes; the blue line shows applications.** Decisions can concern earlier applications. Gaps indicate unavailable records, not confirmed zeros. Click a chart to enlarge it.

:::: {.origin-gallery .receiving-gallery}
"""]
    with plt.rc_context({"font.family":"DejaVu Sans", "font.size":10, "text.color":"#20383b", "axes.labelcolor":"#45605b", "axes.titleweight":"normal"}):
        for rank, code in enumerate(ranking.index, 1):
            country = pycountry.countries.get(alpha_3=code)
            name = country.name if country else code
            fig, ax = plt.subplots(figsize=(12, 6), layout="constrained")
            a = apps.loc[apps["Country of asylum (ISO)"].eq(code)]
            d = decs.loc[decs["Country of asylum (ISO)"].eq(code)]
            flows(ax, a, d, "applications / decisions")
            fig.suptitle(f"{name} · {code}\nApplications and decision outcomes | 2000–2025", fontsize=17)
            ax.legend(loc="upper left", ncol=3, frameon=False, fontsize=9)
            filename = f"assets/receiving/{code.lower()}.png"
            fig.savefig(DEST / filename, dpi=125, facecolor="white")
            plt.close(fig)
            parts.append(f"""::: {{.origin-card}}
### {rank}. {name}

![{name}: annual reported applications and decision outcomes, persons and cases combined, 2000–2025.]({filename}){{loading="lazy"}}

[Open full-size chart]({filename}) · **{code}**
:::
""")
        parts.append("::::\n")
        (DEST / "_receiving-gallery.qmd").write_text("\n".join(parts), encoding="utf-8")
        productivity(apps, decs, ranking)
        papps = apps.loc[apps["Cases / Persons"].eq("P")]
        pdecs = decs.loc[decs["Cases / Persons"].eq("P")]
        # Preserve the application-type breakdown used by the chapter.
        papps = papps.copy()
        papps["Application group"] = papps["Application type"].map({"N": "New", "R": "Repeat", "A": "Appeal"}).fillna("Other / unspecified")
        types = papps.groupby(["Year", "Application group"])["applied"].sum().unstack().reindex(index=YEARS, columns=["New", "Repeat", "Appeal", "Other / unspecified"])
        if not np.allclose(types.sum(axis=1), annual(papps, ["applied"])["applied"]):
            raise ValueError("Application-type stacks must reconcile to all recorded applications.")
        fig, ax = plt.subplots(figsize=(12, 6), layout="constrained")
        bottom = np.zeros(len(YEARS))
        for key, colour in zip(types.columns, COLOURS):
            v = types[key].fillna(0).to_numpy()
            ax.bar(YEARS, v, bottom=bottom, color=colour, width=.78, label=str(key))
            bottom += v
        ax.plot(YEARS, annual(pdecs, ["Total decisions"])["Total decisions"], color="#164b63", marker="o", markersize=3, linewidth=2.5, label="Recorded decisions")
        decorate(ax, "Reported persons")
        ax.set_title("Applications by type and recorded decisions", loc="left", fontsize=18, pad=55)
        ax.legend(loc="lower left", bbox_to_anchor=(0,1.01), ncol=3, frameon=False)
        fig.savefig(DEST / "assets/applications-and-decisions.png", dpi=160, facecolor="white")
        plt.close(fig)
        values = annual(pdecs, OUTCOMES)
        totals = annual(pdecs, ["Total decisions"])["Total decisions"]
        fig, ax = plt.subplots(figsize=(12, 5.5), layout="constrained")
        bottom = np.zeros(len(YEARS))
        for key, label, colour in zip(OUTCOMES, LABELS, COLOURS):
            v = (values[key]/totals).to_numpy()
            ax.bar(YEARS, v, bottom=bottom, color=colour, width=.88, label=label)
            bottom += v
        decorate(ax, "Share of recorded decisions")
        ax.set_ylim(0,1)
        ax.yaxis.set_major_formatter(PercentFormatter(1))
        ax.set_title("How recorded decisions are composed", loc="left", fontsize=18, pad=40)
        ax.legend(loc="lower left", bbox_to_anchor=(0,1.01), ncol=4, frameon=False)
        fig.savefig(DEST / "assets/decision-composition.png", dpi=160, facecolor="white")
        plt.close(fig)
    print("Styled worldwide figures and prepared 20 receiving-country profiles from pinned inputs.")


if __name__ == "__main__":
    main()
