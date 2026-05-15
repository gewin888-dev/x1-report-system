# X1-negative_pressure-reset接力卡

## 建卡时间
2026-04-16 15:23 GMT+8

## 用途
给 `/reset` 后的新会话直接接手，避免再次卡在旧结论、旧模板认知或“重复改 cell 写法”。

---

## 一句话现状
`negative_pressure` 在 **新模板** 下，`物体表面微生物` / `细菌浓度(沉降法)` 两项的 payload 已确认带值，但最终 `.filled.docx` 目标结果位仍未命中；当前问题已收敛为：

> **不是不会写，而是写入没有落到最终生效的 `document.xml` 上。**

---

## 本轮前置事实（reset 后不要重跑这些判断）

### 模板事实已确认
模板路径：
- `/Users/fuwuqi/公司资料/检测部/检测报告模板/医院洁净部/负压病房检测报告模板.docx`

新模板里：
- `细菌浓度(沉降法)`：`Table 3 / Row 12`
- `物体表面微生物`：`Table 3 / Row 13`

两行均为：
- 5 个真实 `<w:tc>`
- 第 4 个真实 `<w:tc>` = 结果位（0-based index = 3）

### payload 带值已确认
使用：
- `/Users/fuwuqi/检测报告生成系统_X1/temp_x1/negative_pressure_project_payload.json`

其中真实带值：
- `settling_bacteria.result = 1`
- `surface_bacteria.result = 2`

### 已做过且未收口的方案（不要 reset 后又从头重复）
1. anchor + row_match_index 柔性命中
2. table/row 固定坐标写入
3. `_replace_table_cell_by_table_and_row(...)` 强制重建
4. `negative_pressure` 专用行级硬写 `_replace_negative_pressure_result_row(...)`

结论：
- 上述方案都已尝试
- 最终 `.filled.docx` 目标结果位仍未稳定命中

---

## 最新真实回归样本
重点看这些：
- `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/X1EXPORT_20260416144600.filled.docx`
- `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/X1EXPORT_20260416145042.filled.docx`
- `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/X1EXPORT_20260416150835.filled.docx`
- `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/X1EXPORT_20260416152146.filled.docx`

最新状态：
- `物体表面微生物` 目标结果位仍空
- `细菌浓度(沉降法)` 仍未拿到结果位命中铁证

---

## 当前代码事实
关键文件：
- `/Users/fuwuqi/检测报告生成系统_X1/adapters/template_fill.py`

当前已新增：
- `_replace_negative_pressure_result_row(document_xml, row_label, result_text, debug_notes=None)`

当前 `negative_pressure` 分支已经改成：
- `细菌浓度(沉降法)` / `细菌浓度（沉降法）` / `物体表面微生物`
  走专用硬写函数

---

## reset 后唯一正确方向
不要再继续盲改 cell 写法。

### 直接追这个链：
`build_template_filled_docx()` 内，`document_xml` 在以下阶段是否发生了“中间态已写入，但最终成品丢失/被覆盖”：

1. 进入 `negative_pressure` 分支前
2. 调用 `_replace_negative_pressure_result_row(...)` 后
3. 写入 zip 之前
4. 最终 `word/document.xml` 解包后

### 要验证的核心问题
1. `_replace_negative_pressure_result_row(...)` 执行后，内存里的 `document_xml` 是否已经包含 `1/2`
2. 如果包含，为什么最终 `.filled.docx` 里没保留
3. 是否存在：
   - 命中了错误的同名行/错误 table
   - 后续逻辑又覆盖回去了
   - debug 文件没落地，说明 debug 链本身也没真正打通

---

## reset 后建议第一动作（不要换）
在 `build_template_filled_docx()` 里，围绕 `negative_pressure` 两个目标行插入 **中间态断点输出/临时 dump**：
- 写入前 dump 一次目标 row
- `_replace_negative_pressure_result_row(...)` 后 dump 一次目标 row
- zip 写出前再 dump 一次

目标不是再猜，而是：

> **确认“值到底有没有进入内存中的最终 `document_xml`”。**

只要这步一清，下一刀就不会再空转。

---

## 相关文档
- `/Users/fuwuqi/检测报告生成系统_X1/docs/X1-negative_pressure-模板调整后新任务卡.md`
- `/Users/fuwuqi/检测报告生成系统_X1/docs/X1-当前工作总台账.md`

---

## 给 reset 后的你
别再回到“模板是不是 5-cell”“结果位是不是第 4 格”这些问题上了。
这些都已经确认过。

现在只查：
**写入是否真的进入最终生效链。**
