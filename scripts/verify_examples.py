"""Run the bundled examples in an isolated directory without data downloads."""
import os
from pathlib import Path
import runpy
import shutil
import socket
import tempfile
from contextlib import contextmanager
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
os.environ["MPLBACKEND"] = "Agg"
os.environ["SKIP_MAP_PNG"] = "1"

def deny_network(*args, **kwargs):
    raise RuntimeError("Network disabled: examples must use bundled data")

socket.socket.connect = deny_network
socket.create_connection = deny_network

@contextmanager
def workspace():
    previous = Path.cwd()
    with tempfile.TemporaryDirectory() as work:
        try:
            yield work
        finally:
            os.chdir(previous)


with workspace() as work:
    os.chdir(work)
    for name in ("NASA_JSC", "SmallBoats"):
        script = "FoliumNASASpaceCenter.py" if name == "NASA_JSC" else "FoliumSmallBoats2022-24.py"
        runpy.run_path(str(ROOT / script), run_name="__main__")
        assert Path(name + ".html").stat().st_size > 1000
    runpy.run_path(str(ROOT / "UNHCRData.py"), run_name="__main__")
    charts = list(Path(work).glob("*.png"))
    assert len(charts) >= 10, "Expected UNHCR chart exports"
    out = ROOT / "artifacts"
    out.mkdir(exist_ok=True)
    for path in list(Path(work).glob("*.html")) + charts:
        shutil.copy2(path, out / path.name)
print("All chart scripts passed using bundled data.")
