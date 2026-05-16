# X1 部署执行清单（macOS 通用）

## 部署前
- [ ] 确认目标主机为 macOS
- [ ] 确认 `python3` 可用
- [ ] 如需重建前端，确认 `node` / `npm` 可用
- [ ] 确认已准备 `x1_config.json`
- [ ] 确认模板资源已准备
- [ ] 确认数据恢复包已准备（如需要）

## 初始化
- [ ] 执行 `./install_x1.sh`
- [ ] 执行 `./init_x1_env.sh`
- [ ] 检查 `x1_config.json` 中 `host_mode`
- [ ] 如为办公机，设为 `desktop`
- [ ] 如为服务机，设为 `server`

## 体检
- [ ] 执行 `python3 doctor_x1_migration.py`
- [ ] 确认所有检查项通过

## 模板恢复（如迁移模板）
- [ ] 准备模板资源包 `x1_template_bundle_*.tar.gz`
- [ ] 执行 `python3 restore_x1_template_bundle.py <bundle.tar.gz>`
- [ ] 如需校验解压目录，执行 `python3 verify_x1_template_bundle.py <bundle_dir>`

- [ ] 执行 `bash start_x1_daemon.sh`
- [ ] 确认服务监听 8082
- [ ] 确认 `/api/x/health` 正常

## 验收
- [ ] 执行 `python3 smoke_test_x1.py`
- [ ] 确认 smoke test 全绿
- [ ] 打开登录页人工复核界面正常
- [ ] 如为 desktop 模式，抽查本地打开能力
- [ ] 如为 server 模式，抽查是否自动降级为下载

## 上线前
- [ ] 确认正式报告归档目录正确
- [ ] 确认正式原始记录归档目录正确
- [ ] 确认模板根目录正确
- [ ] 如启用飞书，确认飞书配置已核对
