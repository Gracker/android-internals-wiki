import os
import re

dir_path = 'src/part3-tools/ch19-apm'

# Lines to remove
lines_to_remove = [
    'task6_state: reviewed',
    'task6_result: pass-light-edit',
    'reviewed_by: openclaw-task6',
    'reviewed_date: "2026-04-24"',
    'task9_state: reviewed',
    'task9_result: pass-tech-review',
    'task9_reviewed_by: "openclaw-task9"',
    'task9_reviewed_date: "2026-04-24"',
    'task2b_state: fixed',
    'task2b_result: fixed'
]

new_state_lines = """pipeline_stage: task6_pending
task6_state: pending
task9_state: pending
task2b_state: pending"""

for filename in os.listdir(dir_path):
    if not filename.endswith('.md') or filename == 'README.md':
        continue
    filepath = os.path.join(dir_path, filename)
    with open(filepath, 'r') as f:
        lines = f.readlines()
        
    in_yaml = False
    new_lines = []
    yaml_end_index = -1
    
    for i, line in enumerate(lines):
        if line.strip() == '---':
            if i == 0:
                in_yaml = True
            elif in_yaml:
                in_yaml = False
                yaml_end_index = len(new_lines)
        
        if in_yaml:
            should_remove = False
            for r in lines_to_remove:
                if line.startswith(r) or line.startswith(r.split(':')[0] + ':'):
                    should_remove = True
                    break
            if line.startswith('pipeline_stage:'):
                should_remove = True
            
            if not should_remove:
                new_lines.append(line)
        else:
            new_lines.append(line)
            
    if yaml_end_index != -1:
        # Insert the new state lines before the end of yaml
        new_lines.insert(yaml_end_index, new_state_lines + '\n')
        
        with open(filepath, 'w') as f:
            f.writelines(new_lines)
        print(f"Updated {filename}")

