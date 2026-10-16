# Markdown Figure Tool

An offline Windows desktop tool for restoring the visual content of **conversations downloaded or exported from the ChatGPT website**. It focuses on HTML, SVG, Canvas, Mermaid and supported layout components that Markdown readers cannot display directly, aiming to reproduce their appearance in the original conversation page.

The tool executes and renders this content in a local browser, saves the results as PNG images, and embeds them in a new Markdown document for reading in Typora or another Markdown reader. Surrounding text and ordinary programming examples are preserved. The new document and its image directory are written beside the source without overwriting the original or previous outputs.

## Portable download

Download the Windows x64 portable ZIP from [Releases](https://github.com/BattleForever/markdown-figure-tool/releases), extract the **entire** archive, and run `Start.cmd` or `MarkdownFigureTool.exe`. The full package includes Python, Playwright and Chromium Headless Shell. No additional Python, Node.js or browser installation is required. Windows 10/11 x64 is supported.

Drag Markdown files into the window and start conversion. Read the resulting `_图像版.md` file in Typora or another Markdown reader. Keep its matching `_assets` folder when moving it. Existing files are never overwritten; repeated runs use numbered names.

Supported component syntax is compiled locally, including expressions, template strings, each/if directives and DIL state. This is an independent compatibility implementation and does not use ChatGPT's private runtime. Fidelity depends on what the export contains: missing styles, private component definitions and historical interaction states cannot be reconstructed, so pixel-for-pixel reproduction is not guaranteed. PNG output captures the default state; arbitrary React/Vue applications are not reconstructed.

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
