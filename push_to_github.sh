#!/bin/bash
# GitHub 推送脚本
# 用途：推送代码和版本标签到GitHub

set -e  # 遇到错误立即退出

cd "$(dirname "$0")"

echo "======================================"
echo "   GitHub 推送脚本"
echo "======================================"
echo ""

# 检查当前分支
CURRENT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
echo "当前分支: $CURRENT_BRANCH"

# 检查是否有未提交的修改
if [[ -n $(git status -s) ]]; then
    echo "⚠️  警告：有未提交的修改"
    git status -s
    echo ""
    read -p "是否继续推送？(y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ 取消推送"
        exit 1
    fi
fi

# 显示最新的commit
echo ""
echo "最新commit:"
git log --oneline -3
echo ""

# 显示标签
echo "本地标签:"
git tag -l | tail -5
echo ""

# 推送代码
echo "======================================"
echo "1. 推送代码到 origin/$CURRENT_BRANCH"
echo "======================================"
read -p "继续？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "正在推送..."
    if git push origin $CURRENT_BRANCH; then
        echo "✅ 代码推送成功！"
    else
        echo "❌ 代码推送失败"
        echo ""
        echo "可能的原因："
        echo "1. 需要输入GitHub用户名和Personal Access Token"
        echo "2. 网络连接问题"
        echo "3. 没有推送权限"
        echo ""
        echo "解决方法："
        echo "- 获取Personal Access Token: https://github.com/settings/tokens"
        echo "- 输入时 Username: gewin888-dev"
        echo "- 输入时 Password: [粘贴你的token]"
        exit 1
    fi
else
    echo "⏭️  跳过代码推送"
fi

echo ""

# 推送标签
echo "======================================"
echo "2. 推送版本标签"
echo "======================================"
LATEST_TAG=$(git tag -l | tail -1)
echo "最新标签: $LATEST_TAG"
echo ""
read -p "推送标签 $LATEST_TAG？(y/N): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "正在推送标签..."
    if git push origin $LATEST_TAG; then
        echo "✅ 标签推送成功！"
        echo ""
        echo "🎉 完成！"
        echo ""
        echo "验证："
        echo "- 代码: https://github.com/gewin888-dev/x1-report-system/commits/$CURRENT_BRANCH"
        echo "- 标签: https://github.com/gewin888-dev/x1-report-system/releases"
    else
        echo "❌ 标签推送失败"
        exit 1
    fi
else
    echo "⏭️  跳过标签推送"
fi

echo ""
echo "======================================"
echo "   推送完成"
echo "======================================"
