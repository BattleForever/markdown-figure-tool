from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
version = json.loads((ROOT / 'project.json').read_text(encoding='utf-8'))['version']
exe = ROOT / 'releases' / ('v' + version) / 'MarkdownFigureTool.exe'
artifacts = ROOT / 'tests' / 'artifacts' / ('exe-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
artifacts.mkdir(parents=True)
source = artifacts / '打包测试 中文(1).md'
source.write_text('''# 打包版测试

```python
print("<svg>普通代码</svg>")
```

<svg viewBox="0 0 600 130"><rect x="5" y="5" width="590" height="120" fill="#e0f2fe"/><text x="30" y="80" font-size="30">打包版 SVG 测试</text></svg>

```mermaid
sequenceDiagram
  participant 用户
  participant 转换器
  用户->>转换器: 拖入 Markdown
  转换器-->>用户: 新文件和 PNG 图片
```

```html
<h2>Canvas in packaged EXE</h2><canvas id="c" width="600" height="100"></canvas><script>let ctx=document.querySelector('#c').getContext('2d');ctx.fillStyle='#f59e0b';ctx.fillRect(10,10,580,80);</script>
```

正文末尾。
''', encoding='utf-8')
before = source.read_bytes()
report = artifacts / 'packaged_report.json'
completed = subprocess.run([str(exe), '--cli', str(source), '--report', str(report)], timeout=120, capture_output=True)
assert completed.returncode == 0, (completed.returncode, completed.stderr)
results = json.loads(report.read_text(encoding='utf-8'))
assert len(results) == 1
assert results[0]['total'] == results[0]['succeeded'] == 3, results
assert not results[0]['failures']
assert source.read_bytes() == before
assert '普通代码' in Path(results[0]['output']).read_text(encoding='utf-8')
print(json.dumps({'packaged_exe_pass': True, 'figures': 3, 'source_unchanged': True, 'exe_sha256': hashlib.sha256(exe.read_bytes()).hexdigest(), 'report': str(report)}, ensure_ascii=False))
