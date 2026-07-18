# Trust and update model

- Root and top-level targets keys are kept offline.
- The online `nightly` role is delegated only to stable-channel and immutable
  Pack target paths.
- Snapshot and timestamp use separate online keys.
- Consistent snapshots are enabled: target and versioned metadata filenames
  are content/version prefixed.
- Existing Pack versions and target files are never overwritten or deleted by
  the publisher.
- GitHub artifact attestations are supplemental provenance. TUF metadata is the
  update trust boundary.

SmartPerfetto pins the initial root metadata and validates the Pack manifest,
compressed and uncompressed hashes, SQLite schema, `quick_check`, compatibility,
license notices, and retrieval smoke tests before activation.
