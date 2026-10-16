"""Preserve the source; publish a new Markdown plus relative PNG assets."""
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import shutil
import tempfile
import re
from urllib.parse import quote

from . import __version__
from .parser import find_figures
from .inline_adapter import inline_replacements


@dataclass
class ConversionResult:
    source: str
    output: str = ""
    assets: str = ""
    total: int = 0
    succeeded: int = 0
    failures: list = field(default_factory=list)
    source_sha256: str = ""


def decode_source(data):
    if data.startswith(b"\xef\xbb\xbf"):
        return data[3:].decode("utf-8"), b"\xef\xbb\xbf"
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16"), b""
    try:
        return data.decode("utf-8"), b""
    except UnicodeDecodeError:
        return data.decode("gb18030"), b""


def convert_file(path, renderer, progress=lambda message: None, cancelled=lambda: False):
    path = Path(path).resolve()
    if path.suffix.lower() not in {".md", ".markdown", ".mdown"}:
        raise ValueError("请选择 Markdown 文件（.md、.markdown 或 .mdown）。")
    # A prior PNG cannot recover missing primitives. Rebuild only from a verified
    # original in the same directory, using our own adjacent conversion record.
    if re.search(r'_图像版(?:_\d+)?$', path.stem):
        report = path.with_name(path.stem + '_assets') / '转换记录.json'
        try:
            record = json.loads(report.read_text(encoding='utf-8'))
            candidate = Path(record['source']).resolve()
            if (candidate != path and candidate.parent == path.parent
                    and candidate.suffix.lower() in {'.md', '.markdown', '.mdown'}
                    and hashlib.sha256(candidate.read_bytes()).hexdigest() == record['source_sha256']):
                progress('检测到旧图像版，依据同目录且校验一致的原始文件重新渲染：' + candidate.name)
                path = candidate
        except (OSError, ValueError, KeyError, TypeError):
            pass
    original = path.read_bytes()
    source, bom = decode_source(original)
    figures = find_figures(source, renderer.options.include_mermaid)
    result = ConversionResult(str(path), total=len(figures), source_sha256=hashlib.sha256(original).hexdigest())
    if not figures:
        progress("未找到需要转换的图形代码，未生成副本。")
        return result
    with tempfile.TemporaryDirectory(prefix=".mdfig-render-", dir=path.parent) as temporary:
        temporary = Path(temporary)
        replacements = []
        records = []
        for index, figure in enumerate(figures, 1):
            if cancelled():
                raise RuntimeError("转换已取消；未写入输出文件。")
            filename = f"figure_{index:03}.png"
            progress(f"图形 {index}/{len(figures)}，源文件第 {figure.line} 行（{figure.kind}）")
            try:
                dimensions = renderer.render(figure, path.parent, temporary / filename)
                replacements.append((figure, filename))
                result.succeeded += 1
                records.append({"index": index, "line": figure.line, "kind": figure.kind, "status": "ok", "image": filename, **dimensions})
            except Exception as error:
                message = str(error).strip()
                result.failures.append({"index": index, "line": figure.line, "error": message})
                records.append({"index": index, "line": figure.line, "kind": figure.kind, "status": "failed", "error": message})
                progress(f"  未转换，保留代码：{message[:160]}")
        if not result.succeeded:
            progress("所有图形均未转换成功，未生成误导性的输出副本。")
            return result
        if path.read_bytes() != original:
            raise RuntimeError("源文件在转换期间发生变化，已停止保存；请保存编辑后重试。")
        if cancelled():
            raise RuntimeError("转换已取消；未写入输出文件。")
        # Reserve both names exclusively, so parallel right-click invocations cannot overwrite.
        for number in range(1, 10000):
            suffix = "_图像版" if number == 1 else f"_图像版_{number}"
            output = path.with_name(path.stem + suffix + ".md")
            assets = path.with_name(path.stem + suffix + "_assets")
            if output.exists():
                continue
            try:
                assets.mkdir()
            except FileExistsError:
                continue
            try:
                descriptor = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(descriptor)
                break
            except FileExistsError:
                assets.rmdir()
                continue
            except Exception:
                assets.rmdir()
                raise
        else:
            raise RuntimeError("同名输出过多，请先整理目标目录。")
        try:
            result.output, result.assets = str(output), str(assets)
            changes, inline_count = inline_replacements(source, figures)
            for figure, filename in reversed(replacements):
                relative_url = quote(f'./{assets.name}/{filename}', safe='/')
                link = f"![图形 {figures.index(figure) + 1}](<{relative_url}>)"
                changes.append((figure.start, figure.end, link))
                shutil.copyfile(temporary / filename, assets / filename)
            converted = source
            for start, end, content in sorted(changes, reverse=True):
                converted = converted[:start] + content + converted[end:]
            report = {"software_version": __version__, "created_utc": datetime.now(timezone.utc).isoformat(), "source": str(path), "source_sha256": result.source_sha256, "options": asdict(renderer.options), "figures": records, 'inline_styles_adapted':inline_count, "source_unchanged": True}
            (assets / "转换记录.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
            staged = temporary / "converted.md"
            staged.write_bytes(bom + converted.encode("utf-8"))
            # Source text outside the successful spans is copied verbatim, including line endings.
            if path.read_bytes() != original:
                raise RuntimeError("源文件在保存前发生变化，已停止保存。")
            os.replace(staged, output)
            progress(f"已保存：{output.name}（{result.succeeded}/{result.total} 幅）")
        except Exception:
            output.unlink(missing_ok=True)
            shutil.rmtree(assets)
            raise
    return result
