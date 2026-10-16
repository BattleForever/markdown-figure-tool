"""Regression tests for GUI failure paths, not only successful conversions."""
from pathlib import Path
import sys
import tempfile
import tkinter as tk
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mdfig.app import Application
from mdfig.converter import ConversionResult


class GuiErrorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mdfig-gui-errors-')
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.home_patch = patch('mdfig.app.project_home', return_value=self.home)
        self.home_patch.start()
        self.addCleanup(self.home_patch.stop)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = None
        self.addCleanup(self.cleanup)

    def cleanup(self):
        if self.app:
            self.app.running = False
            self.app.drop.close()
        self.root.update_idletasks()
        self.root.destroy()

    def create(self):
        self.app = Application(self.root)
        return self.app

    def test_non_object_settings_do_not_prevent_startup(self):
        (self.home / 'data').mkdir()
        (self.home / 'data/settings.json').write_text('[]', encoding='utf-8')
        self.create()

    def test_unwritable_settings_do_not_break_start_button(self):
        app = self.create()
        source = self.home / 'sample.md'
        source.write_text('# no figures', encoding='utf-8')
        app.add_files([str(source)])
        with patch.object(Path, 'write_text', side_effect=PermissionError('read only')), patch('threading.Thread.start'):
            app.start()
        self.assertTrue(app.running)

    def test_unwritable_log_does_not_stop_event_polling(self):
        app = self.create()
        app.running = True
        app.events.put(('done',))
        with patch.object(Path, 'mkdir', side_effect=PermissionError('read only')):
            app.poll()
        self.assertFalse(app.running)

    def test_completed_progress_does_not_wrap_back_to_zero(self):
        app = self.create()
        source = self.home / 'sample.md'
        source.write_text('# test', encoding='utf-8')
        app.add_files([str(source)])
        item = next(iter(app.items))
        app.progress.configure(maximum=1, value=0)
        app.events.put(('result', item, ConversionResult(str(source))))
        app.events.put(('done',))
        app.poll()
        self.assertEqual(float(app.progress['value']), 1)

    def test_open_result_never_opens_source_before_conversion(self):
        app = self.create()
        app.add_files([str(self.home / 'source.md')])
        with patch('mdfig.app.os.startfile') as opened, patch('mdfig.app.messagebox.showinfo') as info:
            app.open_result()
        opened.assert_not_called()
        info.assert_called_once()

    def test_polling_continues_after_bad_ui_event(self):
        app = self.create()
        app.running = True
        app.events.put(('state', 'missing-item', 'x'))
        app.events.put(('done',))
        app.poll()
        app.poll()
        self.assertFalse(app.running)
        self.assertTrue(app.poll_id)

    def test_thread_start_failure_does_not_leave_running_state(self):
        app = self.create()
        app.add_files([str(self.home / 'source.md')])
        with patch('threading.Thread.start', side_effect=RuntimeError('cannot start thread')):
            app.start()
        self.assertFalse(app.running)
        self.assertEqual(str(app.start_button['state']), 'normal')


if __name__ == '__main__':
    unittest.main(verbosity=2)
