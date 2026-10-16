"""Translate exported layout wrappers; never recreate SVG paths or plot data."""
from html import escape
from html.parser import HTMLParser
import re

COLORS = {'default':'#0f172a','secondary':'#64748b','tertiary':'#94a3b8','success':'#15803d','danger':'#dc2626','warning':'#b45309','primary':'#0f766e','strong':'#475569','subtle':'#e2e8f0','surface-secondary':'#f5f6f8','surface-primary':'#ffffff'}

BASE_CSS = """
html,body{margin:0;background:#fff;color:#172033;font-family:'Microsoft YaHei','Segoe UI',Arial,sans-serif}
*{box-sizing:border-box}body{padding:0}#mdfig-capture{padding:20px;display:flow-root;overflow:visible}
svg{max-width:100%;height:auto;font-family:inherit}canvas{max-width:100%}img{max-width:100%}
table{border-collapse:collapse}td,th{border:1px solid #cbd5e1;padding:8px 12px}
.mdfig-component{overflow-wrap:anywhere}.mdfig-component input[type=radio]{accent-color:#0f766e;margin:0}
.mdfig-component svg[data-mdfig-icon]{max-width:none;height:18px;width:18px;display:inline-block;vertical-align:middle}
.mdfig-markdown p{margin:0 0 .7em}.mdfig-markdown p:last-child{margin-bottom:0}
.mdfig-markdown ul,.mdfig-markdown ol{margin:.4em 0;padding-left:1.5em}.mdfig-markdown li+li{margin-top:.25em}
.mdfig-markdown pre{overflow:auto;padding:12px;background:#f5f6f8;border-radius:8px}
.mdfig-markdown code{font-family:Consolas,monospace}.mdfig-component strong{font-weight:600}
"""


def value(raw):
    return (raw or "").strip("{}\"' ")


def space(raw, default="0"):
    raw = value(raw)
    if re.fullmatch(r"\d+(?:\.\d+)?", raw):
        return f"{float(raw) * 4:g}px"
    return raw if re.fullmatch(r"[\d.]+(?:px|rem|em|%)", raw) else default


def layout_style(tag, attrs):
    styles = []
    if tag == "row":
        styles += ["display:flex", "align-items:center"]
    elif tag == "box":
        styles += ["display:flex", "flex-direction:column"]
    elif tag == "text":
        styles += ["display:inline-block"]
    if "border" in attrs:
        styles += ["border:1px solid #dce3ec"]
    if "radius" in attrs:
        styles += ["border-radius:" + {"sm": "4px", "md": "6px", "lg": "10px", "xl": "14px"}.get(value(attrs["radius"]), "8px")]
    for key in ("padding", "gap"):
        if key in attrs:
            styles.append(key + ":" + space(attrs[key]))
    for key in ("width", "height", "background"):
        if key in attrs and value(attrs[key]):
            raw = value(attrs[key])
            if key in {"width", "height"} and raw.isdigit():
                raw += "px"
            styles.append(key + ":" + COLORS.get(raw, raw))
    if value(attrs.get("wrap")) == "wrap":
        styles += ["flex-wrap:wrap"]
    if value(attrs.get('justify')):
        styles += ['justify-content:' + {'between':'space-between','center':'center','end':'flex-end','start':'flex-start'}.get(value(attrs['justify']), 'flex-start')]
    if value(attrs.get('textalign')):
        styles += ['text-align:' + value(attrs['textalign'])]
    if value(attrs.get("align")):
        styles += ["align-items:" + {"center": "center", "start": "flex-start", "end": "flex-end"}.get(value(attrs["align"]), "center")]
    if value(attrs.get("size")):
        styles += ["font-size:" + {"xs": "12px", "sm": "14px", "md": "16px", "lg": "19px", "xl": "22px"}.get(value(attrs["size"]), "16px")]
    if value(attrs.get("weight")):
        styles += ["font-weight:" + {"medium": "500", "semibold": "600", "bold": "700"}.get(value(attrs["weight"]), "400")]
    if value(attrs.get("color")):
        raw = value(attrs["color"])
        styles += ["color:" + COLORS.get(raw, raw)]
    if attrs.get("style"):
        styles.append(attrs["style"])
    return ";".join(styles)


class Adapter(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.parts = []
        self.stack = []
        self.svg_depth = 0
        self.table_depth = 0

    def mapping(self, tag):
        if tag in {"html", "head", "body"}:
            return ""
        if tag in {"meta", "base", "cite"}:
            return ""
        if tag in {"box", "row", "appblock"}:
            return "div"
        if tag == "text" and not self.svg_depth:
            return "span"
        if tag == "caption" and not self.table_depth:
            return "div"
        return tag

    def start(self, tag, attrs, closed):
        mapped = self.mapping(tag)
        if mapped:
            if mapped != tag:
                styles = layout_style(tag, dict(attrs))
                if tag == "caption":
                    styles += ";color:#64748b;font-size:13px;line-height:1.6"
                self.parts.append(f'<{mapped} style="{escape(styles, quote=True)}">')
                if closed:
                    self.parts.append(f"</{mapped}>")
            else:
                self.parts.append(self.get_starttag_text())
        if not closed and tag not in {"meta", "base", "br", "img", "hr", "input", "link", "source", "wbr"}:
            self.stack.append((tag, mapped))
            self.svg_depth += tag == "svg"
            self.table_depth += tag == "table"

    def handle_starttag(self, tag, attrs):
        self.start(tag, attrs, False)

    def handle_startendtag(self, tag, attrs):
        self.start(tag, attrs, True)

    def handle_endtag(self, tag):
        mapped = tag
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                mapped = self.stack[index][1]
                removed = self.stack[index:]
                self.svg_depth -= sum(item[0] == "svg" for item in removed)
                self.table_depth -= sum(item[0] == "table" for item in removed)
                del self.stack[index:]
                break
        if mapped:
            self.parts.append(f"</{mapped}>")

    def handle_data(self, data):
        self.parts.append(data)

    def handle_entityref(self, name):
        self.parts.append(f"&{name};")

    def handle_charref(self, name):
        self.parts.append(f"&#{name};")

    def handle_comment(self, data):
        self.parts.append(f"<!--{data}-->")


def adapt_html(source):
    parser = Adapter()
    parser.feed(source)
    return "".join(parser.parts)
