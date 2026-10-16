"""Locate replaceable figures without changing surrounding Markdown text."""
from dataclasses import dataclass, field
from html.parser import HTMLParser
import re
from markdown_it import MarkdownIt
from .components import body_directives


@dataclass
class Figure:
    start: int
    end: int
    kind: str
    content: str
    line: int


@dataclass
class Node:
    tag: str
    start: int
    end: int | None = None
    parent: object = None
    children: list = field(default_factory=list)


VOID = set("area base br col embed hr img input link meta param source track wbr".split())
ROOTS = {"box", "appblock", "svg", "canvas", "div", "section", "figure", "table", "html", "article", "grid", "row", "list", "radio-group", "writingblock"}


class Positions(HTMLParser):
    def __init__(self, source):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = [0]
        for match in re.finditer("\n", source):
            self.lines.append(match.end())
        self.nodes = []
        self.stack = []

    def char_position(self):
        line, column = self.getpos()
        return self.lines[line - 1] + column

    def handle_starttag(self, tag, attrs):
        node = Node(tag, self.char_position(), parent=self.stack[-1] if self.stack else None)
        if node.parent:
            node.parent.children.append(node)
        self.nodes.append(node)
        if tag in VOID:
            node.end = self.char_position() + len(self.get_starttag_text())
        else:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        node = Node(tag, self.char_position(), self.char_position() + len(self.get_starttag_text()), self.stack[-1] if self.stack else None)
        if node.parent:
            node.parent.children.append(node)
        self.nodes.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index].tag == tag:
                end = self.source.find(">", self.char_position()) + 1
                self.stack[index].end = end
                del self.stack[index:]
                break


def fences(source):
    """Yield all fences, including ordinary code that must be excluded from HTML parsing."""
    lines = source.splitlines(keepends=True)
    offset = 0
    index = 0
    while index < len(lines):
        match = re.match(r"^ {0,3}(`{3,}|~{3,})([^\r\n]*)", lines[index])
        if not match:
            offset += len(lines[index])
            index += 1
            continue
        marker = match[1]
        language = match[2].strip().split()[0].lower() if match[2].strip() else ""
        start = offset
        opening_end = offset + len(lines[index])
        offset = opening_end
        index += 1
        closing_start = None
        while index < len(lines):
            line = lines[index]
            if re.match(r"^ {0,3}" + re.escape(marker[0]) + "{" + str(len(marker)) + r",}[ \t]*(?:\r?\n)?$", line):
                closing_start = offset
                # Preserve the closing line ending outside the replacement span.
                end = offset + len(line.rstrip("\r\n"))
                offset += len(line)
                index += 1
                yield start, end, language, source[opening_end:closing_start]
                break
            offset += len(line)
            index += 1
        if closing_start is None:
            yield start, len(source), "unclosed", ""


def mask_code(source, spans=None):
    """Mask code examples while retaining original character positions."""
    masked = list(source)
    exclusions = list(spans if spans is not None else fences(source))
    line_offsets = [0]
    for line in source.splitlines(keepends=True):
        line_offsets.append(line_offsets[-1] + len(line))
    for token in MarkdownIt('commonmark').parse(source):
        if token.type in {'code_block', 'fence'} and token.map:
            start_line, end_line = token.map
            exclusions.append((line_offsets[start_line], line_offsets[end_line], '', ''))
    for start, end, _, _ in exclusions:
        masked[start:end] = ["\n" if char == "\n" else " " for char in source[start:end]]
    # Inline backtick code is documentation, not a visual HTML block.
    scan = "".join(masked)
    position = 0
    while position < len(scan):
        if scan[position] != "`" or (position and scan[position - 1] == "\\"):
            position += 1
            continue
        opening = re.match(r"`+", scan[position:])[0]
        closing = re.search(r"(?<!`)" + re.escape(opening) + r"(?!`)", scan[position + len(opening):])
        if closing:
            end = position + len(opening) + closing.end()
            masked[position:end] = ["\n" if char == "\n" else " " for char in scan[position:end]]
            position = end
        else:
            position += len(opening)
    return "".join(masked)


def find_figures(source, include_mermaid=True):
    spans = list(fences(source))
    figures = []
    for start, end, language, content in spans:
        if language in {"html", "htm", "svg"} and re.search(r"<[A-Za-z!]", content):
            figures.append(Figure(start, end, "html", content, source.count("\n", 0, start) + 1))
        elif language == "mermaid" and include_mermaid:
            figures.append(Figure(start, end, "mermaid", content, source.count("\n", 0, start) + 1))
    scan = mask_code(source, spans)
    masked = list(scan)
    declarations = list(body_directives(scan))
    for start, end, _ in declarations:
        masked[start:end] = ["\n" if char == "\n" else " " for char in scan[start:end]]
    scan = "".join(masked)
    parser = Positions(scan)
    parser.feed(scan)
    selected = []
    for node in parser.nodes:
        if node.tag not in ROOTS or node.end is None:
            continue
        parent = node.parent
        has_root_parent = False
        while parent:
            if parent.tag in ROOTS:
                has_root_parent = True
                break
            parent = parent.parent
        if not has_root_parent:
            selected.append(node)
    previous_raw_end = -1
    for node in selected:
        start, end = node.start, node.end
        # Keep preceding styles/helpers without crossing ordinary code examples.
        siblings = [item for item in parser.nodes if item.parent is node.parent]
        for sibling in reversed(siblings):
            if sibling.end is None or sibling.end > start:
                continue
            if source[sibling.end:start].strip() or sibling.start < previous_raw_end:
                break
            if sibling.tag not in {"script", "style"}:
                break
            start = sibling.start
        # Keep sibling scripts/styles that calculate or style this figure.
        for sibling in parser.nodes:
            if sibling.start < end or sibling.parent is not node.parent:
                continue
            if source[end:sibling.start].strip():
                break
            if sibling.tag not in {"script", "style", "caption"} or sibling.end is None:
                break
            end = sibling.end
        # State/helpers immediately before the root belong to that same component.
        for decl_start, decl_end, _ in reversed(declarations):
            if decl_end <= start and not source[decl_end:start].strip():
                start = decl_start
        figures.append(Figure(start, end, "html", source[start:end], source.count("\n", 0, start) + 1))
        previous_raw_end = end
    figures.sort(key=lambda item: item.start)
    previous_end = -1
    for figure in figures:
        if figure.start < previous_end:
            raise ValueError("检测到重叠的图形块，请检查 HTML 标签是否配对。")
        previous_end = figure.end
    return figures

