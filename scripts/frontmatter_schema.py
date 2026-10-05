"""Canonical AIW article frontmatter fields.

Keep reader-facing metadata and only the workflow fields consumed or emitted by
the currently enabled Hermes AIW lanes. Historical OpenClaw/Hermes execution
details belong in logs, manifests, reports, and review-findings, not articles.
"""

REQUIRED_FIELDS = {
    "title",
    "chapter",
    "status",
    "applicable_versions",
    "tags",
}

CONTENT_FIELDS = {
    "section",
    "section_title",
    "applicable_versions_note",
    "last_verified",
    "last_verified_against",
    "last_source_verified_at",
    "confidence",
    "sources",
    "related_chapters",
    # Narrow, reader-relevant source/version boundary notes.
    "androidx_source_note",
    "note",
    "policy_snapshot",
    "source_repos",
    "verification_scope_note",
    "verified_note",
    "version_boundary",
    "version_note",
    "version_notes",
    "weight",
    # The 2026-08 canonical chapter consolidation provenance is still used by
    # the repository audit and must not be confused with agent run history.
    "consolidated_from",
    "last_consolidated_at",
}

ACTIVE_WORKFLOW_FIELDS = {
    # Recency stamps read by current Hermes lane selectors. Run IDs, OpenClaw
    # task2b/task6/task9 states, and pipeline_stage belong in logs/manifests.
    "last_body_apply_at",
    "last_review_finalize_at",
    "last_deep_review_at",
    "last_rework_at",
    "last_idle_audit_at",
    "last_draft_polish_at",
}

ALLOWED_FIELDS = REQUIRED_FIELDS | CONTENT_FIELDS | ACTIVE_WORKFLOW_FIELDS
