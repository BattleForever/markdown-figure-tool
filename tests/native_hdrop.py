"""Create a real asynchronous WM_DROPFILES delivery inside the target process."""
import ctypes
from ctypes import wintypes


class DROPFILES(ctypes.Structure):
    _fields_ = [('pFiles', wintypes.DWORD), ('pt', wintypes.POINT), ('fNC', wintypes.BOOL), ('fWide', wintypes.BOOL)]


def post_drop(hwnd, paths):
    payload = ('\0'.join(str(path) for path in paths) + '\0\0').encode('utf-16le')
    drop = DROPFILES(ctypes.sizeof(DROPFILES), wintypes.POINT(0, 0), False, True)
    kernel = ctypes.windll.kernel32
    kernel.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
    kernel.GlobalAlloc.restype = wintypes.HGLOBAL
    kernel.GlobalLock.argtypes = [wintypes.HGLOBAL]
    kernel.GlobalLock.restype = ctypes.c_void_p
    kernel.GlobalUnlock.argtypes = [wintypes.HGLOBAL]
    handle = kernel.GlobalAlloc(0x0002, ctypes.sizeof(drop) + len(payload))
    pointer = kernel.GlobalLock(handle)
    ctypes.memmove(pointer, ctypes.byref(drop), ctypes.sizeof(drop))
    ctypes.memmove(pointer + ctypes.sizeof(drop), payload, len(payload))
    kernel.GlobalUnlock(handle)
    post = ctypes.windll.user32.PostMessageW
    post.argtypes = [wintypes.HWND, wintypes.UINT, ctypes.c_size_t, ctypes.c_ssize_t]
    post.restype = wintypes.BOOL
    assert post(hwnd, 0x0233, handle, 0)
