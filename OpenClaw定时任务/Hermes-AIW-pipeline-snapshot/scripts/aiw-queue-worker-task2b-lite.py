#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-queue-worker.py','--mode','task2b-lite']
raise SystemExit(subprocess.run(cmd).returncode)
