"""Windows scanners may briefly deny reads of newly published IPC packets."""
import ctypes
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mdfig.isolated import read_json


class ProtocolReadTests(unittest.TestCase):
    def test_real_windows_exclusive_handle_is_retried(self):
        with tempfile.TemporaryDirectory(prefix='mdfig-lock-') as folder:
            path=Path(folder)/'request-1.json'
            path.write_text('{"value":12}',encoding='utf-8')
            kernel=ctypes.WinDLL('kernel32',use_last_error=True)
            kernel.CreateFileW.argtypes=[ctypes.c_wchar_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p,ctypes.c_uint,ctypes.c_uint,ctypes.c_void_p]
            kernel.CreateFileW.restype=ctypes.c_void_p
            kernel.CloseHandle.argtypes=[ctypes.c_void_p]
            handle=kernel.CreateFileW(str(path),0x80000000,0,None,3,0,None)
            self.assertNotEqual(handle,ctypes.c_void_p(-1).value)
            with self.assertRaises(PermissionError):
                path.read_text(encoding='utf-8')
            timer=threading.Timer(.12,lambda:kernel.CloseHandle(handle))
            timer.start()
            try:
                self.assertEqual(read_json(path),{'value':12})
            finally:
                timer.join()

    def test_persistent_denial_still_fails_within_bound(self):
        started=time.monotonic()
        with patch.object(Path,'read_text',side_effect=PermissionError('locked')):
            with self.assertRaises(PermissionError):
                read_json(Path('locked.json'))
        self.assertLess(time.monotonic()-started,1)


if __name__=='__main__':
    unittest.main()
