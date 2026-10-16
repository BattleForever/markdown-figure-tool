"""A missing/unsupported file must not prevent the next valid file converting."""
from pathlib import Path
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))['version']
exe = ROOT / 'releases' / ('v' + version) / 'MarkdownFigureTool.exe'
directory = ROOT / 'tests/artifacts' / ('batch-' + time.strftime('%Y%m%d-%H%M%S'))
directory.mkdir(parents=True)
source = directory / 'good#20%.md'
source.write_text('<svg width="400" height="100"><rect width="400" height="100" fill="orange"/></svg>', encoding='utf-8')
unsupported = directory / 'unsupported.txt'
unsupported.write_text('# text', encoding='utf-8')
report = directory / 'batch_report.json'
result = subprocess.run([str(exe), '--cli', str(directory / 'missing.md'), str(source), str(unsupported), '--report', str(report)], timeout=60)
assert result.returncode == 1
records = json.loads(report.read_text(encoding='utf-8'))
assert 'error' in records[0]
assert records[1]['succeeded'] == records[1]['total'] == 1
assert 'error' in records[2]
assert Path(records[1]['output']).is_file()
print('PACKAGED_BATCH_ERROR_PASS', report)
