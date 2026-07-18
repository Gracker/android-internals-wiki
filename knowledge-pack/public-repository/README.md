# Android Internals Knowledge Pack

This public repository distributes immutable, TUF-signed knowledge snapshots
generated from policy-eligible Android Internals Wiki articles.

It contains:

- TUF metadata under `metadata/`;
- hash-prefixed immutable targets under `targets/`;
- community, commercial, and redistribution notices under `LICENSES/`.

It does not contain the private source repository, draft articles, review
queues, logs, local filesystem paths, or unpublished metadata.

Consumers must begin with a trusted `1.root.json` shipped by SmartPerfetto and
use a TUF client. Do not treat a Git branch head, release tag, or raw target URL
as a replacement for TUF verification.

The content is available under CC BY-NC-SA 4.0 unless the recipient holds a
separate written AIW Commercial License. See `LICENSES/`.
