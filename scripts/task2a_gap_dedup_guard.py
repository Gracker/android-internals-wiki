#!/usr/bin/env python3
"""
Task 2A gap-mining duplicate guard.

This guard is intentionally read-only. It compares proposed gap-mining
candidates against all non-superseded AIW chapters, including
ready-for-review/finalized chapters and substantive draft outlines.

Exit codes:
  0  no blocking duplicate coverage found
  1  invalid input or self-test failure
  2  at least one candidate is already covered and must not be created
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = "src"
SKIP_NAMES = {"readme.md", "summary.md"}
BLOCKING_STATUSES = {
    "draft",
    "ready-for-review",
    "reviewed",
    "finalized",
    "finalized-v2",
    "ready-to-publish",
}
IGNORED_STATUSES = {"superseded", "deprecated", "archived"}

ASCII_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_+.#-]{1,}")
CJK_RUN_RE = re.compile(r"[\u3400-\u9fff]{2,}")

ASCII_STOP = {
    "android",
    "api",
    "aosp",
    "the",
    "and",
    "with",
    "for",
    "task",
    "draft",
}
CJK_STOP = {
    "性能",
    "优化",
    "源码",
    "分析",
    "实现",
    "内部",
    "原理",
    "工具",
    "新特性",
    "实践",
    "真相",
    "条件",
    "影响",
    "章节",
    "通信",
    "监控",
    "性能监",
    "性能监控",
    "通信性能",
}

REGRESSION_CANDIDATES = [
    {
        "title": "Android 17 RPC Binder 事务上限提升",
        "keywords": ["Binder RPC", "事务上限", "600KB"],
    },
    {
        "title": "Android 17 MemoryLimiter 的 30 秒 Kill 窗口真相与 ProfilingServiceHelper 触发条件",
        "keywords": ["MemoryLimiter", "30 秒 kill", "ProfilingServiceHelper", "AnonSwap"],
    },
    {
        "title": "Android 17 系统启动耗时优化新特性与 bootanalyze 工具链",
        "keywords": ["bootanalyze", "系统启动", "Zygote preload", "SystemServer"],
    },
    {
        "title": "Android 17 Vulkan 多队列并行渲染与 GPU 负载均衡",
        "keywords": ["Vulkan", "多队列", "GPU", "HWUI", "GrallocUploadThread"],
    },
    {
        "title": "Compose Pausable Composition 内部实现",
        "keywords": ["Compose", "PausableComposition", "LazyList", "shouldPause"],
    },
    {
        "title": "Adaptive Layout 多形态设备性能",
        "keywords": ["Adaptive Layout", "多形态设备", "WindowSizeClass", "折叠屏"],
    },
]


@dataclass(frozen=True)
class ChapterDoc:
    path: Path
    relpath: str
    title: str
    section: str
    status: str
    searchable: str
    compact: str
    title_compact: str
    ascii_tokens: frozenset[str]
    substantive_lines: int


def compact_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).casefold()
    return "".join(ch for ch in value if ch.isalnum() or "\u3400" <= ch <= "\u9fff")


def parse_frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    frontmatter = text[3:end]
    body = text[end + 4 :]
    parsed: dict[str, str] = {}
    for line in frontmatter.splitlines():
        raw = line.strip()
        if not raw or raw.startswith("-") or ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        parsed[key.strip()] = value.strip().strip("\"'")
    return parsed, body


def substantive_line_count(body: str) -> int:
    count = 0
    for line in body.splitlines():
        raw = line.strip()
        if not raw:
            continue
        if raw.startswith("<!--") or raw.startswith("-->"):
            continue
        if raw == "> 本节内容待加工。":
            continue
        count += 1
    return count


def iter_chapters(root: Path) -> list[ChapterDoc]:
    docs: list[ChapterDoc] = []
    src = root / SRC_DIR
    for path in sorted(src.rglob("*.md")):
        if path.name.casefold() in SKIP_NAMES:
            continue
        text = path.read_text("utf-8", errors="ignore")
        fm, body = parse_frontmatter(text)
        status = fm.get("status", "").strip().casefold()
        if status in IGNORED_STATUSES:
            continue

        lines = substantive_line_count(body)
        # Empty placeholders are not coverage. Substantive outlines are.
        if status == "draft" and lines < 8:
            continue

        title = fm.get("title") or first_heading(body) or path.stem
        section = fm.get("chapter") or ""
        searchable = "\n".join(
            [
                title,
                section,
                fm.get("tags", ""),
                fm.get("related_chapters", ""),
                body,
            ]
        )
        docs.append(
            ChapterDoc(
                path=path,
                relpath=str(path.relative_to(root)),
                title=title,
                section=section,
                status=status or "unknown",
                searchable=searchable,
                compact=compact_text(searchable),
                title_compact=compact_text(title),
                ascii_tokens=frozenset(
                    token.group(0).casefold().strip("-_.+#")
                    for token in ASCII_RE.finditer(searchable)
                ),
                substantive_lines=lines,
            )
        )
    return docs


def first_heading(body: str) -> str:
    for line in body.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def add_term(terms: dict[str, float], term: str, weight: float) -> None:
    clean = compact_text(term)
    if not clean:
        return
    if clean in ASCII_STOP or clean in CJK_STOP:
        return
    if len(clean) < 2:
        return
    terms[clean] = max(terms.get(clean, 0.0), weight)


def extract_terms(value: str) -> dict[str, float]:
    normalized = unicodedata.normalize("NFKC", value)
    terms: dict[str, float] = {}

    for match in ASCII_RE.finditer(normalized):
        term = match.group(0).casefold().strip("-_.+#")
        if len(term) < 3 or term in ASCII_STOP:
            continue
        weight = 3.0 if len(term) >= 5 else 2.0
        add_term(terms, term, weight)

    for run_match in CJK_RUN_RE.finditer(normalized):
        run = run_match.group(0)
        pieces = [p for p in re.split(r"[的与和及、：，。；（）()]+", run) if len(p) >= 2]
        for piece in pieces:
            if len(piece) <= 8:
                add_term(terms, piece, min(3.0, 1.2 + len(piece) / 4))
            max_n = min(6, len(piece))
            for n in range(2, max_n + 1):
                for i in range(0, len(piece) - n + 1):
                    gram = piece[i : i + n]
                    if gram in CJK_STOP:
                        continue
                    add_term(terms, gram, 1.0 + min(n, 4) / 4)
    return terms


def load_candidates(args: argparse.Namespace) -> list[dict[str, Any]]:
    if args.self_test:
        return REGRESSION_CANDIDATES

    raw: Any
    if args.stdin:
        raw = json.load(sys.stdin)
    elif args.json_file:
        raw = json.loads(Path(args.json_file).read_text("utf-8"))
    elif args.candidate:
        raw = [
            {
                "title": title,
                "keywords": split_keywords(args.keywords),
            }
            for title in args.candidate
        ]
    else:
        raise SystemExit("Provide --candidate, --json-file, --stdin, or --self-test")

    if isinstance(raw, dict):
        raw = raw.get("candidates", [])
    if not isinstance(raw, list):
        raise SystemExit("Candidate input must be a list or {'candidates': [...]}")

    candidates: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, str):
            candidates.append({"title": item, "keywords": []})
        elif isinstance(item, dict) and item.get("title"):
            keywords = item.get("keywords", [])
            if isinstance(keywords, str):
                keywords = split_keywords(keywords)
            candidates.append({"title": str(item["title"]), "keywords": list(keywords)})
        else:
            raise SystemExit(f"Invalid candidate item: {item!r}")
    return candidates


def split_keywords(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in re.split(r"[,，;；\n]+", value) if part.strip()]


def score_candidate(candidate: dict[str, Any], doc: ChapterDoc, threshold: float) -> dict[str, Any] | None:
    title = str(candidate["title"])
    keywords = [str(k) for k in candidate.get("keywords", [])]
    source = "\n".join([title, *keywords])
    terms = extract_terms(source)
    if not terms:
        return None

    title_compact = compact_text(title)
    if title_compact and title_compact in doc.compact:
        return match_payload(doc, 1.0, sorted(terms), "title-contained")

    total_weight = sum(terms.values())
    matched = [term for term in terms if term_matches(term, doc)]
    matched_weight = sum(terms[term] for term in matched)
    ratio = matched_weight / total_weight if total_weight else 0.0
    title_matched = [term for term in terms if term_matches_title(term, doc)]
    title_weight = sum(terms[term] for term in title_matched)
    title_ratio = title_weight / total_weight if total_weight else 0.0
    score = min(1.0, ratio + title_ratio * 0.25)
    tech_hits = [term for term in matched if terms[term] >= 2.5]

    reason = ""
    if score >= threshold:
        reason = f"weighted-overlap>={threshold:.2f}"
    elif len(tech_hits) >= 2 and score >= 0.24:
        reason = "multiple-tech-terms"
    elif len(tech_hits) >= 1 and score >= 0.48:
        reason = "tech-term-plus-context"
    else:
        return None

    return match_payload(doc, score, matched, reason)


def term_matches(term: str, doc: ChapterDoc) -> bool:
    if term.isascii():
        if len(term) <= 4:
            return term in doc.ascii_tokens
        return term in doc.ascii_tokens or term in doc.compact
    return term in doc.compact


def term_matches_title(term: str, doc: ChapterDoc) -> bool:
    if term.isascii():
        if len(term) <= 4:
            return term in {
                token.group(0).casefold().strip("-_.+#")
                for token in ASCII_RE.finditer(doc.title)
            }
        return term in doc.title_compact
    return term in doc.title_compact


def match_payload(doc: ChapterDoc, score: float, matched_terms: list[str], reason: str) -> dict[str, Any]:
    return {
        "section": doc.section,
        "title": doc.title,
        "status": doc.status,
        "path": doc.relpath,
        "score": round(score, 3),
        "reason": reason,
        "matched_terms": matched_terms[:24],
        "substantive_lines": doc.substantive_lines,
    }


def run(root: Path, candidates: list[dict[str, Any]], threshold: float) -> dict[str, Any]:
    docs = iter_chapters(root)
    blocked: list[dict[str, Any]] = []
    clear: list[dict[str, Any]] = []

    for candidate in candidates:
        matches = []
        for doc in docs:
            match = score_candidate(candidate, doc, threshold)
            if match:
                matches.append(match)
        matches.sort(key=lambda item: (-item["score"], item["path"]))
        payload = {
            "title": candidate["title"],
            "keywords": candidate.get("keywords", []),
            "matches": matches[:8],
        }
        if matches:
            blocked.append(payload)
        else:
            clear.append(payload)

    return {
        "status": "blocked" if blocked else "clear",
        "root": str(root),
        "chapter_corpus": len(docs),
        "candidate_count": len(candidates),
        "blocked_count": len(blocked),
        "blocked": blocked,
        "clear": clear,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="AIW repository root")
    parser.add_argument("--candidate", action="append", help="Candidate title; can be repeated")
    parser.add_argument("--keywords", help="Comma/newline separated keywords for --candidate")
    parser.add_argument("--json-file", help="JSON list of {'title', 'keywords'} candidates")
    parser.add_argument("--stdin", action="store_true", help="Read candidate JSON from stdin")
    parser.add_argument("--threshold", type=float, default=0.42, help="Weighted overlap block threshold")
    parser.add_argument("--self-test", action="store_true", help="Run known duplicate regression set")
    args = parser.parse_args()

    root = Path(args.root).expanduser().resolve()
    candidates = load_candidates(args)
    result = run(root, candidates, args.threshold)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.self_test:
        return 0 if result["blocked_count"] == len(candidates) else 1
    return 2 if result["blocked_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
