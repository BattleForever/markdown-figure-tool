# 第三方组件

- Python 3.12：Python Software Foundation License；完整正文位于便携包 `licenses/Python/LICENSE.txt`。
- Tcl/Tk：随 Python 分发的 Tcl/Tk 许可。
- Playwright 1.61.0：Apache License 2.0；渲染驱动及相关许可随 Python 包收集。
- Greenlet、Pyee：Playwright 的运行时依赖，完整分发许可位于 `licenses/greenlet/` 和 `licenses/pyee/`。
- Mermaid 11.12.0：MIT License，完整许可位于 `vendor/mermaid/LICENSE`（发布包内为 `_internal/vendor/mermaid/LICENSE`）。下载来源及 SHA-256 位于相邻的 `manifest.json`。
- markdown-it-py 4.2.0 与 mdurl：MIT License，用于保护 Markdown 的缩进代码块和嵌套代码示例。
- Python 依赖的分发许可同时收集到 `licenses/`；Tcl 许可保存在 `licenses/Tcl/license.terms`，Tk 许可随 `_internal/_tk_data/` 保留。
- Babel Standalone 7.28.5：MIT License，用于在本机解析用户导出的 JSX 表达式；许可与下载哈希位于 `vendor/babel/`。
- Preact 10.27.2 及 Hooks：MIT License，本地组件状态与 SVG 渲染；许可与下载哈希位于 `vendor/preact/`。
- markdown-it 14.1.0 浏览器版：MIT License，渲染卡片中的加粗、列表等 Markdown；许可与下载哈希位于 `vendor/markdown-it/`。
- PyInstaller 6.16.0：构建工具和引导程序采用带引导程序例外条款的 GPL，完整正文保存在 `licenses/pyinstaller/COPYING.txt`。
- 完整便携包包含 Playwright 固定版本的 Chromium Headless Shell。其 Chromium 与第三方完整许可保存在 `browser/LICENSE.headless_shell`，版本及文件哈希见 `portable.json` 与 `release_manifest.json`。本项目 MIT 许可不改变这些第三方许可。
- Microsoft Edge、Google Chrome：仍可选择使用本机已安装的浏览器；不分发用户安装的 Edge/Chrome 或浏览器资料。

公开组件下载仅涉及这些组件，不上传待转换文档。
