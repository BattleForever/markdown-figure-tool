"""Real hung JavaScript must time out, recover, cancel and clean its owned job."""
from pathlib import Path
import json
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mdfig.isolated import IsolatedRenderer
from mdfig.parser import Figure
from mdfig.renderer import RenderOptions
from mdfig.converter import convert_file

artifacts = ROOT / 'tests' / 'artifacts' / ('isolation-' + time.strftime('%Y%m%d-%H%M%S'))
artifacts.mkdir(parents=True)
good = Figure(0, 1, 'html', '<svg width="300" height="100"><rect width="300" height="100" fill="green"/></svg>', 1)
# Force an infinite loop in screenshot state inspection, after page.set_content.
hang = Figure(0, 1, 'html', '<div>will hang</div><script>Element.prototype.getBoundingClientRect=function(){while(true){}};</script>', 1)
options = RenderOptions(timeout_ms=600, wait_ms=0)
report = {}
with IsolatedRenderer(options, job_root=artifacts / 'jobs') as renderer:
    renderer.render(good, artifacts, artifacts / 'before.png')
    report['windows_job_owns_children'] = bool(renderer.owner.job)
    assert renderer.owner.job
    started = time.monotonic()
    try:
        renderer.render(hang, artifacts, artifacts / 'hang.png')
        raise AssertionError('hung script was reported as success')
    except TimeoutError:
        report['hang_deadline_seconds'] = round(time.monotonic() - started, 2)
        assert report['hang_deadline_seconds'] < 6
    assert renderer.owner is None
    renderer.render(good, artifacts, artifacts / 'after.png')
    report['recovers_after_timeout'] = True
assert not list((artifacts / 'jobs').iterdir())

cancel = threading.Event()
with IsolatedRenderer(RenderOptions(wait_ms=0), cancel.is_set, artifacts / 'jobs') as renderer:
    renderer.render(good, artifacts, artifacts / 'cancel-before.png')
    timer = threading.Timer(0.5, cancel.set)
    timer.start()
    started = time.monotonic()
    try:
        renderer.render(hang, artifacts, artifacts / 'cancel-hang.png')
        raise AssertionError('cancelled render returned success')
    except RuntimeError as error:
        assert '取消' in str(error), error
        report['cancel_seconds'] = round(time.monotonic() - started, 2)
        assert report['cancel_seconds'] < 4
    timer.join()
assert not list((artifacts / 'jobs').iterdir())
with IsolatedRenderer(RenderOptions(browser_path=str(artifacts / 'missing-browser.exe'))) as renderer:
    try:
        renderer.render(good, artifacts, artifacts / 'missing.png')
        raise AssertionError('missing browser was silently replaced')
    except RuntimeError as error:
        assert '所选浏览器不存在' in str(error)
        report['missing_selected_browser_reported'] = True
plain = artifacts / 'plain.md'
plain.write_text('# Plain file', encoding='utf-8')
with IsolatedRenderer(RenderOptions(browser_path='missing.exe')) as renderer:
    assert convert_file(plain, renderer).total == 0
    assert renderer.owner is None
report['plain_file_needs_no_browser'] = True
(artifacts / 'isolation_report.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
print(json.dumps(report))
