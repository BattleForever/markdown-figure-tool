"""Opt-in support diagnostics that exercise the shipped native GUI event path."""
from dataclasses import asdict
from pathlib import Path
import ctypes
from ctypes import wintypes
import json
import threading
import time


def schedule_drop_diagnostic(app, report, count=1000, convert=False):
    root = app.root
    root.withdraw()
    files = list(app.items.values())
    app.clear_files()
    state = {'posted': 0, 'heartbeat_ticks': 0, 'max_heartbeat_gap': 0.0, 'errors': []}
    last_tick = time.monotonic()
    started = time.monotonic()
    conversion_started = False

    class DROPFILES(ctypes.Structure):
        _fields_ = [('pFiles', wintypes.DWORD), ('pt', wintypes.POINT), ('fNC', wintypes.BOOL), ('fWide', wintypes.BOOL)]

    def post_files():
        kernel = ctypes.windll.kernel32
        kernel.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
        kernel.GlobalAlloc.restype = wintypes.HGLOBAL
        kernel.GlobalLock.argtypes = [wintypes.HGLOBAL]
        kernel.GlobalLock.restype = ctypes.c_void_p
        kernel.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
        kernel.GlobalFree.argtypes = [wintypes.HGLOBAL]
        post = ctypes.windll.user32.PostMessageW
        post.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
        post.restype = wintypes.BOOL
        payload = ('\0'.join(files) + '\0\0').encode('utf-16le')
        header = DROPFILES(ctypes.sizeof(DROPFILES), wintypes.POINT(0, 0), False, True)
        time.sleep(0.25)
        try:
            for _ in range(count):
                if not app.drop.active:
                    break
                handle = kernel.GlobalAlloc(0x0002, ctypes.sizeof(header) + len(payload))
                pointer = kernel.GlobalLock(handle)
                if not pointer:
                    raise OSError('GlobalLock failed')
                ctypes.memmove(pointer, ctypes.byref(header), ctypes.sizeof(header))
                ctypes.memmove(pointer + ctypes.sizeof(header), payload, len(payload))
                kernel.GlobalUnlock(handle)
                if not post(app.drop.hwnd, 0x0233, handle, 0):
                    kernel.GlobalFree(handle)
                    raise OSError('PostMessage failed')
                state['posted'] += 1
                time.sleep(0.002)
        except Exception as error:
            state['errors'].append(str(error))

    def finish(passed):
        result = {**state, 'received': app.drop.received, 'delivered': app.drop.delivered, 'unique_files': len(app.items), 'passed': passed, 'results': [asdict(value) for value in app.results.values()]}
        Path(report).parent.mkdir(parents=True, exist_ok=True)
        Path(report).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        app.close()

    def heartbeat():
        nonlocal last_tick, conversion_started
        now = time.monotonic()
        state['max_heartbeat_gap'] = max(state['max_heartbeat_gap'], now - last_tick)
        state['heartbeat_ticks'] += 1
        last_tick = now
        if now - started > 60:
            state['errors'].append('diagnostic deadline exceeded')
            app.cancel.set()
            finish(False)
            return
        if app.drop.delivered == count and not producer.is_alive():
            if len(app.items) != len(set(files)) or state['errors']:
                finish(False)
                return
            if convert and not conversion_started:
                conversion_started = True
                app.start()
            elif not convert or not app.running:
                passed = not state['errors'] and (not convert or len(app.results) == len(files) and all(result.succeeded == result.total and not result.failures for result in app.results.values()))
                finish(passed)
                return
        root.after(20, heartbeat)

    producer = threading.Thread(target=post_files, daemon=True)
    producer.start()
    root.after(20, heartbeat)
