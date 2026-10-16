"""Portable paths must be based on the current executable location."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from mdfig.app import project_home
from mdfig.renderer import browser_candidates

class PortablePaths(unittest.TestCase):
    def test_frozen_home_does_not_climb_to_an_unrelated_project(self):
        with tempfile.TemporaryDirectory(prefix='portable-path-') as folder:
            root=Path(folder)
            (root/'project.json').write_text('{}',encoding='utf-8')
            app=root/'copy'/'app'
            app.mkdir(parents=True)
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(app/'MarkdownFigureTool.exe')):
                self.assertEqual(project_home(),app.resolve())

    def test_bundled_browser_is_first_after_relocation(self):
        with tempfile.TemporaryDirectory(prefix='portable-browser-') as folder:
            app=Path(folder)/'moved app 中文'
            browser=app/'browser'/'chrome-headless-shell.exe'
            browser.parent.mkdir(parents=True)
            browser.write_bytes(b'test placeholder')
            with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(app/'MarkdownFigureTool.exe')):
                self.assertEqual(browser_candidates()[0],browser.resolve())

if __name__=='__main__':unittest.main()
