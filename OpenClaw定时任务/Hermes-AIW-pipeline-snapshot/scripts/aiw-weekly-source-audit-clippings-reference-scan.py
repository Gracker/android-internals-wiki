#!/usr/bin/env python3
import subprocess, sys
cmd=[sys.executable,'/Users/gracker/.hermes/scripts/aiw-weekly-source-audit.py','--mode','clippings-reference-scan']
raise SystemExit(subprocess.run(cmd).returncode)
