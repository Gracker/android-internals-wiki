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


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def infer_section(path: Path) -> str | None:
    m = re.search(r"\d{4}-\d{2}-\d{2}-\d{2}-(.+)-external-review\.md$", path.name)
    if not m:
        return None
    value = m.group(1)
    if re.fullmatch(r"\d+(?:\.\d+)?", value):
        return value
    text = load_text(path)
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

    return (len(reasons) > 0, reasons)


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
