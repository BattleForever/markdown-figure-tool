"""Run the complete finite stability matrix and keep each failure log."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
output = ROOT / 'tests/artifacts' / ('suite-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
output.mkdir(parents=True)
commands = [
    ['-m', 'unittest', 'discover', '-s', 'tests', '-p', 'test_*.py', '-v'],
    ['tests/repro_native_drop.py'],
    ['tests/gui_stress.py'],
    ['tests/gui_smoke.py'],
    ['tests/gui_convert.py'],
    ['tests/gui_cancel_close.py'],
    ['tests/isolation_regression.py'],
    ['tests/integration.py'],
    ['tests/render_boundaries.py'],
    ['tests/component_rendering.py'],
]
if '--packaged' in sys.argv:
    commands += [['tests/packaged_smoke.py'], ['tests/gui_stress.py', '--packaged'], ['tests/packaged_batch_errors.py'], ['tests/packaged_components.py'], ['tests/portable_relocation.py']]
records = []
for index, args in enumerate(commands, 1):
    name = args[0].replace('/', '_').replace('.py', '') if args[0] != '-m' else 'unit'
    started = time.monotonic()
    with (output / f'{index:02}-{name}.log').open('w', encoding='utf-8') as log:
        try:
            result = subprocess.run([sys.executable, *args], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=150)
            code = result.returncode
        except subprocess.TimeoutExpired:
            code = 'timeout'
    record = {'command': args, 'returncode': code, 'seconds': round(time.monotonic() - started, 2)}
    records.append(record)
    print(json.dumps(record, ensure_ascii=False), flush=True)
    (output / 'suite_report.json').write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding='utf-8')
print('REGRESSION_REPORT', output, flush=True)
raise SystemExit(0 if all(record['returncode'] == 0 for record in records) else 1)
