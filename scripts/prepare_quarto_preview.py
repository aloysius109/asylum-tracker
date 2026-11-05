"""Prepare a four-figure Quarto chapter from the verified analysis snapshots."""
import base64
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
import nbformat
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"


def main():
    notebook = nbformat.read(ROOT / "UNHCRData.ipynb", as_version=4)
    cells = [c for c in notebook.cells if c.cell_type == "code"]
    digest = hashlib.sha256(json.dumps([c.source for c in cells], ensure_ascii=False).encode("utf-8")).hexdigest()
    if notebook.metadata.get("executed_code_sha256") != digest:
        raise ValueError("Notebook code changed since its verified execution.")
    if any(c.execution_count is None or any(o.output_type == "error" for o in c.outputs) for c in cells):
        raise ValueError("The notebook must be fully and successfully executed.")

    input_lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    if input_lock["executed_code_sha256"] != digest:
        raise ValueError("This sample is pinned to a different notebook edition.")
    manifest_cell = next(c for c in cells if c.source.startswith("# %% Input manifest"))
    manifest_html = "\n".join(o.get("data", {}).get("text/html", "") for o in manifest_cell.outputs)
    hashes = {}
    frames = {}
    for filename in ["asylum-applications.csv", "asylum-decisions.csv"]:
        hashes[filename] = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
        if hashes[filename] != input_lock["inputs"][filename] or hashes[filename][:45] not in manifest_html:
            raise ValueError(f"{filename} differs from the notebook's verified input.")
        frames[filename] = pd.read_csv(ROOT / filename)
    apps = frames["asylum-applications.csv"]
    decs = frames["asylum-decisions.csv"]
    year = min(int(apps.Year.max()), int(decs.Year.max()))
    if year != 2025 or min(apps.Year.min(), decs.Year.min()) != 2000:
        raise ValueError("The authored chapter covers 2000–2025. Review its dates before using new snapshots.")
    assets = DEST / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    figures = {
        "# %% Worldwide 2000 onwards — Applications by Type and Decisions": "applications-and-decisions.png",
        "# %% Plot worldwide annual decision-outcome rates as a stacked bar chart": "decision-composition.png",
        "# %% Worldwide annual application-flow waterfall": "observed-pending.png",
    }
    for prefix, filename in figures.items():
        matches = [c for c in cells if c.source.startswith(prefix)]
        if len(matches) != 1:
            raise ValueError(f"Expected one figure cell for {prefix}")
        images = [o.data["image/png"] for o in matches[0].outputs if "image/png" in o.get("data", {})]
        if len(images) != 1:
            raise ValueError(f"Expected one saved figure for {prefix}")
        (assets / filename).write_bytes(base64.b64decode(images[0], validate=True))

    annual_apps = apps.groupby("Year")["applied"].sum()
    annual_decs = decs.groupby("Year")["Total decisions"].sum()
    app_coverage = apps.groupby("Year")["Country of asylum (ISO)"].nunique()
    dec_coverage = decs.groupby("Year")["Country of asylum (ISO)"].nunique()
    latest_apps = int(annual_apps.loc[year])
    latest_decs = int(annual_decs.loc[year])
    latest_reporters = int(app_coverage.loc[year])
    pending = json.loads((DEST / "data/pending-stock-2025.json").read_text(encoding="utf-8"))
    if pending["year"] != year or pending["pending_persons"] <= 0:
        raise ValueError("Pending headline requires a positive observed stock for the headline year.")
    snapshot = f"""::: {{.snapshot}}
<div><span class="value">{latest_apps / 1e6:.1f}m</span><span class="label">application events recorded in {year}<br>Persons and cases combined</span></div>
<div><span class="value">{latest_decs / 1e6:.1f}m</span><span class="label">decisions recorded in {year}<br>Persons and cases combined</span></div>
<div><span class="value">{pending['pending_persons']/1e6:.1f}m</span><span class="label">asylum seekers pending at end-{year}<br>Observed UNHCR stock (persons)</span></div>
:::

::: {{.snapshot-note}}
Application and decision totals: latest shared year in the saved extracts. These totals are not estimates of complete worldwide coverage, and applications are not necessarily unique individuals. Pending stock is a separate population measure: **{pending['pending_persons']:,} persons**, from the [UNHCR worldwide population API]({pending['url']}), retrieved {pending['retrieved_at_utc'][:10]}. The stock chart uses the same latest-year total from its separately saved annual-series snapshot.
:::
"""
    (DEST / "_snapshot.qmd").write_text(snapshot, encoding="utf-8")
    peak_year = int(annual_apps.idxmax())
    (DEST / "_flow-reading.qmd").write_text(
        f"In this combined reported-applications extract, application volume is highest in **{peak_year}**, at "
        f"**{annual_apps.loc[peak_year]:,.0f} recorded events**. The latest shared year, {year}, "
        f"contains **{latest_apps:,}**. Those are descriptions of the saved records—not "
        "adjusted estimates of global demand. The coverage check below helps qualify the comparison.\n",
        encoding="utf-8")
    ratios = annual_decs.div(annual_apps.where(annual_apps.gt(0)))
    below = int((annual_decs < annual_apps).sum())
    (DEST / "_productivity-reading.qmd").write_text(
        f"Recorded decisions fell below reported applications in **{below} of {len(ratios)} years** "
        f"between 2000 and {year}. In **{year}**, the extracts record **{latest_apps:,} applications** "
        f"and **{latest_decs:,} decisions**: **{ratios.loc[year]*100:.0f} decisions per 100 applications**. "
        f"The annual flow difference was **{latest_apps-latest_decs:,}**. This is a mixed-unit comparison "
        "of recorded flows, not a measured increase in the pending caseload.\n", encoding="utf-8")
    totals = decs[["Recognized decisions", "Otherwise closed", "Total decisions"]].sum()
    recognised = totals["Recognized decisions"] / totals["Total decisions"]
    closed = totals["Otherwise closed"] / totals["Total decisions"]
    (DEST / "_outcome-reading.qmd").write_text(
        f"Across the full 2000–{year} combined reported-units extract, **{recognised:.0%}** of all "
        f"recorded decisions recognised refugee status and **{closed:.0%}** were otherwise closed. "
        "These period shares weight each recorded decision equally; they are not averages "
        "of national percentages or the likelihood that a new applicant receives protection.\n",
        encoding="utf-8")
    from style_reporting_coverage import main as style_reporting_coverage
    style_reporting_coverage()
    stock = next(c for c in cells if c.source.startswith("# %% Worldwide annual application-flow"))
    stock_time = next(
        (o.text.strip() for o in stock.outputs if o.output_type == "stream" and "retrieved at:" in o.text),
        "See the executed notebook for stock provenance.")
    provenance = f"""**Notebook code fingerprint:** <code>{digest}</code>

| Input snapshot | Rows | SHA-256 |
|---|---:|---|
| Applications | {len(frames['asylum-applications.csv']):,} | <code>{hashes['asylum-applications.csv']}</code> |
| Decisions | {len(frames['asylum-decisions.csv']):,} | <code>{hashes['asylum-decisions.csv']}</code> |

**Stock provenance:** {stock_time}

File hashes identify exact inputs; they do not establish when the source first published them.
"""
    (DEST / "_provenance.qmd").write_text(provenance, encoding="utf-8")
    print("Prepared four figures, verified source hashes, and data-derived chapter text.")


if __name__ == "__main__":
    main()
