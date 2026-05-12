#!/bin/bash
# Pre-commit hook for Android Internals Wiki
# 安装方法: ln -sf ../../scripts/pre-commit-hook.sh .git/hooks/pre-commit

echo "🔍 检查 YAML frontmatter..."
python3 scripts/check-metadata.py
if [ $? -ne 0 ]; then
    echo "❌ YAML frontmatter 检查失败，请修复后重新提交"
    exit 1
fi

echo "✅ 所有检查通过"
exit 0
