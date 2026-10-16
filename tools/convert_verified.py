"""Convert with the versioned EXE and audit that existing local files stay intact."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
from urllib.parse import unquote
import re

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('source',type=Path)
parser.add_argument('--audit',type=Path,required=True)
args=parser.parse_args()
source=args.source.resolve()
version=json.loads((ROOT/'project.json').read_text(encoding='utf-8'))['version']
release=json.loads((ROOT/'versions'/('v'+version+'.json')).read_text(encoding='utf-8'))
exe=ROOT/release['executable']
digest=lambda path:hashlib.sha256(path.read_bytes()).hexdigest()
assert digest(exe)==release['exe_sha256']
protected=[source]
old_assets=source.with_name(source.stem+'_assets')
if old_assets.is_dir():
    protected += [p for p in old_assets.rglob('*') if p.is_file()]
    record=old_assets/'转换记录.json'
    if record.is_file():
        original=Path(json.loads(record.read_text(encoding='utf-8'))['source']).resolve()
        if original.parent==source.parent and original.is_file():protected.append(original)
baseline={str(p):digest(p) for p in protected}
args.audit.parent.mkdir(parents=True,exist_ok=True)
raw=args.audit.with_suffix('.conversion.json')
completed=subprocess.run([str(exe),'--cli',str(source),'--report',str(raw)],capture_output=True,timeout=150)
results=json.loads(raw.read_text(encoding='utf-8'))
assert completed.returncode==0,results
assert all(result.get('output') and result['succeeded']==result['total'] and not result['failures'] for result in results),results
assert all(digest(Path(p))==value for p,value in baseline.items()),'An existing file changed'
for result in results:
    output=Path(result['output'])
    text=output.read_text(encoding='utf-8-sig')
    images=[output.parent/unquote(url) for url in re.findall(r'!\[图形 \d+\]\(<([^>]+)>\)',text)]
    assert len(images)==result['succeeded'] and all(p.is_file() and p.stat().st_size>100 for p in images)
    record=json.loads((Path(result['assets'])/'转换记录.json').read_text(encoding='utf-8'))
    assert record['software_version']==version and record['source_unchanged']
audit={'version':version,'executable':str(exe),'exe_sha256':digest(exe),'existing_files_unchanged':True,'protected_sha256':baseline,'results':results}
args.audit.write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'audit':str(args.audit),'output':[r['output'] for r in results],'figures':[r['succeeded'] for r in results],'existing_files_unchanged':True},ensure_ascii=False),flush=True)
