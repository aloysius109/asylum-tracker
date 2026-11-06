"""Stage or validate the exact reviewed Quarto HTML for manual Pages publication."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "quarto-preview/_site"
DEST = ROOT / "docs/asylum"
REQUIRED = ["index.html","worldwide.html","methods.html","explore.html","origins.html",
            "productivity.html","grants.html","maps.html","uk.html","population.html"]
MANIFEST = "publication.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(root, relative):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError(f"Unsafe publication path: {relative}")
    return path


class Links(HTMLParser):
    def __init__(self):
        super().__init__(); self.refs=[]
    def handle_starttag(self,tag,attrs):
        for key,value in attrs:
            if key in ["src","href","data-profile-src"] and value:
                self.refs.append(value)


def check_links(root):
    broken=[]
    for page in root.rglob("*.html"):
        parser=Links(); parser.feed(page.read_text(encoding="utf-8"))
        for reference in parser.refs:
            url=urlsplit(reference)
            if url.hostname in ["localhost","127.0.0.1"]:
                broken.append((page.relative_to(root).as_posix(),reference));continue
            if url.scheme or url.netloc or not url.path:
                continue
            # Root-absolute project links are checked against the GitHub Pages project prefix.
            relative=unquote(url.path)
            if relative.startswith("/asylum-tracker/asylum/"):
                target=root/relative.removeprefix("/asylum-tracker/asylum/")
            elif relative.startswith("/"):
                continue
            else:
                target=page.parent/relative
            if not target.exists():
                broken.append((page.relative_to(root).as_posix(),reference))
    if broken:
        raise ValueError("Broken local publication links: "+repr(broken[:20]))


def validate(root=DEST):
    for name in REQUIRED:
        if not (root/name).is_file():
            raise ValueError(f"Required page missing: {name}")
    manifest=json.loads((root/MANIFEST).read_text(encoding="utf-8"))
    actual={p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p.name!=MANIFEST}
    if actual!=set(manifest['files']):
        raise ValueError("Publication files do not match the reviewed manifest")
    for relative,expected in manifest['files'].items():
        path=safe_path(root,relative)
        if path.is_symlink() or digest(path)!=expected:
            raise ValueError(f"Reviewed file changed: {relative}")
    check_links(root)
    print(f"Verified {len(actual)} reviewed publication files and their local HTML links.")


def stage():
    if not SOURCE.is_dir():
        raise ValueError("Render and review the Quarto report first")
    for name in REQUIRED:
        if not (SOURCE/name).is_file():
            raise ValueError(f"Render the whole report first: missing {name}")
    files=[p for p in SOURCE.rglob('*') if p.is_file()]
    if any(p.is_symlink() for p in files):
        raise ValueError("Publication cannot include symbolic links")
    check_links(SOURCE)
    previous=json.loads((DEST/MANIFEST).read_text(encoding="utf-8"))['files'] if (DEST/MANIFEST).exists() else {}
    current={p.relative_to(SOURCE).as_posix():digest(p) for p in files}
    DEST.mkdir(parents=True,exist_ok=True)
    for source in files:
        target=safe_path(DEST,source.relative_to(SOURCE))
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(source,target)
    # Remove only stale files from our own prior manifest, with a checked destination.
    for relative in set(previous)-set(current):
        path=safe_path(DEST,relative)
        if path.is_file():path.unlink()
    manifest={"prepared_at_utc":datetime.now(timezone.utc).isoformat(),
              "description":"Reviewed static report; no source refresh or notebook execution at deployment.",
              "input_lock":json.loads((ROOT/"quarto-preview/_inputs.json").read_text(encoding="utf-8")),
              "files":current}
    (DEST/MANIFEST).write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    validate()


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='Validate the staged reviewed publication without rebuilding it')
    args=parser.parse_args()
    validate() if args.check else stage()
