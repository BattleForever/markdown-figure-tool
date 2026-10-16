"""Exercise the shipped runtime, including rebuilding an old image-version input."""
from pathlib import Path
from datetime import datetime
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT/'project.json').read_text(encoding='utf-8'))['version']
exe = ROOT/'releases'/('v'+version)/'MarkdownFigureTool.exe'
out = ROOT/'tests/artifacts'/('packaged-components-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True)
source = out/'网格与表达式.md'
source.write_text('''# 正文保留

<text color="success">成功标记</text>

{@body const n=12}
<grid columns={2} gap={2}><grid-item><box border padding={2}>**左列**<svg viewBox="0 0 240 80">{#each Array.from({length:n},(_,i)=>i) as i}<line x1={10+i*18} y1={10} x2={10+i*18} y2={70} stroke="#0d9488" strokeWidth="2"/>{/each}</svg></box></grid-item><grid-item><box border padding={2}>右列</box></grid-item></grid>
<caption>说明文字</caption>
''',encoding='utf-8')
before = source.read_bytes()
paths = [source]
report = out/'report.json'
completed = subprocess.run([str(exe),'--cli',*map(str,paths),'--report',str(report)],capture_output=True,timeout=120)
assert completed.returncode==0,(completed.returncode,completed.stderr)
results = json.loads(report.read_text(encoding='utf-8'))
assert len(results)==len(paths)
for result in results:
    assert result['total']==result['succeeded'] and not result['failures'],result
    record=json.loads((Path(result['assets'])/'转换记录.json').read_text(encoding='utf-8'))
    assert record['software_version']==version
    assert record['inline_styles_adapted']>=1
    assert any(f['svg_lines']==12 and f['grids']==1 for f in record['figures']),record
assert source.read_bytes()==before
rebuild_report=out/'rebuild.json'
completed=subprocess.run([str(exe),'--cli',results[0]['output'],'--report',str(rebuild_report)],capture_output=True,timeout=40)
assert completed.returncode==0,(completed.returncode,completed.stderr)
rebuilt=json.loads(rebuild_report.read_text(encoding='utf-8'))[0]
assert rebuilt['source']==str(source.resolve()) and rebuilt['output']!=results[0]['output'],rebuilt
assert source.read_bytes()==before
gui_report=out/'gui-components.json'
completed=subprocess.run([str(exe),'--diagnose-drop',str(gui_report),'--diagnose-drop-count','100','--diagnose-convert',str(source)],capture_output=True,timeout=50)
assert completed.returncode==0,(completed.returncode,completed.stderr)
gui=json.loads(gui_report.read_text(encoding='utf-8'))
assert gui['passed'] and gui['delivered']==100 and gui['max_heartbeat_gap']<1,gui
assert len(gui['results'])==1 and gui['results'][0]['succeeded']==1,gui
print(json.dumps({'packaged_components':True,'figures':[r['succeeded'] for r in results],'verified_original_rebuild':True,'gui_native_component_drops':100,'gui_max_heartbeat_gap':gui['max_heartbeat_gap'],'exe_sha256':hashlib.sha256(exe.read_bytes()).hexdigest(),'report':str(report)},ensure_ascii=False),flush=True)
