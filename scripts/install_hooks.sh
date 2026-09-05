#!/bin/bash
# 安装Git Hooks以启用版本自动升级

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "======================================"
echo "安装X1系统版本自动升级Hooks"
echo "======================================"

# 1. pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'HOOK1'
#!/bin/bash
# X1系统版本自动升级Hook

# 检查是否是版本升级提交本身（避免递归）
if git diff --cached --name-only | grep -q "^x1_config.json$" && \
   git diff --cached --name-only | grep -q "^CHANGELOG.md$" && \
   [ $(git diff --cached --name-only | wc -l) -eq 2 ]; then
    exit 0
fi

# 检查暂存区是否有实质性变更
STAGED_FILES=$(git diff --cached --name-only | grep -vE "^(x1_config.json|CHANGELOG.md)$")
if [ -z "$STAGED_FILES" ]; then
    exit 0
fi

echo "PENDING" > .git/BUMP_VERSION_PENDING
exit 0
HOOK1

chmod +x "$HOOKS_DIR/pre-commit"
echo "✓ pre-commit hook 已安装"

# 2. prepare-commit-msg hook
cat > "$HOOKS_DIR/prepare-commit-msg" << 'HOOK2'
#!/bin/bash

COMMIT_MSG_FILE="$1"
COMMIT_SOURCE="$2"

if [ ! -f .git/BUMP_VERSION_PENDING ]; then
    exit 0
fi

rm -f .git/BUMP_VERSION_PENDING

if [ "$COMMIT_SOURCE" = "merge" ] || [ "$COMMIT_SOURCE" = "squash" ]; then
    exit 0
fi

COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")

if echo "$COMMIT_MSG" | grep -qE "^chore:.*(升级版本|版本号)"; then
    exit 0
fi

BUMP_TYPE=""
if echo "$COMMIT_MSG" | grep -q "BREAKING CHANGE"; then
    BUMP_TYPE="major"
elif echo "$COMMIT_MSG" | grep -q "^feat"; then
    BUMP_TYPE="minor"
elif echo "$COMMIT_MSG" | grep -q "^fix"; then
    BUMP_TYPE="patch"
fi

if [ -n "$BUMP_TYPE" ]; then
    echo "======================================"
    echo "检测到 $BUMP_TYPE 类型变更，自动升级版本..."
    echo "======================================"
    
    python3 scripts/bump_version.py "$BUMP_TYPE"
    git add x1_config.json CHANGELOG.md
    
    echo ""
    echo "✓ 版本文件已更新并添加到暂存区"
    echo ""
fi

exit 0
HOOK2

chmod +x "$HOOKS_DIR/prepare-commit-msg"
echo "✓ prepare-commit-msg hook 已安装"

# 3. post-commit hook
cat > "$HOOKS_DIR/post-commit" << 'HOOK3'
#!/bin/bash

if git diff --cached --quiet x1_config.json CHANGELOG.md 2>/dev/null; then
    exit 0
fi

echo ""
echo "======================================"
echo "创建版本升级提交..."
echo "======================================"

LAST_COMMIT_MSG=$(git log -1 --pretty=%B)
NEW_VERSION=$(grep '"version"' x1_config.json | sed -E 's/.*"version": "([^"]+)".*/\1/')

git commit --no-verify -m "chore: 升级版本至 ${NEW_VERSION}

由以下提交自动触发:
${LAST_COMMIT_MSG}"

echo ""
echo "✓ 版本号已在独立提交中更新: ${NEW_VERSION}"
echo ""

exit 0
HOOK3

chmod +x "$HOOKS_DIR/post-commit"
echo "✓ post-commit hook 已安装"

echo ""
echo "======================================"
echo "✓ 版本自动升级已启用"
echo "======================================"
echo ""
echo "提交规范:"
echo "  feat: xxx  -> 自动升级 minor 版本"
echo "  fix: xxx   -> 自动升级 patch 版本"
echo "  其他类型   -> 不升级版本"
echo ""
