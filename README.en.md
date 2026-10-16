# Markdown Figure Tool

An offline Windows desktop tool that renders HTML, SVG, Canvas, Mermaid and supported exported layout components inside Markdown into PNG images. It writes a new Markdown document and an image directory beside the source, preserving the original and previous outputs.

## Portable download

Download the Windows x64 portable ZIP from [Releases](https://github.com/BattleForever/markdown-figure-tool/releases), extract the **entire** archive, and run `Start.cmd` or `MarkdownFigureTool.exe`. The full package includes Python, Playwright and Chromium Headless Shell. No additional Python, Node.js or browser installation is required. Windows 10/11 x64 is supported.

Drag Markdown files into the window and start conversion. Read the resulting `_图像版.md` file in Typora or another Markdown reader. Keep its matching `_assets` folder when moving it. Existing files are never overwritten; repeated runs use numbered names.

Move the entire application folder to another computer. Optional shortcut and context-menu scripts use the current folder; run them again after relocating the app. Runtime settings, logs and jobs live in the adjacent `data/` folder. Official downloads contain no runtime data; remove this folder before sharing a used copy.

Supported component syntax is compiled locally, including expressions, template strings, each/if directives and DIL state. This is an independent compatibility implementation, not a proprietary platform renderer. PNG output captures the default state; arbitrary React/Vue applications and missing private component definitions are not reconstructed.

## Development

Use Python 3.12 on Windows, create a virtual environment and install `requirements-dev.txt`. Run `src/launcher.py` or the tests:

```powershell
python -m unittest discover -s tests -p "test_*.py" -v
python -m playwright install chromium --only-shell
python tools/build_release.py --bundle-browser
python tests/regression_suite.py --packaged
```

Public tests use synthetic fixtures. See [CONTRIBUTING.md](CONTRIBUTING.md), [PRIVACY.md](PRIVACY.md), [SECURITY.md](SECURITY.md) and [validation](docs/VALIDATION.md).

Project code is MIT licensed. Bundled dependencies retain their own licenses; see [THIRD_PARTY.md](THIRD_PARTY.md).
