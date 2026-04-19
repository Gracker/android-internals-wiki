import os
import re

log_dir = "logs/external-review"
todo_file = "logs/external-review/TODO-part2-performance.md"

with open(todo_file, "r") as f:
    todo_lines = f.readlines()

filepaths = []
for line in todo_lines:
    if line.startswith("- ["):
        filepaths.append(line[6:].strip())

def get_chapter_number(filepath):
    m = re.search(r'ch(\d+)[^/]*/(\d+)-.*\.md', filepath)
    if m:
        return f"{int(m.group(1))}.{int(m.group(2))}"
    m2 = re.search(r'ch(\d+)[^/]*/README\.md', filepath)
    if m2:
        return f"{int(m2.group(1))}.0"
    return os.path.splitext(os.path.basename(filepath))[0]

# create a mapping from basename to chapter number
name_to_chapter = {}
for path in filepaths:
    basename = os.path.splitext(os.path.basename(path))[0]
    name_to_chapter[basename] = get_chapter_number(path)

files = [f for f in os.listdir(log_dir) if f.endswith("-external-review.md") and not re.match(r'\d{4}-\d{2}-\d{2}-\d{2}-\d+\.\d+-external-review\.md', f)]

for f in files:
    m = re.match(r'(\d{4}-\d{2}-\d{2}-\d{2})-(.*)-external-review\.md', f)
    if m:
        timestamp = m.group(1)
        name_part = m.group(2)
        if name_part in name_to_chapter:
            ch_str = name_to_chapter[name_part]
            new_name = f"{timestamp}-{ch_str}-external-review.md"
            old_path = os.path.join(log_dir, f)
            new_path = os.path.join(log_dir, new_name)
            os.rename(old_path, new_path)
            print(f"Renamed: {f} -> {new_name}")
        else:
            print(f"Warning: could not map {name_part}")
