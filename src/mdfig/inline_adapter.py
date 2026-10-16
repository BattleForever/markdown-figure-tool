"""Keep prose selectable while replacing simple exported inline style tags."""
from html import escape
from html.parser import HTMLParser
import re

from .html_adapter import layout_style
from .parser import Positions, mask_code


def inline_replacements(source, figures):
    masked = list(mask_code(source))
    for figure in figures:
        masked[figure.start:figure.end] = ['\n' if c=='\n' else ' ' for c in source[figure.start:figure.end]]
    parser = Positions(''.join(masked))
    parser.feed(''.join(masked))
    replacements = []
    count = 0
    for node in parser.nodes:
        if node.tag not in {'text','badge'} or node.end is None:
            continue
        fragment = source[node.start:node.end]
        opening = re.match(r'<[^>]+>', fragment)
        closing = re.search(r'</(?:text|badge)\s*>$', fragment, re.I)
        if not opening or not closing or '{' in fragment or '}' in fragment:
            continue
        class Attrs(HTMLParser):
            def handle_starttag(self, tag, attrs):
                self.attrs = dict(attrs)
        attributes = Attrs()
        attributes.feed(opening[0])
        attrs = getattr(attributes,'attrs',{})
        style = layout_style('text', attrs)
        if node.tag == 'badge':
            style = 'display:inline-block;border-radius:6px;padding:2px 7px;background:#f1f3f5;font-size:12px;' + style
        replacements.append((node.start,node.start+opening.end(),'<span style="'+escape(style,quote=True)+'">'))
        replacements.append((node.start+closing.start(),node.end,'</span>'))
        count += 1
    return replacements, count
