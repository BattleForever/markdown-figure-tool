# Privacy

Documents are processed locally. The application has no telemetry, account login, cloud API, analytics or automatic document upload. Figure contexts block external page requests, downloads, popups, frames and service workers. Only supported resources resolved beneath the selected document directory are served to the renderer.

Conversion writes a new Markdown document, PNGs and a conversion record beside the input. That record intentionally contains the local source path, source digest, rendering options and figure failures for diagnosis. Logs/settings beside the application may also contain selected document and browser paths. These are user runtime files, never part of official releases or this repository.

Before sharing a used portable folder, remove `data/` and check for files you added manually. When filing a bug, replace private paths and document content with a minimal synthetic example; do not attach your full working document unless you intend to make it public.

The public repository starts with a clean export. It does not contain private development Git history, original documents, user fixtures, old conversion reports, profiles, credentials or private test images. Release audits check source files, archive members, Python bytecode paths and Git metadata for personal information.

Third-party code and license notices retain upstream authorship and contact details. These are not private runtime data from this project.
