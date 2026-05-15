# X1 检测报告生成系统 - API 文档

> 版本：X5.0
> 更新时间：2026-05-15
> 文档类型：B类说明书（低频更新）
> Base URL：`http://127.0.0.1:8082`

---

## 一、接口分组总览（126个路由）

| 分组 | 数量 | 说明 |
|------|------|------|
| 认证与入口 | 3 | 登录/登出/首页路由 |
| 前台录入与草稿 | 12 | 草稿保存/加载/导出/转让 |
| 项目管理 | 8 | 项目CRUD/摘要/报告关联/任务列表 |
| 任务派单（后台） | 5 | 创建/查看/更新/取消任务 + 检测员列表 |
| 任务执行（检测员） | 5 | 我的任务/接单/开始/完成/预填 |
| 客户界面 | 9 | 客户资料/项目/下单/催单/反馈/历史 |
| 客户管理（后台） | 6 | 客户列表/详情/编辑/反馈回复/创建/清催单 |
| 报告管理 | 7 | 记录列表/删除/批量删除/飞书重试/回收站 |
| 用户与权限 | 8 | 用户CRUD/角色权限配置 |
| 模板管理 | 20 | 模板注册/上传/验证/映射/预览 |
| 数据统计 | 1 | 综合统计数据 |
| 标准数据库 | 2 | 标准列表/详情 |
| 系统设置 | 12 | 配置读写/路径探测/飞书测试/备份恢复 |
| 操作日志 | 3 | 日志查询/批量删除/月份列表 |
| 系统文档 | 2 | 技术文档/workspace文档读取 |
| 其他 | 若干 | 文件下载/预览/健康检查/监控页 |

---

## 二、认证与入口

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET/POST | `/login` | 登录页（表单或JSON） | 公开 |
| GET | `/logout` | 登出 | 已登录 |
| GET | `/` | 首页路由（admin→后台，customer→客户界面） | 已登录 |
| GET | `/api/user` | 当前用户信息 | 公开（返回空或用户数据） |

---

## 三、前台录入与草稿

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/x/save_draft` | 保存草稿 | draft.write |
| GET | `/api/x/load_draft/<draft_id>` | 加载草稿 | draft.read |
| GET | `/api/x/list_drafts` | 草稿列表 | draft.read |
| POST | `/api/x/submit_export` | 主导出入口（判定→生成→落盘→飞书） | record.export |
| POST | `/api/x/build_export` | 预览导出 | record.export |
| GET | `/api/x/list_exports` | 导出记录列表 | 已登录 |
| POST | `/api/x/transfer_draft` | 转让草稿 | draft.write |
| GET | `/api/x/meta` | 系统元数据 | 已登录 |
| GET | `/api/x/inspectors` | 检测员列表（转让用） | 已登录 |
| POST | `/api/x/template_probe` | 模板探测 | 已登录 |
| POST | `/api/save` | 兼容保存 | 已登录 |
| GET | `/download/<filename>` | 下载导出文件 | 已登录 |

---

## 四、项目管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/admin/api/business_projects` | 项目列表（支持分页/筛选） | admin.projects.view |
| GET | `/admin/api/business_projects/summary` | 摘要统计（8卡数据） | admin.projects.view |
| GET | `/admin/api/business_projects/<id>` | 项目详情 | admin.projects.view |
| POST | `/admin/api/business_projects` | 创建项目（自动分配PJ-YYYY-NNNN） | admin.projects.manage |
| PUT | `/admin/api/business_projects/<id>` | 更新项目 | admin.projects.manage |
| DELETE | `/admin/api/business_projects/<id>` | 删除项目 | admin.projects.manage |
| GET | `/admin/api/business_projects/<id>/reports` | 关联报告列表（反查reports_x1/） | admin.projects.view |
| GET | `/admin/api/business_projects/<id>/tasks` | 项目下任务列表 | admin.tasks.view |

### 自动同步（路线3）
检测员导出时，`_auto_sync_project_and_task()` 自动按项目名+客户名查重，不存在则创建项目+任务记录。同步失败不阻断导出主链。

---

## 五、任务派单（后台）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/admin/api/project_tasks` | 创建任务/派单 | admin.tasks.manage |
| GET | `/admin/api/project_tasks/<id>` | 任务详情 | admin.tasks.view |
| PUT | `/admin/api/project_tasks/<id>` | 更新任务 | admin.tasks.manage |
| POST | `/admin/api/project_tasks/<id>/cancel` | 取消任务 | admin.tasks.manage |
| GET | `/admin/api/inspectors` | 可派单人员列表 | admin.projects.view |

### 任务状态流转
`pending_assign → assigned → accepted → in_progress → completed`
任意状态可 → `cancelled`

---

## 六、任务执行（检测员）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/my_tasks` | 我的任务（?status=active/completed/all） | tasks.execute |
| POST | `/api/project_tasks/<id>/accept` | 接单 | tasks.execute |
| POST | `/api/project_tasks/<id>/start` | 开始执行 | tasks.execute |
| POST | `/api/project_tasks/<id>/complete` | 完成任务 | tasks.execute |
| GET | `/api/project_tasks/<id>/prefill` | 获取预填信息（进入录入用） | tasks.execute |

---

## 七、客户界面

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/customer` | 客户门户页面 | customer.access |
| GET | `/customer/api/profile` | 获取客户资料 | customer.profile |
| PUT | `/customer/api/profile` | 更新客户资料（开票/收件） | customer.profile |
| GET | `/customer/api/projects` | 项目列表（按client_name隔离） | customer.projects |
| POST | `/customer/api/projects` | 下单（创建项目，source='客户需求'） | customer.projects |
| POST | `/customer/api/projects/<id>/urge` | 催单（type=report/invoice，24h冷却） | customer.projects |
| GET | `/customer/api/history` | 历史检测记录 | customer.history |
| GET | `/customer/api/feedback` | 反馈列表 | customer.feedback |
| POST | `/customer/api/feedback` | 提交反馈 | customer.feedback |

### 数据隔离
所有客户API通过 `current_user.client_name` 实现数据隔离，客户只能看到自己公司的数据。

---

## 八、客户管理（后台）

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/admin/api/customer_management/list` | 客户聚合列表（6源数据） | admin.customers.view |
| GET | `/admin/api/customer_management/detail` | 客户详情（项目/催单/反馈/报告） | admin.customers.view |
| PUT | `/admin/api/customer_management/profile` | 编辑客户资料 | admin.customers.manage |
| PUT | `/admin/api/customer_management/feedback/<id>/reply` | 回复反馈 | admin.customers.manage |
| POST | `/admin/api/customer_management/create` | 创建客户 | admin.customers.manage |
| POST | `/admin/api/customer_management/clear_urge/<id>` | 清除催单标记 | admin.customers.manage |

### 聚合数据源
客户列表从 business_projects、client_profiles、users、reports_x1、urge_logs、feedback 六个来源自动聚合，无需单独的客户主表。

---

## 九、报告管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/admin/api/records` | 记录列表（分页/搜索/筛选） | admin.records.view |
| GET | `/admin/api/records/summary` | 记录摘要统计 | admin.records.view |
| DELETE | `/admin/api/records/<id>` | 删除记录（移入trash/） | admin.records.delete |
| POST | `/admin/api/records/batch_delete` | 批量删除 | admin.records.batch_delete |
| POST | `/admin/api/records/<id>/retry_feishu` | 飞书重试 | admin.feishu.retry |
| POST | `/admin/api/cleanup_trash` | 清理回收站 | admin.trash.cleanup |
| GET | `/admin/api/trash_status` | 回收站状态 | admin.trash.cleanup |

---

## 十、用户与权限管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/admin/api/users` | 用户列表 | admin.users.view |
| POST | `/admin/api/users` | 创建用户 | admin.users.manage |
| PUT | `/admin/api/users/<username>` | 更新用户 | admin.users.manage |
| DELETE | `/admin/api/users/<username>` | 删除用户 | admin.users.manage |
| POST | `/admin/api/users/<username>/toggle_active` | 启停用户 | admin.users.manage |
| POST | `/admin/api/users/<username>/reset_password` | 重置密码 | admin.users.manage |
| GET | `/admin/api/permissions/roles` | 角色权限列表 | admin.permissions.view |
| PUT | `/admin/api/permissions/roles/<role>` | 更新角色权限 | admin.permissions.manage |

---

## 十一、模板管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/api/templates` | 模板列表 |
| GET | `/admin/api/templates/<id>` | 模板详情 |
| POST | `/admin/api/templates/<id>/upload` | 上传模板 |
| GET | `/admin/api/templates/<id>/versions` | 版本历史 |
| GET | `/admin/api/templates/<id>/preview` | 预览模板 |
| GET | `/admin/api/templates/<id>/variables` | 提取变量 |
| GET | `/admin/api/template-registry/options` | 注册选项 |
| POST | `/admin/api/template-registry/register` | 注册模板 |
| POST | `/admin/api/template-registry/upload-and-register` | 上传并注册 |
| POST | `/admin/api/template-registry/verify` | 验证模板 |
| POST | `/admin/api/template-registry/smoke-export` | 冒烟导出测试 |
| POST | `/admin/api/template-registry/toggle` | 启停模板 |
| POST | `/admin/api/template-registry/delete` | 删除模板 |
| GET/POST | `/admin/api/template-type-mappings/*` | 类型映射管理 |
| GET/POST | `/admin/api/template-semantic-mappings/*` | 语义映射管理 |

权限：均需 `admin.templates.*` 相关权限

---

## 十二、系统设置、监控、日志、文档

### 系统设置（12个接口）
- `GET/PUT /admin/api/settings` — 配置读写
- 路径探测、飞书测试、备份/恢复等

### 数据统计
- `GET /admin/api/stats` — 综合统计

### 标准数据库
- `GET /admin/api/standards` — 标准列表
- `GET /admin/api/standards/<code>` — 标准详情

### 操作日志
- `GET /admin/api/logs` — 日志查询
- `GET /admin/api/logs/months` — 月份列表
- `POST /admin/api/logs/batch_delete` — 批量删除

### 系统文档
- `GET /admin/api/docs/<doc_name>` — ARCHITECTURE / API
- `GET /admin/api/workspace_doc?path=...` — workspace文档

### 其他
- `GET /api/system/health` — 健康信息
- `GET /admin/api/download_file?path=...` — 文件下载（admin.files.download）

---

## 十三、一句话接口判断

> X1 接口体系共 126 个路由，覆盖录入→导出→项目管理→任务派单→客户服务→后台治理全链路，通过 5 角色 + 精细权限 key 实现分层访问控制。
