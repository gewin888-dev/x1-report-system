# X1 系统守护进程使用说明

## 快速开始

### 启动服务
```bash
./start_x1_daemon.sh
```

### 停止服务
```bash
./stop_x1_daemon.sh
```

### 重启服务
```bash
./restart_x1_daemon.sh
```

### 检查状态
```bash
./status_x1_daemon.sh
```

### 运行回归测试
```bash
./regression_test.sh
```

## 详细说明

### 1. 守护进程管理

当前脚本体系：
- `daemon_common.sh`：公共运维函数库
- `start_x1_daemon.sh`：启动
- `stop_x1_daemon.sh`：停止
- `restart_x1_daemon.sh`：标准重启
- `status_x1_daemon.sh`：状态与诊断
- `doctor_x1_daemon.sh`：健康体检（只读诊断，不做启停）

**start_x1_daemon.sh**
- 以后台守护进程方式启动 X1 服务
- 自动创建日志目录 `logs/`（守护脚本日志）和 `logs_x1/`（应用日志）
- 守护脚本日志按日期命名：`logs/x1_YYYYMMDD.log`
- 应用日志：`logs_x1/app_YYYYMMDD.log`（按天分卷）
- 人工运维日志：`logs_x1/manual_restart_YYYYMMDD_HHMMSS.log`
- PID 文件：`x1.pid`
- 启动前会检查 8082 端口是否已被其他进程占用
- 启动后自动检查服务健康状态；若进程秒退，会自动清理 PID 文件并写诊断日志

**stop_x1_daemon.sh**
- 优雅停止 X1 服务
- 等待最多 10 秒让进程正常退出
- 如果进程未响应，强制终止
- 自动清理 PID 文件
- 若 PID 文件不存在但 8082 端口仍被占用，会提示占用者信息

**restart_x1_daemon.sh**
- 按正式流程执行 stop → start → health check
- 自动记录重启前后状态
- 自动生成 `manual_restart_*.log`
- 失败时自动摘取端口与应用日志尾部，便于追溯

**status_x1_daemon.sh**
- 显示服务运行状态
- 显示进程 PID、启动时间、内存使用
- 执行健康检查（调用 `/api/x/health`）
- 同时显示：
  - 守护脚本日志最后 10 行
  - 应用日志最后 10 行
- 若 PID 已死但 8082 端口被其他进程占用，会明确提示占用者 PID / 进程名 / 命令行

### 2. 端口占用诊断能力

当前脚本已具备自动采集：
- 端口占用者 PID
- 用户名
- 进程名（comm）
- 完整命令行（command）

当 8082 被占用时，不再只看到“Address already in use”，而是能直接看到是谁占着端口。

### 3. 回归测试

**regression_test.sh**
- 基于 2026-04-29 的 9/9 全通过基线
- 测试 9 个核心对象的导出功能
- 自动保存测试日志到 `/tmp/x1_regression_*.log`
- 返回码：0=通过，1=失败

**测试覆盖对象：**
1. operating_room（洁净手术部）
2. clean_function_room（洁净功能用房）
3. bsl（实验室）
4. animal_room（动物房）
5. laminar_hood（层流罩）
6. gmp_workshop（GMP车间）
7. food_workshop（食品洁净车间）
8. pass_box（传递窗）
9. veterinary_gmp_workshop（兽药车间）

## 日志管理

### 守护脚本日志
位置：`logs/x1_YYYYMMDD.log`

查看实时日志：
```bash
tail -f logs/x1_$(date +%Y%m%d).log
```

### 应用日志
位置：`logs_x1/app_YYYYMMDD.log`（按天分卷）

查看今天日志：
```bash
tail -f logs_x1/app_$(date +%Y%m%d).log
```

每次启动会在日志中插入边界标记：
```
================================================================================
  X1 SERVICE START — 2026-05-05 06:53:31
================================================================================
```
便于区分当次启动与历史日志。

### 人工重启 / 运维诊断日志
位置：`logs_x1/manual_restart_YYYYMMDD_HHMMSS.log`

用途：
- 记录每次手工启停 / 重启的诊断快照
- 保留端口占用者信息、PID 文件状态、健康检查结果、应用日志尾部

查看最近一份：
```bash
ls -t logs_x1/manual_restart_*.log | head -1 | xargs tail -80
```

清理旧守护日志（保留最近7天）：
```bash
find logs/ -name "x1_*.log" -mtime +7 -delete
```

## 开机自启动（可选）

### macOS (launchd)

创建 plist 文件：`~/Library/LaunchAgents/com.x1.daemon.plist`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.x1.daemon</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/fuwuqi/检测报告生成系统_X1/start_x1_daemon.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/fuwuqi/检测报告生成系统_X1/logs/launchd.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/fuwuqi/检测报告生成系统_X1/logs/launchd_error.log</string>
</dict>
</plist>
```

加载服务：
```bash
launchctl load ~/Library/LaunchAgents/com.x1.daemon.plist
```

### 健康体检
```bash
./doctor_x1_daemon.sh
```

输出内容：
- PID 状态 / 内存
- 健康接口
- 端口监听者
- 页面可达性
- 日志文件位置 / 磁盘占用
- 最近异常痕迹
- 综合结论评分（4/4）

不做任何启停操作，纯诊断。

## 故障排查

### 服务无法启动
1. 检查状态：`./status_x1_daemon.sh`
2. 执行标准重启：`./restart_x1_daemon.sh`
3. 检查端口占用：`lsof -nP -iTCP:8082 -sTCP:LISTEN`
4. 检查守护脚本日志：`tail -50 logs/x1_$(date +%Y%m%d).log`
5. 检查应用日志：`tail -50 logs_x1/app_$(date +%Y%m%d).log`
6. 检查最近诊断日志：`ls -t logs_x1/manual_restart_*.log | head -1 | xargs tail -80`
7. 必要时前台启动测试：`python3 app_x1.py`

### 健康检查失败
```bash
curl http://localhost:8082/api/x/health
```

### 进程僵死 / PID 假存活
```bash
./stop_x1_daemon.sh
rm -f x1.pid
./start_x1_daemon.sh
```

## 维护建议

1. **每日检查**：运行 `./status_x1_daemon.sh` 确认服务正常
2. **标准重启**：优先用 `./restart_x1_daemon.sh`，不要手工拼 stop/start
3. **每周回归**：运行 `./regression_test.sh` 确保核心功能稳定
4. **日志清理**：定期清理旧日志文件
5. **异常留痕**：出现问题先保留 `manual_restart_*.log`，再分析原因

## 版本信息

- 创建日期：2026-04-29
- 运维升级：2026-05-05 V2.1
- 基线版本：9/9 对象全通过
- 服务端口：8082
- Python 版本：3.9+
