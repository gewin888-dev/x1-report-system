# X1系统版本管理指南

## 快速使用

### 手动升级版本

```bash
# Bug修复：4.9.2 -> 4.9.3
python scripts/bump_version.py patch

# 新功能：4.9.2 -> 4.10.0
python scripts/bump_version.py minor

# 重大变更：4.9.2 -> 5.0.0
python scripts/bump_version.py major
```

执行后会自动：
1. 更新 `x1_config.json` 中的版本号
2. 在 `CHANGELOG.md` 中添加新版本记录
3. 提示下一步操作

### 自动升级版本（推荐）

使用规范的 commit 提交信息，系统会自动判断版本升级类型：

```bash
# Bug修复 -> 自动升级 patch 版本
git commit -m "fix: 修复批量删除功能的幂等性问题"

# 新功能 -> 自动升级 minor 版本
git commit -m "feat: 添加项目任务派单功能"

# 破坏性变更 -> 自动升级 major 版本
git commit -m "feat: 重构报告生成引擎

BREAKING CHANGE: API返回结构变更，不兼容旧版本"
```

## 设置自动升级

### 方式1：Git Hook（提交时自动）

```bash
# 安装 pre-commit hook
cat > .git/hooks/prepare-commit-msg << 'HOOK'
#!/bin/bash
exec < /dev/tty
bash scripts/auto_bump_on_commit.sh "$1"
HOOK

chmod +x .git/hooks/prepare-commit-msg
```

### 方式2：GitHub Actions（推送时自动）

创建 `.github/workflows/version-bump.yml`：

```yaml
name: Auto Version Bump

on:
  push:
    branches: [ main ]

jobs:
  bump:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: 检查提交类型并升级版本
        run: |
          COMMIT_MSG=$(git log -1 --pretty=%B)
          
          if echo "$COMMIT_MSG" | grep -q "^feat:"; then
            python scripts/bump_version.py minor
          elif echo "$COMMIT_MSG" | grep -q "^fix:"; then
            python scripts/bump_version.py patch
          elif echo "$COMMIT_MSG" | grep -q "BREAKING CHANGE"; then
            python scripts/bump_version.py major
          fi
      
      - name: 提交版本变更
        run: |
          git config user.name "X1 System"
          git config user.email "x1@local"
          git add x1_config.json CHANGELOG.md
          git commit -m "chore: 自动升级版本号" || exit 0
          git push
```

## Commit 消息规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

### 类型标识

- `feat:` - 新功能
- `fix:` - Bug修复
- `docs:` - 文档变更
- `style:` - 代码格式（不影响功能）
- `refactor:` - 重构（既不是新功能也不是修复）
- `perf:` - 性能优化
- `test:` - 测试相关
- `chore:` - 构建/工具/依赖更新

### 示例

```bash
# 好的提交信息
git commit -m "feat: 添加项目报告批量导出功能"
git commit -m "fix: 修复检测数据导入时的编码问题"
git commit -m "docs: 更新API文档"

# 包含详细说明
git commit -m "feat: 添加飞书通知集成

- 支持项目状态变更通知
- 支持报告生成完成通知
- 配置化的通知模板"
```

## 版本号含义

当前版本：**4.9.2**

- **4** (Major) - 第4代系统架构
- **9** (Minor) - 第9轮功能迭代
- **2** (Patch) - 第2次Bug修复

## 查看版本历史

```bash
# 查看完整更新日志
cat CHANGELOG.md

# 查看Git版本标签
git tag -l

# 查看当前运行版本
curl http://localhost:8082/api/version
```

## 发布流程

1. 开发完成后提交代码
2. 版本号自动升级（或手动升级）
3. 补充 CHANGELOG.md 中的变更说明
4. 推送到远程仓库
5. 创建 Git Tag（可选）

```bash
# 创建版本标签
git tag -a v4.9.2 -m "Release v4.9.2"
git push origin v4.9.2
```

## 故障排查

### 版本号未自动升级

检查：
1. commit 消息是否符合规范（`feat:`/`fix:` 前缀）
2. Git hook 是否正确安装
3. Python脚本是否有执行权限

### 版本号冲突

如果多人同时修改版本号：
```bash
# 拉取最新代码
git pull origin main

# 重新运行升级脚本
python scripts/bump_version.py patch
```
