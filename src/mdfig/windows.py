"""Optional user-level Explorer menu and native file-drop support."""
import ctypes
from ctypes import wintypes
import os
import queue
from pathlib import Path
import subprocess
import sys

MENU_NAME = "MarkdownFigureTool"
EXTENSIONS = (".md", ".markdown", ".mdown")


def launch_command():
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([sys.executable])
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        pythonw = Path(sys.executable)
    launcher = Path(__file__).resolve().parents[1] / "launcher.py"
    return subprocess.list2cmdline([str(pythonw), str(launcher)])


def install_context_menu():
    import winreg
    command = launch_command() + ' --auto "%1"'
    for extension in EXTENSIONS:
        root = rf"Software\Classes\SystemFileAssociations\{extension}\shell\{MENU_NAME}"
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root) as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "转换图形代码为图片")
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Document")
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, root + r"\command") as key:
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def remove_context_menu():
    import winreg
    for extension in EXTENSIONS:
        root = rf"Software\Classes\SystemFileAssociations\{extension}\shell\{MENU_NAME}"
        for subkey in (root + r"\command", root):
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, subkey)
            except FileNotFoundError:
                pass
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


class FileDrop:
    def __init__(self, root, callback):
        self.hwnd = None
        self.pending = queue.SimpleQueue()
        self.root = root
        self.callback = callback
        self.poll_id = None
        self.active = True
        self.received = 0
        self.delivered = 0
        if os.name != "nt":
            return
        root.update_idletasks()
        self.user32 = ctypes.windll.user32
        self.shell32 = ctypes.windll.shell32
        self.user32.GetAncestor.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user32.GetAncestor.restype = wintypes.HWND
        self.hwnd = self.user32.GetAncestor(root.winfo_id(), 2)
        self.proc_type = ctypes.WINFUNCTYPE(ctypes.c_ssize_t, wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t)
        self.set_proc = self.user32.SetWindowLongPtrW
        self.set_proc.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
        self.set_proc.restype = ctypes.c_void_p
        self.user32.CallWindowProcW.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
        self.user32.CallWindowProcW.restype = ctypes.c_ssize_t
        self.shell32.DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
        self.shell32.DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
        self.shell32.DragQueryFileW.restype = wintypes.UINT
        self.shell32.DragFinish.argtypes = [wintypes.HANDLE]

        def window_proc(hwnd, message, wparam, lparam):
            if message == 0x0233:  # WM_DROPFILES
                try:
                    paths = []
                    count = self.shell32.DragQueryFileW(wparam, 0xFFFFFFFF, None, 0)
                    for index in range(count):
                        length = self.shell32.DragQueryFileW(wparam, index, None, 0)
                        buffer = ctypes.create_unicode_buffer(length + 1)
                        self.shell32.DragQueryFileW(wparam, index, buffer, length + 1)
                        paths.append(buffer.value)
                    # Tk is already inside its native event dispatch here. Reentering
                    # Tcl via root.after corrupts its saved Python thread state.
                    # Native callbacks only copy data; a normal Tk timer drains it.
                    self.pending.put(paths)
                    self.received += 1
                finally:
                    self.shell32.DragFinish(wparam)
                return 0
            return self.user32.CallWindowProcW(self.original, hwnd, message, wparam, lparam)

        self.proc = self.proc_type(window_proc)
        get_proc = self.user32.GetWindowLongPtrW
        get_proc.argtypes = [wintypes.HWND, ctypes.c_int]
        get_proc.restype = ctypes.c_void_p
        self.original = get_proc(self.hwnd, -4)
        installed = self.set_proc(self.hwnd, -4, ctypes.cast(self.proc, ctypes.c_void_p))
        if not installed:
            self.hwnd = None
            return
        self.shell32.DragAcceptFiles(self.hwnd, True)
        self.poll_id = root.after(40, self.poll)

    def poll(self):
        if not self.active:
            return
        try:
            for _ in range(64):
                paths = self.pending.get_nowait()
                try:
                    self.callback(paths)
                    self.delivered += 1
                except Exception:
                    self.root.report_callback_exception(*sys.exc_info())
        except queue.Empty:
            pass
        finally:
            if self.active:
                self.poll_id = self.root.after(40, self.poll)

    def close(self):
        self.active = False
        if self.poll_id:
            self.root.after_cancel(self.poll_id)
            self.poll_id = None
        if self.hwnd:
            self.shell32.DragAcceptFiles(self.hwnd, False)
            self.set_proc(self.hwnd, -4, self.original)
            self.hwnd = None

