#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, os, re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Shanghai')
AW=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/AndroidWeekly')
AIW=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian/Android-Internal-Wiki')
STATE=Path('/Users/gracker/.hermes/state/aiw-androidweekly')
PROG=AIW/'metadata/weekly-scan-progress.json'
INDEX=AIW/'metadata/source-index.json'
REPORT_DIR=AIW/'intake/androidweekly'
PASS='android kotlin java jetpack compose gradle aosp ndk jni performance memory render startup ui animation network database security thread coroutine handler binder zygote surfaceflinger choreographer vsync perfetto systrace trace gpu vulkan skia flutter linux kernel process compile build maven dex apk aab proguard r8 shrink 性能 内存 渲染 启动 动画 网络 数据库 安全 线程 协程 内核 进程 编译 混淆'.split()
EXCL='iphone ipad apple swiftui figma sketch 产品 运营 增长 商业 招人 招聘 hr 求职 面经 薪资 生活 摄影旅行 健康 心理 读书 电影 音乐 vue angular node css html 非技术 灌水 杂谈'.split()

STOPWORDS=set('android kotlin java jetpack compose gradle performance source code article weekly issue users gracker library mobile documents obsidian status completed report review quality intake feed run sort type limit path source target markdown https http com www github medium blog'.split())

def text(path):
    try: return path.read_text(encoding='utf-8', errors='ignore')
    except Exception: return ''

def terms(s):
    raw=re.findall(r'[A-Za-z][A-Za-z0-9+.#-]{2,}|[\u4e00-\u9fff]{2,}', s or '')
    out=[]
    for x in raw:
        t=x.lower().strip('-_')
        if len(t)<3 or t in STOPWORDS: continue
        if t.startswith('202'): continue
        out.append(t)
    return list(dict.fromkeys(out))[:20]

def frontmatter(md):
    m=re.match(r'^---\n(.*?)\n---', md, re.S)
    fm={}
    if not m: return fm
    for line in m.group(1).splitlines():
        if ':' in line and not line.lstrip().startswith(('#','-')):
            k,v=line.split(':',1); fm[k.strip()]=v.strip().strip('\"\'')
    return fm

def route_existing_target(title, url=''):
    src_terms=terms(title+' '+url)
    if not src_terms: return {'route_status':'unrouted-existing-chapter-needed'}
    best=[]
    for p in (AIW/'src').rglob('*.md'):
        if p.name in ('SUMMARY.md','README.md'): continue
        txt=text(p)[:7000]
        fm=frontmatter(txt)
        hay=' '.join([p.stem, str(p), str(fm), txt[:2500]]).lower()
        overlap=[t for t in src_terms if t in hay]
        distinct=[t for t in overlap if t not in {'android','androidx','jetpack','compose','kotlin','java'}]
        if len(distinct)<2: continue
        score=len(distinct)*3 + min(4, len(overlap))
        if '参考资料' in str(p): score-=5
        best.append((score, str(p.relative_to(AIW)), distinct[:8]))
    best.sort(reverse=True,key=lambda x:x[0])
    if best and best[0][0] >= 25:
        return {'target_path':best[0][1], 'route_confidence':best[0][0], 'route_terms':best[0][2], 'route_status':'existing-chapter-routed'}
    return {'route_status':'unrouted-existing-chapter-needed'}

def files(): return sorted(AW.glob('*.md')) if AW.exists() else []
def load_progress(total):
    if PROG.exists():
        try:
            p=json.loads(PROG.read_text(encoding='utf-8'))
        except Exception: p={}
    else: p={}
    p.setdefault('current_issue',0); p.setdefault('total_issues',total); p.setdefault('completed_issues',[]); p.setdefault('indexed_links',0); p.setdefault('skipped_links',0)
    return p

def extract_tech(md):
    lines=md.splitlines(); on=False; buf=[]
    for l in lines:
        if l.startswith('##'):
            on=('技术' in l and '非技术' not in l)
            if '非技术' in l and on: on=False
            continue
        if on: buf.append(l)
    return '\n'.join(buf)

def title_date(md,path):
    m=re.search(r'title:\s*["\']?([^"\'\n]+)',md); title=m.group(1).strip() if m else path.stem
    d=re.search(r'date:\s*([0-9-]{10})',md); date=d.group(1) if d else ''
    im=re.search(r'#\s*(\d+)',title) or re.search(r'(\d+)',path.stem)
    issue='#'+im.group(1) if im else path.stem
    return title,date,issue

def prefilter(title,url):
    low=(title+' '+url).lower()
    if any(x in low for x in EXCL) and 'android' not in low: return False
    return any(x in low for x in PASS)

def score(title,url,date):
    low=(title+' '+url).lower(); relevance=5 if 'android' in low else 3
    depth=4 if any(x in low for x in ['aosp','source','源码','perfetto','binder','surfaceflinger','gradle','compose']) else 3
    timeliness=4
    ver=4 if re.search(r'(api|android|kotlin|gradle|\d+\.\d+|class|method)',low) else 3
    total=relevance+depth+timeliness+ver
    return total, {'relevance':relevance,'depth':depth,'timeliness':timeliness,'verifiability':ver}

def append_index(entries):
    if not entries: return
    try: data=json.loads(INDEX.read_text(encoding='utf-8'))
    except Exception: data={'files':[]}
    arr=data.setdefault('files',[])
    existing={x.get('source_url') for x in arr if isinstance(x,dict)}
    added=0
    for e in entries:
        if e['source_url'] not in existing:
            arr.append(e); existing.add(e['source_url']); added+=1
    INDEX.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return added

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--dry-run',action='store_true')
    args=ap.parse_args(); STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    fs=files()
    if not AW.exists():
        payload={'schema_version':1,'profile':'aiw-androidweekly','dry_run':args.dry_run,'status':'blocked','reason':'AndroidWeekly source directory missing','source_dir':str(AW),'generated_at':datetime.now(TZ).isoformat()}
        out=STATE/(datetime.now(TZ).date().isoformat()+('-dry' if args.dry_run else '')+'.json')
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(out,0o600)
        print(f"# AIW AndroidWeekly · {datetime.now(TZ).date().isoformat()}\n- status: blocked\n- reason: AndroidWeekly source directory missing\n- source_dir: {AW}\n- Evidence: {out}")
        return 2
    p=load_progress(len(fs)); idx=int(p.get('current_issue',0)); completed=set(p.get('completed_issues',[]))
    while idx < len(fs) and idx in completed: idx+=1
    if idx>=len(fs):
        REPORT_DIR.mkdir(parents=True,exist_ok=True)
        payload={'schema_version':1,'profile':'aiw-androidweekly','dry_run':args.dry_run,'status':'complete','total_issues':len(fs),'progress':p,'generated_at':datetime.now(TZ).isoformat()}
        out=STATE/(datetime.now(TZ).date().isoformat()+('-dry' if args.dry_run else '')+'.json')
        out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(out,0o600)
        report=REPORT_DIR/(datetime.now(TZ).date().isoformat()+'-androidweekly-complete.md')
        body=f'# AIW AndroidWeekly · {datetime.now(TZ).date().isoformat()}\n- status: complete\n- 修改内容: 未修改正文；全部期刊已扫描完成\n- 影响范围: total_issues={len(fs)}, completed={len(p.get("completed_issues",[]))}, indexed_links={p.get("indexed_links",0)}\n- Obsidian: {report}\n- Evidence: {out}'
        if not args.dry_run: report.write_text(body,encoding='utf-8')
        print(body)
        return 0
    f=fs[idx]; md=f.read_text(encoding='utf-8',errors='ignore'); title,date,issue=title_date(md,f); tech=extract_tech(md)
    links=re.findall(r'\[([^\]]{3,160})\]\((https?://[^)\s]+)\)',tech)
    filtered=[(t,u) for t,u in links if prefilter(t,u)]
    entries=[]; skipped=0
    for t,u in filtered:
        total,scores=score(t,u,date)
        if total>=10:
            route=route_existing_target(t,u)
            item={'title':t,'path':f'AndroidWeekly/{issue}/{t[:80]}','source_url':u,'weekly_issue':issue,'weekly_date':date,'score':total,'quality':'high' if total>=16 else 'medium','scores':scores,'mapped_chapters':[{'chapter':'AIW候选','confidence':'medium'}],'summary':'AndroidWeekly 技术链接，标题预过滤通过，待正文深读。','action':'indexed-only-chapter-freeze','scored_at':datetime.now(TZ).isoformat()}
            item.update(route)
            entries.append(item)
        else: skipped+=1
    added=0
    if not args.dry_run:
        added=append_index(entries) or 0
        p['current_issue']=idx+1; p['total_issues']=len(fs); p['completed_issues']=sorted(set(p.get('completed_issues',[]))|{idx}); p['indexed_links']=p.get('indexed_links',0)+added; p['skipped_links']=p.get('skipped_links',0)+skipped+(len(links)-len(filtered))
        PROG.parent.mkdir(parents=True,exist_ok=True); PROG.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    payload={'schema_version':1,'profile':'aiw-androidweekly','dry_run':args.dry_run,'file':str(f),'issue':issue,'links':len(links),'filtered':len(filtered),'indexed_candidates':len(entries),'added':added,'progress':p,'generated_at':datetime.now(TZ).isoformat()}
    out=STATE/(datetime.now(TZ).date().isoformat()+('-dry' if args.dry_run else '')+'.json'); out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(out,0o600)
    report=REPORT_DIR/(datetime.now(TZ).date().isoformat()+f'-androidweekly-{issue.strip("#")}.md')
    body='\n'.join([f'# AIW AndroidWeekly · {datetime.now(TZ).date().isoformat()}', f'- status: completed', f'- 修改内容: 未修改正文；纳入索引 {added if not args.dry_run else len(entries)} 个候选链接', f'- 影响范围: issue={issue}, extracted_links={len(links)}, filtered={len(filtered)}, skipped={skipped + len(links)-len(filtered)}', f'- Obsidian: {report}', f'- Evidence: {out}', '', '## 本轮索引文章']+[f'- [{issue}] {e["title"]}（{e["score"]}/20）→ AIW候选' for e in entries[:20]]+['', '## 累计进度', f'- 已完成期刊：{len(p.get("completed_issues",[]))}/{len(fs)}', f'- 已索引链接：{p.get("indexed_links",0)}', f'- 下次处理：{idx+2 if idx+1<len(fs) else "完成"}'])
    if not args.dry_run: report.write_text(body,encoding='utf-8')
    print(body[:3500])
    return 0
if __name__=='__main__': raise SystemExit(main())
