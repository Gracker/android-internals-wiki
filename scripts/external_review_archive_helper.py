#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path("/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki")
ACTIVE = ROOT / "logs" / "external-review"
ARCHIVE = ACTIVE / "archive"
QUEUE = ROOT / "metadata" / "queue.json"
SUGGESTIONS = ROOT / "intake" / "suggestions.md"
RESEARCH_GAPS = ROOT / "intake" / "research-gaps.md"
INTEGRATION_LOG_DIR = ROOT / "logs" / "external-review-integration"


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def infer_section(path: Path) -> str | None:
    # Simple section-slug pattern: 9.1-anr-design.md → 9.1, 18.21-eyedropper.md → 18.21
    m_simple = re.fullmatch(r"(\d+\.\d+)-.+\.md$", path.name)
    if m_simple:
        return m_simple.group(1)
    # Batch-summary / README: 10.batch-summary.md → skip (no section)
    if path.name.endswith(".batch-summary.md") or path.name.endswith(".README.md"):
        return None
    # New pattern: 15.XX-YY-slug.md or 15.XX-YY.md → XX.YY
    m_new = re.fullmatch(r"(\d+)\.(\d{2})-(\d{2})(?:-.+)?\.md$", path.name)
    if m_new:
        return f"{int(m_new.group(2))}.{int(m_new.group(3))}"
    # New pattern: 15.README-chXX.md → XX.README
    m_rm = re.fullmatch(r"\d+\.README-ch(\d{2})\.md$", path.name)
    if m_rm:
        return f"{int(m_rm.group(1))}.README"
    # Handle 15.XX-slug.md format (e.g. 15.11-webview-performance.md)
    m_single = re.fullmatch(r"\d+\.(\d{2})-.+\.md$", path.name)
    if m_single:
        # Need to determine chapter from file content
        ftext = load_text(path)
        # Look for target path like ch07-smoothness/11- or ch08-responsiveness/01-
        m_ch = re.search(r"ch(\d{2})-[\w-]+/(\d{2})-", ftext)
        if m_ch:
            return f"{int(m_ch.group(1))}.{int(m_ch.group(2))}"
        # Try 章节 pattern
        m_sec = re.search(r"章节[：:]\s*(\d+\.\d+)", ftext)
        if m_sec:
            return m_sec.group(1)
    # Capture everything after YYYY-MM-DD- (include HH in the value)
    m = re.search(r"\d{4}-\d{2}-\d{2}-(.+)-external-review\.md$", path.name)
    if not m:
        return None
    value = m.group(1)  # e.g. "14-01-as-profiler" or "06-15.6"

    # Direct section number (e.g. "15.6")
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return value

    # XX-YY-slug → XX.YY (e.g. "14-01-as-profiler" → 14.1)
    m_sub = re.fullmatch(r"(\d+)-(\d+)-.+", value)
    if m_sub:
        return f"{int(m_sub.group(1))}.{int(m_sub.group(2))}"

    # HH-XX.YY → XX.YY (e.g. "06-15.6" → 15.6)
    m_dot = re.fullmatch(r"\d+-(\d+\.\d+)", value)
    if m_dot:
        return m_dot.group(1)

    # Handle 15.XX-YY-slug.md format (from batch review runs)
    m_batch = re.search(r"(\d+)\.(\d{2})-(\d{2})-", path.name)
    if m_batch:
        return f"{int(m_batch.group(2))}.{int(m_batch.group(3))}"
    # Fallback: search file content for explicit section marker
    text = load_text(path)
    # Try 章节： pattern in 9.1
    m3 = re.search(r"章节[：:]\s*(\d+\.\d+)", text)
    if m3:
        return m3.group(1)
    m2 = re.search(r"\*\*章节号\*\*：\s*([^\n]+)", text)
    return m2.group(1).strip() if m2 else None


def consumed(path: Path) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    section = infer_section(path)
    if not section:
        return False, ["missing-section"]

    qtext = load_text(QUEUE)
    if qtext:
        try:
            arr = json.loads(qtext)
            for item in arr:
                if str(item.get("section", "")).strip() == section:
                    reasons.append("queue")
                    break
        except Exception:
            pass

    stext = load_text(SUGGESTIONS)
    if f"] {section} " in stext or f"**章节**：{section}" in stext:
        reasons.append("suggestions")

    rtext = load_text(RESEARCH_GAPS)
    if f"] {section} " in rtext or f"### 关联章节\n- {section}" in rtext or f"{section} " in rtext:
        reasons.append("research-gaps")

    if INTEGRATION_LOG_DIR.exists():
        for log_path in sorted(INTEGRATION_LOG_DIR.glob("*.md"), reverse=True):
            text = load_text(log_path)
            if not text:
                continue
            if section not in text:
                continue
            if any(marker in text for marker in [f"- {section} ", f"### {section}", f"{section}（", f"{section} "]):
                if "已整合" in text or "上轮已整合" in text or "本轮无需新增写入" in text:
                    reasons.append("integration-log")
                    break

    deduped = []
    for reason in reasons:
        if reason not in deduped:
            deduped.append(reason)

    return (len(deduped) > 0, deduped)


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive consumed external review files")
    parser.add_argument("action", choices=["status", "archive"], help="status or archive")
    args = parser.parse_args()

    ARCHIVE.mkdir(parents=True, exist_ok=True)
    files = [p for p in ACTIVE.glob("*.md") if p.name not in {"README.md", "TEMPLATE.md"} and "batch-review-summary" not in p.name]
    rows = []
    for p in sorted(files):
        ok, reasons = consumed(p)
        rows.append((p, ok, reasons))

    if args.action == "status":
        for p, ok, reasons in rows:
            print(f"{p.name}\t{'consumed' if ok else 'pending'}\t{','.join(reasons) if reasons else '-'}")
        return 0

    moved = 0
    for p, ok, reasons in rows:
        if not ok:
            continue
        target = ARCHIVE / p.name
        if target.exists():
            target.unlink()
        shutil.move(str(p), str(target))
        moved += 1
        print(f"archived\t{p.name}\t{','.join(reasons)}")
    print(f"total_archived\t{moved}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
