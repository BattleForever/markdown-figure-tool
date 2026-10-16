"""Browser-level acceptance of state, loops, SVG attributes and full layouts."""
from datetime import datetime
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from mdfig.components import compile_component
from mdfig.converter import convert_file
from mdfig.html_adapter import BASE_CSS
from mdfig.parser import Figure, find_figures
from mdfig.renderer import RenderSession, RenderOptions, resource_path

out = ROOT / 'tests/artifacts' / ('components-' + datetime.now().strftime('%Y%m%d-%H%M%S'))
out.mkdir(parents=True)
sample = '''{@body const [mode,setMode] = DIL.useState("a")}
{@body const choices={a:{title:"选择 A",items:["甲","乙"]},b:{title:"选择 B",items:["丙","丁"]}}}
<box border radius="xl" padding={3} gap={2}>
 <row justify="between">**原始标题**<badge color="success">成功</badge></row>
 <radio-group value={mode} onChange={setMode}><radio value="a">A</radio><radio value="b">B</radio></radio-group>
 <title>{choices[mode].title}</title>
 <list marker="number">{#each choices[mode].items as item}<list-item>{item}</list-item>{/each}</list>
 <grid columns={2} gap={2}><grid-item><box background="surface-secondary" padding={2}>左列</box></grid-item><grid-item>右列</grid-item></grid>
 <svg viewBox="0 0 240 80" width="240">
 {#each Array.from({length:12},(_,i)=>i) as i}<line x1={10+i*18} y1={10} x2={10+i*18} y2={70} stroke="#0d9488" strokeWidth="2"/>{/each}
 <circle cx="40" cy="40" r="20" fill="#0d9488" fillOpacity="0.18"/>
 <path d={`M ${120+5} 20 l 40 30`} stroke="#0d9488" strokeWidth="2"/>
 </svg>
</box>'''
with RenderSession(RenderOptions(wait_ms=100)) as session:
    figure, = find_figures(sample)
    state = session.render(figure, out, out / 'components.png')
    assert state['svg_lines'] == 12, state
    assert state['svg_paths'] == 1 and state['grids'] == 1, state
    page = session.browser.new_page(viewport={'width':960,'height':900})
    page.on('pageerror', lambda error: print('COMPONENT_ERROR', str(error), flush=True))
    page.set_content('<style>' + BASE_CSS + '</style><main id="mdfig-capture"></main>')
    for library in ('vendor/preact/preact.umd.js','vendor/preact/hooks.umd.js','vendor/markdown-it/markdown-it.min.js','vendor/babel/babel.min.js','assets/component-runtime.js'):
        page.add_script_tag(content=resource_path(library).read_text(encoding='utf-8'))
    page.evaluate('(source)=>window.__mdfigCompile(source)', compile_component(sample))
    assert page.locator('strong').inner_text() == '原始标题'
    assert page.locator('svg circle').get_attribute('fill-opacity') == '0.18'
    assert page.locator('svg path').get_attribute('d') == 'M 125 20 l 40 30'
    assert page.locator('li').all_inner_texts() == ['甲','乙']
    page.locator('input[value=b]').check()
    page.wait_for_timeout(250)
    print('AFTER_CHECK', page.locator('li').all_inner_texts(), page.locator('input').evaluate_all('(els)=>els.map(e=>({checked:e.checked,value:e.value}))'), flush=True)
    assert page.locator('li').all_inner_texts() == ['丙','丁']
    assert '选择 B' in page.inner_text('main')
    page.screenshot(path=str(out/'state-b.png'),full_page=True)
    page.close()
    bad = Figure(0,0,'html','<box><unimplemented-chart/></box>',1)
    try:
        session.render(bad,out,out/'bad.png')
    except Exception as error:
        assert '尚不支持组件' in str(error), str(error)
    else:
        raise AssertionError('Unknown components must not be silently accepted')
(out/'report.json').write_text(json.dumps({'state_and_each':True,'radio_state_changes':True,'markdown_bold':True,'svg_attributes_and_template_path':True,'grid_whole':True,'unknown_component_rejected':True,**state},indent=2),encoding='utf-8')
print('COMPONENT_PASS',out,flush=True)
