# Context

Input: local Markdown from file selection, native drop, Explorer context menu or CLI.

Parsing locates complete figures and preserves source positions; ordinary code examples are masked. Native HTML/DOM scripts and Mermaid use fresh browser contexts. Exported layout syntax is compiled locally with Babel and rendered with Preact compatibility components. Unknown or failed figures keep their original code.

Output is a new Markdown plus relative PNG assets and conversion metadata beside the source. Runtime data lives beside the portable EXE. The bundled Chromium Headless Shell is tried before local Edge/Chrome; an explicitly selected browser takes priority.

Tk owns the UI thread. Native callbacks enqueue data. Rendering runs in a cancellable service with hard deadlines and a Windows Job Object. Each published version is independently packaged, validated and privacy audited.
