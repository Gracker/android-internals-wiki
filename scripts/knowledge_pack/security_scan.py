"""Fail-closed scans for material that must not enter a public Pack."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class SecurityFinding:
    code: str
    severity: str


HIGH_CONFIDENCE_SECRET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("github_token", re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b")),
    ("aws_access_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    (
        "provider_api_key",
        re.compile(r"\b(?:sk|sk-ant)-[A-Za-z0-9_-]{24,}\b"),
    ),
)

PRIVATE_CONTEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("macos_user_path", re.compile(r"(?<![\w.-])/Users/[A-Za-z0-9._-]+/")),
    ("linux_user_path", re.compile(r"(?<![\w.-])/home/[A-Za-z0-9._-]+/")),
    ("windows_user_path", re.compile(r"\b[A-Za-z]:\\Users\\[^\\\r\n]+\\", re.IGNORECASE)),
)


def scan_public_text(text: str) -> tuple[SecurityFinding, ...]:
    findings: list[SecurityFinding] = []
    for code, pattern in HIGH_CONFIDENCE_SECRET_PATTERNS:
        if pattern.search(text):
            findings.append(SecurityFinding(code=code, severity="fatal"))
    for code, pattern in PRIVATE_CONTEXT_PATTERNS:
        if pattern.search(text):
            findings.append(SecurityFinding(code=code, severity="exclude"))
    return tuple(findings)


def redact_private_context_lines(text: str) -> tuple[str, tuple[str, ...]]:
    """Remove complete lines containing private context while preserving line numbers."""

    output: list[str] = []
    redaction_codes: list[str] = []
    for line in text.splitlines(keepends=True):
        codes = sorted(
            {
                code
                for code, pattern in PRIVATE_CONTEXT_PATTERNS
                if pattern.search(line)
            }
        )
        if not codes:
            output.append(line)
            continue
        newline = ""
        if line.endswith("\r\n"):
            newline = "\r\n"
        elif line.endswith("\n"):
            newline = "\n"
        elif line.endswith("\r"):
            newline = "\r"
        output.append(f"[REDACTED_PRIVATE_CONTEXT:{','.join(codes)}]{newline}")
        redaction_codes.extend(codes)
    return "".join(output), tuple(redaction_codes)
