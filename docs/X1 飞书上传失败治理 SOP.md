# X1 飞书上传失败治理 SOP

**更新时间**: 2026-05-16

---

## 飞书上传流程

```
导出报告 → 获取 token → 解析目标文件夹 → 上传文件 → 记录结果
```

## 配置文件

- 开关：`x1_config.json` → `feishu.enabled`
- 凭证：`feishu_config.json` → `app_id` / `app_secret`
- 目录：`feishu_config.json` → `folders.reports` / `folders.exports`

## 目录模式

X1 支持三种飞书目录组织模式（自动识别）：

| 模式 | 说明 | 子目录结构 |
|------|------|-----------|
| direct | 直接上传到配置的文件夹 | 无子目录 |
| month-root | 按月份子目录归档 | `2026-05/`、`2026-06/` |
| year-month | 按年+月归档 | `2026/05/` |

当前使用：**month-root**（按月份自动切换）

## 排障流程

### Step 1: 确认开关

```python
# x1_config.json
{"feishu": {"enabled": true}}
```

### Step 2: 测试 Token

```bash
cd /Users/fuwuqi/检测报告生成系统_X1
python3 -c "from feishu_utils import get_feishu_token; t=get_feishu_token(); print('OK' if t else 'FAIL', len(t or ''))"
```

### Step 3: 测试文件夹解析

```bash
python3 -c "
from feishu_utils import resolve_feishu_upload_folder
r = resolve_feishu_upload_folder('reports')
e = resolve_feishu_upload_folder('exports')
print(f'reports: {r}')
print(f'exports: {e}')
"
```

### Step 4: 检查月份目录

如果是 month-root 模式，确认当月子目录存在。如不存在，系统会自动创建。

### Step 5: 重试上传

后台 → 记录管理 → 找到失败记录 → 点击"重试飞书上传"

## 常见失败原因

| 原因 | 解决 |
|------|------|
| Token 获取失败 | 检查 app_id/app_secret 是否正确 |
| 文件夹不可访问 | 确认飞书应用有云空间权限 |
| 网络超时 | 检查网络连通性 |
| 文件过大 | 飞书单文件限制 20MB |
| 月份目录不存在 | 系统自动创建，如失败检查父目录权限 |

## 批量重试

后台 → 记录管理 → 筛选飞书上传失败的记录 → 逐条重试
