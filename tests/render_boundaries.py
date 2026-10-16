"""Regression checks for leading styles, blocked resources and broken images."""
from datetime import datetime
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mdfig.converter import convert_file
from mdfig.renderer import RenderSession

artifacts = ROOT / 'tests' / 'artifacts' / ('boundaries-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
artifacts.mkdir(parents=True)
source = artifacts / '边界测试.md'
source.write_text('''# 保留示例 `<div>ordinary inline code</div>`

<style>rect{fill:rgb(13,148,136)}</style>
<svg viewBox="0 0 400 100" width="400"><rect width="400" height="100"/></svg>

```html
<div>远程 CSS 不应静默丢失</div><link rel="stylesheet" href="https://blocked.invalid/style.css">
```

```html
<div><img src="missing.png"></div>
```

```html
<div><img src="data:image/png;base64,invalid"></div>
```
''', encoding='utf-8')
with RenderSession() as renderer:
    result = convert_file(source, renderer, print)
assert result.total == 4
assert result.succeeded == 1
assert len(result.failures) == 3
assert '`<div>ordinary inline code</div>`' in Path(result.output).read_text(encoding='utf-8')
from PIL import Image
pixel = Image.open(Path(result.assets) / 'figure_001.png').convert('RGB').getpixel((200, 100))
assert pixel == (13, 148, 136), pixel
(artifacts / 'boundary_report.json').write_text(json.dumps({'total': 4, 'success': 1, 'expected_failures_preserved': 3, 'leading_css_applied': True, 'inline_code_preserved': True}, indent=2), encoding='utf-8')
print('BOUNDARY_PASS', artifacts)
