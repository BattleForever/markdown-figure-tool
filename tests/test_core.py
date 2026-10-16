import base64
import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote, unquote, urlparse
import re

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from mdfig.converter import convert_file
from mdfig.html_adapter import adapt_html
from mdfig.parser import find_figures
from mdfig.renderer import RenderOptions

SVG = '<svg viewBox="0 0 100 40"><path d="M0 0L90 30"/></svg>'
PNG = base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aZ1sAAAAASUVORK5CYII=')


class FakeRenderer:
    options = RenderOptions()

    def render(self, figure, source_dir, output):
        if "FAIL" in figure.content:
            raise RuntimeError("fixture failure")
        output.write_bytes(PNG)
        return {"css_width": 100, "css_height": 50, "scale": 2}


class ParserTests(unittest.TestCase):
    def test_nested_wrappers_keep_whole_figure(self):
        text = 'before\n<box padding={3}><row><box width="3px"/><text>title</text></row>' + SVG + '</box>\nafter'
        figures = find_figures(text)
        self.assertEqual(len(figures), 1)
        self.assertTrue(figures[0].content.startswith('<box'))
        self.assertTrue(figures[0].content.endswith('</box>'))

    def test_fenced_programming_code_is_untouched(self):
        text = '```python\nprint("' + SVG + '")\n```\n' + SVG
        figures = find_figures(text)
        self.assertEqual(len(figures), 1)
        self.assertGreater(figures[0].start, text.index('```\n'))

    def test_html_and_mermaid_fences(self):
        text = '```html\n<div>title</div>\n```\n\n```mermaid\nflowchart LR\nA-->B\n```'
        self.assertEqual([item.kind for item in find_figures(text)], ['html', 'mermaid'])
        self.assertEqual(len(find_figures(text, False)), 1)

    def test_script_pseudo_markup_not_parsed(self):
        text = '<div>' + SVG + '<script>const s="<svg><div>";</script></div>'
        self.assertEqual(len(find_figures(text)), 1)
        self.assertEqual(find_figures(text)[0].content, text)

    def test_sibling_script_is_included(self):
        text = SVG + '\n<script>document.querySelector("path").setAttribute("d","M1 1L3 3")</script>\ntext'
        self.assertIn('</script>', find_figures(text)[0].content)

    def test_adapter_keeps_original_math_and_svg(self):
        text = '<box padding={3}><text weight="medium">title</text>' + SVG + '<script>let x=Math.exp(-3);</script></box>'
        converted = adapt_html(text)
        self.assertIn(SVG, converted)
        self.assertIn('Math.exp(-3)', converted)
        self.assertIn('<span', converted)
        self.assertNotIn('<box', converted)

    def test_inline_code_is_untouched(self):
        source = '示例：`<div>do not render</div>`\n\n' + SVG
        figures = find_figures(source)
        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].content, SVG)

    def test_leading_styles_and_helpers_are_retained(self):
        source = '<style>svg{color:red}</style>\n<script>const helper=3;</script>\n' + SVG
        figures = find_figures(source)
        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].content, source)

    def test_fences_between_raw_blocks_are_not_swallowed(self):
        source = SVG + '\n```python\nprint(1)\n```\n<script>console.log(1)</script>'
        self.assertEqual(find_figures(source)[0].content, SVG)

    def test_neighboring_figures_do_not_share_replacement_spans(self):
        source = SVG + '<script>let a=1;</script>\n' + SVG
        figures = find_figures(source)
        self.assertEqual(len(figures), 2)
        self.assertLessEqual(figures[0].end, figures[1].start)

    def test_indented_code_example_is_not_a_figure(self):
        source = 'Example:\n\n    ' + SVG + '\n\nActual:\n\n' + SVG
        figures = find_figures(source)
        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].start, source.rindex('<svg'))


class ConverterTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='mdfig-unit-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_bom_crlf_source_and_prose_are_preserved(self):
        source = self.root / '中文 空格(1).md'
        original = b'\xef\xbb\xbf' + ('标题\r\n\r\n' + SVG + '\r\n\r\n正文\r\n').encode('utf-8')
        source.write_bytes(original)
        result = convert_file(source, FakeRenderer())
        self.assertEqual(source.read_bytes(), original)
        output = Path(result.output).read_bytes()
        self.assertTrue(output.startswith(b'\xef\xbb\xbf'))
        self.assertIn('标题\r\n\r\n'.encode(), output)
        self.assertTrue(output.endswith('\r\n\r\n正文\r\n'.encode()))
        self.assertTrue((Path(result.assets) / 'figure_001.png').is_file())
        self.assertIn('<' + quote('./中文 空格(1)_图像版_assets/figure_001.png', safe='/') + '>', output.decode('utf-8-sig'))

    def test_repeated_runs_never_overwrite(self):
        source = self.root / 'sample.md'
        source.write_text(SVG, encoding='utf-8')
        first = convert_file(source, FakeRenderer())
        before = Path(first.output).read_bytes()
        second = convert_file(source, FakeRenderer())
        self.assertNotEqual(first.output, second.output)
        self.assertEqual(Path(first.output).read_bytes(), before)
        self.assertEqual(source.read_text(), SVG)

    def test_rebuild_old_image_version_from_verified_original(self):
        source = self.root / 'again.md'
        source.write_text(SVG, encoding='utf-8')
        first = convert_file(source, FakeRenderer())
        previous = Path(first.output).read_bytes()
        second = convert_file(first.output, FakeRenderer())
        self.assertEqual(second.source, str(source.resolve()))
        self.assertNotEqual(first.output, second.output)
        self.assertEqual(Path(first.output).read_bytes(), previous)

    def test_inline_styles_do_not_touch_code_or_failed_figures(self):
        source = self.root / 'inline.md'
        example = '`<text color="success">示例</text>`'
        failed = '<box>FAIL<text color="success">保留</text></box>'
        source.write_text(SVG+'\n\n'+example+'\n\n<text color="success">正文</text>\n\n'+failed, encoding='utf-8')
        result = convert_file(source, FakeRenderer())
        output = Path(result.output).read_text(encoding='utf-8')
        self.assertIn(example, output)
        self.assertIn(failed, output)
        self.assertIn('color:#15803d', output)
        self.assertIn('>正文</span>', output)

    def test_failed_block_is_preserved_exactly(self):
        source = self.root / 'partial.md'
        failed = '<div>FAIL</div>'
        source.write_text(SVG + '\n\n' + failed + '\nunchanged', encoding='utf-8')
        result = convert_file(source, FakeRenderer())
        self.assertEqual((result.succeeded, result.total), (1, 2))
        self.assertIn(failed + '\nunchanged', Path(result.output).read_text(encoding='utf-8'))

    def test_all_failures_create_no_output(self):
        source = self.root / 'failed.md'
        source.write_text('<div>FAIL</div>', encoding='utf-8')
        result = convert_file(source, FakeRenderer())
        self.assertFalse(result.output)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_no_figures_create_no_output(self):
        source = self.root / 'plain.md'
        source.write_text('# title\n```python\nprint(1)\n```', encoding='utf-8')
        self.assertEqual(convert_file(source, FakeRenderer()).total, 0)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_cancellation_publishes_nothing(self):
        source = self.root / 'cancel.md'
        source.write_text(SVG, encoding='utf-8')
        with self.assertRaisesRegex(RuntimeError, '取消'):
            convert_file(source, FakeRenderer(), cancelled=lambda: True)
        self.assertEqual(len(list(self.root.iterdir())), 1)

    def test_hash_and_percent_in_filename_do_not_break_image_urls(self):
        source = self.root / '笔记#号%20 空格.md'
        source.write_text(SVG, encoding='utf-8')
        result = convert_file(source, FakeRenderer())
        markdown = Path(result.output).read_text(encoding='utf-8')
        url = re.search(r'!\[.*?\]\(<(.*?)>\)', markdown)[1]
        self.assertFalse(urlparse(url).fragment)
        self.assertFalse(urlparse(url).query)
        self.assertTrue((source.parent / unquote(url)).is_file())

    def test_parallel_conversions_reserve_distinct_outputs(self):
        source = self.root / 'parallel.md'
        source.write_text(SVG, encoding='utf-8')
        with ThreadPoolExecutor(max_workers=6) as pool:
            results = list(pool.map(lambda _: convert_file(source, FakeRenderer()), range(6)))
        self.assertEqual(len({result.output for result in results}), 6)
        for result in results:
            self.assertTrue(Path(result.output).is_file())
            self.assertTrue((Path(result.assets) / 'figure_001.png').is_file())
        self.assertEqual(source.read_text(encoding='utf-8'), SVG)


if __name__ == '__main__':
    unittest.main(verbosity=2)
