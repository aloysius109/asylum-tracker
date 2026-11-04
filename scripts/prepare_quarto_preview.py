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

    apps = apps.loc[apps["Cases / Persons"].eq("P")]
    decs = decs.loc[decs["Cases / Persons"].eq("P")]
    annual_apps = apps.groupby("Year")["applied"].sum()
    annual_decs = decs.groupby("Year")["Total decisions"].sum()
    app_coverage = apps.groupby("Year")["Country of asylum (ISO)"].nunique()
    dec_coverage = decs.groupby("Year")["Country of asylum (ISO)"].nunique()
    latest_apps = int(annual_apps.loc[year])
    latest_decs = int(annual_decs.loc[year])
    latest_reporters = int(app_coverage.loc[year])
    snapshot = f"""::: {{.snapshot}}
<div><span class="value">{latest_apps / 1e6:.2f}m</span><span class="label">application events recorded in {year}<br>Persons-reported subset</span></div>
<div><span class="value">{latest_decs / 1e6:.2f}m</span><span class="label">decisions recorded in {year}<br>Persons-reported subset</span></div>
<div><span class="value">{latest_reporters}</span><span class="label">receiving-country codes with<br>persons-reported applications in {year}</span></div>
:::

::: {{.snapshot-note}}
Latest shared year in the saved extracts. These totals are not estimates of complete worldwide coverage, and applications are not necessarily unique individuals.
:::
"""
    (DEST / "_snapshot.qmd").write_text(snapshot, encoding="utf-8")
    peak_year = int(annual_apps.idxmax())
    (DEST / "_flow-reading.qmd").write_text(
        f"In this persons-reported extract, application volume is highest in **{peak_year}**, at "
        f"**{annual_apps.loc[peak_year]:,.0f} recorded events**. The latest shared year, {year}, "
        f"contains **{latest_apps:,}**. Those are descriptions of the saved records—not "
        "adjusted estimates of global demand. The coverage check below helps qualify the comparison.\n",
        encoding="utf-8")
    totals = decs[["Recognized decisions", "Otherwise closed", "Total decisions"]].sum()
    recognised = totals["Recognized decisions"] / totals["Total decisions"]
    closed = totals["Otherwise closed"] / totals["Total decisions"]
    (DEST / "_outcome-reading.qmd").write_text(
        f"Across the full 2000–{year} persons-reported extract, **{recognised:.1%}** of all "
        f"recorded decisions recognised refugee status and **{closed:.1%}** were otherwise closed. "
        "These period shares weight each recorded decision equally; they are not averages "
        "of national percentages or the likelihood that a new applicant receives protection.\n",
        encoding="utf-8")
    (DEST / "_coverage-reading.qmd").write_text(
        f"The application file contains persons-reported records for **{app_coverage.loc[year-1]}** "
        f"receiving-country codes in {year-1} and **{app_coverage.loc[year]}** in {year}. "
        f"The decision file contains **{dec_coverage.loc[year-1]}** and **{dec_coverage.loc[year]}**, "
        "respectively. This shows that the set of represented reporters is not constant.\n",
        encoding="utf-8")
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11}):
        fig, ax = plt.subplots(figsize=(11, 4.8), layout="constrained")
        ax.plot(app_coverage.index, app_coverage.values, color="#153b40", linewidth=2.3, label="Applications")
        ax.plot(dec_coverage.index, dec_coverage.values, color="#ae633f", linewidth=2.3, linestyle="--", label="Decisions")
        ax.scatter([year], [app_coverage.loc[year]], color="#153b40", zorder=3)
        ax.scatter([year], [dec_coverage.loc[year]], color="#ae633f", zorder=3)
        ax.set(xlabel="Year", ylabel="Receiving-country codes represented",
               title="Reporting presence in the persons-reported subset")
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y", alpha=.2)
        ax.legend(frameon=False)
        fig.savefig(assets / "reporting-coverage.png", dpi=160, facecolor="white")
        plt.close(fig)
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
