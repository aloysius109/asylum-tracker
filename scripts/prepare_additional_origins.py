"""Extend the original gallery with on-demand profiles for every recorded origin."""
import argparse
import hashlib
from html import escape
import json
import os
from pathlib import Path
import re

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as mtick
import nbformat
import numpy as np
import pandas as pd
import pycountry

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "quarto-preview"
CACHE = DEST / "assets/origins/additional"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--notebook", type=Path, default=ROOT / "UNHCRData.ipynb")
    args = parser.parse_args()
    notebook = nbformat.read(args.notebook, as_version=4)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    code_hash = hashlib.sha256(json.dumps([cell.source for cell in cells], ensure_ascii=False).encode("utf-8")).hexdigest()
    lock = json.loads((DEST / "_inputs.json").read_text(encoding="utf-8"))
    if code_hash != lock["executed_code_sha256"] or code_hash != notebook.metadata.get("executed_code_sha256"):
        raise ValueError("Additional profiles require the pinned, verified notebook edition.")
    if any(cell.execution_count is None or any(o.output_type == "error" for o in cell.outputs) for cell in cells):
        raise ValueError("The notebook must have completed successfully.")
    for filename, expected in lock["inputs"].items():
        if hashlib.sha256((ROOT / filename).read_bytes()).hexdigest() != expected:
            raise ValueError(f"Snapshot changed: {filename}")
    featured = json.loads((DEST / "assets/origins/manifest.json").read_text(encoding="utf-8"))
    featured = {entry["origin"]: entry for entry in featured["profiles"]}
    apps = pd.read_csv(ROOT / "asylum-applications.csv")
    decisions = pd.read_csv(ROOT / "asylum-decisions.csv")
    year_to = min(int(apps.Year.max()), int(decisions.Year.max()))
    apps = apps.loc[apps.Year.between(2000, year_to)].copy()
    decisions = decisions.loc[decisions.Year.between(2000, year_to)].copy()
    codes = sorted(apps["Country of origin (ISO)"].dropna().unique())
    if any(not re.fullmatch("[A-Z]{3}", code) for code in codes):
        raise ValueError("Unexpected origin code; review source labels before creating paths.")
    names = {country.alpha_3: country.name for country in pycountry.countries}
    names["UNK"] = "Unknown"
    source_names = apps.drop_duplicates("Country of origin (ISO)").set_index("Country of origin (ISO)")["Country of origin"].to_dict()
    for code in codes:
        names.setdefault(code, source_names.get(code, code))
    # The notebook uses ISO lookup names and falls back to the code in chart titles.
    notebook_names = {country.alpha_3: country.name for country in pycountry.countries}
    notebook_names["UNK"] = "Unknown"
    destination_codes = sorted(set(
        pd.concat([apps["Country of asylum (ISO)"], decisions["Country of asylum (ISO)"]])
        .dropna().astype(str).loc[lambda values: values.str.fullmatch("[A-Z]{3}")]))
    palette = plt.get_cmap("turbo", len(destination_codes))
    colours = {code: mpl.colors.to_hex(palette(i)) for i, code in enumerate(destination_codes)}
    colours["OTHER"] = "#7A7A7A"
    plot_cell = next(cell for cell in cells if cell.source.startswith("def plot_origin_application_grant_comparison("))
    namespace = {
        "pd": pd, "np": np, "plt": plt, "mpl": mpl, "mtick": mtick,
        "UNapps": apps, "UNdecs": decisions, "last_calendar_year": year_to,
        "destination_colour_map": colours,
        "country_label": lambda code: notebook_names.get(code, code),
    }
    # Reuse verified selection and calculations; presentation colours are assigned per profile.
    exec(compile(plot_cell.source, "verified-notebook-origin-plot", "exec"), namespace)
    render_key = hashlib.sha256(json.dumps({
        "notebook": code_hash, "inputs": lock["inputs"],
        "matplotlib": mpl.__version__, "renderer": "origin-profile-v2-contrasting-local"
    }, sort_keys=True).encode()).hexdigest()
    CACHE.mkdir(parents=True, exist_ok=True)
    manifest_path = CACHE / "manifest.json"
    cached = json.loads(manifest_path.read_text(encoding="utf-8")) if manifest_path.exists() else {}
    previous = {entry["origin"]: entry for entry in cached.get("profiles", [])} if cached.get("render_key") == render_key else {}
    profiles = []
    needed = codes
    print(f"Preparing {len(codes)} contrasting origin profiles, including the {len(featured)} featured gallery countries.", flush=True)
    mpl.rcParams.update(mpl.rcParamsDefault)
    generated = 0
    original_show = plt.show
    try:
        for index, code in enumerate(needed, 1):
            path = CACHE / (code.lower() + ".png")
            old = previous.get(code)
            if old and path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == old["sha256"]:
                profiles.append(old)
            else:
                def save_profile(*args, **kwargs):
                    figure = plt.gcf()
                    for artist in figure.findobj(match=mpl.text.Text):
                        artist.set_fontweight("normal")
                    figure.savefig(path, dpi=100, bbox_inches="tight")
                plt.show = save_profile
                class ProfileColours(dict):
                    def __missing__(self, destination):
                        palette = ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#D55E00", "#56B4E9"]
                        colour = palette[len(self)-1]
                        self[destination] = colour
                        return colour
                namespace["destination_colour_map"] = ProfileColours({"OTHER": "#929292"})
                namespace["plot_origin_application_grant_comparison"](code)
                plt.close("all")
                if not path.exists() or path.stat().st_size < 1000:
                    raise ValueError(f"Profile did not render: {code}")
                profiles.append({
                    "origin": code, "name": names[code],
                    "file": "assets/origins/additional/" + path.name,
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                })
                generated += 1
            if index % 10 == 0 or index == len(needed):
                print(f"Additional profiles ready: {index}/{len(needed)} ({generated} newly rendered).", flush=True)
    finally:
        plt.show = original_show
        plt.close("all")
    manifest_path.write_text(json.dumps({
        "render_key": render_key, "period": [2000, year_to], "profiles": profiles
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Keep featured image paths stable while publishing the new colours everywhere.
    for entry in profiles:
        if entry["origin"] in featured:
            old = featured[entry["origin"]]
            (DEST / old["file"]).write_bytes((DEST / entry["file"]).read_bytes())
            old["sha256"] = entry["sha256"]
    featured_manifest = DEST / "assets/origins/manifest.json"
    featured_data = json.loads(featured_manifest.read_text(encoding="utf-8"))
    featured_data["profiles"] = list(featured.values())
    featured_data["presentation"] = "contrasting colours within each profile; underlying data unchanged"
    featured_manifest.write_text(json.dumps(featured_data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    profiles = [entry for entry in profiles if entry["origin"] not in featured]
    all_profiles = {**featured, **{entry["origin"]: entry for entry in profiles}}
    options = ['<option value="">Choose a country of origin...</option>']
    for label, group in [("Additional origins", profiles), ("Original gallery", list(featured.values()))]:
        options.append(f'<optgroup label="{label}">')
        for entry in sorted(group, key=lambda entry: entry["name"]):
            options.append(
                f'<option value="{entry["origin"]}" data-profile-src="{escape(entry["file"], quote=True)}?v=contrast2" '
                f'data-profile-name="{escape(entry["name"], quote=True)}">'
                f'{escape(entry["name"])} ({entry["origin"]})</option>')
        options.append("</optgroup>")
    selector = f'''## Explore another country of origin

Choose from **{len(all_profiles)} recorded origins** to see where applications were made and where refugee status was recognised. The featured 20 profiles are also available in the dropdown, with the same colours and three-panel layout.

<div class="origin-picker">
<label for="origin-profile-select">Country of origin</label>
<select id="origin-profile-select" aria-controls="origin-selected-profile">
{chr(10).join(options)}
</select>
</div>
<p id="origin-profile-status" class="origin-selection-status" role="status" aria-live="polite">Choose an origin to display its profile.</p>
<section id="origin-selected-profile" class="origin-selected-profile" hidden>
<h3 id="origin-selected-title"></h3>
<a id="origin-selected-image-link" target="_blank" rel="noopener">
<img id="origin-selected-image" alt="" width="1590" height="1510" loading="eager" hidden>
</a>
<p><a id="origin-selected-full" target="_blank" rel="noopener">Open full-size chart</a> · <a id="origin-selected-download" download>Download chart (PNG)</a></p>
</section>

## Gallery: Top 20 reported origins

The **20 origins with the largest combined reported application volume, 2000-2025**, in the notebook edition. This includes **Unknown origin**. The ranking combines persons- and case-reported values: it describes application events in mixed reporting units, not unique applicants or harmonised person counts.
'''
    page = DEST / "origins.qmd"
    text = page.read_text(encoding="utf-8")
    text = text.replace("the same receiving country keeps its colour across the collection", "each receiving country keeps its colour across the three panels of that profile")
    text = text.replace("A destination's colour remains consistent across profiles, but colours do not indicate better or worse outcomes.", "Six contrasting colours distinguish the featured destinations within each profile; Other is grey. Colours can differ between profiles, so use each chart's ISO-code legend when comparing countries. Colours do not indicate better or worse outcomes.")
    text = text.replace("The figures reproduce the", "The figures use the data and calculations from the")
    text = re.sub(r'^subtitle: ".*"$',
                  f'subtitle: "Explore all {len(all_profiles)} recorded origins and their receiving-country profiles."',
                  text, count=1, flags=re.MULTILINE)
    marker = '<nav class="origin-jump"'
    if marker not in text:
        raise ValueError("Regenerate the featured gallery before adding the dropdown.")
    # Keep repeated preparation runs idempotent after the chart cache is restored.
    start = text.find("## Explore another country of origin")
    if start >= 0:
        end = text.index(marker, start)
        text = text[:start] + text[end:]
    text = text.replace('\n<script type="module" src="assets/origin-selector.js"></script>\n', '')
    text = text.replace(marker, selector + "\n" + marker, 1)
    text = re.sub(r"(assets/origins/[a-z]{3}\.png)(?!\?v=contrast2)", r"\1?v=contrast2", text)
    text += '\n<script type="module" src="assets/origin-selector.js"></script>\n'
    page.write_text(text, encoding="utf-8")
    print(f"Country dropdown ready with {len(all_profiles)} profiles.", flush=True)


if __name__ == "__main__":
    main()
