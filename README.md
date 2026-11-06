# Python Data Visualizations & Analytics

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Matplotlib](https://img.shields.io/badge/Library-Matplotlib-orange.svg)](https://matplotlib.org/)
[![Folium](https://img.shields.io/badge/Library-Folium-green.svg)](https://python-visualization.github.io/folium/)
[![Pandas](https://img.shields.io/badge/Library-Pandas-150458.svg)](https://pandas.pydata.org/)
[![License](https://img.shields.io/badge/License-MIT-lightgrey.svg)](LICENSE)

A collection of publication-quality data visualization projects, automated analytics pipelines, and interactive geospatial maps built in Python.

---

## Highlights

### 1. Global Asylum & Refugee Analytics (`UNHCRData.py` / `UNHCRData.ipynb`)
An end-to-end analytics script that interfaces with the **UNHCR Population Statistics API** (`https://api.unhcr.org/population/v1`) to download, normalize, analyze, and visualize global asylum application and decision trends from 2000 to the latest available reporting year.

**Key Features:**
* **API Integration & Smart Caching:** Automatically downloads country-level application and decision datasets, extracts in-memory ZIP streams, and maintains local data integrity.
* **Statistical Normalization:** Applies official UNHCR case-to-person multiplier rules (e.g. UK and US case size adjustments) to ensure accurate cross-country comparisons.
* **Decision Outcome Metrics:** Computes grant rates, complementary protection rates, refusal rates, and administrative backlog indicators.
* **Publication-Quality Chart Suite:**
  * **Global Share:** Donut/pie charts showing application distributions between the Top 20 receiving nations and the rest of the world.
  * **Time-Series Trends:** Multi-line trend comparisons across leading asylum-receiving countries.
  * **Decision Outcomes:** Horizontal and stacked bar charts detailing application volumes alongside decision breakdown rates (`G` Grant, `OP` Other Protection, `R` Refused, `C` Closed).
  * **Country Profiles:** Detailed deep dives for key destination nations including the United Kingdom, United States, Germany, France, Spain, and more.

#### Visual Gallery

**Application Volumes: Top 20 vs. All Other Countries**
![AppVolumesPieChart](https://github.com/aloysius109/PythonMatplotlib/assets/92214796/a90fe8b0-aa5d-47e9-b81b-007657d8f4f8)

**Multi-Year Application Volume Trends**
![Applications2017To23](https://github.com/aloysius109/PythonMatplotlib/assets/92214796/a07a87f9-d2d3-41dd-a7cb-b8bfbfc4528a)

---

### 2. Interactive Geospatial Mapping (`Folium*.py`)
Interactive map visualizations created using **Folium**, **Leaflet**, and geospatial GeoJSON layers:

* **UK Small Boat Arrivals (`FoliumSmallBoats2022-24.py`):**
  * Choropleth world map combining UK Home Office migration data with global country polygon GeoJSON boundaries.
  * Custom centroid coordinates, styled `DivIcon` HTML annotations, highlighted regional callouts (e.g. Albania), and custom map styling (`Esri.WorldShadedRelief`).
* **NASA Johnson Space Center Location (`FoliumNASASpaceCenter.py`):**
  * High-precision coordinates, custom radius overlays, popups, and HTML title headers with raster screenshot export options.

---

## Repository Structure

```text
Python Charts/
??? UNHCRData.py                  # Automated UNHCR API ingestion & Matplotlib chart generation (supports offline mode)
??? UNHCRData.ipynb               # Interactive Jupyter Notebook for exploratory analysis
??? FoliumSmallBoats2022-24.py     # Interactive Choropleth map for UK migration statistics
??? FoliumNASASpaceCenter.py      # Interactive location map for NASA JSC
??? asylum-applications.csv       # Bundled UNHCR asylum applications export (for clean/offline environments)
??? asylum-decisions.csv          # Bundled UNHCR asylum decisions export (for clean/offline environments)
??? world-countries.json          # GeoJSON polygon boundaries for country mapping
??? unhcr_and_geojson_data.zip    # Bundled archive containing the offline datasets
??? footnotes.csv                 # Reference metadata and footnotes for multiplier rules
??? persons_of_concern.csv        # Supplementary population statistics
??? requirements.txt              # Project dependencies
??? .gitignore                    # Git ignore configuration
??? README.md                     # Project documentation & visual showcase
```

---

## Offline & Clean Environment Support

All scripts in this repository support zero-network / offline execution:
* **UNHCR Data Scripts (`UNHCRData.py`, `UNHCRData.ipynb`):** Check for local CSV exports (`asylum-applications.csv`, `asylum-decisions.csv`) and cached datasets before attempting live API calls.
* **Folium Mapping (`FoliumSmallBoats2022-24.py`):** Bundles `world-countries.json` locally and provides built-in fallback data for UK migration statistics.
* **Archive Distribution:** `unhcr_and_geojson_data.zip` is provided as an all-in-one package containing the applications, decisions, and GeoJSON datasets.

---

## Quickstart & Installation

### 1. Clone the Repository
```bash
git clone https://github.com/aloysius109/python-charts.git
cd python-charts
```

### 2. Create and Activate a Virtual Environment
```bash
# On Windows
python -m venv venv
.\venv\Scripts\Activate.ps1

# On macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Visualizations
* **Generate all UNHCR Charts:**
  ```bash
  python UNHCRData.py
  ```
* **Generate Interactive Folium Maps:**
  ```bash
  python FoliumSmallBoats2022-24.py
  python FoliumNASASpaceCenter.py
  ```

---

## Data Sources & Attribution

* **UNHCR:** [UNHCR Refugee Data Finder](https://www.unhcr.org/refugee-statistics/) / Population Statistics API.
* **UK Home Office:** [Statistics relating to the Illegal Migration Act](https://www.gov.uk/government/statistics/statistics-relating-to-the-illegal-migration-bill).
* **GeoJSON:** [Python Visualization Folium Data Repository](https://github.com/python-visualization/folium).

## Automated offline verification

From the repository root with Python 3.12:

```bash
python -m pip install -r requirements.txt
python -X utf8 scripts/verify_examples.py
```

This runs all three Python scripts with network connections disabled, checks both
HTML maps and the UNHCR chart exports, and copies outputs to `artifacts/`.
It uses the tracked UNHCR CSV snapshots and `world-countries.json`; keep these
files in the repository. Small-boats arrivals and coordinates use the script's
existing embedded fallback when the optional source spreadsheet is absent.
This check validates execution, not the accuracy of those fallback figures.
Map HTML generation is offline; displaying map tiles and remote JavaScript in a
browser still needs internet. Browser-dependent map PNG screenshots are skipped.

Pushes, pull requests, and manual runs trigger `.github/workflows/examples.yml`.
Download charts and HTML maps from its `example-outputs` artifact after a successful
run. The checked-in notebook is an exploratory companion; CI runs the Python scripts.

### Refresh the saved notebook outputs

```bash
python -X utf8 scripts/execute_notebook.py
```

This clears saved outputs in memory and executes every cell in a fresh Python
kernel. The notebook is replaced only after all cells pass, so a failed run cannot
publish a partially executed notebook. Temporary copies of the input CSVs and any
local caches keep generated files separate from the source files. The notebook's
observed-stock charts query UNHCR and Eurostat; this full refresh needs internet,
unlike the offline Python-script checks above. Parquet cache support and notebook
execution dependencies are included in `requirements.txt`.

The examples use Matplotlib, Folium, and Jupyter widgets. This repository does not
include a Plotly Dash application.

## Public chart portfolio

Visit **[Python Charts](https://aloysius109.github.io/python-charts/)** for a curated
selection of notebook charts and the interactive NASA Johnson Space Center map.
GitHub Pages publishes the static `docs/` folder from `main`.

To update the published snapshots after a successful notebook refresh:

```bash
python -X utf8 scripts/execute_notebook.py
python -X utf8 scripts/build_portfolio.py
```

Review the resulting charts, then commit and push `docs/` along with the updated
notebook. The build script selects three verified notebook outputs and regenerates
the NASA HTML map from its Python source. It refuses notebooks with missing
execution counts or saved errors. The existing example-check workflow uploads its
outputs as artifacts; it does not update or deploy the curated Pages files.

The portfolio uses aggregate public UNHCR snapshots and a geographic location
example. Maps require external JavaScript and map-tile services. No private work
files or client datasets are included in `docs/`.

## Complete asylum-statistics report

Read the **[full published analysis](https://aloysius109.github.io/python-charts/asylum-analysis.html)**.
It includes the complete notebook narrative and charts, expandable Python source,
and saved initial views of the Jupyter controls. Changing dropdown selections
requires a live Jupyter kernel; GitHub Pages does not execute Python.

The publication distinguishes persons from cases, recognised shares of all
recorded decisions from substantive-decision recognition rates, and observed
pending stocks from annual flow differences. Main worldwide summaries use
persons-reported records. Mixed-unit country selections remain exploratory and
are identified in the text. Decisions without current-year matching applications
are retained, and unsupported case-to-person estimates and modelled backlog
allocations have been removed. Eurostat pending observations are labelled as
all-instance pending persons.

To refresh the complete publication and gallery:

```bash
python -m pip install -r requirements.txt
python -X utf8 scripts/execute_notebook.py
python -X utf8 scripts/publish_notebook.py
python -X utf8 scripts/build_portfolio.py
```

Review and commit the updated notebook, `docs/asylum-analysis.html`,
`docs/assets/report/`, and gallery assets together. The exporter refuses unexecuted
cells and saved errors, including failures captured in widget callbacks. Input
hashes, source coverage, and cache provenance appear in the notebook. Live stock
sources can change between executions, so retain the executed version used for
any published figure.

## Interactive Quarto publication and scheduled refreshes

The publication is served under `/asylum/`, with the country explorer at
`/asylum/explore.html`. It searches receiving countries, separates persons and
cases, and provides chart-data CSV downloads, country-filtered UNHCR links, and
source-snapshot ZIP downloads with provenance.

From the repository root:

    python scripts/prepare_quarto_preview.py
    python scripts/prepare_origin_gallery.py
    python scripts/prepare_additional_origins.py
    python scripts/style_publication_charts.py
    python scripts/refresh_explorer_data.py --refresh
    quarto preview quarto-preview

Use `--bundled` instead of `--refresh` for an offline demonstration. That mode is
labelled as a bundled snapshot, with no claim of a fresh API download.

The local `.github/workflows/publish-quarto.yml` has been changed to a
**review-only** source-check workflow. Once explicitly pushed/enabled, it checks
weekly on Monday at 06:17 UTC, on relevant main-branch pushes and via its manual
Run workflow button. It saves the `unhcr-refresh-review` artifact for 30 days.
It has read-only repository permissions and no Pages deployment job. Scheduling
can be delayed. These local changes have not activated any remote schedule.

For a safe source check, use `python scripts/refresh_report.py --refresh` rather
than overwriting the report's explorer data in place; see the review process below.

The narrative chapter is a fixed notebook edition. Refreshing the explorer does
not rewrite that chapter; new editions require updating the input lock and dates.

### Country-of-origin chart gallery

The Quarto Origins & destinations page (`/asylum/origins.html`) reproduces all
20 multicoloured country-of-origin profiles from the verified notebook. Each
profile shows receiving-country shares of applications and recognised decisions,
plus their percentage-point difference. Charts retain the notebook colours and
open at full size. They are the fixed 2000?2025 edition and retain its exploratory
mixed-unit reporting conventions, explained on the page.

    python scripts/prepare_origin_gallery.py
    python scripts/prepare_additional_origins.py
    python scripts/style_publication_charts.py
    quarto render quarto-preview

The reviewed edition regenerates its gallery from the pinned notebook outputs;
the refresh checker does not replace those with independently downloaded data.

### Additional origin profiles

The Origins & destinations dropdown covers all 215 origins in the pinned
2000?2025 application snapshot, with 195 additional profiles beyond the featured
20. It reuses the verified notebook plotting function and destination palette.
The original saved figures remain unchanged. Additional images are generated by
`python scripts/prepare_additional_origins.py`, cached locally and in Actions, and
loaded in the browser only when selected. The generated image directory is
excluded from Git. A changed notebook/input fingerprint requires deliberate review
rather than silently updating the publication edition.


### Reproducible report commentary

After preparing or refreshing the report datasets and galleries, run
`python scripts/prepare_commentary.py` before `quarto render quarto-preview`.
This validates the pinned application/decision files and regenerates the Top 20
receiving and origin profiles, worldwide analysis, UK/Rwanda comparison and
grant-rate commentary. It attaches the profiles to the existing gallery cards
without duplicate includes. Grant commentary uses the same saved refreshed ZIP
as the Grant Rates page; fixed gallery commentary uses the pinned edition.
The generated `quarto-preview/data/commentary-evidence.json` records annual
counts, source fingerprints and eligible recent grant-rate comparisons.
These are descriptive comparisons, with missing/reconciled-year rules explicit;
they do not infer policy effects or predict future flows.


### Executive summary and processing assessment

Run `python scripts/prepare_report_summary.py` after the gallery/data generators
and `prepare_commentary.py`, before rendering Quarto. It validates all 20
country/year chart counts against the pinned CSVs, creates the front-page
summary and a weighted 2021-2025 processing assessment, and attaches the latter
to `productivity.qmd`. The detailed former front page is retained at
`worldwide.qmd`. Classification rules, annual variation, closures and incomplete
coverage are explained beside the chart/table; this is not an efficiency ranking.
The generated CSV/JSON in `quarto-preview/data/processing-assessment.*` retain
unrounded period ratios and paired-year counts. Running the generator again
refreshes the summary without duplicating the assessment include.


## Review-first UNHCR refresh process

This is a working **source-change review process**, not yet an automatic migration
of the entire notebook-based report to a new edition. Its preview recalculates
worldwide figures, pending stock, country/year activity, substantive protection
rates, revision comparisons and candidate Top 20 rankings from the candidate
sources. It does not claim that the authored report has been rebuilt.

From `Python Charts`, run:

    python scripts/refresh_report.py --refresh

For an offline rehearsal with the accepted data:

    python scripts/refresh_report.py --offline

Each run creates a new directory under `artifacts/refresh-review/`. The command
prints its path. An optional `--output PATH` specifies a **new** directory; an
existing directory is rejected. `READY.txt` marks a completed candidate. A failed
run writes `FAILED.json`, returns a failing exit code, and never replaces the
accepted data or report. Download/schema errors do not fall back to old data
labelled as new. Offline rehearsals explicitly say no new data was downloaded.

To open a completed run, serve that directory and open localhost:

    python -m http.server 4393 --bind 127.0.0.1 --directory "PATH_PRINTED_BY_COMMAND"

Open `http://localhost:4393/`. Extract a downloaded Actions artifact before serving
it the same way. The preview works offline, with local charts and embedded
country/year data. No source data is fetched when readers open it.

### What the check does

1. Verifies that accepted application/decision CSV fingerprints still match the
   input lock. It downloads both candidate datasets into the new run directory,
   plus the worldwide UNHCR asylum-seeker population series.
2. Reuses the explorer's schema, integer-count, reporting-unit, date-range and
   coverage-loss safeguards; also validates origin identifiers and population
   pagination, unique years, units and historical coverage.
3. Compares activity at year/receiving-country/origin/reporting-unit level, keeping
   unavailable records distinct from reported zero. Row reordering or splitting
   does not create spurious activity changes. Checks candidate Top 20 membership.
4. Builds a separate HTML review with new figures, accepted/candidate comparisons,
   an interactive country selector and CSV downloads. Source ZIPs, download times,
   hashes, new years and reconciliation issues are recorded in `audit.json`.

The request stops at the **previous calendar year**, so it does not collect
current-year provisional releases. A calendar-year return can still be incomplete.
A newly appearing year is flagged for edition migration even when only one of the
two activity sources has reported it. The headline year uses the shared endpoint;
pending stock retains its own year and persons unit.

### Adopting a candidate is a separate step

Review the source audit, revisions, coverage, classifications and rankings first.
Then rebuild an authored edition against the chosen candidate, including:

- Notebook-dependent origin charts and verified-input provenance.
- All fixed date labels, chart ranges, Top 20 selections and stock headlines.
- Summary, country commentary, processing assessments and grant-rate comparisons.
- UK comparison alignment, flags and map resources, and population-year joins.

The current 2000-2025 edition has explicit year/input locks. **Do not bypass those
locks or replace its CSVs beneath existing charts.** Generalising those generators
and validating a complete candidate edition remain necessary before full automatic
report rebuilding. This command intentionally does not perform that migration,
replace the accepted report, commit, push, or publish. Home Office and World Bank
snapshots have separate release schedules and are not refreshed by this UNHCR check.

Once the complete rebuilt edition has been checked, obtain explicit approval
before adopting or publishing it. The weekly workflow produces review artifacts
only; publication is not part of the refresh process.


## Publishing a reviewed report

The shareable report is at https://aloysius109.github.io/python-charts/asylum/.
The portfolio at https://aloysius109.github.io/python-charts/ links to it.

After a complete local render and review, run
`python scripts/stage_report_publication.py` to copy the exact HTML/assets into
`docs/asylum/` and record a SHA-256 publication manifest. Commit that snapshot
using `git add -f docs/asylum` (generated HTML is normally ignored). The manual
**Publish reviewed report** workflow validates the manifest/links and deploys
`docs/` without running the notebook or refreshing any data. It has no push or
scheduled trigger. Run it only for a reviewed release.

The independent **Check UNHCR data and prepare review preview** workflow remains
review-only. Its weekly source checks do not update the public report. Future
releases require a complete edition rebuild/review before staging and publishing.
