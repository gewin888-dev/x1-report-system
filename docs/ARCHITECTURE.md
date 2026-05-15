# X1 检测报告生成系统 - 架构文档

> 版本：X5.0
> 更新时间：2026-05-15
> 文档类型：B类说明书（低频更新）
> 用途：说明 X1 当前系统结构、核心模块分工与运行边界。

---

## 一、系统定位

X1 是一套面向洁净室检测领域的全流程业务系统，覆盖：
- 前台录入与草稿管理
- 后端业务判定
- Word / Excel 模板导出（含多房间混合报告）
- 飞书上传与失败治理
- 项目全生命周期管理
- 任务派单与检测员执行
- 客户自助服务门户
- 后台管理与运维

---

## 二、整体架构

```text
┌──────────────────────────────────────────────────────────────────────────┐
│                              使用者层                                    │
│  检测员（录入/执行）  管理员/主管（后台）  客户（自助门户）  访客（只读后台） │
└──────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                          表现层（HTML / JS）                             │
│  record_index.html + record.js        检测员：录入/恢复/导出/我的任务     │
│  admin.html + admin_projects.js       后台：12个管理面板                  │
│           + admin_customers.js        客户管理面板                        │
│  customer.html + customer.js          客户：自助门户（4个功能tab）         │
│  login.html                           统一登录                           │
└──────────────────────────────────────────────────────────────────────────┘
                                │ HTTP / JSON
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                       应用层（Flask）                                     │
│  app_x1.py            主应用：认证/草稿/导出/后台/项目/任务/统计          │
│  customer_routes.py    客户界面路由（9个API）                             │
│  customer_admin_routes.py  客户管理后台路由（6个API）                     │
│  auth.py               5角色权限体系（admin/supervisor/viewer/inspector/  │
│                        customer）+ 精细权限key                           │
│  database.py           SQLite 初始化与访问                               │
│  monitor.py            操作日志、健康监控                                │
└──────────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                           核心业务层                                     │
│  judgement_engine.py         后端业务判定（14个对象）                     │
│  report_context_builder.py   导出上下文构建                              │
│  clean_class_semantics.py    等级/上下文语义归一                         │
│  payload_normalizer.py       前后台载荷兼容与归一化                      │
│  template_rules.py           对象级模板填充规则                          │
│  template_resources.py       模板资源与映射管理                          │
│  adapters/export_docx.py     DOCX 导出（含混合报告）                     │
│  adapters/export_excel.py    Excel 导出                                 │
│  adapters/template_fill.py   模板绑定/填充/XML级精确写入                  │
│  feishu_utils.py             飞书文件夹与文件上传                        │
└──────────────────────────────────────────────────────────────────────────┘
                                │
          ┌─────────────────────┼──────────────────────┐
          ▼                     ▼                      ▼
┌──────────────────┐  ┌──────────────────┐  ┌──────────────────────┐
│ x1_data.db（根）  │  │ data/x1_data.db  │  │ 文件系统              │
│ - users           │  │ - business_      │  │ - records_x1/ 草稿    │
│ - role_permissions │  │   projects       │  │ - reports_x1/ 导出    │
│                   │  │ - project_tasks  │  │ - logs_x1/ 业务日志   │
│                   │  │ - client_profiles│  │ - docs/ 系统文档      │
│                   │  │ - project_urge_  │  │ - 模板基目录          │
│                   │  │   logs           │  │                      │
│                   │  │ - client_feedback│  │                      │
│                   │  │ - exports/drafts │  │                      │
└──────────────────┘  └──────────────────┘  └──────────────────────┘
```

---

## 三、角色与权限体系

### 5个角色

| 角色 | 说明 | 主入口 |
|------|------|--------|
| admin | 系统管理员，全权限（`*`通配） | /admin |
| supervisor | 主管，项目/任务/客户/报告管理 | /admin |
| viewer | 访客，只读后台 | /admin |
| inspector | 检测员，录入/导出/接单执行 | / |
| customer | 客户，自助门户 | /customer |

### 权限 key 体系

| 分组 | 权限 key | admin | supervisor | viewer | inspector | customer |
|------|----------|:-----:|:----------:|:------:|:---------:|:--------:|
| 项目管理 | admin.projects.view / .manage | ✅ | ✅读写 | ✅只读 | - | - |
| 任务派单 | admin.tasks.view / .manage | ✅ | ✅读写 | ✅只读 | - | - |
| 任务执行 | tasks.execute | ✅ | - | - | ✅ | - |
| 客户管理 | admin.customers.view / .manage | ✅ | ✅读写 | - | - | - |
| 客户界面 | customer.* | ✅预览 | - | - | - | ✅ |
| 报告管理 | admin.records.* | ✅ | ✅ | ✅只读 | - | - |
| 模板管理 | admin.templates.* | ✅ | ✅ | ✅只读 | - | - |
| 用户管理 | admin.users.* | ✅ | - | ✅只读 | - | - |
| 文件下载 | admin.files.download | ✅ | ✅ | ✅ | - | - |

---

## 四、核心业务主链

### 1. 录入链
前台填写项目与房间信息 → 保存草稿 → 生成草稿 JSON

### 2. 恢复链
读取草稿 JSON → 归一化 payload → 页面回填项目、房间、参数、判定摘要

### 3. 判定链
前端提交房间信息 → 后端按对象类型分发（14个对象） → 生成统一判定结果

### 4. 导出链
项目数据归一化 → 构建导出上下文 → 生成 Word/Excel → 落盘到 reports_x1/
- 支持单房间导出和多房间混合报告导出

### 5. 外部链路
导出成功后上传飞书 → 失败状态落账 → 后台可见 → 支持后台重试

### 6. 项目管理链
项目创建（手动/自动同步） → 项目编号分配（PJ-YYYY-NNNN） → 派单给检测员 → 检测员接单/执行/完成 → 项目状态自动更新 → 报告数据关联

### 7. 客户服务链
客户登录 → 维护资料 → 下单需求 → 查看项目进度 → 催单（24h冷却） → 反馈建议 → 管理员后台处理

### 8. 后台治理链
后台查看记录 → 搜索/筛选/分页 → 批量删除/回收站 → 查看日志与系统信息

---

## 五、后台管理面板（12个）

按导航栏顺序：

| 分区 | 面板 | 说明 |
|------|------|------|
| 经营概览 | 📊 数据统计 | 累计产出、月度趋势、领域分布、检测员工作量 |
| | 📁 项目管理 | 项目CRUD、8卡摘要、分组列表、项目信息卡（派单+报告关联） |
| | 🏢 客户管理 | 聚合视图（6源数据）、详情、编辑、反馈回复、催单处理 |
| 检测业务 | 📋 报告管理 | 记录列表、批量操作、飞书重试、回收站 |
| | 📄 模板管理 | 模板注册/上传/验证、类型映射、语义映射 |
| | 📖 标准数据库 | 标准查看/搜索 |
| 系统管理 | 👤 用户管理 | 用户CRUD、角色权限配置（按角色分组显示） |
| | 📝 操作日志 | 按月归档、搜索、批量删除 |
| | ⚙️ 系统设置 | 路径配置、飞书配置、备份/恢复 |
| | 🖥️ 系统监控 | 系统信息、CPU/内存/磁盘 |
| | 📚 系统文档 | 架构文档、API文档 |
| 客户视角 | 🔍 客户界面预览 | iframe预览客户门户 |

---

## 六、数据库结构

### x1_data.db（根目录，用户库）
- `users` — 用户账号（含 client_name 绑定）
- `role_permissions` — 角色权限覆盖
- `operation_logs` — 操作日志

### data/x1_data.db（业务库）
- `business_projects` — 项目管理主表（含 project_no、source、has_urge）
- `project_tasks` — 任务/派单表
- `client_profiles` — 客户资料（开票/收件信息）
- `project_urge_logs` — 催单记录
- `client_feedback` — 客户反馈

---

## 七、文件结构

```text
检测报告生成系统_X1/
├── app_x1.py                 主应用（~5000行）
├── auth.py                   认证与权限
├── database.py               数据库初始化
├── monitor.py                监控与日志
├── customer_routes.py        客户界面路由
├── customer_admin_routes.py  客户管理路由
├── judgement_engine.py       后端判定引擎
├── report_context_builder.py 导出上下文
├── clean_class_semantics.py  语义归一
├── payload_normalizer.py     载荷归一
├── template_rules.py         模板规则
├── template_resources.py     模板资源
├── feishu_utils.py           飞书工具
├── x1_config.json            系统配置
├── adapters/
│   ├── export_docx.py        Word导出（含混合报告）
│   ├── export_excel.py       Excel导出
│   └── template_fill.py      模板填充（XML级）
├── templates/
│   ├── admin.html            后台管理页
│   ├── record_index.html     前台录入页
│   ├── customer.html         客户自助门户
│   └── login.html            登录页
├── static/
│   ├── record.js             前台交互
│   ├── admin_projects.js     项目管理
│   ├── admin_customers.js    客户管理
│   ├── customer.js           客户门户
│   ├── standards_db.js       标准数据库
│   └── standards_*.json      标准数据
├── data/x1_data.db           业务数据库
├── records_x1/               草稿目录
├── reports_x1/               导出产物
├── logs_x1/                  业务日志
├── docs/                     系统文档
└── *.sh                      守护脚本
```

---

## 八、配置与运行

### 配置入口
- `x1_config.json`：host、port、paths、template_base

### 启停脚本（V2.1）
- `start_x1_daemon.sh` — 启动（自动诊断+留痕）
- `stop_x1_daemon.sh` — 停止（自动清PID+留痕）
- `restart_x1_daemon.sh` — 标准重启+摘要输出
- `status_x1_daemon.sh` — 状态与诊断
- `doctor_x1_daemon.sh` — 健康体检（只读，4项评分）

### 运行方式
- Flask 单体应用，端口 8082
- SQLite 双库（用户库+业务库）
- Bash 守护脚本做启停和验活

---

## 九、一句话架构判断

> X1 采用「Flask 单体 + SQLite 双库 + 模板导出 + 飞书链路 + 5角色权限 + 客户门户」架构，已覆盖检测业务全流程（录入→判定→导出→项目管理→客户服务→后台治理）。
