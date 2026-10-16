# Contributing

Use Windows x64 and Python 3.12. Install `requirements-dev.txt` into a virtual environment. Rendering uses a local Chromium-family browser and the versioned JavaScript libraries already in `vendor/`.

- Keep document conversion local, preserve source bytes and avoid output overwrites.
- Add synthetic test fixtures. Never commit personal documents, usernames, local paths, conversion records, screenshots of private content, browser profiles or credentials.
- A Win32 native drop callback must only collect/drop paths and enqueue them. It must never call Tk/Tcl APIs.
- Maintain bounded rendering, cancellation, process ownership and cleanup; do not terminate unrelated browsers.
- Validate source and actual packaged EXE workflows after runtime changes. A direct callback test does not cover a live Tk message loop.
- Increment `project.json` and `src/mdfig/__init__.py` together. Release directories and ZIPs are immutable.
- Retain dependency licenses and public download manifests. Bundled browser files must exclude logs, profiles and cache state.

Run `python tests/regression_suite.py --packaged` after building. Test outputs stay under ignored `tests/artifacts/`. Summarize results with relative paths and generic fixtures when adding public validation notes.

The project uses local Markdown issue records under `docs/issues/` and a single domain context in `CONTEXT.md`; design records may live under `docs/adr/`.
