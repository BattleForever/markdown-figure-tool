"""Verify native Windows drag/drop and user-menu registration without leaving a menu."""
import ctypes
from ctypes import wintypes
import json
from pathlib import Path
import sys
import tkinter as tk
import uuid

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mdfig.app import Application
import mdfig.windows as windows

artifacts = ROOT / 'tests' / 'artifacts' / 'gui'
artifacts.mkdir(parents=True, exist_ok=True)
files = [artifacts / '拖放测试 一.md', artifacts / '拖放测试(二).md']
for path in files:
    path.write_text('# GUI drop test', encoding='utf-8')
root = tk.Tk()
app = Application(root)
root.update()


class DROPFILES(ctypes.Structure):
    _fields_ = [('pFiles', wintypes.DWORD), ('pt', wintypes.POINT), ('fNC', wintypes.BOOL), ('fWide', wintypes.BOOL)]


payload = ('\0'.join(str(path) for path in files) + '\0\0').encode('utf-16le')
drop = DROPFILES(ctypes.sizeof(DROPFILES), wintypes.POINT(0, 0), False, True)
kernel32 = ctypes.windll.kernel32
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalAlloc.restype = wintypes.HGLOBAL
kernel32.GlobalLock.argtypes = [wintypes.HGLOBAL]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
handle = kernel32.GlobalAlloc(0x0002, ctypes.sizeof(drop) + len(payload))
pointer = kernel32.GlobalLock(handle)
ctypes.memmove(pointer, ctypes.byref(drop), ctypes.sizeof(drop))
ctypes.memmove(pointer + ctypes.sizeof(drop), payload, len(payload))
kernel32.GlobalUnlock(handle)
send = ctypes.windll.user32.SendMessageW
send.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
send.restype = ctypes.c_ssize_t
assert app.drop.hwnd
send(app.drop.hwnd, 0x0233, handle, 0)
root.after(150, root.quit)
root.mainloop()
assert len(app.items) == 2, app.items
app.add_files([str(files[0])])
assert len(app.items) == 2
root.update()
try:
    from PIL import Image
    # Capture this exact application window, never another application behind it.
    user32, gdi32 = ctypes.windll.user32, ctypes.windll.gdi32
    rect = wintypes.RECT()
    user32.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user32.GetWindowRect(app.drop.hwnd, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    user32.GetWindowDC.argtypes = [wintypes.HWND]
    user32.GetWindowDC.restype = wintypes.HDC
    gdi32.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi32.CreateCompatibleDC.restype = wintypes.HDC
    gdi32.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi32.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi32.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi32.SelectObject.restype = wintypes.HGDIOBJ
    user32.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    screen = user32.GetWindowDC(app.drop.hwnd)
    memory = gdi32.CreateCompatibleDC(screen)
    bitmap = gdi32.CreateCompatibleBitmap(screen, width, height)
    previous = gdi32.SelectObject(memory, bitmap)
    assert user32.PrintWindow(app.drop.hwnd, memory, 2)
    import struct
    header = struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0, width * height * 4, 0, 0, 0, 0)
    info = ctypes.create_string_buffer(header + b'\0' * 16)
    buffer = ctypes.create_string_buffer(width * height * 4)
    gdi32.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT, wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    assert gdi32.GetDIBits(memory, bitmap, 0, height, buffer, info, 0)
    Image.frombuffer('RGB', (width, height), buffer.raw, 'raw', 'BGRX', 0, 1).save(artifacts / 'gui_preview.png')
    gdi32.SelectObject(memory, previous)
    gdi32.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi32.DeleteDC.argtypes = [wintypes.HDC]
    user32.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi32.DeleteObject(bitmap)
    gdi32.DeleteDC(memory)
    user32.ReleaseDC(app.drop.hwnd, screen)
except ImportError:
    pass
app.clear_files()
assert not app.items
app.close()

import winreg
original_name = windows.MENU_NAME
windows.MENU_NAME = 'MarkdownFigureTool_SelfTest_' + uuid.uuid4().hex
try:
    windows.install_context_menu()
    for extension in windows.EXTENSIONS:
        keypath = rf'Software\Classes\SystemFileAssociations\{extension}\shell\{windows.MENU_NAME}\command'
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, keypath) as key:
            command = winreg.QueryValue(key, None)
            assert '--auto "%1"' in command
finally:
    windows.remove_context_menu()
    for extension in windows.EXTENSIONS:
        keypath = rf'Software\Classes\SystemFileAssociations\{extension}\shell\{windows.MENU_NAME}'
        try:
            winreg.OpenKey(winreg.HKEY_CURRENT_USER, keypath).Close()
            raise AssertionError('test key was not removed')
        except FileNotFoundError:
            pass
    windows.MENU_NAME = original_name
report = {'window_created': True, 'native_unicode_multifile_drop': True, 'deduplicates': True, 'clear_files': True, 'context_menu_roundtrip_temporary_key': True}
(artifacts / 'gui_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
