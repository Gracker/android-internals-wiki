# Android Internals Knowledge Pack

This public repository distributes immutable, TUF-signed knowledge snapshots
generated from the complete Android Internals Wiki body corpus. Article
workflow states and review queues do not gate body inclusion.

It contains:

- TUF metadata under `metadata/`;
- hash-prefixed immutable targets under `targets/`;
- community, commercial, and redistribution notices under `LICENSES/`.

It can contain body content whose source workflow state is draft, under review,
deprecated, or finalized. It does not contain the private source repository,
review queues, logs, raw local filesystem paths, or unpublished workflow
metadata. Private-context lines are redacted before packaging, and detected
secrets fail publication.

Consumers must begin with a trusted `1.root.json` shipped by SmartPerfetto and
use a TUF client. Do not treat a Git branch head, release tag, or raw target URL
as a replacement for TUF verification.

The content is available under CC BY-NC-SA 4.0 unless the recipient holds a
separate written AIW Commercial License. See `LICENSES/`.
