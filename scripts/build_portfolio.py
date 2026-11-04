"""Refresh the curated GitHub Pages assets from verified notebook outputs."""
import base64
import os
from pathlib import Path
import runpy
import shutil
import tempfile

import nbformat

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
CHARTS = {
    "Annual Person and Case Applications and Decisions since 2000": "annual-asylum-flows.png",
    "Combined Decision Outcome Rates 2000": "decision-outcomes.png",
    "Last calendar year: plot Top 20 application volumes": "receiving-countries.png",
}


def main():
    notebook = nbformat.read(ROOT / "UNHCRData.ipynb", as_version=4)
    cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if any(cell.execution_count is None for cell in cells):
        raise ValueError("Execute every notebook cell before refreshing the portfolio.")
    if any(output.output_type == "error" for cell in cells for output in cell.outputs):
        raise ValueError("Notebook has error outputs; run scripts/execute_notebook.py first.")
    images = {}
    for heading, filename in CHARTS.items():
        matches = [cell for cell in cells if heading in cell.source.splitlines()[0]]
        if len(matches) != 1:
            raise ValueError(f"Expected one chart cell for {heading!r}.")
        outputs = [output.data["image/png"] for output in matches[0].outputs
                   if output.output_type in ("display_data", "execute_result")
                   and "image/png" in output.data]
        if len(outputs) != 1:
            raise ValueError(f"Expected one PNG output for {heading!r}.")
        images[filename] = base64.b64decode(outputs[0], validate=True)

    # Generate the map from its source rather than publishing an arbitrary artifact.
    previous_directory = Path.cwd()
    previous_skip = os.environ.get("SKIP_MAP_PNG")
    os.environ["SKIP_MAP_PNG"] = "1"
    try:
        with tempfile.TemporaryDirectory() as work:
            try:
                os.chdir(work)
                runpy.run_path(str(ROOT / "FoliumNASASpaceCenter.py"), run_name="__main__")
                (DOCS / "maps").mkdir(parents=True, exist_ok=True)
                shutil.copy2(Path(work) / "NASA_JSC.html", DOCS / "maps/nasa-johnson-space-center.html")
            finally:
                os.chdir(previous_directory)
    finally:
        if previous_skip is None:
            os.environ.pop("SKIP_MAP_PNG", None)
        else:
            os.environ["SKIP_MAP_PNG"] = previous_skip
    (DOCS / "assets").mkdir(parents=True, exist_ok=True)
    for filename, content in images.items():
        (DOCS / "assets" / filename).write_bytes(content)
    (DOCS / ".nojekyll").touch()
    print("Refreshed three charts and the NASA map in docs/.")


if __name__ == "__main__":
    main()
