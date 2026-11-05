"""Build a responsive annual decision-outcome doughnut gallery."""
import hashlib
import json
import os
from pathlib import Path
os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"
KEYS = ["Recognized decisions", "Complementary protection", "Rejected decisions", "Otherwise closed"]
LABELS = ["Refugee status", "Other protection", "Rejected", "Otherwise closed"]
COLOURS = ["#00a98f", "#f4c542", "#ef6655", "#8574bd"]


def percent(value):
    p = value * 100
    if p == 0:
        return "0%"
    if p < .1:
        return "&lt;0.1%"
    return f"{p:.1f}%" if round(p, 1) < 10 else f"{p:.0f}%"


def main():
    path = ROOT / "asylum-decisions.csv"
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    if hashlib.sha256(path.read_bytes()).hexdigest() != lock["inputs"][path.name]:
        raise ValueError("Decision input differs from the pinned edition.")
    raw = pd.read_csv(path)
    raw_totals = raw.groupby("Year")["Total decisions"].sum().reindex(range(2000,2026))
    eligible = raw[KEYS+["Total decisions"]].notna().all(axis=1) & raw[KEYS].ge(0).all(axis=1) & raw[KEYS].sum(axis=1).eq(raw["Total decisions"]) & raw["Total decisions"].gt(0)
    data = raw.loc[eligible].groupby("Year")[KEYS+["Total decisions"]].sum(min_count=1).reindex(range(2000,2026))
    if data.isna().any().any() or not (data["Total decisions"] > 0).all() or not np.array_equal(data[KEYS].sum(axis=1),data["Total decisions"]):
        raise ValueError("Each annual pie requires four complete outcomes reconciling to a positive total.")
    assets = DEST / "assets/annual-outcomes"
    assets.mkdir(parents=True,exist_ok=True)
    parts = ['''<div class="annual-pie-intro"><span class="eyebrow">Recorded decision outcomes · 2000–2025</span><p>One year, one picture. Each ring divides that year's decisions into four outcomes; the centre shows the included decision count. Only source records whose four outcomes reconcile to their recorded total are included; coverage is shown on each card.</p></div>

::: {.annual-pie-grid}
''']
    data["All reported decisions"] = raw_totals
    data["Included share"] = data["Total decisions"]/raw_totals
    with plt.rc_context({"font.family":"DejaVu Sans", "text.color":"#20383b"}):
        for year, row in data.iterrows():
            total = int(row["Total decisions"])
            shares = row[KEYS]/total
            fig, ax = plt.subplots(figsize=(3,2.7),layout="constrained")
            ax.pie(shares,colors=COLOURS,startangle=90,counterclock=False,
                   wedgeprops={"width":.27,"edgecolor":"white","linewidth":2.5})
            ax.text(0,.08,f"{total/1e6:.1f}m",ha="center",va="center",fontsize=23,color="#20383b")
            ax.text(0,-.2,"decisions",ha="center",va="center",fontsize=10,color="#526767")
            filename=f"assets/annual-outcomes/{year}.png"
            fig.savefig(DEST/filename,dpi=145,facecolor="white");plt.close(fig)
            legend = "".join(f'<li><span class="annual-outcome-label"><i style="background:{colour}"></i>{label}</span><strong>{percent(share)}</strong></li>' for label,colour,share in zip(LABELS,COLOURS,shares))
            alt = f"{year}: " + "; ".join(f"{label} {percent(share)}" for label,share in zip(LABELS,shares))
            parts.append(f'''<section class="annual-pie-card" aria-label="Decision outcomes in {year}">
<h3>{year}</h3>
<img src="{filename}" alt="{alt}" width="435" height="391" loading="lazy">
<ul>{legend}</ul>
<p class="annual-pie-total">{total:,} decisions included<br>of {int(raw_totals.loc[year]):,} reported ({percent(total/raw_totals.loc[year])})</p>
</section>
''')
    parts.append(''':::

Each percentage uses **all decisions in the included, reconciled records for that year**, including administrative closures. Source records with missing outcomes, inconsistent totals, or no positive decision total are excluded; the inclusion percentage compares eligible decision totals with all reported decision totals. The headline application and decision totals still use the full extract. Original persons- and case-reported counts are combined without conversion. Rounded percentages may not sum to 100%. Coverage and procedure mix can change between years; these are not application-cohort success rates.

[Download annual decision counts and unrounded shares (CSV)](data/annual-decision-outcomes.csv)
''')
    (DEST/"_annual-decision-pies.qmd").write_text("\n".join(parts),encoding="utf-8")
    for key in KEYS:
        data[key+" share"] = data[key]/data["Total decisions"]
    data.to_csv(DEST/"data/annual-decision-outcomes.csv",index_label="year")
    print("Prepared 26 annual doughnut cards; every year's outcome counts reconcile to total decisions.")


if __name__ == "__main__":
    main()
