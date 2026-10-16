# Public release validation

Version: 0.3.1. Platform: Windows x64, Python 3.12, Playwright 1.61.0. The portable distribution includes Chromium Headless Shell 149.0.7827.55, Playwright revision 1228.

## Test results

All 15 regression groups passed, including the unit-test group with 35 checks. Public fixtures contain only synthetic content. The matrix covers parser boundaries, protected code samples, UTF-8/BOM/line endings, exclusive output naming, preserved failures, component state and loops, native HTML/Canvas/SVG, Mermaid, cancellation, timeouts, process cleanup, GUI errors and actual packaged execution.

- Source and packaged GUI each handled 1000 asynchronous native drop messages.
- Component behavior was checked through the actual EXE and native GUI.
- A sealed ZIP was extracted with external Python/browser paths removed from the test environment. All three demo figures rendered using the included `chrome-headless-shell.exe`.
- The extracted application was moved into a new directory containing spaces and non-ASCII characters. `Start.cmd` produced another successful conversion and retained the source bytes.
- After relocation, 100 native drop messages and GUI conversion passed; maximum GUI heartbeat gap was 47 ms.
- Data and jobs were created beside the relocated application, without relying on an unrelated parent project.

The environment-isolation test simulates missing external runtimes on the same host. It is not a claim that every supported Windows installation or security-software configuration has been tested.

## Distribution integrity

Archive: `MarkdownFigureTool-v0.3.1-windows-x64-portable.zip`

- Archive bytes: 172,068,443 (about 164 MiB).
- Archive SHA-256: `d971de3d4c309160fada3375cd4e2c9c724657269b5287cffcd826c7f36001a5`.
- EXE SHA-256: `8c7bfaa5ad103b799ea2e9f80e9eee6aa6d6d0eee020f7fea18b94821afbe15e`.
- 1436 files in the release manifest, excluding the manifest itself; 1525 archive entries including directories.

The ZIP was checked for corruption, and its digest was checked before relocation testing. Dependency licenses and the complete browser license notices are included.

## Privacy review

The public repository is a fresh source export. Private documents, historic conversion reports, private Git commits and old screenshots were excluded. Tests that previously depended on private local documents were replaced with synthetic fixtures.

The publication audit checked source contents, ZIP members and embedded Python bytecode, including 15,029 code objects and their source filenames. No configured personal path, account, private document marker or credential pattern was found. The Git commit metadata and reachable public history were separately checked before upload.

This check is scoped to known personal markers, credential patterns, selected files and build artifacts; it is not a general proof about all third-party software internals. Upstream authors' copyright/license notices remain intact.

Machine-specific execution logs and local audit details are intentionally not committed. The public test matrix summary is in `validation_summary.json`.
