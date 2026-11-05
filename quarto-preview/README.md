# Quarto publication prototype

A chart-led publication with worldwide trends, a country explorer, and a methods page.

From your main Python workspace folder, preview it in PowerShell:

    & "$env:LOCALAPPDATA\Programs\Quarto\bin\quarto.cmd" preview ".\Python Charts\quarto-preview"

Quarto opens the site in your browser and refreshes it when you edit a .qmd file.
Stop the preview with Ctrl+C. Edit index.qmd for the chapter, methods.qmd for
methodology, and theme.scss for presentation.

To refresh the figures and data-derived passages, run this from the repository:

    python scripts/prepare_quarto_preview.py

The sample is pinned to the notebook edition and input hashes in _inputs.json.
For a new analytical edition, review and update that lock and the authored date
range deliberately. Rendered files live in _site/ and are excluded from Git.

Explorer data is refreshed using python scripts/refresh_explorer_data.py --refresh.
Weekly deployment is configured in .github/workflows/publish-quarto.yml.

The Origins & destinations page shows all 20 coloured country-of-origin profiles.
Regenerate its figures from the verified notebook using:

    python scripts/prepare_origin_gallery.py

To populate the dropdown for additional origins, run:

    python scripts/prepare_origin_gallery.py
    python scripts/prepare_additional_origins.py
    python scripts/style_publication_charts.py

The first additional-profile build renders 195 images and can take a few minutes.
Subsequent builds reuse validated cached images. The dropdown covers all 215
origins in the fixed notebook edition, including the original gallery profiles.

Processing Productivity and the combined-unit receiving-country gallery are generated
by python scripts/style_publication_charts.py from pinned inputs. Productivity is
decisions per 100 applications, with a centred three-year mean; source values
and both ratio series are downloadable as data/processing-productivity.csv.

Origin profiles use six contrasting destination colours within each profile,
with grey for Other. Colours can differ between origins; consult each legend.
All 215 profiles are rendered with the verified notebook calculation function
and cached by input hashes and renderer version.

Generate the origin/time comparisons, 2025 application/outcome panels, and
processing-gap galleries with python scripts/prepare_processing_detail.py.
The illustrative zero-opening balance is not an observed backlog.

Generate interactive Top 20 receiving/origin maps with
python scripts/prepare_application_maps.py. Bundled boundaries cover 39 of the
40 selected entries; Unknown origin is listed separately. Maps use identical
circle-area scales and include exact tables and a CSV alternative.

Build the Top 3 application/grant-origin year explorer after refreshing
Country Explorer data: python scripts/prepare_origin_year_explorer.py.
It reads the exact source ZIP and checks every country-year aggregate
against explorer.json. Locally bundled flags are from FlagCDN; unknown or
unmapped origins retain readable country codes without a flag.

UK comparison: python scripts/prepare_uk_comparison.py reads the saved official
Home Office Asy_00a ODS workbook, checks its SHA-256, and extracts calendar years
2010-2025 separately from the year-ending-June-2026 column. Published grant
rates refer to main applicants; people counts include dependants. UNHCR
comparison rows are restricted to GBR, FI, P. No notebook execution is required.

Rwanda context on the UK page: python scripts/prepare_rwanda_context.py
uses pinned UNHCR inputs to chart Rwanda's own asylum system, separately
from the discontinued UK partnership. Policy history links to Home Office
primary sources; no UK-relocation outcomes are inferred from Rwanda totals.

Population comparisons: python scripts/prepare_population_comparison.py joins
saved World Bank SP.POP.TOTL estimates to the same-year Country Explorer rows.
Regional aggregates are excluded and missing populations are never filled from
other years. Main per-resident comparisons use person-reported records; a
separate combined-unit option remains exploratory. Raw population responses,
source hashes, and unrounded per-unit ratios are downloadable.

Small-boats history: python scripts/prepare_small_boats.py --refresh discovers
the current official ODS download through the GOV.UK Content API, validates
the daily series and latest-seven-days feed, and rebuilds local snapshots.
Without --refresh it rebuilds offline from saved files. The UK page
automatically attempts the official CORS-enabled daily API and offers a refresh
button; a failed request keeps dated fallback figures. Live updates do not
change historical snapshots or publish the site.

Small-boat nationality map: python scripts/prepare_small_boat_map.py reads
the saved official IER_D01 workbook, filters small-boat arrivals, and sums
age/sex rows once. Selectable periods include calendar years, January-June
2026, the year ending June 2026, and all available data. Special or unlocated
categories remain in the table and total; no route or departure point is inferred.

Small-boat grant rates: python scripts/prepare_small_boat_grants.py reads
the official Asy_02c/Asy_02d and Data_IER_D03 sheets. Published decision-date
rates are kept separate from linked arrival-cohort rates. Main-applicant
labels are case-normalised, dependants are excluded, and grants plus refusals
form the denominator. Pending/withdrawn/administrative outcomes remain visible.
