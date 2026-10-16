# Development and release procedure

Install `requirements-dev.txt` into a Python 3.12 virtual environment on Windows. Run `src/launcher.py` for the desktop app. The project can use a local Edge/Chrome browser while developing.

For a complete portable build, install the pinned Headless Shell with `python -m playwright install chromium --only-shell`, then run `python tools/build_release.py --bundle-browser`. An explicit clean browser distribution directory can be supplied with `--browser-dir`. Logs and profiles must never be included in that directory's copied release files.

Update `project.json` and `src/mdfig/__init__.py` together. Build scripts refuse to replace existing release directories or archives. Run `python tests/regression_suite.py --packaged`, inspect relevant screenshots and run `python tools/verify_release.py` before publishing.

Do not copy your `data/`, `tests/artifacts/`, build logs or local reports into source control or release archives. The checked-in validation summary should contain commands and aggregate results, not local absolute paths or source-document identifiers. Verify the exact release ZIP hash and public Git history before upload.

Official downloads are portable: runtime data belongs beside the EXE; browser discovery prioritizes the bundled engine; launch and optional shortcut scripts derive paths from their current directory. Moving an extracted app must not require the original drive letter, username or browser cache.

An optional GitHub Actions example is provided in `ci-template.yml`. To enable it, copy the file to `.github/workflows/tests.yml` using an account credential permitted to manage workflows. The release validation described here was executed locally against the actual source and portable package.
