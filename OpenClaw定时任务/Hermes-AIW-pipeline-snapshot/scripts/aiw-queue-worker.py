#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
META=AIW/'metadata'
QUEUE=META/'queue.json'
GAPS=AIW/'intake/research-gaps.md'
TOPICS=Path('/Users/gracker/.openclaw/workspace/AutoResearchClaw/state/daily-topics.json')
STATE=Path('/Users/gracker/.hermes/state/aiw-queue-worker')
REPORT_ROOT=OB/'OpenClaw定时任务/AIW自动化流水线'
MODES={'task2b-lite':'Task2B Lite · 高置信局部小修','source-research':'AIW 每日源码调研','task2a':'AIW 知识加工 2A','task2b-main':'Task 2B · 回炉修复'}
CHAPTER_FREEZE=True

def jload(p, default):
    if not p.exists(): return default
    try: return json.loads(p.read_text(encoding='utf-8'))
    except Exception: return default

def save(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); tmp.replace(p)

def text(p:Path)->str:
    try: return p.read_text(encoding='utf-8', errors='ignore')
    except Exception: return ''

def queue_items():
    q=jload(QUEUE, [])
    items=q if isinstance(q,list) else q.get('pending',[])
    return [x for x in items if isinstance(x,dict) and x.get('status','pending')=='pending']

def gaps_items(limit=8):
    if not GAPS.exists(): return []
    raw=GAPS.read_text(encoding='utf-8',errors='ignore')
    blocks=re.split(r'(?m)^##\s+',raw)[1:]
    return [{'title':b.splitlines()[0][:120], 'source':'research-gaps.md'} for b in blocks[:limit]]

def topic_items():
    d=jload(TOPICS,{})
    arr=d if isinstance(d,list) else d.get('topics', d.get('items', []))
    return [x for x in arr if isinstance(x,dict) and x.get('status','pending')=='pending'][:5]

def existing_empty_drafts(limit=8):
    """Return only existing chapter files that are safe for Task2A under chapter freeze."""
    src=AIW/'src'
    out=[]
    if not src.exists(): return out
    for p in sorted(src.rglob('*.md')):
        if p.name.lower() in ('readme.md','summary.md'): continue
        raw=text(p)
        head=raw[:3000].lower()
        if 'status: draft' not in head: continue
        body=raw.split('---',2)[-1] if raw.startswith('---') else raw
        substantive=[l for l in body.splitlines() if l.strip() and not l.lstrip().startswith(('#','>','- **'))]
        if len(substantive) < 15:
            out.append({'path':str(p.relative_to(AIW)),'title':p.stem,'source':'existing-empty-draft','allowed_action':'fill existing draft only; do not create files or edit SUMMARY.md'})
        if len(out)>=limit: break
    return out

def pick(mode):
    if mode in ('task2b-lite','task2b-main'):
        for x in queue_items():
            qtext=json.dumps(x,ensure_ascii=False).lower()
            if 'new-chapter' in qtext or '新增章节' in qtext:
                continue
            if mode=='task2b-lite' and any(k in qtext for k in ['源码路径','api','frontmatter','交叉引用','版本限定','reference','link']): return x
            if mode=='task2b-main' and any(k in qtext for k in ['task6','task9','external','review','rework','needs-rework','pending','回炉','修复']): return x
        safe=[x for x in queue_items() if '新增章节' not in json.dumps(x,ensure_ascii=False).lower()]
        return (safe or [None])[0]
    if mode=='source-research':
        return (topic_items() or gaps_items() or [None])[0]
    if mode=='task2a':
        return (existing_empty_drafts() or [None])[0]
    return (queue_items() or [None])[0]

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=sorted(MODES),required=True); ap.add_argument('--date',default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args(); STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    cand=pick(args.mode)
    status='skipped' if cand is None else 'candidate_ready'
    freeze_constraints=['CHAPTER_FREEZE: do not create new chapter files','do not append src/SUMMARY.md','do not enqueue new-chapter work','Task2A may only fill existing empty draft chapters; if none, stop']
    packet={'schema_version':1,'profile':'aiw-queue-worker','mode':args.mode,'label':MODES[args.mode],'status':status,'dry_run':args.dry_run,'candidate':cand,'constraints':freeze_constraints+['android-17.0.0_r1 baseline','do not promote any version higher than Android 17','do not modify chapter bodies from this gate','human/agent follow-up required for actual content edits'],'generated_at':datetime.now(TZ).isoformat()}
    outdir=STATE/args.mode; outdir.mkdir(parents=True,exist_ok=True); os.chmod(outdir,0o700)
    out=outdir/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(packet,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    report=REPORT_ROOT/f"{args.date}-aiw-queue-worker-{args.mode}.md"
    if not args.dry_run:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(f"# {MODES[args.mode]} · {args.date}\n\n- status: {status}\n- chapter_freeze: {CHAPTER_FREEZE}\n- evidence: `{out}`\n- candidate:\n```json\n{json.dumps(cand,ensure_ascii=False,indent=2) if cand is not None else 'null'}\n```\n\n> Gate only: no chapter body edits were made. Chapter creation is frozen.\n",encoding='utf-8')
    print(f"{MODES[args.mode]}\nstatus: {status}\nchapter_freeze: {CHAPTER_FREEZE}\ndry_run: {args.dry_run}\nreport: {report}\nevidence: {out}")
    return 0
if __name__=='__main__': raise SystemExit(main())
