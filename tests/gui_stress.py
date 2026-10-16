"""Use source or the actual EXE to exercise asynchronous drops and conversion."""
from pathlib import Path
import json
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))['version']
directory = ROOT / 'tests' / 'artifacts' / ('stress-' + time.strftime('%Y%m%d-%H%M%S'))
directory.mkdir(parents=True)
first = directory / '拖放 中文 空格(1).md'
first.write_text('<svg width="400" height="120"><rect width="400" height="120" fill="#2563eb"/></svg>', encoding='utf-8')
second = directory / '另一个文件.md'
second.write_text('```mermaid\nflowchart LR\nA[拖入]-->B[转换]\n```', encoding='utf-8')
if '--packaged' in sys.argv:
    command = [str(ROOT / 'releases' / ('v' + version) / 'MarkdownFigureTool.exe')]
else:
    command = [sys.executable, str(ROOT / 'src/launcher.py')]
report = directory / 'drop_stress_report.json'
command += ['--diagnose-drop', str(report), '--diagnose-drop-count', '1000', '--diagnose-convert', str(first), str(second)]
completed = subprocess.run(command, capture_output=True, timeout=75)
assert completed.returncode == 0, (completed.returncode, completed.stderr)
result = json.loads(report.read_text(encoding='utf-8'))
assert result['passed'], result
assert result['received'] == result['delivered'] == result['posted'] == 1000, result
assert result['max_heartbeat_gap'] < 1.0, result
assert len(result['results']) == 2
print(json.dumps({'packaged': '--packaged' in sys.argv, 'native_messages': 1000, 'converted_files': 2, 'max_heartbeat_gap': round(result['max_heartbeat_gap'], 3), 'report': str(report)}, ensure_ascii=False))
