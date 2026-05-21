# X1 `role_permissions` 下线清单（建议版）

## 目标
在当前“`role_permission_final` 已成为主真值表”的基础上，制定一个低风险、可回退的 `role_permissions` 遗留补丁表下线顺序，避免再次把旧补丁模型带回运行主链。

---

## 当前现状
### 已确认
1. 运行时权限主读取已优先走 `role_permission_final`
2. 后台权限保存已改为写入 `role_permission_final`
3. `role_permissions` 当前仍保留以下用途：
   - 历史补丁来源
   - 首次迁移参考
   - 遗留兼容 fallback
   - 数据对照排查

### 当前风险
只要 `role_permissions` 仍在运行代码中保留 fallback 语义，就存在以下中长期风险：
- 后续开发误把它当真值表继续读/写
- 默认权限调整后，旧补丁语义再次漂移
- 调试时新旧表混看，重新制造认知混乱

---

## 下线前必须满足的条件
在真正移除 `role_permissions` 的运行时依赖前，建议先满足以下条件：

### 条件 1：所有角色都已在新表落地
检查 `role_permission_final` 是否已覆盖所有角色：
- `admin`
- `supervisor`
- `viewer`
- `inspector`
- `customer`

并确认每个角色权限数量符合预期。

### 条件 2：后台权限页已稳定运行一段时间
建议至少经过一段实际使用观察期，确认：
- 保存后能正常读取
- 当前账号即时刷新正常
- 其他账号重登后权限正常
- 无“保存后丢权限/多权限”反馈

### 条件 3：无新增代码继续写旧表
需要再次搜索确认：
- 没有新的接口或脚本继续 `INSERT/DELETE/UPDATE role_permissions`
- 没有新的业务逻辑把 `role_permissions` 当成主表使用

### 条件 4：保留一次数据库备份
在彻底移除 fallback 前，应备份数据库，至少确保：
- `role_permissions`
- `role_permission_final`
- `users`
相关数据可回滚。

---

## 推荐下线顺序

## 阶段 A：冻结旧表（现在已基本完成）
### 目标
让 `role_permissions` 退出主写入链，退化为遗留只读表。

### 当前状态
已完成：
- 后台保存不再写 `role_permissions`
- 文档说明其为遗留兼容表
- 代码注释标明其不是主真值源

### 还可追加的轻量动作
- 在开发文档中明确禁止新增逻辑写旧表
- 若有内部维护脚本，也应同步注明旧表只读

---

## 阶段 B：移除运行时 fallback（建议下一次稳定窗口执行）
### 目标
让运行时彻底不再依赖 `role_permissions`

### 需要修改的位置
#### 文件 1：`auth.py`
当前函数：
- `_get_effective_permissions_from_legacy(conn, role)`
- `_load_role_permissions(role)`
- `migrate_role_permissions_to_final_store(force=False)`

### 建议修改方式
1. 保留 `_ensure_role_permission_final_table()`
2. 保留 `_get_final_permissions_from_db()`
3. 将 `_load_role_permissions(role)` 改为：
   - `admin` 返回 `{'*'}`
   - 其他角色直接读 `role_permission_final`
   - 若新表中该角色为空，返回空集或默认集前必须显式报警/记录日志，不再悄悄走旧补丁
4. `_get_effective_permissions_from_legacy()` 改为：
   - 仅供一次性迁移脚本使用
   - 不再参与运行时授权主链

### 阶段 B 验证点
- 重启后所有角色仍可正常访问其应有页面
- `/api/user` 返回权限不为空且与后台配置一致
- 当前权限保存/刷新链不受影响

---

## 阶段 C：移除权限页对旧表的展示依赖
### 目标
后台接口不再读取旧表做对照展示。

### 需要修改的位置
#### 文件 2：`routes/admin_misc.py`
当前接口：
- `/admin/api/permissions/roles`

### 建议修改方式
1. 删除读取 `role_permissions` 的对照查询
2. `custom_permissions` 继续保留，但直接基于：
   - `default_permissions`
   - `effective_permissions`
   计算差异
3. 删除 `legacy_custom_permissions` 返回字段
4. `storage_mode` 固定为 `final`

### 阶段 C 验证点
- 权限页仍能正常显示默认/覆盖/最终三层信息
- 前端不再依赖任何 legacy 返回字段

---

## 阶段 D：归档旧表（最后一步）
### 目标
彻底退出 `role_permissions`。

### 推荐做法
不要直接删，先归档：

#### 方案 1：重命名归档
- `role_permissions` → `role_permissions_legacy_backup_YYYYMMDD`

#### 方案 2：导出后删除
- 导出为 SQL / CSV 归档
- 再执行删除

### 不建议直接做的动作
- 不建议在未经历稳定观察期时直接 DROP TABLE
- 不建议在没有数据库备份时直接删

---

## 最小执行清单（给未来操作时用）

### Step 1
确认所有角色都已在 `role_permission_final` 中存在。

### Step 2
确认后台最近一段时间内没有权限异常反馈。

### Step 3
全项目搜索 `role_permissions` 的读写点，确认没有新增正常写入路径。

### Step 4
备份数据库。

### Step 5
修改 `auth.py`，移除运行时 fallback。

### Step 6
重启服务并验证：
- `/api/user`
- 后台权限页
- 至少一个 `viewer`
- 至少一个 `supervisor`
- 至少一个 `inspector`

### Step 7
修改 `routes/admin_misc.py`，移除 legacy 对照字段。

### Step 8
再次验证权限页保存、显示、当前账号即时刷新。

### Step 9
稳定观察后，归档或删除 `role_permissions`。

---

## 当前建议
对 X1 当前环境，建议停在：

### 已完成状态
- 新表已上线
- 新表已迁移
- 旧表已停止主写入
- 旧表已被标注为遗留兼容表

### 暂不建议立刻执行
- 立刻移除 runtime fallback
- 立刻删除 `role_permissions`

### 最优策略
> 先以当前模型稳定运行观察一段时间，再进入“移除 fallback → 去除接口 legacy 字段 → 归档旧表”的第三阶段下线。

---

## 结论
`role_permissions` 现在已经不应该再参与新的主业务设计。它的正确退出路径是：

1. **先停写**
2. **再停运行时依赖**
3. **再停接口展示依赖**
4. **最后归档或删除**

这样风险最小，也最符合当前 X1 这套生产式业务系统的稳妥节奏。
