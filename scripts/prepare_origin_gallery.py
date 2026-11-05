"""Publish the verified notebook's 20 colourful country-of-origin profiles."""
import base64
import hashlib
from html import escape
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import os

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

import nbformat

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"


class CountryTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = []
        self.text = None

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self.row = []
        elif tag == "td":
            self.text = ""

    def handle_data(self, data):
        if self.text is not None:
            self.text += data

    def handle_endtag(self, tag):
        if tag == "td" and self.text is not None:
            self.row.append(self.text.strip())
            self.text = None
        elif tag == "tr" and len(self.row) == 3 and re.fullmatch(r"[A-Z]{3}", self.row[0]):
            self.rows.append(self.row)


def main():
    notebook = nbformat.read(ROOT / "UNHCRData.ipynb", as_version=4)
    nbformat.validate(notebook)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    digest = hashlib.sha256(json.dumps([cell.source for cell in cells], ensure_ascii=False).encode("utf-8")).hexdigest()
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    if notebook.metadata.get("executed_code_sha256") != digest or lock["executed_code_sha256"] != digest:
        raise ValueError("The gallery requires the pinned, verified notebook edition.")
    if any(cell.execution_count is None or any(o.output_type == "error" for o in cell.outputs) for cell in cells):
        raise ValueError("Execute the complete notebook successfully before preparing the gallery.")
    for filename, expected in lock["inputs"].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Input snapshot changed: {filename}")
    table_cell = next(cell for cell in cells if cell.source.startswith("top_20_origin_countries ="))
    chart_cell = next(cell for cell in cells if cell.source.startswith("# %% Plot the Top 20 Origin Countries and their destinations"))
    table = CountryTable()
    for output in table_cell.outputs:
        if "text/html" in output.get("data", {}):
            table.feed(output.data["text/html"])
    images = [output.data["image/png"] for output in chart_cell.outputs if "image/png" in output.get("data", {})]
    if len(table.rows) != 20 or len(images) != len(table.rows):
        raise ValueError("Expected 20 origin profiles in the same order as the saved country table.")
    if len({row[0] for row in table.rows}) != 20:
        raise ValueError("Origin profiles contain duplicate country codes.")
    assets = DEST / "assets/origins"
    assets.mkdir(parents=True, exist_ok=True)
    applications = pd.read_csv(ROOT / "asylum-applications.csv")
    applications = applications.loc[applications.Year.between(2000, 2025)]
    volumes = applications.groupby("Country of origin (ISO)")["applied"].sum()
    selected = volumes.reindex([row[0] for row in table.rows])
    if selected.isna().any() or set(selected.index) != set(volumes.nlargest(20).index):
        raise ValueError("Gallery origins must match the source Top 20 application volumes.")
    for code, name, saved_total in table.rows:
        if int(float(saved_total.replace(",", ""))) != int(volumes.loc[code]):
            raise ValueError(f"Saved gallery volume differs from the input snapshot: {code}")
    summary = pd.DataFrame({"origin": selected.index,
                            "name": [row[1] for row in table.rows],
                            "applications": selected.to_numpy()})
    summary["share_of_all_applications_percent"] = summary.applications / volumes.sum() * 100
    summary.to_csv(assets / "application-volumes.csv", index=False)
    from style_origin_volumes import main as style_origin_volumes
    style_origin_volumes()
    total = int(selected.sum())
    share = total / volumes.sum()
    leader = table.rows[0][1]
    overview = f'''## How large are these application flows?

::: {{.snapshot}}
<div><span class="value">{total/1e6:.1f}m</span><span class="label">reported applications from<br>the Top 20 origins, 2000–2025</span></div>
<div><span class="value">{share:.0%}</span><span class="label">of all reported applications<br>in the same saved extract</span></div>
<div><span class="value">{int(selected.iloc[0]):,}</span><span class="label">from {escape(leader)}<br>the largest recorded origin</span></div>
:::

![Ranked reported application totals for the same 20 origins shown in the gallery, 2000–2025.](assets/origins/application-volumes.png){{fig-alt="Horizontal bars showing all 20 origins in descending application volume, with exact totals labelled." fig-cap="Period totals sum original persons- and case-reported applications without conversion. They count reported application activity, not unique people. Unknown origin is included where recorded. These colours distinguish known and unknown origin, not receiving destinations."}}

[See these origins on a map](maps.qmd#origin-map) ? [Download exact volumes and shares (CSV)](assets/origins/application-volumes.csv)

'''
    country_links = "\n".join(
        f'<a href="#origin-{code.lower()}">{escape(name)}</a>'
        for code, name, _ in sorted(table.rows, key=lambda row: row[1]))
    parts = ['''---
title: "Where applications originated"
subtitle: "Twenty country-of-origin profiles, told through the countries receiving their applications and recognising refugee status."
toc: false
page-layout: full
---

These multicoloured charts follow one **country of origin** at a time. The colours identify **receiving countries**; the same receiving country keeps its colour across the collection. Click any chart to open the full-size version.

**Notebook edition: 2000-2025.** These exploratory profiles retain the original persons- and case-reported values; see the reading guide for interpretation.

::: {.callout-note collapse="true" title="How to read these charts"}
**How to read each profile:** the top panel shows destinations' shares of recorded applications. The middle panel shows their shares of recognised refugee-status decisions. The lower panel compares those two distributions in **percentage points**. It is not a grant rate or an individual's chance of recognition: decisions may concern earlier applications.

The figures reproduce the **2000–2025 notebook edition**. They combine original persons- and case-reported values and are exploratory comparisons, not harmonised counts of people. The 20 origins are selected by combined reported application volume. The six featured destinations per origin are selected using their combined shares of applications and recognised decisions; the remainder form **Other (OTH)**.
:::

<nav class="origin-jump" aria-label="Choose a country of origin">
''' + country_links + '\n</nav>\n\n:::: {.origin-gallery}\n']
    parts[0] = parts[0].replace('::: {.callout-note', overview + '::: {.callout-note', 1)
    manifest = []
    for (code, name, _), image in zip(table.rows, images):
        filename = code.lower() + ".png"
        content = base64.b64decode(image, validate=True)
        (assets / filename).write_bytes(content)
        alt = f"{name}: receiving-country shares of applications and recognised decisions, with percentage-point differences, 2000 to 2025."
        parts.append(f'''::: {{.origin-card}}
## {name} {{#origin-{code.lower()}}}

![{name}: applications and recognised decisions by receiving country.](assets/origins/{filename}){{#fig-origin-{code.lower()} fig-alt="{escape(alt, quote=True)}" loading="lazy"}}

[Open full-size chart](assets/origins/{filename}) · Origin code: **{code}**
:::
''')
        manifest.append({"origin": code, "name": name, "file": "assets/origins/" + filename,
                         "sha256": hashlib.sha256(content).hexdigest()})
    parts.append('''::::

## Reading the colours and country codes

The legend above each chart names the featured receiving countries using ISO codes. **OTH** collects destinations outside that profile's featured six. A destination's colour remains consistent across profiles, but colours do not indicate better or worse outcomes.

Shares can change with source coverage, reporting units, procedures, and the mix of claims. Some years have little or no recorded volume. These charts do not track application cohorts or explain the causes of differences between destinations.

[Methods and source definitions](methods.qmd) · [Explore a receiving country's annual totals](explore.qmd) · [Original analysis notebook](https://github.com/aloysius109/python-charts/blob/main/UNHCRData.ipynb)
''')
    (DEST / "origins.qmd").write_text("\n".join(parts), encoding="utf-8")
    (assets / "manifest.json").write_text(json.dumps({
        "executed_code_sha256": digest, "period": [2000, 2025], "profiles": manifest
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("Prepared 20 country-of-origin profiles from the saved notebook, preserving its country order and colours.")


if __name__ == "__main__":
    main()
