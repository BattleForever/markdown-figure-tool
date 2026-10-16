"""Build a new portable Windows release without copying runtime user data."""
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from mdfig import __version__

parser=argparse.ArgumentParser()
parser.add_argument('--bundle-browser',action='store_true',help='Include the Playwright-pinned Chromium Headless Shell')
parser.add_argument('--browser-dir',type=Path,help='An existing clean headless-shell binary directory')
args=parser.parse_args()
version='v'+__version__
target=ROOT/'releases'/version
archive=ROOT/'releases'/f'MarkdownFigureTool-{version}-windows-x64-portable.zip'
if target.exists() or archive.exists():
    raise SystemExit('Release already exists; increment the version instead of overwriting.')
browser=None
browser_info=None
if args.bundle_browser or args.browser_dir:
    driver=Path(importlib.metadata.distribution('playwright').locate_file('playwright/driver/package/browsers.json'))
    spec=next(b for b in json.loads(driver.read_text(encoding='utf-8'))['browsers'] if b['name']=='chromium-headless-shell')
    cache=Path(os.environ.get('LOCALAPPDATA',''))/'ms-playwright'
    browser=args.browser_dir or cache/f"chromium_headless_shell-{spec['revision']}"/'chrome-headless-shell-win64'
    if not (browser/'chrome-headless-shell.exe').is_file() or not (browser/'LICENSE.headless_shell').is_file():
        raise SystemExit('Install the pinned browser first: python -m playwright install chromium --only-shell')
    browser_info={'name':'Chromium Headless Shell','revision':spec['revision'],'version':spec['browserVersion']}
work=ROOT/'build'/version
work.mkdir(parents=True,exist_ok=True)
parts=tuple(int(v) for v in __version__.split('.'))+(0,)
version_info=work/'version_info.txt'
version_info.write_text("VSVersionInfo(ffi=FixedFileInfo(filevers="+repr(parts)+", prodvers="+repr(parts)+", mask=0x3f, flags=0, OS=0x40004, fileType=1, subtype=0, date=(0,0)), kids=[StringFileInfo([StringTable('040904B0', [StringStruct('FileDescription','Markdown Figure Tool'), StringStruct('FileVersion','"+__version__+"'), StringStruct('ProductName','Markdown Figure Tool'), StringStruct('ProductVersion','"+__version__+"')])]), VarFileInfo([VarStruct('Translation',[1033,1200])])])",encoding='utf-8')
command=[sys.executable,'-m','PyInstaller','--noconfirm','--onedir','--windowed','--name','MarkdownFigureTool','--version-file',str(version_info),'--distpath',str(work/'dist'),'--workpath',str(work/'temp'),'--specpath',str(work),'--paths',str(ROOT/'src'),'--add-data',str(ROOT/'vendor')+';vendor','--add-data',str(ROOT/'assets')+';assets','--exclude-module','PySide6','--exclude-module','PyQt5','--exclude-module','numpy','--exclude-module','matplotlib',str(ROOT/'src/launcher.py')]
with (work/'build.log').open('w',encoding='utf-8') as log:
    subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
app=work/'dist/MarkdownFigureTool'
for name in ('README.md','README.en.md','CHANGELOG.md','THIRD_PARTY.md','LICENSE','PRIVACY.md','SECURITY.md'):
    shutil.copy2(ROOT/name,app/name)
license_root=app/'licenses'
python_license=Path(sys.base_prefix)/'LICENSE.txt'
if not python_license.is_file():
    raise SystemExit('Python distribution license was not found; do not publish an incomplete package.')
(license_root/'Python').mkdir(parents=True)
shutil.copy2(python_license,license_root/'Python/LICENSE.txt')
tcl_license=Path(sys.base_prefix)/'tcl/tcl8.6/license.terms'
if not tcl_license.is_file():tcl_license=ROOT/'vendor/tcl/LICENSE'
if not tcl_license.is_file():
    raise SystemExit('Tcl distribution license was not found.')
(license_root/'Tcl').mkdir()
shutil.copy2(tcl_license,license_root/'Tcl/license.terms')
for package in ('pyinstaller','playwright','greenlet','pyee','markdown-it-py','mdurl'):
    distribution=importlib.metadata.distribution(package)
    entries=[p for p in distribution.files if '.dist-info/' in p.as_posix() and any(word in p.name.lower() for word in ('license','copying','notice'))]
    if not entries:raise SystemExit('Missing distribution license: '+package)
    directory=license_root/package
    directory.mkdir()
    for entry in entries:shutil.copy2(distribution.locate_file(entry),directory/entry.name)
for path in (ROOT/'portable').iterdir():
    if path.is_file():shutil.copy2(path,app/path.name)
shutil.copytree(ROOT/'examples',app/'examples')
if browser:
    # Browser cache directories may contain debug logs from prior local runs.
    # Copy only executable distribution files, with all upstream licenses.
    excluded={'debug.log','Crashpad','Default','User Data','BrowserMetrics','Crash Reports','CrashDumps'}
    def ignore(directory,names):
        return [n for n in names if n in excluded or n.lower().endswith(('.log','.dmp','.tmp')) or n.startswith('Singleton')]
    shutil.copytree(browser,app/'browser',ignore=ignore)
(app/'portable.json').write_text(json.dumps({'version':__version__,'platform':'windows-x64','browser':browser_info},indent=2)+'\n',encoding='utf-8')
files=[]
for path in sorted(app.rglob('*')):
    if path.is_file():
        files.append({'path':path.relative_to(app).as_posix(),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
manifest={'version':__version__,'python':sys.version,'playwright':importlib.metadata.version('playwright'),'pyinstaller':importlib.metadata.version('pyinstaller'),'browser':browser_info,'files':files}
(app/'release_manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
target.parent.mkdir(parents=True,exist_ok=True)
shutil.move(str(app),str(target))
shutil.make_archive(str(archive.with_suffix('')),'zip',root_dir=target.parent,base_dir=target.name)
index={'version':__version__,'executable':(target/'MarkdownFigureTool.exe').relative_to(ROOT).as_posix(),'exe_sha256':hashlib.sha256((target/'MarkdownFigureTool.exe').read_bytes()).hexdigest(),'archive':archive.relative_to(ROOT).as_posix(),'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'file_count':len(files),'uncompressed_bytes':sum(f['bytes'] for f in files),'browser':browser_info}
(ROOT/'versions').mkdir(exist_ok=True)
(ROOT/'versions'/f'{version}.json').write_text(json.dumps(index,indent=2)+'\n',encoding='utf-8')
print(json.dumps(index,indent=2),flush=True)
