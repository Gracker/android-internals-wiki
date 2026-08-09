#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations
import json, os, subprocess, sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
TZ=ZoneInfo('Asia/Shanghai')
BASE=Path('/Users/gracker/.hermes/scripts/aiw-queue-worker.py')
STATE=Path('/Users/gracker/.hermes/state/aiw-queue-worker-dispatcher')
OB=Path('/Users/gracker/Library/Mobile Documents/iCloud~md~obsidian/Documents/Obsidian')
REPORT_DIR=OB/'OpenClaw定时任务/AIW自动化流水线'
LANES=[
  ('task2b-main', lambda h: h%2==0),
  ('task2b-lite', lambda h: h%2==1),
  ('source-research', lambda h: h in {2,5,8,11,14,17,20,23}),
  ('task2a', lambda h: h in {8,14,20}),
]

def run_lane(mode, day):
    cmd=[sys.executable, str(BASE), '--mode', mode, '--date', day]
    r=subprocess.run(cmd,capture_output=True,text=True,timeout=120)
    return {'mode':mode,'returncode':r.returncode,'stdout':r.stdout[-2000:],'stderr':r.stderr[-1000:]}

def main():
    now=datetime.now(TZ); day=now.date().isoformat(); hour=now.hour
    STATE.mkdir(parents=True,exist_ok=True); os.chmod(STATE,0o700)
    due=[m for m,pred in LANES if pred(hour)]
    if not due:
        return 0
    results=[run_lane(m,day) for m in due]
    status='ok' if all(x['returncode']==0 for x in results) else 'partial_failure'
    payload={'schema_version':1,'profile':'aiw-queue-worker-dispatcher','date':day,'hour':hour,'status':status,'due_lanes':due,'results':results,'generated_at':now.isoformat()}
    ev=STATE/f'{day}-{hour:02d}.json'; ev.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); os.chmod(ev,0o600)
    REPORT_DIR.mkdir(parents=True,exist_ok=True)
    report=REPORT_DIR/f'{day}-aiw-queue-worker-dispatcher.md'
    text=f"# AIW Queue Worker Dispatcher · {day} {hour:02d}:00\n\n- status: {status}\n- due_lanes: {', '.join(due)}\n- evidence: `{ev}`\n\n"
    for r in results:
        text += f"## {r['mode']}\n\n- returncode: {r['returncode']}\n\n```text\n{r['stdout'] or r['stderr']}\n```\n\n"
    report.write_text(text,encoding='utf-8')
    changed = '未修改正文，仅运行 queue worker 候选/门禁 lane'
    impact = '; '.join([f"{r['mode']} rc={r['returncode']}" for r in results])
    print(f"# AIW Queue Worker Dispatcher · {day}\n- status: {status}\n- 修改内容: {changed}\n- 影响范围: due_lanes={', '.join(due)}; {impact}\n- Obsidian: {report}\n- Evidence: {ev}\n## 详情\n" + '\n'.join([f"### {r['mode']}\n```text\n{(r['stdout'] or r['stderr'])[:1200]}\n```" for r in results]))
    return 0 if status=='ok' else 2
if __name__=='__main__': raise SystemExit(main())
