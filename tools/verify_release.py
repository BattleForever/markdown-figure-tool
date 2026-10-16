from pathlib import Path
import hashlib
import json
import zipfile

ROOT = Path(__file__).resolve().parents[1]
reports = []
for index_path in sorted((ROOT / 'versions').glob('v*.json')):
    index = json.loads(index_path.read_text(encoding='utf-8'))
    target = ROOT / 'releases' / ('v' + index['version'])
    manifest = json.loads((target / 'release_manifest.json').read_text(encoding='utf-8'))
    for entry in manifest['files']:
        path = target / entry['path']
        assert path.is_file(), path
        assert path.stat().st_size == entry['bytes'], path
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['sha256'], path
    archive = ROOT / index['archive']
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == index['archive_sha256']
    assert hashlib.sha256((ROOT / index['executable']).read_bytes()).hexdigest() == index['exe_sha256']
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        prefix = target.name + '/'
        for entry in manifest['files']:
            assert hashlib.sha256(zipped.read(prefix + entry['path'])).hexdigest() == entry['sha256'], entry['path']
    reports.append({'version': index['version'], 'verified_files': len(manifest['files']), 'zip_verified': True, 'archive_bytes': archive.stat().st_size})
(ROOT / 'docs' / 'release_verification.json').write_text(json.dumps(reports, indent=2), encoding='utf-8')
print(json.dumps(reports, indent=2))
