import os
import re

dir_path = 'src/part3-tools/ch19-apm'

for filename in os.listdir(dir_path):
    if not filename.endswith('.md') or filename == 'README.md':
        continue
    filepath = os.path.join(dir_path, filename)
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Update YAML
    if 'status: draft' in content:
        content = content.replace('status: draft', 'status: ready-for-review')
    if 'pipeline_stage: drafted' in content:
        content = content.replace('pipeline_stage: drafted', 'pipeline_stage: task6_pending')
        
    # Check if outline exists
    if '<!-- outline-start -->' not in content:
        # Extract H1
        h1_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if h1_match:
            h1 = h1_match.group(0)
            
            # Extract H2s
            h2s = re.findall(r'^##\s+(.+)$', content, re.MULTILINE)
            
            outline = "<!-- outline-start -->\n## 本节要点大纲\n\n### 锚点（必须覆盖）\n\n"
            for h2 in h2s:
                outline += f"- 🔹 {h2}\n"
            
            outline += """
### 扩展（可选深入）

- 🔸 待补充

### OpenClaw 加工指引

> **锚点**是最低覆盖要求，加工时必须逐条落实并标注验证结果。
> **扩展**视素材丰富程度选择性深入。
> 如果从 Obsidian 素材或 AOSP 源码中发现大纲未列出但与本节强相关的知识点，
> 可**就地插入**最相关的锚点之后，并用 `[自动发现]` 标注，方便后续 review。
> 锚点内容需 L1/L2 验证，扩展内容至少 L2 验证，自动发现内容至少标注来源。
<!-- outline-end -->"""
            # Insert outline after H1
            content = content.replace(h1, h1 + "\n\n" + outline)
            
    with open(filepath, 'w') as f:
        f.write(content)
        print(f"Updated {filename}")
