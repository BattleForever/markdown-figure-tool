"""Closing the GUI during an endless page must complete, without publishing output."""
from pathlib import Path
import json
import sys
import time
import tkinter as tk

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mdfig.app import Application

directory = ROOT / 'tests/artifacts' / ('close-' + time.strftime('%Y%m%d-%H%M%S'))
directory.mkdir(parents=True)
source = directory / '关闭测试.md'
source.write_text('<div>hang</div><script>Element.prototype.getBoundingClientRect=function(){while(true){}};</script>', encoding='utf-8')
root = tk.Tk()
root.withdraw()
app = Application(root, [str(source)])
app.start()
started = time.monotonic()
close_started = []

def wait_until_render():
    if any('图形 1/1' in line for line in app.log_lines):
        close_started.append(time.monotonic())
        root.after(600, app.close)
    else:
        assert time.monotonic() - started < 20
        root.after(50, wait_until_render)

root.after(50, wait_until_render)
root.mainloop()
elapsed = time.monotonic() - close_started[0] - 0.6
assert elapsed < 4, elapsed
assert not list(directory.glob('*_图像版.md'))
assert not list(directory.glob('.mdfig-render-*'))
(directory / 'close_report.json').write_text(json.dumps({'closed_after_cancel_seconds': elapsed, 'no_partial_output': True}, indent=2), encoding='utf-8')
print('GUI_CLOSE_PASS', round(elapsed, 2))
