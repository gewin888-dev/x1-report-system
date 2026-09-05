#!/bin/bash
# Git commit 时自动判断并升级版本号
# 用法: 在 .git/hooks/pre-commit 中调用

# 检查提交信息前缀，自动判断版本升级类型
# feat: -> minor (新功能)
# fix: -> patch (bug修复)
# BREAKING CHANGE: -> major (破坏性变更)

COMMIT_MSG_FILE="$1"

if [ ! -f "$COMMIT_MSG_FILE" ]; then
    # 如果没有提交信息文件，跳过（可能是 git commit --amend）
    exit 0
fi

COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

# 判断是否需要升级版本
if echo "$COMMIT_MSG" | grep -q "^feat:"; then
    BUMP_TYPE="minor"
elif echo "$COMMIT_MSG" | grep -q "^fix:"; then
    BUMP_TYPE="patch"
elif echo "$COMMIT_MSG" | grep -q "BREAKING CHANGE"; then
    BUMP_TYPE="major"
else
    # 其他类型提交（chore/docs/style等）不自动升级版本
    exit 0
fi

echo "检测到 $BUMP_TYPE 类型变更，自动升级版本..."
python3 scripts/bump_version.py "$BUMP_TYPE"

# 将版本文件添加到本次提交
git add x1_config.json CHANGELOG.md
