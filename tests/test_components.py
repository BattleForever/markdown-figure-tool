"""Real exported dialect patterns: preserve a complete component boundary."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from mdfig.parser import find_figures


class ComponentSpans(unittest.TestCase):
    def test_grid_is_one_figure_with_caption(self):
        source = '<grid columns={2}><grid-item><box>A</box></grid-item><grid-item><box>B</box></grid-item></grid>\n<caption>双模态</caption>'
        figures = find_figures(source)
        self.assertEqual(len(figures), 1)
        self.assertEqual(figures[0].content, source)

    def test_state_declarations_stay_with_component(self):
        source = '说明\n\n{@body const [mode,setMode] = DIL.useState("a")}\n{@body const choices={a:{title:"A"}}}\n<box>{choices[mode].title}</box>\n\n正文'
        figure, = find_figures(source)
        self.assertTrue(figure.content.startswith('{@body'))
        self.assertTrue(figure.content.endswith('</box>'))

    def test_writing_block_is_not_lost(self):
        figure, = find_figures('<WritingBlock id="1">**标题**\n\n1. 任务</WritingBlock>')
        self.assertIn('1. 任务', figure.content)


if __name__ == '__main__':
    unittest.main()
