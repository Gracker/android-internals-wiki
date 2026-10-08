#!/usr/bin/env python3
"""中文正文文风检查与事实保真校验（标准库实现，无第三方依赖）。

用法：
  python3 scripts/style_lint.py rank [--top N] [--exclude-days D]   # 按 H2 小节列出文风最差的候选
  python3 scripts/style_lint.py check FILE                          # 输出单篇文风指标
  python3 scripts/style_lint.py compare OLD NEW                     # 改写前后对比；不通过时退出码为 1

compare 的两类检查：
  1. 事实保真：frontmatter、代码块、标题数量、行内代码集合、链接集合、数字集合必须一致；
     汉字数量需在原文的 70%～110% 之间。
  2. 文风不退化：括注密度、否定密度、重复括注、禁用词都不能变差，且至少有一项明显改善。
"""
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

FRONTMATTER = re.compile(r"\A---\n.*?\n---\n", re.S)
FENCE = re.compile(r"^```.*?^```", re.S | re.M)
INLINE_CODE = re.compile(r"`[^`\n]+`")
LINK = re.compile(r"\]\(([^)\s]+)\)")
CJK = re.compile(r"[一-鿿]")
GLOSS = re.compile(r"（[^（）\n]{1,40}）")
TERM_GLOSS = re.compile(r"([A-Za-z][A-Za-z0-9_/\-\.]*(?: [A-Za-z][A-Za-z0-9_/\-\.]*){0,3})（[^（）\n]{1,40}）")
NEG = re.compile(r"不能|不代表|不等于|无法|不应|并非|不意味着|不能据此")
JARGON = re.compile(r"口径|边界|锚点|证据")
NUM = re.compile(r"(?<![A-Za-z_\-./#])\d+(?:\.\d+)?")
BANNED = [
    "赋能", "闭环", "底座", "抓手", "下钻", "落地", "打通", "心智", "颗粒度", "组合拳",
    "先说判断", "先给结论", "综上所述", "总而言之", "一言以蔽之", "值得重点关注", "值得深思",
    "不难看出", "显然", "众所周知", "不言而喻", "由此可见", "值得注意的是", "需要指出的是",
    "关键在于", "核心要点", "本质上", "换句话说", "可以说",
]


def strip_for_prose(text):
    """去掉 frontmatter、代码块、表格行与标题行，只留正文段落。"""
    text = FRONTMATTER.sub("", text)
    text = FENCE.sub("", text)
    lines = [l for l in text.split("\n") if not l.lstrip().startswith(("|", "#"))]
    return "\n".join(lines)


def metrics(prose):
    no_code = INLINE_CODE.sub("", prose)
    n = max(len(CJK.findall(no_code)), 1)
    terms = Counter(m.group(1) for m in TERM_GLOSS.finditer(no_code))
    paras = [p for p in re.split(r"\n\s*\n", no_code) if p.strip() and not p.lstrip().startswith(("-", ">", "1."))]
    return {
        "cjk": n,
        "gloss_per_1k": round(len(GLOSS.findall(no_code)) * 1000 / n, 2),
        "neg_per_1k": round(len(NEG.findall(no_code)) * 1000 / n, 2),
        "jargon_per_1k": round(len(JARGON.findall(no_code)) * 1000 / n, 2),
        "regloss": sum(v - 1 for v in terms.values() if v > 1),
        "regloss_terms": sorted(t for t, v in terms.items() if v > 1),
        "banned": sorted({w for w in BANNED if w in no_code}),
        "women": no_code.count("我们"),
        "long_paras": sum(1 for p in paras if len(CJK.findall(p)) > 220),
    }


def score(m):
    return m["gloss_per_1k"] + 2 * m["neg_per_1k"] + m["jargon_per_1k"] + m["regloss"] + 3 * len(m["banned"])


def split_h2(text):
    body = FRONTMATTER.sub("", text)
    parts = re.split(r"^(## .+)$", body, flags=re.M)
    yield "(导语)", parts[0]
    for i in range(1, len(parts), 2):
        yield parts[i][3:].strip(), parts[i + 1]


def recently_touched(days):
    if days <= 0:
        return set()
    out = subprocess.run(
        ["git", "log", f"--since={days} days ago", "--grep=aiw-chinese-", "--name-only", "--format="],
        capture_output=True, text=True,
    ).stdout
    return {l.strip() for l in out.splitlines() if l.strip()}


def cmd_rank(args):
    top = int(args[args.index("--top") + 1]) if "--top" in args else 10
    days = int(args[args.index("--exclude-days") + 1]) if "--exclude-days" in args else 3
    skip = recently_touched(days)
    rows = []
    for f in sorted(Path("src").rglob("*.md")):
        if str(f) in skip or f.name == "SUMMARY.md":
            continue
        for head, sec in split_h2(f.read_text(encoding="utf-8")):
            m = metrics(strip_for_prose(sec))
            if m["cjk"] >= 800:
                rows.append((round(score(m), 1), str(f), head, m))
    rows.sort(key=lambda r: -r[0])
    for s, f, head, m in rows[:top]:
        print(f"{s:6.1f}  {f}  ## {head}  cjk={m['cjk']} gloss={m['gloss_per_1k']} neg={m['neg_per_1k']} "
              f"jargon={m['jargon_per_1k']} regloss={m['regloss']} banned={m['banned']}")


def facts(text):
    fm = FRONTMATTER.match(text)
    body = FRONTMATTER.sub("", text)
    blocks = FENCE.findall(body)
    rest = FENCE.sub("", body)
    no_code = INLINE_CODE.sub("", rest)
    no_links = LINK.sub("", no_code)
    return {
        "frontmatter": fm.group(0) if fm else "",
        "code_blocks": blocks,
        "headings": len(re.findall(r"^#{1,6} ", rest, re.M)),
        "inline_code": set(INLINE_CODE.findall(rest)),
        "links": set(LINK.findall(rest)),
        "numbers": set(NUM.findall(no_links)),
        "cjk": len(CJK.findall(rest)),
    }


def cmd_compare(old_path, new_path):
    old_t = Path(old_path).read_text(encoding="utf-8")
    new_t = Path(new_path).read_text(encoding="utf-8")
    fo, fn = facts(old_t), facts(new_t)
    errors = []
    if fo["frontmatter"] != fn["frontmatter"]:
        errors.append("frontmatter 被修改")
    if fo["code_blocks"] != fn["code_blocks"]:
        errors.append("代码块被修改")
    if fo["headings"] != fn["headings"]:
        errors.append(f"标题数量变化 {fo['headings']} -> {fn['headings']}")
    for key, label in (("inline_code", "行内代码"), ("links", "链接"), ("numbers", "数字")):
        added, removed = fn[key] - fo[key], fo[key] - fn[key]
        if key == "links":
            added = {l for l in added if l.startswith("http")}  # 允许新增站内链接（如指向术语表）
        if added:
            errors.append(f"新增{label}: {sorted(added)[:10]}")
        if removed:
            errors.append(f"删除{label}: {sorted(removed)[:10]}")
    ratio = fn["cjk"] / max(fo["cjk"], 1)
    if not 0.70 <= ratio <= 1.10:
        errors.append(f"汉字数量变化超出范围：{ratio:.0%}")

    mo, mn = metrics(strip_for_prose(old_t)), metrics(strip_for_prose(new_t))
    for k in ("gloss_per_1k", "neg_per_1k", "regloss"):
        if mn[k] > mo[k] + 0.05:
            errors.append(f"{k} 变差 {mo[k]} -> {mn[k]}")
    if set(mn["banned"]) - set(mo["banned"]):
        errors.append(f"新增禁用词 {sorted(set(mn['banned']) - set(mo['banned']))}")
    improved = (mo["gloss_per_1k"] - mn["gloss_per_1k"] >= 0.5 or mo["neg_per_1k"] - mn["neg_per_1k"] >= 0.3
                or mo["regloss"] - mn["regloss"] >= 2 or len(mo["banned"]) > len(mn["banned"]))
    if not improved:
        errors.append("文风指标没有明显改善（视为无效润色，不应提交）")

    def view(m):
        return {k: v for k, v in m.items() if k != "regloss_terms"}

    print(json.dumps({"pass": not errors, "errors": errors, "before": view(mo), "after": view(mn)},
                     ensure_ascii=False, indent=2))
    return 0 if not errors else 1


def main(argv):
    if len(argv) >= 2 and argv[1] == "rank":
        cmd_rank(argv[2:])
        return 0
    if len(argv) == 3 and argv[1] == "check":
        m = metrics(strip_for_prose(Path(argv[2]).read_text(encoding="utf-8")))
        print(json.dumps(m, ensure_ascii=False, indent=2))
        return 0
    if len(argv) == 4 and argv[1] == "compare":
        return cmd_compare(argv[2], argv[3])
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
