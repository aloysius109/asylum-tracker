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

The first additional-profile build renders 195 images and can take a few minutes.
Subsequent builds reuse validated cached images. The dropdown covers all 215
origins in the fixed notebook edition, including the original gallery profiles.
