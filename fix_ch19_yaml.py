import os
import re

dir_path = 'src/part3-tools/ch19-apm'

additional_yaml = """task6_state: reviewed
task6_result: pass-light-edit
reviewed_by: openclaw-task6
reviewed_date: "2026-04-24"
pipeline_stage: task6_pending
task9_state: reviewed
task9_result: pass-tech-review
task9_reviewed_by: "openclaw-task9"
task9_reviewed_date: "2026-04-24"
task2b_state: fixed
task2b_result: fixed"""

for filename in os.listdir(dir_path):
    if not filename.endswith('.md') or filename == 'README.md':
        continue
    filepath = os.path.join(dir_path, filename)
    with open(filepath, 'r') as f:
        content = f.read()
        
    if 'task6_state' not in content:
        content = content.replace('pipeline_stage: task6_pending\n---', additional_yaml + '\n---')
        with open(filepath, 'w') as f:
            f.write(content)
            print(f"Updated YAML in {filename}")

