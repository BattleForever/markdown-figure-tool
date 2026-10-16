"""Render original figure code in a fresh offline browser page, then capture PNG."""
from dataclasses import dataclass
from pathlib import Path
import mimetypes
import os
import sys
from urllib.parse import unquote, urlparse

from .html_adapter import BASE_CSS, adapt_html
from .components import compile_component, uses_components


@dataclass
class RenderOptions:
    width: int = 960
    scale: float = 2
    wait_ms: int = 1000
    timeout_ms: int = 20000
    include_mermaid: bool = True
    browser_path: str = ""


def resource_path(relative):
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / relative


def browser_candidates():
    found = []
    app_root = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[2]
    found.append(app_root / 'browser' / 'chrome-headless-shell.exe')
    if os.name == "nt":
        import winreg
        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            for name in ("msedge.exe", "chrome.exe"):
                for flags in (winreg.KEY_READ, winreg.KEY_READ | winreg.KEY_WOW64_32KEY):
                    try:
                        with winreg.OpenKey(hive, "SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App Paths\\" + name, 0, flags) as key:
                            found.append(Path(winreg.QueryValue(key, None).strip('"')))
                    except OSError:
                        pass
        for root in (os.environ.get("PROGRAMFILES", ""), os.environ.get("PROGRAMFILES(X86)", ""), os.environ.get("LOCALAPPDATA", "")):
            for relative in ("Microsoft/Edge/Application/msedge.exe", "Google/Chrome/Application/chrome.exe"):
                found.append(Path(root) / relative)
        cache = Path(os.environ.get("LOCALAPPDATA", "")) / "ms-playwright"
        found.extend(sorted(cache.glob("chromium-*/chrome-win64/chrome.exe"), reverse=True))
        found.extend(sorted(cache.glob("chromium_headless_shell-*/chrome-headless-shell-win64/chrome-headless-shell.exe"), reverse=True))
    unique = []
    for path in found:
        if path.is_file() and path not in unique:
            unique.append(path)
    return unique


class RenderSession:
    def __init__(self, options=None):
        self.options = options or RenderOptions()
        self.playwright = None
        self.browser = None
        self.browser_name = ""

    def __enter__(self):
        if self.options.browser_path and not Path(self.options.browser_path).is_file():
            raise RuntimeError('所选浏览器不存在，请重新选择浏览器 exe：' + self.options.browser_path)
        from playwright.sync_api import sync_playwright
        self.playwright = sync_playwright().start()
        candidates = [Path(self.options.browser_path)] if self.options.browser_path else browser_candidates()
        errors = []
        for candidate in candidates:
            try:
                self.browser = self.playwright.chromium.launch(executable_path=str(candidate), headless=True, timeout=20000, args=["--disable-background-networking", "--disable-component-update"])
                self.browser_name = str(candidate)
                return self
            except Exception as error:
                errors.append(str(error).splitlines()[0])
        if self.options.browser_path:
            self.playwright.stop()
            raise RuntimeError('无法启动所选浏览器：' + '; '.join(errors))
        try:
            self.browser = self.playwright.chromium.launch(headless=True, timeout=20000)
            self.browser_name = "Playwright Chromium"
            return self
        except Exception as error:
            self.playwright.stop()
            raise RuntimeError("找不到可用的 Edge、Chrome 或 Chromium。请在设置中选择浏览器的 exe。\n" + str(error).splitlines()[0]) from error

    def __exit__(self, *_):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def render(self, figure, source_dir, output):
        options = self.options
        errors = []
        blocked = []
        source_dir = source_dir.resolve()
        context = self.browser.new_context(viewport={"width": options.width, "height": 900}, device_scale_factor=options.scale, accept_downloads=False, service_workers="block", color_scheme="light")
        page = context.new_page()
        page.set_default_timeout(options.timeout_ms)
        page.on("pageerror", lambda error: errors.append(str(error)))
        context.on("page", lambda other: other.close() if other is not page else None)

        def route_resource(route):
            parsed = urlparse(route.request.url)
            if parsed.scheme in {"data", "blob", "about"}:
                return route.continue_()
            if parsed.hostname == "mdfig.local":
                path = (source_dir / unquote(parsed.path).lstrip("/")).resolve()
                allowed = {".js", ".mjs", ".css", ".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp", ".woff", ".woff2", ".ttf", ".otf"}
                if path.is_relative_to(source_dir) and path.is_file() and path.suffix.lower() in allowed:
                    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
                    if path.suffix.lower() in {".js", ".mjs"}:
                        mime = "application/javascript"
                    return route.fulfill(body=path.read_bytes(), content_type=mime)
            blocked.append(route.request.url[:300])
            route.abort()

        context.route("**/*", route_resource)
        try:
            csp = "default-src 'none'; script-src 'unsafe-inline' 'unsafe-eval' http://mdfig.local; style-src 'unsafe-inline' http://mdfig.local; img-src data: blob: http://mdfig.local; font-src data: http://mdfig.local; connect-src 'none'; frame-src 'none'; object-src 'none'; base-uri http://mdfig.local; form-action 'none'"
            component = figure.kind == 'html' and uses_components(figure.content)
            body = '<div id="mdfig-mermaid"></div>' if figure.kind == "mermaid" else '' if component else adapt_html(figure.content)
            guard = "<script>window.__mdfigBlocked=[];document.addEventListener('securitypolicyviolation',e=>window.__mdfigBlocked.push(e.blockedURI||e.violatedDirective));</script>"
            document = f'<!doctype html><html><head><meta charset="utf-8"><meta http-equiv="Content-Security-Policy" content="{csp}"><base href="http://mdfig.local/"><style>{BASE_CSS}</style>{guard}</head><body><main id="mdfig-capture">{body}</main></body></html>'
            page.set_content(document, wait_until="load", timeout=options.timeout_ms)
            if component:
                for library in ('vendor/preact/preact.umd.js', 'vendor/preact/hooks.umd.js', 'vendor/markdown-it/markdown-it.min.js', 'vendor/babel/babel.min.js', 'assets/component-runtime.js'):
                    path = resource_path(library)
                    if not path.is_file():
                        raise RuntimeError('软件目录缺少组件渲染库：' + library)
                    page.add_script_tag(content=path.read_text(encoding='utf-8'))
                page.evaluate('(source)=>window.__mdfigCompile(source)', compile_component(figure.content))
            if figure.kind == "mermaid":
                library = resource_path("vendor/mermaid/mermaid.min.js")
                if not library.is_file():
                    raise RuntimeError("软件目录缺少内置 Mermaid 渲染库。")
                page.add_script_tag(content=library.read_text(encoding="utf-8"))
                page.evaluate("""async source => {
                    mermaid.initialize({startOnLoad:false,securityLevel:'strict',theme:'default',fontFamily:'Microsoft YaHei,Segoe UI,Arial,sans-serif',flowchart:{htmlLabels:true},maxTextSize:150000});
                    const result=await mermaid.render('mdfig-mermaid-svg',source);
                    document.getElementById('mdfig-mermaid').innerHTML=result.svg;
                }""", figure.content)
            page.evaluate("async () => { await Promise.race([document.fonts.ready,new Promise(r=>setTimeout(r,3000))]); }")
            page.wait_for_timeout(options.wait_ms)
            blocked.extend(page.evaluate("window.__mdfigBlocked || []"))
            if errors:
                raise RuntimeError("绘图脚本出错：" + errors[0][:600])
            if blocked:
                raise RuntimeError("图形引用了未提供或禁止联网的资源：" + blocked[0])
            state = page.evaluate(r"""() => {
                const el=document.getElementById('mdfig-capture');
                const emptyPaths=[...el.querySelectorAll('svg path')].filter(p=>p.getClientRects().length&&getComputedStyle(p).display!=='none'&&getComputedStyle(p).visibility!=='hidden'&&!(p.getAttribute('d')||'').trim()&&getComputedStyle(p).d==='none').length;
                const bounds=el.getBoundingClientRect();
                let blankCanvas=false;
                for(const c of el.querySelectorAll('canvas')){
                  const ctx=c.getContext('2d'); if(!ctx)continue;
                  const pixels=ctx.getImageData(0,0,c.width,c.height).data;
                  let drawn=false;for(let i=3;i<pixels.length;i+=4){if(pixels[i]){drawn=true;break;}}
                  if(!drawn)blankCanvas=true;
                }
                const brokenImages=[...el.querySelectorAll('img')].filter(img=>!img.complete||!img.naturalWidth).length;
                const invalidSvg=[...el.querySelectorAll('svg *')].some(e=>[...e.attributes].some(a=>/\{[#@]|\{[^}]+\}/.test(a.value)));
                return {width:Math.ceil(Math.max(bounds.width,el.scrollWidth)),height:Math.ceil(Math.max(bounds.height,el.scrollHeight)),emptyPaths,blankCanvas,brokenImages,invalidSvg,text:el.innerText.trim().length,visuals:el.querySelectorAll('svg,canvas,img,table').length,svg_lines:el.querySelectorAll('svg line').length,svg_paths:el.querySelectorAll('svg path').length,grids:el.querySelectorAll('[data-mdfig-grid]').length};
            }""")
            if state["emptyPaths"]:
                raise RuntimeError(f"有 {state['emptyPaths']} 条 SVG 路径没有生成坐标，已保留原代码。")
            if state["blankCanvas"]:
                raise RuntimeError("Canvas 仍为空白，已保留原代码。")
            if state["brokenImages"]:
                raise RuntimeError("图形内有图片未能加载，已保留原代码。")
            if state['invalidSvg']:
                raise RuntimeError('SVG 仍包含未执行的表达式，已保留原代码。')
            if not state["text"] and not state["visuals"]:
                raise RuntimeError("没有可见图形或文字；该块可能需要 React 或其他组件运行环境。")
            if state["height"] <= 40 or state["height"] > 20000 or state["width"] * state["height"] * options.scale ** 2 > 100000000:
                raise RuntimeError("图形尺寸为空或超出可处理范围；请调整渲染宽度或源图尺寸。")
            page.screenshot(path=str(output), clip={"x": 0, "y": 0, "width": state["width"], "height": state["height"]}, animations="disabled", timeout=options.timeout_ms)
            return {"css_width": state["width"], "css_height": state["height"], "scale": options.scale, 'engine':'components' if component else figure.kind, 'svg_lines':state['svg_lines'], 'svg_paths':state['svg_paths'], 'grids':state['grids'], 'browser_engine':Path(self.browser_name).name}
        finally:
            context.close()

