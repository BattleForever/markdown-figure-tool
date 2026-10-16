"""Download the pinned public rendering library; never sends document content."""
from pathlib import Path
import hashlib
import json
import urllib.request

root = Path(__file__).resolve().parents[1]
target = root / "vendor" / "mermaid"
target.mkdir(parents=True, exist_ok=True)
urls = {
    "mermaid.min.js": "https://cdn.jsdelivr.net/npm/mermaid@11.12.0/dist/mermaid.min.js",
    "LICENSE": "https://cdn.jsdelivr.net/npm/mermaid@11.12.0/LICENSE",
}
records = []
for filename, url in urls.items():
    with urllib.request.urlopen(url, timeout=45) as response:
        data = response.read()
    (target / filename).write_bytes(data)
    records.append({"filename": filename, "url": url, "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()})
(target / "manifest.json").write_text(json.dumps({"version": "11.12.0", "files": records}, indent=2), encoding="utf-8")
print(json.dumps(records, indent=2))
