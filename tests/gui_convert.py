"""Drive the real GUI queue/worker through a successful conversion."""
from pathlib import Path
import json
import sys
import time
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mdfig.app import Application

artifacts = ROOT / 'tests' / 'artifacts' / 'gui-conversion'
artifacts.mkdir(parents=True, exist_ok=True)
source = artifacts / 'GUI全流程.md'
source.write_text('''# GUI conversion

<svg viewBox="0 0 500 100"><rect width="500" height="100" fill="#dbeafe"/><text x="30" y="65" font-size="26">GUI worker OK</text></svg>

```mermaid
flowchart LR
A[拖入文件]-->B[开始转换]-->C[完成]
```
''', encoding='utf-8')
root = tk.Tk()
root.withdraw()
app = Application(root, [str(source)])
app.start()
deadline = time.monotonic() + 90
failure = []

def poll_result():
    if app.running and time.monotonic() < deadline:
        root.after(100, poll_result)
        return
    try:
        assert not app.running, 'GUI conversion timed out'
        assert len(app.results) == 1, app.log_lines
        result = next(iter(app.results.values()))
        assert (result.total, result.succeeded) == (2, 2)
        assert Path(result.output).is_file()
        assert len(list(Path(result.assets).glob('*.png'))) == 2
        (artifacts / 'gui_conversion_report.json').write_text(json.dumps({'gui_worker_pass': True, 'succeeded': 2, 'output': result.output}, ensure_ascii=False, indent=2), encoding='utf-8')
    except Exception as error:
        failure.append(str(error))
    finally:
        app.cancel.set()
        app.running = False
        app.close()

root.after(100, poll_result)
root.mainloop()
assert not failure, failure
print('GUI_CONVERSION_PASS')
