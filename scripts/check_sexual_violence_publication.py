"""Check the sexual violence Pages snapshot against its reviewed file hashes."""
import hashlib
import json
from pathlib import Path
from stage_report_publication import check_links, safe_path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / 'docs/sexual-violence'
manifest = json.loads((SITE / 'publication.json').read_text(encoding='utf-8'))
actual = {p.relative_to(SITE).as_posix() for p in SITE.rglob('*') if p.is_file() and p.name != 'publication.json'}
if actual != set(manifest['files']):
    raise ValueError('Sexual violence publication file set differs from reviewed manifest')
for name, expected in manifest['files'].items():
    path = safe_path(SITE, name)
    if path.is_symlink() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError(f'Reviewed publication file changed: {name}')
for name in ['index.html', 'worldwide.html', 'uk.html', 'children.html', 'justice.html', 'methods.html', 'medium/article.html']:
    if not (SITE / name).is_file():
        raise ValueError(f'Missing page: {name}')
check_links(SITE)
print(f'Verified {len(actual)} sexual violence publication files and local links.')
