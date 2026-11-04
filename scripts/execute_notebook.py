"""Refresh saved notebook outputs only after a complete successful execution."""
from pathlib import Path
import shutil
import tempfile
import nbformat
from nbclient import NotebookClient

root = Path(__file__).resolve().parents[1]
source = root / "UNHCRData.ipynb"
notebook = nbformat.read(source, as_version=4)
for cell in notebook.cells:
    if cell.cell_type == "code":
        cell.outputs = []
        cell.execution_count = None

def progress(cell, cell_index, **kwargs):
    print(f"Executing cell {cell_index + 1}/{len(notebook.cells)}", flush=True)

with tempfile.TemporaryDirectory() as work:
    for name in ("asylum-applications.csv", "asylum-decisions.csv", "persons_of_concern.csv", "footnotes.csv"):
        shutil.copy2(root / name, Path(work) / name)
    if (root / "unhcr_cache").exists():
        shutil.copytree(root / "unhcr_cache", Path(work) / "unhcr_cache")
    client = NotebookClient(notebook, timeout=1200, kernel_name="python3",
                            resources={"metadata": {"path": work}},
                            on_cell_start=progress)
    client.execute()
    errors = [o for c in notebook.cells if c.cell_type == "code"
              for o in c.outputs if o.output_type == "error"]
    assert not errors
    nbformat.validate(notebook)
    nbformat.write(notebook, source)
    print("Saved successfully executed notebook", flush=True)
