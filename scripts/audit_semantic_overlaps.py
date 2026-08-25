#!/usr/bin/env python3
"""Rank canonical article pairs that may describe the same topic.

The report is an editorial candidate list, not an automatic merge decision.
It uses IDF-weighted title, outline and technical-term vectors so common book
vocabulary such as Android, performance and diagnostics contributes little.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")
LATIN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:+/-]{1,}")
HAN_RE = re.compile(r"[\u3400-\u9fff]+")
CODE_RE = re.compile(r"`([^`\n]{2,80})`")
GENERIC = {
    "android",
    "性能",
    "优化",
    "分析",
    "机制",
    "实践",
    "系统",
    "应用",
    "工具",
    "版本",
    "源码",
    "边界",
    "诊断",
    "管理",
    "实现",
    "流程",
    "原理",
    "架构",
    "问题",
    "方法",
    "指南",
}


def split_frontmatter(text: str) -> tuple[dict[str, object], str]:
    if not text.startswith("---\n"):
        return {}, text
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    meta = yaml.safe_load(text[4:end]) or {}
    return meta if isinstance(meta, dict) else {}, text[end + 5 :]


def headings(body: str) -> list[tuple[int, str]]:
    result: list[tuple[int, str]] = []
    fenced = False
    for line in body.splitlines():
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_RE.match(line)
        if match:
            result.append((len(match.group(1)), match.group(2)))
    return result


def tokens(value: str, *, han_sizes: tuple[int, ...] = (2, 3)) -> list[str]:
    value = re.sub(r"\d+(?:\.\d+)*", " ", value)
    result = [item.casefold() for item in LATIN_RE.findall(value)]
    for run in HAN_RE.findall(value):
        if run in GENERIC:
            continue
        for size in han_sizes:
            if len(run) < size:
                continue
            result.extend(run[index : index + size] for index in range(len(run) - size + 1))
    return [item for item in result if item not in GENERIC]


def canonical() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for path in sorted(ROOT.glob("src/part*/ch*/*.md")):
        if path.name == "README.md":
            continue
        text = path.read_text(encoding="utf-8")
        meta, body = split_frontmatter(text)
        hs = headings(body)
        title = str(meta.get("title") or next((value for level, value in hs if level == 1), path.stem))
        outline = " ".join(value for level, value in hs if level in {2, 3})
        code_terms = " ".join(CODE_RE.findall(body))
        prose_sample = re.sub(r"```.*?```|~~~.*?~~~", " ", body, flags=re.S)[:16000]
        result.append(
            {
                "path": str(path.relative_to(ROOT)),
                "chapter": str(meta.get("chapter") or ""),
                "title": title,
                "title_tf": Counter(tokens(title, han_sizes=(1, 2, 3))),
                "outline_tf": Counter(tokens(outline, han_sizes=(2, 3))),
                "body_tf": Counter(tokens(code_terms + " " + prose_sample, han_sizes=(3,))),
            }
        )
    return result


def vectors(rows: list[dict[str, object]], field: str) -> list[dict[str, float]]:
    doc_freq: Counter[str] = Counter()
    for row in rows:
        doc_freq.update((row[field]).keys())  # type: ignore[union-attr]
    total = len(rows)
    result: list[dict[str, float]] = []
    for row in rows:
        tf: Counter[str] = row[field]  # type: ignore[assignment]
        vector: dict[str, float] = {}
        for term, count in tf.items():
            df = doc_freq[term]
            if df < 2 or df > total * 0.35:
                continue
            idf = math.log((total + 1) / (df + 1)) + 1
            vector[term] = (1 + math.log(count)) * idf
        norm = math.sqrt(sum(value * value for value in vector.values())) or 1.0
        result.append({term: value / norm for term, value in vector.items()})
    return result


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if len(left) > len(right):
        left, right = right, left
    return sum(value * right.get(term, 0.0) for term, value in left.items())


def report(limit: int, threshold: float) -> dict[str, object]:
    rows = canonical()
    title_vectors = vectors(rows, "title_tf")
    outline_vectors = vectors(rows, "outline_tf")
    body_vectors = vectors(rows, "body_tf")
    pairs: list[dict[str, object]] = []
    for left in range(len(rows)):
        for right in range(left + 1, len(rows)):
            title_score = cosine(title_vectors[left], title_vectors[right])
            outline_score = cosine(outline_vectors[left], outline_vectors[right])
            body_score = cosine(body_vectors[left], body_vectors[right])
            score = 0.52 * title_score + 0.33 * outline_score + 0.15 * body_score
            if score < threshold:
                continue
            pairs.append(
                {
                    "score": round(score, 4),
                    "title_score": round(title_score, 4),
                    "outline_score": round(outline_score, 4),
                    "body_score": round(body_score, 4),
                    "left": {
                        "chapter": rows[left]["chapter"],
                        "title": rows[left]["title"],
                        "path": rows[left]["path"],
                    },
                    "right": {
                        "chapter": rows[right]["chapter"],
                        "title": rows[right]["title"],
                        "path": rows[right]["path"],
                    },
                }
            )
    pairs.sort(key=lambda item: (-float(item["score"]), str(item["left"]), str(item["right"])))
    return {
        "schema_version": 1,
        "scope": f"{len(rows)} canonical chapter bodies",
        "method": "IDF-weighted title 52% + H2/H3 outline 33% + technical/body sample 15%",
        "threshold": threshold,
        "candidate_count_before_limit": len(pairs),
        "pairs": pairs[:limit],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=160)
    parser.add_argument("--threshold", type=float, default=0.16)
    parser.add_argument("--output")
    args = parser.parse_args()
    value = report(args.limit, args.threshold)
    if args.output:
        output = Path(args.output)
        if not output.is_absolute():
            output = ROOT / output
        output.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for index, pair in enumerate(value["pairs"], 1):
        left = pair["left"]
        right = pair["right"]
        print(
            f'{index:>3}. {pair["score"]:.4f}  '
            f'{left["chapter"]} {left["title"]}  <->  {right["chapter"]} {right["title"]}'
        )
    print(f'candidates: {value["candidate_count_before_limit"]}; shown: {len(value["pairs"])}')
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
