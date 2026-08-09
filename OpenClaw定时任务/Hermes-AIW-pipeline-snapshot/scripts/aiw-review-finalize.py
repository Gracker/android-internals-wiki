#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
SRC=AIW/'src'
META=AIW/'metadata'
QUEUE=META/'queue.json'
STATE=Path('/Users/gracker/.hermes/state/aiw-review-finalize')
REPORT_ROOT=OB/'OpenClaw定时任务/AIW自动化流水线'
MODES={'reader-final':'AIW · DeepSeek 中文读者终审','task2b-verifier':'Task2B Verifier · 回流复查','deep-tech-review':'AIW · 深度技术Review','draft-review':'AIW · 草稿Review与精修'}

def fm(p:Path):
    t=p.read_text(encoding='utf-8',errors='ignore')[:5000]
    if not t.startswith('---'): return {}
    e=t.find('\n---',3)
    if e<0: return {}
    d={}
    for l in t[3:e].splitlines():
        if ':' in l and not l.lstrip().startswith('-'):
            k,v=l.split(':',1); d[k.strip()]=v.strip().strip('"\'')
    return d

def qitems():
    try: q=json.loads(QUEUE.read_text(encoding='utf-8'))
    except Exception: q=[]
    arr=q if isinstance(q,list) else q.get('pending',[])
    return [x for x in arr if isinstance(x,dict) and x.get('status','pending')=='pending']

def scan_candidates(mode):
    out=[]
    for p in sorted(SRC.rglob('*.md'))[:250]:
        if p.name.lower() in ('readme.md','summary.md'): continue
        d=fm(p); text=json.dumps(d,ensure_ascii=False).lower()
        rel=str(p.relative_to(AIW))
        if mode=='reader-final' and (d.get('status') in ['draft','review','finalized','finalized-v2'] or 'task6' in text): out.append({'path':rel,'reason':'reader-experience candidate','frontmatter':d})
        elif mode=='task2b-verifier' and any(k in text for k in ['fixed','fixed-lite','auto-fixed','task6_pending','ready-for-task6']): out.append({'path':rel,'reason':'verifier回流候选','frontmatter':d})
        elif mode=='draft-review' and (d.get('task6_state') in ['pending','idle','needs-review'] or d.get('status') in ['draft','review']): out.append({'path':rel,'reason':'draft-review候选','frontmatter':d})
        elif mode=='deep-tech-review' and (d.get('task9_state') in ['pending','idle','needs-review'] or d.get('status') in ['draft','review']): out.append({'path':rel,'reason':'deep-tech-review候选','frontmatter':d})
        if len(out)>=8: break
    if not out and mode!='reader-final':
        out=qitems()[:5]
    return out

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=sorted(MODES),required=True); ap.add_argument('--date',default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args(); STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    cands=scan_candidates(args.mode)
    status='candidate_ready' if cands else 'skipped'
    payload={'schema_version':1,'profile':'aiw-review-finalize','mode':args.mode,'label':MODES[args.mode],'status':status,'dry_run':args.dry_run,'candidates':cands,'constraints':['gate/report only','no chapter body edits','android-17.0.0_r1 baseline','versions higher than Android 17 are out of scope'],'generated_at':datetime.now(TZ).isoformat()}
    od=STATE/args.mode; od.mkdir(parents=True,exist_ok=True); os.chmod(od,0o700)
    out=od/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    report=REPORT_ROOT/f"{args.date}-aiw-review-finalize-{args.mode}.md"
    if not args.dry_run:
        report.parent.mkdir(parents=True,exist_ok=True)
        report.write_text(f"# {MODES[args.mode]} · {args.date}\n\n- status: {status}\n- candidates: {len(cands)}\n- evidence: `{out}`\n\n```json\n{json.dumps(cands[:5],ensure_ascii=False,indent=2)}\n```\n\n> Gate only: no chapter body edits were made.\n",encoding='utf-8')
    print(f"{MODES[args.mode]}\nstatus: {status}\ndry_run: {args.dry_run}\ncandidates: {len(cands)}\nreport: {report}\nevidence: {out}")
    return 0
if __name__=='__main__': raise SystemExit(main())
