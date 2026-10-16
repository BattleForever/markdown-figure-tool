"""Exercise real browser rendering, failure accounting, using synthetic fixtures."""
from dataclasses import asdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mdfig.converter import convert_file
from mdfig.renderer import RenderSession

artifacts = ROOT / 'tests' / 'artifacts' / datetime.now().strftime('%Y%m%d-%H%M%S')
artifacts.mkdir(parents=True)
sample = artifacts / '综合样例 空格(1).md'
sample.write_text('''# 综合测试

保留普通代码：

```python
print("<svg>this is ordinary code</svg>")
```

<box border radius="xl" padding={3} gap={2}>
<text weight="bold" size="lg">脚本绘制的衰减振动</text>
<AppBlock><div id="plot"><svg viewBox="0 0 600 200" style="width:100%;height:auto"><line x1="20" y1="100" x2="580" y2="100" stroke="#aaa"/><path id="wave" fill="none" stroke="#2563eb" stroke-width="2"/></svg><script>const p=[];for(let i=0;i<560;i++){let t=i/560;p.push((i?'L':'M')+(20+i)+','+(100-70*Math.exp(-3*t)*Math.sin(2*Math.PI*12*t)));}document.querySelector('#wave').setAttribute('d',p.join(' '));</script></div></AppBlock>
<row gap={2}><box width="20px" height="3px" background="#2563eb"/><text size="sm">振铃曲线</text></row>
<caption>测试图形</caption>
</box>

```html
<h2>Canvas 测试</h2><canvas id="c" width="600" height="180"></canvas><script>const c=document.querySelector('#c').getContext('2d');c.fillStyle='#0d9488';c.fillRect(20,20,420,100);c.fillStyle='#fff';c.font='24px sans-serif';c.fillText('Canvas OK',40,80);</script>
```

```mermaid
flowchart LR
 A[读取 Markdown] --> B{发现图形代码?}
 B -->|是| C[渲染为 PNG]
 C --> D[生成新 Markdown]
```

<svg viewBox="0 0 600 100"><rect x="10" y="10" width="580" height="80" fill="#eef2ff"/><text x="30" y="60" font-size="24">纯 SVG：中文正常</text></svg>

```html
<div><img src="local_asset.svg" width="500"></div>
```

故意失败，必须保留原代码：

```html
<div>故意失败</div><script>throw new Error('EXPECTED_FAILURE')</script>
```

```mermaid
this is not a valid mermaid diagram
```

结束正文原样保留。
''', encoding='utf-8')
(artifacts / 'local_asset.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="500" height="110"><rect width="500" height="110" fill="#fef3c7"/><text x="20" y="65" font-size="24">Local relative image OK</text></svg>', encoding='utf-8')
original = sample.read_bytes()
with RenderSession() as renderer:
    result = convert_file(sample, renderer, print)
    assert result.total == 7, asdict(result)
    assert result.succeeded == 5, asdict(result)
    assert len(result.failures) == 2
    assert sample.read_bytes() == original
    converted = Path(result.output).read_text(encoding='utf-8')
    assert 'EXPECTED_FAILURE' in converted
    assert 'this is not a valid mermaid diagram' in converted
    assert 'print("<svg>this is ordinary code</svg>")' in converted
    assert len(list(Path(result.assets).glob('*.png'))) == 5
    results = [asdict(result)]
(artifacts / 'integration_report.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
print('INTEGRATION_PASS', artifacts)
