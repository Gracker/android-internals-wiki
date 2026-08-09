#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
from aiw_pipeline_common import MIN_ROUTE_CONFIDENCE
TZ=ZoneInfo('Asia/Shanghai')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
AIW=OB/'Android-Internal-Wiki'
DAILY=AIW/'intake/daily-info'
STATE=Path('/Users/gracker/.hermes/state/aiw-daily-intake')
WORK=Path('/Users/gracker/.openclaw/workspace')
TECH=WORK/'tasks/tech-article-aiw-intake/scan_tech_articles_to_aiw.py'
INCR=WORK/'aiw_incremental_scan.py'
KEYWORDS=('android','aosp','androidx','jetpack','perfetto','surfaceflinger','choreographer','binder','zygote','ams','wms','lmkd','art runtime','hwui','skia','camera2','camerax','media3','vulkan','opengl','hal','anr','jank','startup','启动','渲染','内存','功耗','卡顿','流畅','调度','源码','系统服务','输入','音频','视频','定位','权限')
EXCLUDE_TOPICS=('agent workflow','token budget','openrouter','grok','claude code','prompt','workflow budget','ai agent rules','llm','大模型','智能体','知识编译')
STOPWORDS=set('android performance perf source code article deepresearch 技术文章 掘金 每日 论文 精读 源码 性能 优化 分析 实战 机制 架构 系统 应用 开发 研究 资料 官方 users gracker library mobile documents obsidian icloud status completed report review quality intake feed run sort type limit path source target markdown https http juejin post cn com www 原文链接 发布时间'.split())
AGGREGATE_TITLE_PATTERNS=(r'juejin android intake', r'\[掘金android\]\s*\d{4}-\d{2}-\d{2}', r'quality review', r'phase 0', r'status$', r'四层质检报告', r'prompt ·', r'style provenance')

def red(t:str)->str: return t[-3500:]
def run(cmd:list[str], timeout:int=600): return subprocess.run(cmd,cwd=str(WORK),capture_output=True,text=True,timeout=timeout,check=False)
def file_id(p:Path)->str: return hashlib.sha256(str(p).encode()).hexdigest()[:16]
def text(p:Path)->str:
    try: return p.read_text(encoding='utf-8', errors='ignore')
    except Exception: return ''
def is_aggregate_title(title: str) -> bool:
    low = (title or '').lower().strip()
    return any(re.search(pat, low) for pat in AGGREGATE_TITLE_PATTERNS)

def related(s:str)->bool:
    low=s.lower()
    if any(k in low for k in EXCLUDE_TOPICS) and not any(k in low for k in ['android','aosp','androidx','perfetto','surfaceflinger','binder','lmkd','camerax','media3']):
        return False
    return any(k.lower() in low for k in KEYWORDS)

def terms(s:str)->list[str]:
    raw=re.findall(r'[A-Za-z][A-Za-z0-9+.#-]{2,}|[\u4e00-\u9fff]{2,}', s or '')
    out=[]
    for x in raw:
        t=x.lower().strip('-_')
        if len(t)<3 or t in STOPWORDS: continue
        if t.startswith('202'): continue
        out.append(t)
    return list(dict.fromkeys(out))[:24]

def frontmatter(md:str)->dict:
    m=re.match(r'^---\n(.*?)\n---', md, re.S)
    fm={}
    if not m: return fm
    for line in m.group(1).splitlines():
        if ':' in line and not line.lstrip().startswith(('#','-')):
            k,v=line.split(':',1); fm[k.strip()]=v.strip().strip('\"\'')
    return fm

def route_existing_target(title:str, summary:str, chapter_hint:str='')->dict:
    # Conservative router: only routes to an existing chapter when at least two
    # distinctive title/material terms overlap. Low-confidence material remains
    # indexed-only and cannot be consumed by body-apply.
    src_terms=terms(title+' '+summary)
    if not src_terms: return {}
    best=[]
    for p in (AIW/'src').rglob('*.md'):
        if p.name in ('SUMMARY.md','README.md'): continue
        txt=text(p)[:9000]
        fm=frontmatter(txt)
        hay=' '.join([str(p), json.dumps(fm,ensure_ascii=False), txt[:3000]]).lower()
        overlap=[t for t in src_terms if t in hay]
        distinct=[t for t in overlap if t not in {'android','androidx','jetpack','compose','performance'}]
        if len(distinct)<2: continue
        score=len(distinct)*3 + min(4, len(overlap))
        ch=str(fm.get('chapter',''))
        if chapter_hint and ch.startswith(chapter_hint.replace('ch','').lstrip('0')+'.'):
            score+=2
        if '参考资料' in str(p): score-=5
        best.append((score,str(p.relative_to(AIW)),distinct[:8]))
    best.sort(reverse=True,key=lambda x:x[0])
    if best and best[0][0] >= MIN_ROUTE_CONFIDENCE:
        return {'target_path':best[0][1], 'route_confidence':best[0][0], 'route_terms':best[0][2], 'route_status':'existing-chapter-routed'}
    return {'route_status':'unrouted-existing-chapter-needed'}
def chapter(s:str)->str:
    low=s.lower()
    for pat,ch in [('surfaceflinger|vsync|choreographer|渲染','ch02'),('inputdispatcher|触摸|输入','ch03'),('lmk|zram|memcg|内存','ch04'),('cpu|eas|调度|freq','ch05'),('f2fs|ext4|i/o|存储','ch06'),('jank|卡顿|fps|流畅','ch07'),('启动|startup','ch08'),('anr|watchdog','ch09'),('battery|doze|功耗','ch11'),('perfetto|trace','ch13')]:
        if any(x in low for x in pat.split('|')): return ch
    return 'ch16'
def append_entries(path:Path, entries:list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a', encoding='utf-8') as f:
        if path.exists() and path.stat().st_size: f.write('\n')
        f.write('\n\n'.join(entries)+'\n')
def deepresearch(args)->dict:
    roots=[OB/'DeepResearch', OB/'deep research']
    found=[]; since=datetime.now(TZ)-timedelta(days=args.since_days)
    for root in roots:
        if not root.exists(): continue
        for p in root.rglob('*.md'):
            if p.stat().st_mtime >= since.timestamp(): found.append(p)
    stfile=STATE/'deepresearch-state.json'; state=json.loads(stfile.read_text()) if stfile.exists() else {'seen':{}}
    entries=[]; items=[]
    for p in sorted(found, key=lambda x:x.stat().st_mtime, reverse=True)[:args.max_files or 50]:
        h=hashlib.sha256(text(p).encode()).hexdigest(); key=str(p)
        if state['seen'].get(key)==h: continue
        content=text(p)
        if not related(content+p.name):
            state['seen'][key]=h; continue
        title=next((l[2:].strip() for l in content.splitlines() if l.startswith('# ')), p.stem)
        if is_aggregate_title(title) or is_aggregate_title(p.stem):
            state['seen'][key]=h
            continue
        summary=re.sub(r'\s+',' ',content.replace('\n',' '))[:220]
        ch=chapter(content+' '+p.name)
        entries.append(f"## [DeepResearch] {title}\n- **来源**：AIW DeepResearch 材料注入\n- **时间**：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')}\n- **链接**：{p}\n- **摘要**：{summary}\n- **推荐映射章节**：{ch}\n- **内容类型**：DeepResearch 素材\n- **相关标签**：#Android #系统开发")
        items.append({'title':title,'path':str(p),'chapter':ch})
        state['seen'][key]=h
    daily=DAILY/f"{args.date}.md"
    if entries and not args.dry_run:
        append_entries(daily, entries); stfile.parent.mkdir(parents=True, exist_ok=True); stfile.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    return {'mode':'deepresearch','status':'ok','found':len(found),'appended':0 if args.dry_run else len(entries),'candidates':len(entries),'dry_run':args.dry_run,'daily_info':str(daily),'items':items[:10]}
def tech(args)->dict:
    cmd=[sys.executable,str(TECH),'--date',args.date,'--max-files',str(args.max_files)]
    if args.dry_run: cmd.append('--dry-run')
    r=run(cmd)
    try: js=json.loads(r.stdout[r.stdout.find('{'):])
    except Exception: js={}
    return {'mode':'tech-articles','status':'ok' if r.returncode==0 else 'error','returncode':r.returncode,'dry_run':args.dry_run,'daily_info':str(DAILY/f"{args.date}.md"),'report':js,'tail':red(r.stdout+r.stderr)}
def incr(args)->dict:
    if args.dry_run:
        cmd=['find',str(OB),'-name','*.md','-mtime','-1','-not','-path','*/Android-Internal-Wiki/*','-not','-path','*/.trash/*','-not','-path','*/.obsidian/*']
        r=run(cmd,120); files=[x for x in r.stdout.splitlines() if x]
        return {'mode':'incremental','status':'ok' if r.returncode==0 else 'error','dry_run':True,'found':len(files),'sample':files[:10],'daily_info':str(DAILY/f"{args.date}.md")}
    r=run([sys.executable,str(INCR)],600)
    return {'mode':'incremental','status':'ok' if r.returncode==0 else 'error','returncode':r.returncode,'dry_run':False,'daily_info':str(DAILY/f"{args.date}.md"),'tail':red(r.stdout+r.stderr)}

def parse_daily_entries(path:Path)->list[dict]:
    if not path.exists(): return []
    raw=path.read_text(encoding='utf-8', errors='ignore')
    blocks=re.split(r'(?m)^##\s+', raw)
    out=[]
    for b in blocks[1:]:
        title=b.splitlines()[0].strip()
        link=''; summary=''; source=''
        for line in b.splitlines()[1:]:
            if '链接' in line or '来源' in line:
                m=re.search(r'(/Users/[^\n]+|https?://\S+)', line)
                if m and not link: link=m.group(1).strip()
            if '摘要' in line: summary=line.split('：',1)[-1].strip()
            if '来源' in line and not source: source=line.split('：',1)[-1].strip()
        out.append({'title':title,'link':link,'summary':summary,'source':source,'raw':b[:800]})
    return out
def score_entry(e:dict)->dict:
    if is_aggregate_title(e.get('title','')):
        return {'total':0,'reason':'aggregate/status/report artifact, not source material'}
    s=(e.get('title','')+' '+e.get('summary','')+' '+e.get('raw','')).lower()
    if re.search(r'android\s*18|api\s*38|targetsdk\s*3[89]', s):
        return {'total':0,'reason':'out-of-scope higher-than-Android-17'}
    if not related(s):
        return {'total':0,'reason':'not AIW/Android-internals related'}
    rel=5
    depth=5 if any(k in s for k in ['aosp','source','源码','benchmark','perfetto','trace','commit','androidx','developer.android']) else 3
    recency=4
    trust=5 if any(k in s for k in ['android.googlesource','developer.android','aosp','官方','commit','source','androidx']) else 3
    return {'relevance':rel,'depth':depth,'recency':recency,'trust':trust,'total':rel+depth+recency+trust,'reason':'ok'}
def load_json(path:Path, default):
    if not path.exists(): return default
    try: return json.loads(path.read_text(encoding='utf-8'))
    except Exception: return default
def save_json(path:Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp')
    tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    tmp.replace(path)
def classify(args)->dict:
    daily=DAILY/f"{args.date}.md"
    entries=parse_daily_entries(daily)
    qpath=AIW/'metadata/queue.json'; spath=AIW/'metadata/source-index.json'
    queue=load_json(qpath, [])
    sidx=load_json(spath, {'files':[]})
    migrated_routes=0
    for item in sidx.get('files',[]) if isinstance(sidx,dict) else []:
        if not isinstance(item,dict) or item.get('route_status')!='existing-chapter-routed': continue
        try: confidence=int(item.get('route_confidence'))
        except (TypeError,ValueError): continue
        if confidence < MIN_ROUTE_CONFIDENCE and item.get('action') not in {'body-applied','applied'}:
            item['route_status']='provisional-low-confidence'
            item['route_migration_reason']=f'route_confidence {confidence} below shared threshold {MIN_ROUTE_CONFIDENCE}'
            migrated_routes+=1
    existing={x.get('path') for x in sidx.get('files',[]) if isinstance(x,dict)}
    passed=[]; queued=[]; rejected=[]
    now=datetime.now(TZ).isoformat()
    for e in entries:
        link=e.get('link') or e.get('title')
        if not link or link in existing:
            continue
        sc=score_entry(e)
        if sc['total'] < 12:
            rejected.append({'title':e.get('title'), 'score':sc}); continue
        ch=chapter(e.get('title','')+' '+e.get('summary',''))
        passed.append({'title':e.get('title'), 'link':link, 'chapter':ch, 'score':sc['total']})
        # Chapter creation is frozen. Route only to a high-confidence existing chapter;
        # otherwise keep indexed-only but non-actionable for body-apply.
        route=route_existing_target(e.get('title',''), e.get('summary','')+' '+e.get('raw',''), ch)
        item={'path':link,'title':e.get('title'),'summary':e.get('summary'),'chapter':ch,'processed_at':now,'action':'indexed-only-chapter-freeze','score':sc['total']}
        item.update(route)
        sidx.setdefault('files',[]).append(item)
        existing.add(link)
    if passed and not args.dry_run:
        save_json(spath, sidx)
        raw=daily.read_text(encoding='utf-8') if daily.exists() else ''
        if f'已消费：{args.date}' not in raw:
            daily.write_text(f"> ✅ 已消费：{datetime.now(TZ).strftime('%Y-%m-%d %H:%M')} by hermes-task8\n\n"+raw, encoding='utf-8')
    if migrated_routes and not args.dry_run and not passed:
        save_json(spath,sidx)
    return {'mode':'classify','status':'ok','dry_run':args.dry_run,'daily_info':str(daily),'entries':len(entries),'passed':len(passed),'queued':0 if args.dry_run else len(passed),'rejected':len(rejected),'migrated_low_confidence_routes':migrated_routes,'passed_items':passed[:10]}

def main()->int:
    ap=argparse.ArgumentParser(); ap.add_argument('--mode', choices=['deepresearch','tech-articles','incremental','classify'], required=True); ap.add_argument('--date', default=datetime.now(TZ).date().isoformat()); ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--since-days', type=float, default=7); ap.add_argument('--max-files', type=int, default=30)
    args=ap.parse_args(); STATE.mkdir(parents=True, exist_ok=True); os.chmod(STATE,0o700)
    for p in [AIW,DAILY,WORK]:
        if not p.exists(): raise SystemExit(f'missing {p}')
    payload={'deepresearch':deepresearch,'tech-articles':tech,'incremental':incr,'classify':classify}[args.mode](args)
    payload.update({'schema_version':1,'profile':'aiw-daily-intake','generated_at':datetime.now(TZ).isoformat(),'date':args.date})
    outdir=STATE/args.mode; outdir.mkdir(parents=True, exist_ok=True); os.chmod(outdir,0o700)
    out=outdir/(args.date+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2,sort_keys=True)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    changed = payload.get('appended', payload.get('queued', payload.get('report',{}).get('appended','n/a')))
    impact = []
    for key in ['found','candidates','entries','passed','rejected','migrated_low_confidence_routes']:
        if key in payload: impact.append(f"{key}={payload.get(key)}")
    print(f"# AIW Daily Intake · {args.date}\n- status: {payload.get('status')}\n- mode: {args.mode}\n- 修改内容: {'未修改正文，仅生成/更新素材索引或队列' if changed in [0,'0','n/a',None] else f'新增/更新 {changed} 条素材或队列项'}\n- 影响范围: {', '.join(impact) if impact else 'daily-info / metadata queue/source-index'}\n- Obsidian: {payload.get('daily_info')}\n- Evidence: {out}\n## 详情\n```json\n{json.dumps({k:payload.get(k) for k in ['items','passed_items','sample','report','migrated_low_confidence_routes'] if k in payload}, ensure_ascii=False, indent=2)[:1800]}\n```")
    return 0 if payload.get('status')=='ok' else 3
if __name__=='__main__': raise SystemExit(main())
