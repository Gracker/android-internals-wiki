#!/usr/bin/env python3
import subprocess, sys
cmd=[
    sys.executable,
    '/Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py',
    '--mode',
    'freshness-check',
    *sys.argv[1:],
]
raise SystemExit(subprocess.run(cmd).returncode)
