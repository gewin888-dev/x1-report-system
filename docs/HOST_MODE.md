# X1 host_mode 行为说明

## desktop
启用本机桌面能力：
- `/admin/api/open_file/<filename>`
- `/admin/api/open_feishu_file`
- `/admin/api/settings/native_choose_path`
- `pdf_converter.py`（Pages PDF 转换）

## server
禁用上述桌面能力，改为：
- 使用下载接口替代本机打开
- 使用路径浏览器或手动填写替代原生目录选择器
- 禁用 Pages PDF 转换链

## 设计原则
`host_mode` 只影响宿主机能力，不应影响核心业务链：
- 登录
- 记录列表
- 模板管理
- 健康检查
- 导出主链控制
