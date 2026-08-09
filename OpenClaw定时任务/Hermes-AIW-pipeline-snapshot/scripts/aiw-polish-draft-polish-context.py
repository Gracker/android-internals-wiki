#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from pathlib import Path
import runpy, sys
sys.argv = [sys.argv[0], '--mode', 'draft-polish', *sys.argv[1:]]
runpy.run_path(str(Path(__file__).with_name('aiw-polish-context.py')), run_name='__main__')
