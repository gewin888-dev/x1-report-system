# X1 样板工作区命名迁移说明

## 目的

将前端样板控制器从 `x-passbox.js` 升级为更中性的 `x-sample-workspace.js`。

这样做不是简单改名，而是为了体现 X 的真实发展方向：

- 不再把 X 理解成单一 `pass_box` 试验页
- 而是把它建设成一个可持续扩展的对象样板工作区
- 当前已覆盖：`pass_box`、`laminar_hood`
- 后续可继续纳入：`operating_room`、`clean_function_room`、`bsl`

---

## 当前变更

### 模板引用已切换
- 从：`/static/x-passbox.js`
- 改为：`/static/x-sample-workspace.js`

### 当前职责
`x-sample-workspace.js` 负责：
1. X 样板对象工作区初始化
2. 对象类型切换
3. canonical draft 预览
4. X 草稿保存
5. X 草稿读取与回填
6. X 导出构建

---

## 原则意义

这次迁移体现的是：
- X 的前端主链正在从“单对象实验代码”走向“对象级可扩展控制器”
- 命名必须服务架构目标，不能继续让文件名把系统认知锁死在 `pass_box`

---

_创建时间：2026-04-14 18:16 GMT+8_
