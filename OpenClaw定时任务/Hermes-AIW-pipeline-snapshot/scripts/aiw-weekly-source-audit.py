#!/usr/bin/env python3
from __future__ import annotations

import argparse, json, os, re, subprocess, sys
import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from aiw_pipeline_common import affirmative_higher_android_mentions, iter_canonical_chapters

TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
SRC=AIW/'src'
META=AIW/'metadata'
QUEUE=META/'queue.json'
FINDINGS=META/'review-findings.json'
CLIP=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Clippings')
SUG=AIW/'intake/suggestions.md'
GAPS=AIW/'intake/research-gaps.md'
STATE=Path('/Users/gracker/.hermes/state/aiw-weekly-source-audit')
REPORT_ROOT=OB/'OpenClaw定时任务/AIW自动化流水线'
BOOKS=[
 ('Android 应用稳定性剖析与优化 - Pika','Android 应用稳定性剖析与优化',15,'ch20'),
 ('Android 性能优化 - 赵子健','Android 性能优化',16,'ch21-ch25'),
 ('线上疑难问题该如何排查和跟踪','线上疑难问题该如何排查和跟踪',59,'ch26'),
]
KW=[('crash|anr|stability|稳定|崩溃|oom','ch20'),('startup|启动|apk|安装包','ch21'),('render|渲染|帧|jank|卡顿|surface','ch22'),('memory|内存|heap|native','ch23'),('io|存储|文件|缓存','ch24'),('power|功耗|电量|调度|cpu','ch25'),('trace|监控|排查|observability|日志|埋点','ch26')]

def jload(path:Path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default

def jsave(path:Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    tmp.replace(path)

def append(path:Path, body:str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        if path.exists() and path.stat().st_size: f.write('\n')
        f.write(body.strip()+'\n')

def clean(s:str)->str:
    # Clippings may contain one-line SVG/audio payloads. They are transport/UI
    # markup, not knowledge points, and previously polluted suggestions.md.
    s=re.split(r'<(?:svg|audio|script|style)\b',s,maxsplit=1,flags=re.I)[0]
    s=re.sub(r'<[^>]+>',' ',s)
    return re.sub(r'\s+',' ',s).strip()

def chapter(s:str)->str:
    low=s.lower()
    for pat,ch in KW:
        if any(x in low for x in pat.split('|')): return ch
    return 'ch26'

def init_clip_state():
    return {'schema_version':1,'cursor':0,'processed':{},'total_knowledge_points':0,'total_suggestions':0,'total_gaps':0,'last_scan_date':None}

def clip_files():
    if not CLIP.exists(): return []
    files=[]
    for p in sorted(CLIP.glob('*.md'), key=lambda x:x.name):
        name=p.name
        if name.startswith('Android 应用稳定性剖析与优化') or name.startswith('Android 性能优化') or name.startswith('线上疑难问题该如何排查'):
            files.append(p)
    return files

def extract_points(p:Path, max_points:int=4):
    text=p.read_text(encoding='utf-8', errors='ignore')[:12000]
    lines=[]
    for l in text.splitlines():
        s=l.strip(' #-*\t')
        if len(s)>=18 and not s.startswith('http') and not s.startswith('!['):
            lines.append(clean(s))
    if not lines:
        lines=[p.stem]
    pts=[]
    for s in lines[:60]:
        if any(k.lower() in s.lower() for k in ['android','crash','anr','内存','线程','binder','启动','渲染','性能','监控','排查','native','oom','卡顿','缓存','cpu','功耗']):
            pts.append(s[:130])
        if len(pts)>=max_points: break
    return pts or [p.stem]

def run_clippings(args):
    files=clip_files(); state_path=META/'clippings-scan-progress.json'; state=jload(state_path, init_clip_state())
    done=state.setdefault('processed',{})
    start=int(state.get('cursor',0))
    batch=[]; i=start
    while len(batch)<args.max_files and i < len(files):
        if str(files[i]) not in done: batch.append(files[i])
        i+=1
    if not batch and start>=len(files):
        return {'mode':'clippings-reference-scan','status':'ok','completed':True,'scanned':0,'total_files':len(files),'message':'参考资料差异扫描已全部完成'}
    today=args.date; sug=[]; gaps=[]; items=[]; kp=0
    for p in batch:
        pts=extract_points(p); kp+=len(pts); ch=chapter(p.name+' '+' '.join(pts)); target=GAPS if ch in ['ch21','ch22','ch23','ch24','ch25','ch26'] else SUG
        block=f"## [Task14 参考书扫描] {ch} — {today}\n- **类型**：现有章节参考/案例候选（章节冻结：不新增章节）\n- **来源**：[结构参考: Clippings/{p.name}]\n- **建议补充**："+'；'.join(pts[:4])+"\n- **参考书覆盖深度**：结构索引，不搬运原文"
        sug.append(block)
        items.append({'file':p.name,'chapter':ch,'points':len(pts),'target':'suggestions.md','chapter_freeze':True})
        done[str(p)]={'processed_at':datetime.now(TZ).isoformat(),'chapter':ch,'points':len(pts)}
    if not args.dry_run:
        if sug: append(SUG,'\n\n'.join(sug))
        if gaps: append(GAPS,'\n\n'.join(gaps))
        state.update({'cursor':i,'last_scan_date':today,'total_knowledge_points':state.get('total_knowledge_points',0)+kp,'total_suggestions':state.get('total_suggestions',0)+len(sug),'total_gaps':state.get('total_gaps',0)+len(gaps)})
        jsave(state_path,state)
    return {'mode':'clippings-reference-scan','status':'ok','dry_run':args.dry_run,'scanned':len(batch),'knowledge_points':kp,'suggestions':len(sug),'gaps':len(gaps),'progress':f"{min(i,len(files))}/{len(files)}",'items':items}

def extract_meta(text:str, key:str):
    m=re.search(rf'(?mi)^\s*{re.escape(key)}\s*[:：]\s*["\']?([^"\'\n]+)', text)
    return m.group(1).strip() if m else ''

def load_queue():
    q=jload(QUEUE, [])
    return q if isinstance(q,list) else q.get('pending',[])

def save_queue(q): jsave(QUEUE,q)

def save_freshness_log(summary):
    """Preserve the historical freshness log instead of overwriting it with a tiny latest-run object."""
    path = META/'freshness-log.json'
    old = jload(path, {})
    if not isinstance(old, dict):
        old = {'legacy_value': old}
    runs = old.get('runs')
    if not isinstance(runs, list):
        runs = []
    pending_freshness = sum(
        1 for item in load_queue()
        if isinstance(item, dict)
        and item.get('section') == 'freshness'
        and item.get('status', 'pending') == 'pending'
    )
    summary = dict(summary)
    summary['queued'] = pending_freshness
    runs.append(summary)
    old.update({
        'last_run_at': summary.get('last_run_at'),
        'last_check': summary.get('last_run_at'),
        'scanned': summary.get('scanned'),
        'risks': summary.get('risks', []),
        'findings_added': summary.get('findings_added'),
        'legacy_queue_migrated': summary.get('legacy_queue_migrated'),
        'queued': pending_freshness,
        'runs': runs[-30:],
    })
    jsave(path, old)

def strip_review_noise(text: str) -> str:
    """Return body assertions only: no YAML, code blocks, or review-note sections."""
    text = re.sub(r'^---\n.*?\n---\n?', '', text, flags=re.S)
    text = re.sub(r'```.*?```', '', text, flags=re.S)
    # Drop common historical review/audit sections that mention forbidden terms as instructions.
    text = re.split(r'(?m)^##\s*(Review|审计|复核|review_notes|质量|风险)', text, maxsplit=1)[0]
    return text


HIGH_VERSION = r'(?:Android\s*(?:1[89]|[2-9][0-9])|API(?:\s+level|[_\s]*LEVEL)?[_\s]*(?:3[8-9]|[4-9][0-9])|(?:Build\.)?VERSION_CODES\.[A-Z0-9_]*(?:3[8-9]|[4-9][0-9])|targetSdk(?:Version)?\s*[=:]?\s*(?:3[8-9]|[4-9][0-9])|SDK_INT\s*(?:>=|>|==)\s*(?:3[8-9]|[4-9][0-9]))'


def is_scope_exclusion(sentence: str) -> bool:
    patterns = [
        rf'(?:本文|本章|本节|正文|这里|本书|结论).{{0,120}}(?:不讨论|不涉及|不纳入|不采用|不依赖|不适用|不外推).{{0,48}}{HIGH_VERSION}',
        rf'(?:本文|本章|本节|正文|本书)?.{{0,12}}不(?:要)?把.{{0,60}}外推到.{{0,12}}{HIGH_VERSION}',
        rf'(?:不要|不得|不能|不应|不可).{{0,60}}(?:外推|纳入|采用|依赖|写入|作为结论).{{0,24}}{HIGH_VERSION}',
        rf'{HIGH_VERSION}.{{0,24}}(?:不进入|不纳入|不属于|超出).{{0,24}}(?:本文|本章|正文|本书|结论|范围|基线)',
        rf'(?:不|未)(?:把|将)?.{{0,12}}{HIGH_VERSION}.{{0,80}}(?:外推|写成|作为|纳入|进入).{{0,24}}(?:正文|结论|范围|基线)',
        rf'{HIGH_VERSION}.{{0,80}}(?:不|未)(?:应|会|能|可)?(?:被)?(?:外推|写成|作为|纳入|进入).{{0,24}}(?:正文|结论|范围|基线)',
    ]
    return any(re.search(pattern, sentence, re.I) for pattern in patterns)


def freshness_key(target_path: str, rule_id: str, evidence: str) -> str:
    return json.dumps({'target_path': target_path, 'rule_id': rule_id, 'evidence': clean(evidence).lower()}, ensure_ascii=False, sort_keys=True)


def finding_id(target_path: str, rule_id: str, evidence: str) -> str:
    digest=hashlib.sha256(freshness_key(target_path,rule_id,evidence).encode('utf-8')).hexdigest()[:16]
    return f'AIW-FRESH-{digest}'


def load_findings():
    data=jload(FINDINGS, {'schema_version':1,'findings':[]})
    if not isinstance(data,dict): data={'schema_version':1,'findings':[]}
    if not isinstance(data.get('findings'),list): data['findings']=[]
    return data


def migrate_legacy_freshness_queue(q, now):
    migrated=0
    for item in q:
        if not isinstance(item,dict) or item.get('section')!='freshness' or item.get('status','pending')!='pending':
            continue
        item['status']='superseded'
        item['superseded_at']=now.isoformat()
        item['superseded_reason']='freshness risks now use metadata/review-findings.json and rework lane'
        migrated+=1
    return migrated


def run_freshness(args):
    now=datetime.now(TZ); risks=[]; scanned=0
    files=sorted(iter_canonical_chapters())
    cursor_path=META/'freshness-cursor.json'
    cursor=jload(cursor_path, {'offset':0,'total':len(files),'coverage':{}})
    start=int(cursor.get('offset',0)) % max(1,len(files)) if files else 0
    batch=[]
    for n in range(min(args.scan_limit, len(files))):
        batch.append(files[(start+n) % len(files)])
    for p in batch:
        txt=p.read_text(encoding='utf-8', errors='ignore')
        body=strip_review_noise(txt)
        rel=str(p.relative_to(AIW))
        scanned+=1
        for sentence in affirmative_higher_android_mentions(body):
            risks.append({'path':str(p),'target_path':rel,'severity':'high','rule_id':'above-android17-affirmative-claim','evidence':sentence,'reason':'affirmative higher-than-Android-17 out-of-scope claim','action':'标注超出 AIW 范围或移除正文结论'})
        lv=extract_meta(txt,'last_source_verified_at') or extract_meta(txt,'last_verified') or extract_meta(txt,'verified')
        if lv:
            try:
                d=datetime.fromisoformat(lv.split()[0].replace('/','-'))
                if (now.replace(tzinfo=None)-d).days>90:
                    risks.append({'path':str(p),'target_path':rel,'severity':'medium','rule_id':'stale-source-verification','evidence':lv,'reason':f'last source verification {lv} older than 90 days','action':'重新核验至 Android 17'})
            except Exception: pass
    q=load_queue(); findings=load_findings(); added=[]
    existing_ids={str(x.get('id')) for x in findings.get('findings',[]) if isinstance(x,dict) and x.get('id')}
    for r in risks[:20]:
        fid=finding_id(r['target_path'],r['rule_id'],r['evidence'])
        item={'chapter':r['target_path'],'created_at':now.isoformat(),'created_by':'hermes-aiw-weekly-source-audit','created_run_id':f'freshness-{args.date}','details':r['reason']+'\nEvidence: '+r['evidence'],'id':fid,'log_path':str(REPORT_ROOT/f'{args.date}-时效性巡检.md'),'severity':'P1' if r['severity']=='high' else 'P2','source_paths':[r['target_path']],'status':'open','summary':r['reason'],'type':r['rule_id'],'updated_at':now.isoformat()}
        if fid not in existing_ids:
            added.append(item); existing_ids.add(fid)
    migrated=0 if args.dry_run else migrate_legacy_freshness_queue(q,now)
    report=f"# 时效性巡检 · {args.date}\n\n- scanned: {scanned}\n- cursor: {start}->{(start+scanned)%max(1,len(files)) if files else 0}/{len(files)}\n- risks: {len(risks)}\n- findings_added: {0 if args.dry_run else len(added)}\n- legacy_queue_migrated: {migrated}\n\n"+'\n'.join([f"- {x['severity']} {Path(x['path']).name}: {x['reason']} — {x.get('evidence','')[:120]}" for x in risks[:20]])
    report_path=REPORT_ROOT/f'{args.date}-时效性巡检.md'
    if not args.dry_run:
        if added:
            findings['findings'].extend(added); jsave(FINDINGS,findings)
        if migrated:
            save_queue(q)
        report_path.parent.mkdir(parents=True, exist_ok=True); report_path.write_text(report,encoding='utf-8')
        next_offset=(start+scanned)%max(1,len(files)) if files else 0
        coverage=cursor.get('coverage',{}) if isinstance(cursor.get('coverage'),dict) else {}
        for p in batch:
            coverage[str(p.relative_to(AIW))]=now.isoformat()
        jsave(cursor_path, {'schema_version':1,'offset':next_offset,'total':len(files),'updated_at':now.isoformat(),'coverage':coverage})
        save_freshness_log({'last_run_at':now.isoformat(),'scanned':scanned,'cursor_start':start,'cursor_next':next_offset,'risks':risks[:200],'findings_added':len(added),'legacy_queue_migrated':migrated})
    return {'mode':'freshness-check','status':'ok','dry_run':args.dry_run,'scanned':scanned,'cursor_start':start,'risks':len(risks),'findings_added':0 if args.dry_run else len(added),'legacy_queue_migrated':migrated,'queued':0,'report_path':str(report_path),'sample':risks[:5]}

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--mode',choices=['clippings-reference-scan','freshness-check'],required=True); ap.add_argument('--date',default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run',action='store_true'); ap.add_argument('--max-files',type=int,default=4); ap.add_argument('--scan-limit',type=int,default=80)
    args=ap.parse_args(); STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    if not AIW.exists(): raise SystemExit('missing AIW')
    payload=run_clippings(args) if args.mode=='clippings-reference-scan' else run_freshness(args)
    payload.update({'schema_version':1,'profile':'aiw-weekly-source-audit','date':args.date,'generated_at':datetime.now(TZ).isoformat()})
    od=STATE/args.mode; od.mkdir(parents=True,exist_ok=True); os.chmod(od,0o700)
    out=od/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    changed = payload.get('findings_added', payload.get('queued', payload.get('gaps', payload.get('suggestions', 0))))
    obs = payload.get('report_path') or str(REPORT_ROOT)
    print(f"# AIW Weekly Source Audit · {args.date}\n- status: {payload['status']}\n- mode: {args.mode}\n- 修改内容: {'未修改正文，仅生成巡检/参考资料候选' if not changed else f'新增/更新 {changed} 条候选或风险项'}\n- 影响范围: scanned={payload.get('scanned')}, risks={payload.get('risks','n/a')}, progress={payload.get('progress','n/a')}\n- Obsidian: {obs}\n- Evidence: {out}\n## 详情\n```json\n{json.dumps({k:payload.get(k) for k in ['items','sample'] if k in payload}, ensure_ascii=False, indent=2)[:1800]}\n```")
    return 0 if payload['status']=='ok' else 3
if __name__=='__main__': raise SystemExit(main())
