# X1 通用部署说明（macOS）

## 目标

把 X1 部署到任意一台合规 macOS 主机，而不是绑定某一台旧机器路径。

## 一、准备

### 必需
- macOS
- `python3`
- 项目代码目录
- `x1_config.json`

### 按需
- `node` / `npm`（需要重建前端时）
- `WPS Office`（desktop 模式下本地打开 office 文件）
- `Pages` / `osascript`（若仍需桌面转换链）

## 二、运行模式

### desktop
适合办公机：
- 允许 `open`
- 允许本地打开报告/原始记录
- 可接入 WPS / Pages / AppleScript

### server
适合无头或远程服务机：
- 禁用本机打开文件
- 不把 GUI 能力当成基础前提
- 主要走下载、导出、API 服务链

在 `x1_config.json` 中设置：

```json
{
  "host_mode": "desktop"
}
```

可选值：`desktop` / `server`

## 三、部署步骤

### 1. 安装依赖
```bash
cd /path/to/X1
./install_x1.sh
```

### 2. 初始化目录与归档配置
```bash
./init_x1_env.sh
```

该脚本会：
- 创建 records/reports/logs/cache/temp/uploads 目录
- 创建正式报告/原始记录归档目录
- 将 archive 配置写回 `x1_config.json`

### 3. 恢复模板资源包（如需要迁移模板）
```bash
python3 restore_x1_template_bundle.py /path/to/x1_template_bundle_*.tar.gz
python3 verify_x1_template_bundle.py /path/to/unpacked_bundle_dir
```

### 4. 迁移体检
```bash
python3 doctor_x1_migration.py
```

体检通过后再继续。

### 5. 启动服务
```bash
bash start_x1_daemon.sh
```

### 6. 最小验收
```bash
python3 smoke_test_x1.py
```

## 四、主配置约定

唯一运行态主配置：
- `x1_config.json`

历史副本：
- `config/x1_config.example.json`

不要再把 `config/x1_config.example.json` 当成运行态真配置。

## 五、模板路径约定

模板注册表已开始支持两类相对路径：

- `template_relpath`：相对于 `template_base`
- `template_project_relpath`：相对于项目根目录

不要再新增绑定旧主机的绝对路径。

## 六、迁移成功最低标准

- `doctor_x1_migration.py` 全绿
- `smoke_test_x1.py` 全绿
- `/api/x/health` 正常
- 登录页正常
- 关键受保护路由能正确跳登录
- 后续再补业务主链导出验证
