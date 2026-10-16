# Markdown Figure Tool

[中文](#中文使用说明) · [English](README.en.md) · [MIT License](LICENSE)

用于渲染还原 **从 ChatGPT 网页版下载或导出的对话内容** 的 Windows 本地工具。重点处理 Markdown 阅读器无法直接呈现的 HTML、SVG、Canvas、Mermaid 和受支持的布局组件，尽量还原它们在对话网页中的显示效果。

软件通过本地浏览器执行、渲染这些复杂内容，将渲染结果保存为 PNG，再嵌入新的 Markdown。正文和普通编程代码保持原样，方便在 Typora 等阅读器中阅读完整对话。

## 中文使用说明

从 [Releases](https://github.com/BattleForever/markdown-figure-tool/releases) 下载 `MarkdownFigureTool-v0.3.1-windows-x64-portable.zip`，**完整解压**到可写文件夹，双击 `Start.cmd` 或 `MarkdownFigureTool.exe`。完整便携包已包含 Python 运行时、浏览器驱动和 Chromium Headless Shell，无需安装 Python、Node.js 或浏览器，转换不需要联网。支持 Windows 10/11 x64。

1. 拖入一个或多个 `.md`、`.markdown`、`.mdown` 文件，或点击“添加文件”。
2. 选择宽度和清晰度，点击“开始转换”。
3. 在源目录得到 `原名_图像版.md` 和 `原名_图像版_assets/`。重复操作自动编号。
4. 用 Typora 等阅读器打开新文件。移动阅读文件时，一起移动相应图片文件夹。

源文件和旧结果不会被覆盖。部分图形失败时保留其原代码，并给出错误位置；原有普通编程代码保持原样。旧图像版旁若有本工具的转换记录，且同目录原始文件通过哈希校验，则可从原始文件重新渲染。

## 支持范围与限制

- 标注为 html、htm、svg、mermaid 的代码块，以及正文中的完整图形。
- 原生浏览器 HTML/JavaScript、SVG、Canvas；源目录内实际引用的相对图片、脚本、CSS 和字体。
- box、row、grid、text、badge、icon、WritingBlock、列表、单选组等已实现布局组件；JSX 表达式、模板路径、body 声明、each/if 及 DIL 状态。
- 本地兼容实现不调用 ChatGPT 的私有运行时。还原效果取决于导出内容是否完整；未导出的 CSS、任意 React/Vue 应用依赖、未知业务组件和历史交互状态不能自动恢复，因此无法保证与原网页逐像素一致。
- 输出是默认状态的静态 PNG，按钮不可点击。正文公式由 Markdown 阅读器处理。

每幅图在独立浏览器上下文中执行，屏蔽外网请求和弹窗，并受独立进程的硬超时控制。页面隔离并不等于可安全运行任意恶意文件，请只转换可信文档。详情见 [PRIVACY.md](PRIVACY.md) 和 [SECURITY.md](SECURITY.md)。

## 命令行

```powershell
.\MarkdownFigureTool.exe --cli "D:\Notes\sample.md" --report ".\conversion.json"
```

exe 为窗口程序，终端可能没有文字输出；使用 `--report` 并检查退出码。0 为本轮无失败，1 表示至少一个文件或图形失败。

## 开发与构建

Python 3.12，Windows x64：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe src\launcher.py
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

源码运行可使用本机 Edge/Chrome。构建完整便携包：

```powershell
.\.venv\Scripts\python.exe -m playwright install chromium --only-shell
.\.venv\Scripts\python.exe tools\build_release.py --bundle-browser
.\.venv\Scripts\python.exe tests\regression_suite.py --packaged
```

构建不覆盖已存在的版本。完整验证和隐私发布说明见 [docs/VALIDATION.md](docs/VALIDATION.md)；源码结构及开发约定见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 许可

项目自有代码采用 MIT License。第三方库与内置浏览器保留各自许可，见 [THIRD_PARTY.md](THIRD_PARTY.md)。本项目与任何聊天平台无隶属关系。
