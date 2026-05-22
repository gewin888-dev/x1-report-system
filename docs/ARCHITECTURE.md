# X1 检测报告生成系统 - 架构文档

版本：X4.8.2  
更新时间：2026-05-22

---

## 一、文档目的

本文件只描述 X1 **当前运行形态** 的核心结构，不承担历史方案、旧计划、阶段性重构蓝图的说明职责。

---

## 二、系统定位

X1 是面向洁净检测业务的生产系统，当前运行核心覆盖：

- 员工端录入、恢复、导出
- 项目与任务联动
- 客户门户
- 后台管理
- 权限治理
- 运维、日志、备份恢复

---

## 三、当前三端结构

### 1. 员工端
- 页面：`templates/record_index.html`
- 真实运行脚本：`static/record.js`
- 主要职责：录入、恢复、导出、我的任务

### 2. 管理端
- 页面：`templates/admin.html`
- 真实运行脚本：`static/admin.js`
- 主要职责：项目、任务、客户、记录、模板、权限、设置、监控

### 3. 客户端
- 页面：`templates/customer.html`
- 脚本：`static/customer.js`
- 主要职责：客户资料、项目进度、历史记录、反馈

> 说明：项目中曾存在历史构建链（`src/record/*` → `dist/record.bundle.js`），该构建链已被清理（`src/record/` 目录不存在），当前员工端运行入口以 `record_index.html` 实际加载的 `static/record.js` 为准。

---

## 四、后端结构

### 1. 主入口
- `app_x1.py`

### 2. 主要路由模块
- `routes/projects.py` — 项目管理
- `routes/tasks.py` — 任务管理与员工任务链
- `routes/records.py` — 后台记录管理
- `routes/export.py` — 导出主链
- `routes/drafts.py` — 草稿链
- `routes/settings.py` — 设置、备份恢复、健康检查
- `routes/template_mgmt.py` — 模板治理
- `routes/admin_misc.py` — 用户、权限、日志、统计、文档等
- `customer_routes.py` — 客户门户接口
- `customer_admin_routes.py` — 客户管理后台接口

---

## 五、双数据库结构

### 1. 根库：`x1_data.db`
主要承载：
- users
- 权限相关数据
- 日志
- 记录索引类数据

### 2. 业务库：`data/x1_data.db`
主要承载：
- business_projects
- project_tasks
- client_profiles
- client_feedback
- report_feedback
- 其他业务过程数据

### 3. 当前权限真相
权限运行真相以：
- `role_permission_final`

为准。

旧表：
- `role_permissions`

仅作为遗留参考，不应再作为当前权限真相说明。

---

## 六、当前核心业务链

### 1. 录入链
录入页面填写数据 → 保存草稿 → 生成草稿 JSON

### 2. 恢复链
读取草稿 → 载荷归一化 → 页面回填

### 3. 导出链
提交导出 → 构建导出上下文 → 模板填充引擎 → 生成 Word → 落盘

导出引擎核心：
- `adapters/template_fill.py` — 填充引擎主模块
  - `build_template_filled_docx()` — 单房间模板填充
  - `build_mixed_report_docx()` — 混合报告装配（统一路径，所有领域）
  - `_fill_data_table_xml()` — 数据表二次填充（锚点定位）
  - `_replace_table_row_cells_by_anchor_index()` — 按文本锚点定位行写值
- `routes/export.py` — 导出入口、混报校验
- `template_bundles/` — 34 个模板文件（按领域/等级分组）
- `template_rules.py` — 模板规则映射

### 4. 项目任务链
项目创建/维护 → 派单 → 员工进入录入 → 检测中 → 完成任务 → 检测完成 → 报告编制推进

### 5. 客户链
客户登录 → 查看项目/历史 → 反馈 → 后台处理

### 6. 运维链
标准启停脚本 → 健康检查 → 日志 → 备份恢复

---

## 七、当前业务口径提醒

### 任务状态对外口径
当前员工端主口径应理解为：
- 待检测
- 检测中
- 检测完成

员工端主动作只保留：
- 进入录入
- 完成任务

### 文档维护原则
如果文档内容与当前运行事实冲突，应以运行事实为准，并优先更新文档，而不是继续沿用旧阶段说法。
