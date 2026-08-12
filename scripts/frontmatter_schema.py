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
    # Current body/review state, read by candidate selection and completion
    # consistency gates.
    "pipeline_stage",
    "task2b_state",
    "task6_state",
    "task9_state",
    # Current enabled lane stamps. Detailed findings, notes, results, log paths,
    # model names, and reviewer identities live outside article frontmatter.
    "last_body_apply_at",
    "last_body_apply_run_id",
    "last_review_finalize_at",
    "last_review_finalize_run_id",
    "last_deep_review_at",
    "last_deep_review_run_id",
    "last_rework_at",
    "last_rework_run_id",
    "last_idle_audit_at",
    "last_idle_audit_run_id",
    "last_draft_polish_at",
    "last_draft_polish_run_id",
}

ALLOWED_FIELDS = REQUIRED_FIELDS | CONTENT_FIELDS | ACTIVE_WORKFLOW_FIELDS
