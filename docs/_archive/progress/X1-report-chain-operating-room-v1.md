# X1 报告主链设计（operating_room 第一版）

## 核心原则
X 的主线不是复用 T 的报告实现，而是建立自己的独立链：

前台录入数据
→ canonical model
→ 模板规则层
→ 报告适配上下文
→ 报告生成

---

## 当前第一对象
- `operating_room`

原因：
- 比设备类更复杂
- 足以检验对象分支、模板规则、业务上下文、报告适配
- 又没有 bsl 那么重

---

## 一、X 自己的模板规则层要解决什么

### 输入
来自 canonical model 的最小事实：
- `domain`
- `type_id`
- `clean_class / level_name`
- `context.surgery_room_type`
- `context.surgery_aux_room`
- `context.surgery_aux_clean_class`

### 输出
- `template_family`
- `template_variant`
- `template_key`
- `report_context_mode`

### 注意
这些输出必须由业务事实推导，不能靠 `ready/source/live/saved` 之类中间态。

---

## 二、operating_room 第一版规则建议

### 主手术室链
当：
- `type_id = operating_room`
- `surgery_room_type in ['手术室', '眼科手术室']`

输出：
- `template_family = hospital.operating_room`
- `template_variant = main-room`
- `template_key = operating_room:<level>`
- `report_context_mode = operating-room-main`

### 洁净辅房链
当：
- `type_id = operating_room`
- `surgery_room_type in ['洁净辅房', '辅房']`

输出：
- `template_family = hospital.operating_room`
- `template_variant = auxiliary-room`
- `template_key = operating_room:aux:<aux_clean_class>`
- `report_context_mode = operating-room-aux`

---

## 三、报告适配层要做什么

### 输入
- canonical model
- 模板规则结果

### 输出
结构化报告上下文，例如：
- `project_context`
- `room_context`
- `template_context`
- `report_sections`

目标：
- 不让模板层直接面对杂乱录入值
- 由适配层先把上下文整理干净

---

## 四、当前阶段不要做什么

- 不要把 T 的 select_template / fill_template 直接搬过来
- 不要为了快而让 X 重新长出多态体系
- 不要把页面控件值直接当最终模板输入

---

## 五、下一步实施建议

1. 在 X 中建立 `template_rules.py` 或同等结构
2. 先只实现 `operating_room` 的规则解析
3. 建立 `report_context_builder.py` 或同等结构
4. 先让 `operating_room` 走通：
   - 前台录入
   - canonical model
   - template rule resolve
   - report context build
   - 样板报告输出

---

_创建时间：2026-04-14 20:32 GMT+8_
