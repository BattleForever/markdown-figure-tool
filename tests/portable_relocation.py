"""Exercise the sealed ZIP with no external Python/browser path, then relocate it."""
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import time
import zipfile

ROOT=Path(__file__).resolve().parents[1]
version=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))['version']
release=json.loads((ROOT/'versions'/('v'+version+'.json')).read_text(encoding='utf-8'))
archive=ROOT/release['archive']
assert hashlib.sha256(archive.read_bytes()).hexdigest()==release['archive_sha256']
out=ROOT/'tests/artifacts'/('portable-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True)
first=out/'computer A'
first.mkdir()
with zipfile.ZipFile(archive) as zipped:
    names=zipped.namelist()
    assert not any('/data/' in name or name.lower().endswith(('.log','.dmp')) for name in names)
    zipped.extractall(first)
app=first/('v'+version)
source=out/'Notes # 中文'/'demo.md'
source.parent.mkdir()
source.write_bytes((ROOT/'examples/demo.md').read_bytes())
before=source.read_bytes()
env=dict(os.environ)
empty=out/'empty-user-runtime'
empty.mkdir()
for name in ('LOCALAPPDATA','APPDATA','PLAYWRIGHT_BROWSERS_PATH'):
    env[name]=str(empty)
env['PATH']=str(Path(os.environ['SystemRoot'])/'System32')+os.pathsep+os.environ['SystemRoot']
report=out/'first.json'
completed=subprocess.run([str(app/'MarkdownFigureTool.exe'),'--cli',str(source),'--report',str(report)],env=env,capture_output=True,timeout=60)
assert completed.returncode==0,(completed.returncode,completed.stderr)
def validate(report,app):
    results=json.loads(report.read_text(encoding='utf-8'))
    assert len(results)==1 and results[0]['succeeded']==results[0]['total']==3 and not results[0]['failures'],results
    record=json.loads((Path(results[0]['assets'])/'转换记录.json').read_text(encoding='utf-8'))
    assert all(f['browser_engine']=='chrome-headless-shell.exe' for f in record['figures']),record
    assert (app/'data').is_dir()
    assert source.read_bytes()==before
    return results
original=validate(report,app)
second=out/'computer B moved 中文'/'app'
second.parent.mkdir()
assert app.resolve().is_relative_to(out.resolve()) and second.resolve().is_relative_to(out.resolve())
assert not second.exists()
app.rename(second)
app=second
report=out/'moved.json'
env.update(MDFIG_PORTABLE_START=str(app/'Start.cmd'),MDFIG_PORTABLE_SOURCE=str(source),MDFIG_PORTABLE_REPORT=str(report))
ps=Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
completed=subprocess.run([str(ps),'-NoProfile','-NonInteractive','-Command','& $env:MDFIG_PORTABLE_START --cli $env:MDFIG_PORTABLE_SOURCE --report $env:MDFIG_PORTABLE_REPORT'],env=env,capture_output=True,timeout=10,creationflags=subprocess.CREATE_NO_WINDOW)
assert completed.returncode==0,(completed.returncode,completed.stderr)
deadline=time.monotonic()+60
while True:
    if report.is_file():
        try:
            moved=validate(report,app)
            break
        except (json.JSONDecodeError,PermissionError):pass
    assert time.monotonic()<deadline,'Moved Start.cmd did not produce a result'
    time.sleep(.1)
assert moved[0]['output']!=original[0]['output']
gui_report=out/'gui.json'
completed=subprocess.run([str(app/'MarkdownFigureTool.exe'),'--diagnose-drop',str(gui_report),'--diagnose-drop-count','100','--diagnose-convert',str(source)],env=env,capture_output=True,timeout=60)
assert completed.returncode==0,(completed.returncode,completed.stderr)
gui=json.loads(gui_report.read_text(encoding='utf-8'))
assert gui['passed'] and gui['delivered']==100 and gui['max_heartbeat_gap']<1,gui
assert gui['results'][0]['succeeded']==3
assert source.read_bytes()==before
summary={'zip_verified':True,'no_external_python_or_browser_path':True,'bundled_browser_used':True,'moved_start_script_passed':True,'source_unchanged':True,'figures_per_run':3,'gui_native_drops':100,'gui_max_heartbeat_gap':round(gui['max_heartbeat_gap'],3)}
(out/'relocation_report.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print('PORTABLE_RELOCATION_PASS',json.dumps(summary),flush=True)
