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
