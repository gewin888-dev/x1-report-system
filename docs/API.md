# X1 检测报告生成系统 - API 文档

版本：X4.8.2  
更新时间：2026-05-22  
Base URL：`http://127.0.0.1:8082`

---

## 一、说明

本文件只保留当前主链接口参考与业务口径说明，不再试图作为某个历史阶段的“全量路由统计快照”。

如代码继续演化，应以当前运行接口与实际权限校验为准。

---

## 二、认证与基础接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET/POST | `/login` | 登录 |
| GET | `/logout` | 登出 |
| GET | `/` | 首页路由 |
| GET | `/api/user` | 当前用户信息 |
| GET | `/api/x/health` | 健康检查 |
| GET | `/api/x/meta` | 系统元数据 |

---

## 三、员工端录入与导出

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/api/x/save_draft` | 保存草稿 | draft.write |
| GET | `/api/x/load_draft/<draft_id>` | 加载草稿 | draft.read |
| GET | `/api/x/list_drafts` | 草稿列表 | draft.read |
| POST | `/api/x/submit_export` | 主导出入口 | record.export |
| POST | `/api/x/build_export` | 预览导出 | record.export |
| GET | `/api/x/list_exports` | 导出记录列表 | 已登录 |
| POST | `/api/x/transfer_draft` | 转让草稿 | draft.write |
| GET | `/download/<filename>` | 下载导出文件 | 已登录 |

---

## 四、员工任务链

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/api/my_tasks` | 我的任务 | tasks.execute |
| GET | `/api/project_tasks/<id>/prefill` | 进入录入前预填 | tasks.execute |
| POST | `/api/project_tasks/<id>/complete` | 完成任务 | tasks.execute |

### 当前业务口径
员工端当前主流程按三态理解：
- 待检测
- 检测中
- 检测完成

员工侧只保留：
- 进入录入
- 完成任务

`接单` / `开始执行` 不再作为员工端主流程说明文档中的推荐动作展示。

---

## 五、项目管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| GET | `/admin/api/business_projects` | 项目列表 | admin.projects.view |
| GET | `/admin/api/business_projects/summary` | 项目摘要 | admin.projects.view |
| GET | `/admin/api/business_projects/<id>` | 项目详情 | admin.projects.view |
| POST | `/admin/api/business_projects` | 创建项目 | admin.projects.manage |
| PUT | `/admin/api/business_projects/<id>` | 更新项目 | admin.projects.manage |
| DELETE | `/admin/api/business_projects/<id>` | 删除项目 | admin.projects.manage |
| GET | `/admin/api/business_projects/<id>/reports` | 关联报告 | admin.projects.view |
| GET | `/admin/api/business_projects/<id>/tasks` | 项目任务列表 | admin.tasks.view |
| POST | `/admin/api/business_projects/<project_id>/upload_report` | 上传项目报告附件 | admin.projects.manage |
| GET | `/admin/api/business_projects/<project_id>/report_files` | 项目报告附件列表 | admin.projects.view |

---

## 六、后台任务管理

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/admin/api/project_tasks` | 创建任务 / 派单 | admin.tasks.manage |
| GET | `/admin/api/project_tasks/<id>` | 任务详情 | admin.tasks.view |
| PUT | `/admin/api/project_tasks/<id>` | 更新任务 | admin.tasks.manage |
| POST | `/admin/api/project_tasks/<id>/cancel` | 取消任务 | admin.tasks.manage |
| GET | `/admin/api/inspectors` | 可派单人员列表 | admin.projects.view |

---

## 七、客户门户与客户管理

### 客户门户
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/customer` | 客户门户页面 |
| GET | `/customer/api/profile` | 获取资料 |
| PUT | `/customer/api/profile` | 更新资料 |
| GET | `/customer/api/projects` | 项目列表 |
| POST | `/customer/api/projects` | 下单 |
| GET | `/customer/api/history` | 历史记录 |
| GET | `/customer/api/feedback` | 反馈列表 |
| POST | `/customer/api/feedback` | 提交反馈 |

### 客户管理后台
| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/admin/api/customer_management/list` | 客户聚合列表 |
| GET | `/admin/api/customer_management/detail` | 客户详情 |
| PUT | `/admin/api/customer_management/profile` | 编辑资料 |
| PUT | `/admin/api/customer_management/feedback/<id>/reply` | 回复反馈 |
| POST | `/admin/api/customer_management/create` | 创建客户 |
| POST | `/admin/api/customer_management/clear_urge/<id>` | 清除催办 |

---

## 八、记录、模板、设置、日志

### 记录管理
- `GET /admin/api/records`
- `GET /admin/api/records/summary`
- `DELETE /admin/api/records/<id>`
- `POST /admin/api/records/batch_delete`

### 模板管理
- `GET /admin/api/templates`
- `GET /admin/api/template-registry/options`
- `POST /admin/api/template-registry/register`
- `POST /admin/api/template-registry/upload-and-register`
- `POST /admin/api/template-registry/verify`
- `POST /admin/api/template-registry/toggle`
- `POST /admin/api/template-registry/delete`

### 系统设置与运维
- `GET/PUT /admin/api/settings`
- 备份恢复、路径巡检、基础设置相关接口

### 日志与统计
- `GET /admin/api/logs`
- `GET /admin/api/logs/months`
- `POST /admin/api/logs/batch_delete`
- `GET /admin/api/stats`

---

## 九、权限说明

当前权限系统理解应以：
- `role_permission_final` 为运行真相

旧表：
- `role_permissions`

不应再作为当前接口权限判断文档的主真相来源。

---

## 十、文档维护原则

1. 不再把本文件当作“精确路由总数统计文档”。
2. 以当前业务主链、常用接口、权限口径为主。
3. 如接口实装与本文不一致，以当前运行事实为准，并及时更新。
