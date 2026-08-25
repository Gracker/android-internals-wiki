#!/usr/bin/env python3
"""Remove temporary editorial process fields from canonical frontmatter."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FIELDS = {
    "editorial_fused_at",
    "editorial_fusion_version",
    "editorial_fusion_note",
}


def clean(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False
    end = text.find("\n---\n", 4)
    if end < 0:
        return False
    frontmatter = text[4:end].splitlines()
    retained = [
        line
        for line in frontmatter
        if line.split(":", 1)[0].strip() not in FIELDS
    ]
    rewritten = "---\n" + "\n".join(retained) + text[end:]
    if rewritten == text:
        return False
    path.write_text(rewritten, encoding="utf-8", newline="\n")
    return True


def main() -> int:
    changed = sum(
        clean(path)
        for path in ROOT.glob("src/part*/ch*/*.md")
        if path.name != "README.md"
    )
    print(f"removed temporary editorial fields from {changed} canonical files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
