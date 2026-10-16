"""A monitored child replays asynchronous drops while Tk.mainloop is active."""
from pathlib import Path
import faulthandler
import json
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))


def child(output):
    import tkinter as tk
    from mdfig.app import Application
    from native_hdrop import post_drop
    output.mkdir(parents=True, exist_ok=True)
    fault = (output / 'fault.log').open('w', encoding='utf-8')
    faulthandler.enable(fault)
    root = tk.Tk()
    root.withdraw()
    app = Application(root)
    sample = output / '异步拖放测试 中文(1).md'
    sample.write_text('# Native drop test', encoding='utf-8')
    state = {'ticks': 0, 'drops': 0}

    def tick():
        state['ticks'] += 1
        (output / 'heartbeat.json').write_text(json.dumps(state), encoding='utf-8')
        root.after(50, tick)

    def producer():
        time.sleep(0.3)
        for _ in range(8):
            post_drop(app.drop.hwnd, [sample])
            state['drops'] += 1
            time.sleep(0.1)

    def finish():
        assert len(app.items) == 1, app.items
        (output / 'passed.json').write_text(json.dumps({'items': len(app.items), **state}), encoding='utf-8')
        app.close()

    root.after(30, tick)
    root.after(2200, finish)
    threading.Thread(target=producer, daemon=True).start()
    root.mainloop()
    fault.close()


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--child':
        child(Path(sys.argv[2]))
    else:
        output = ROOT / 'tests' / 'artifacts' / ('native-drop-' + time.strftime('%Y%m%d-%H%M%S'))
        output.mkdir(parents=True)
        with (output / 'stderr.log').open('w', encoding='utf-8') as errors:
            process = subprocess.Popen([sys.executable, __file__, '--child', str(output)], stdout=errors, stderr=errors)
            try:
                code = process.wait(timeout=12)
            except subprocess.TimeoutExpired:
                process.kill()
                code = process.wait()
                (output / 'timed_out.txt').write_text('Main loop did not finish within 12 seconds', encoding='utf-8')
        report = {'returncode': code, 'passed': (output / 'passed.json').is_file(), 'artifacts': str(output)}
        (output / 'result.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        print(json.dumps(report))
        raise SystemExit(0 if report['passed'] and code == 0 else 1)
