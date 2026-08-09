#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-review-finalize.py','--mode','task2b-verifier']
raise SystemExit(subprocess.run(cmd).returncode)
