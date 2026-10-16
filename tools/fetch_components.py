"""Fetch pinned public browser runtimes, without reading any user document."""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PACKAGES = {
    'babel': ('7.28.5', {'babel.min.js': '@babel/standalone@7.28.5/babel.min.js', 'LICENSE': '@babel/standalone@7.28.5/LICENSE'}),
    'preact': ('10.27.2', {'preact.umd.js': 'preact@10.27.2/dist/preact.umd.js', 'hooks.umd.js': 'preact@10.27.2/hooks/dist/hooks.umd.js', 'LICENSE': 'preact@10.27.2/LICENSE'}),
    'markdown-it': ('14.1.0', {'markdown-it.min.js': 'markdown-it@14.1.0/dist/markdown-it.min.js', 'LICENSE': 'markdown-it@14.1.0/LICENSE'}),
}
for name, (version, files) in PACKAGES.items():
    directory = ROOT / 'vendor' / name
    directory.mkdir(parents=True, exist_ok=True)
    records = []
    for filename, relative in files.items():
        url = 'https://cdn.jsdelivr.net/npm/' + relative
        with urllib.request.urlopen(url, timeout=45) as response:
            data = response.read()
        (directory / filename).write_bytes(data)
        records.append({'filename': filename, 'url': url, 'bytes': len(data), 'sha256': hashlib.sha256(data).hexdigest()})
    (directory / 'manifest.json').write_text(json.dumps({'version': version, 'files': records}, indent=2), encoding='utf-8')
    print(name, version, sum(record['bytes'] for record in records), flush=True)
