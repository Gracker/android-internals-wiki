#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-daily-intake.py','--mode','tech-articles']
raise SystemExit(subprocess.run(cmd).returncode)
