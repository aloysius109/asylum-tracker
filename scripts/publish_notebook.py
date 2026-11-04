"""Export the complete executed analysis as a static GitHub Pages report."""
import copy
import hashlib
import json
import re
from pathlib import Path

import nbformat
from nbconvert import HTMLExporter
from traitlets.config import Config

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
WIDGET_VIEW = "application/vnd.jupyter.widget-view+json"
WIDGET_STATE = "application/vnd.jupyter.widget-state+json"


def static_widget_outputs(model_id, states, seen=None):
    """Extract saved initial Output-widget content, without pretending callbacks run."""
    seen = set() if seen is None else seen
    if model_id in seen:
        return []
    seen.add(model_id)
    state = states.get(model_id, {}).get("state", {})
    outputs = [nbformat.from_dict(output) for output in state.get("outputs", [])]
    for child in state.get("children", []):
        if isinstance(child, str) and child.startswith("IPY_MODEL_"):
            outputs.extend(static_widget_outputs(child.removeprefix("IPY_MODEL_"), states, seen))
    return outputs


def main():
    notebook = nbformat.read(ROOT / "UNHCRData.ipynb", as_version=4)
    nbformat.validate(notebook)
    states = notebook.metadata.get("widgets", {}).get(WIDGET_STATE, {}).get("state", {})
    source_cells = [cell for cell in notebook.cells if cell.cell_type == "code"]
    if any(cell.execution_count is None for cell in source_cells):
        raise ValueError("Every code cell must be executed before publication.")
    fingerprint = hashlib.sha256(json.dumps([cell.source for cell in source_cells], ensure_ascii=False).encode("utf-8")).hexdigest()
    if notebook.metadata.get("executed_code_sha256") != fingerprint:
        raise ValueError("Code changed since its verified execution; rerun scripts/execute_notebook.py.")
    for cell in source_cells:
        if any(output.output_type == "error" for output in cell.outputs):
            raise ValueError("Notebook contains saved execution errors.")
    notebook = copy.deepcopy(notebook)
    for cell in notebook.cells:
        if cell.cell_type != "code":
            continue
        converted = []
        for output in cell.outputs:
            if WIDGET_VIEW in output.get("data", {}):
                model_id = output.data[WIDGET_VIEW]["model_id"]
                converted.extend(static_widget_outputs(model_id, states))
            else:
                converted.append(output)
        if "kernel-widget" in cell.metadata.get("tags", []):
            converted.insert(0, nbformat.v4.new_output("display_data", data={
                "text/html": '<p class="static-note">Static initial view. To change the selection, open the notebook with a running Jupyter kernel.</p>'
            }))
        if any(output.output_type == "error" for output in converted):
            raise ValueError("A widget callback contains a saved error.")
        # Keep complete source and preparation outputs available in expandable panels.
        if "technical" in cell.metadata.get("tags", []) and converted:
            converted.insert(0, nbformat.v4.new_output("display_data", data={
                "text/html": '<span class="technical-marker" hidden></span>'
            }))
        cell.outputs = converted
        # Give static chart images an accessible description from the source heading.
        heading = cell.source.splitlines()[0].lstrip("# %").strip() if cell.source else "Analysis chart"
        for output in converted:
            if "image/png" in output.get("data", {}):
                output.setdefault("metadata", {})["alt"] = heading
    notebook.metadata.pop("widgets", None)
    config = Config()
    config.ExtractOutputPreprocessor.enabled = True
    config.HTMLExporter.exclude_input_prompt = True
    config.HTMLExporter.exclude_output_prompt = True
    config.HTMLExporter.embed_images = False
    exporter = HTMLExporter(config=config, template_name="lab")
    body, resources = exporter.from_notebook_node(notebook, resources={
        "metadata": {"name": "Understanding asylum applications, decisions, and pending claims"},
        "unique_key": "asylum-report",
        "output_files_dir": "assets/report",
    })
    assets = resources.get("outputs", {})
    for filename, content in assets.items():
        target = (DOCS / filename).resolve()
        if not target.is_relative_to(DOCS.resolve()):
            raise ValueError("Export path escapes docs/.")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    # Remove only this exporter's stale generated image files after a successful export.
    figure_directory = DOCS / "assets/report"
    if figure_directory.exists():
        retained = {(DOCS / filename).resolve() for filename in assets}
        for previous in figure_directory.glob("asylum-report_*.png"):
            if previous.resolve().is_relative_to(figure_directory.resolve()) and previous.resolve() not in retained:
                previous.unlink()
    navigation = """<nav class="report-nav" aria-label="Report navigation">
<a href="./">← Python Charts</a><span>Asylum statistics / Full analysis</span>
<a href="https://github.com/aloysius109/python-charts/blob/main/UNHCRData.ipynb">Notebook &amp; source ↗</a></nav>"""
    body = body.replace("</head>", '<link rel="stylesheet" href="assets/report.css"></head>')
    body = body.replace("<body", '<body', 1)
    start = body.index(">", body.index("<body")) + 1
    body = body[:start] + navigation + body[start:]
    script = """<script>
document.querySelectorAll('.jp-CodeCell').forEach(cell => {
  const input = cell.querySelector('.jp-Cell-inputWrapper');
  if (input) {
    const details = document.createElement('details');
    details.className = 'code-panel';
    const summary = document.createElement('summary');
    summary.textContent = 'Show Python source';
    details.append(summary);
    input.before(details);
    details.append(input);
  }
  if (cell.querySelector('.technical-marker')) {
    const output = cell.querySelector('.jp-Cell-outputWrapper');
    if (output) {
      const details = document.createElement('details');
      details.className = 'preparation-panel';
      const summary = document.createElement('summary');
      summary.textContent = 'Data preparation, coverage & provenance';
      details.append(summary);
      output.before(details);
      details.append(output);
    }
  }
});
document.querySelectorAll('img').forEach(img => {
  img.loading = 'lazy';
  if (!img.alt || img.alt === 'No description has been provided for this image') {
    const cell = img.closest('.jp-CodeCell');
    const source = cell && cell.querySelector('.jp-InputArea');
    img.alt = source ? source.textContent.trim().split('\\n')[0].replace(/^#\\s*%*\\s*/, '') : 'Chart from the asylum analysis';
  }
});
</script>"""
    body = re.sub(r'<img(?![^>]*\bloading=)', '<img loading="lazy"', body)
    body = body.replace("</body>", script + "</body>")
    DOCS.mkdir(exist_ok=True)
    (DOCS / "asylum-analysis.html").write_text(body, encoding="utf-8")
    print(f"Published full report with {len(source_cells)} executed code cells and {len(assets)} exported figures.")


if __name__ == "__main__":
    main()
