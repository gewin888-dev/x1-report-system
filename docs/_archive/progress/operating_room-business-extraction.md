# operating_room 业务提炼笔记（来自 T 页面逻辑）

## 来源
- `T1/static/record.js`
- 重点函数：
  - `selSurgeryRoomType(...)`
  - `selSurgeryAuxRoom(...)`
  - `updateRoomSummary(...)`

---

## 一、T 中已经明确存在的业务表达

### 1. 手术室对象不是单层对象
在 T 中，`operating_room` 至少包含以下业务分支：

- `手术室`
- `眼科手术室`
- `洁净辅房 / 辅房`

这说明 X 不能把 `operating_room` 简化成“只有名称 + 等级”的扁平对象。

---

### 2. 房型会决定后续输入链

#### 当选择：`手术室`
- 页面显示洁净等级选择
- 等级范围：
  - `Ⅰ级（百级）`
  - `Ⅱ级（千级）`
  - `Ⅲ级（万级）`
  - `Ⅳ级（十万级）`

#### 当选择：`眼科手术室`
- 也显示同样的等级选择

#### 当选择：`洁净辅房 / 辅房`
- 不直接显示洁净等级
- 先显示辅房名称选择
- 之后再显示辅房等级选择

这说明 `operating_room` 的页面逻辑本质上是一个分阶段对象。

---

### 3. 辅房链至少包含两层业务字段
从 `selSurgeryAuxRoom(...)` 可明确提炼出：

- `surgery_aux_room`
- `surgery_aux_clean_class`

并且：
- 先选辅房名称
- 再选辅房等级
- 之后才进入参数区

---

## 二、对 X 的直接启发

### 1. X 必须尊重这种分阶段业务表达
不能把 `operating_room` 粗暴简化成：
- 房间名称
- 洁净等级
- 依据
- 判定

至少应保留：
- `surgery_room_type`
- `surgery_aux_room`
- `surgery_aux_clean_class`

---

### 2. X 要继承业务逻辑，但不继承旧状态机制
T 中很多 `dataset` 清理、ready/source、summary 状态，是旧结构问题的结果；
但房型分支、辅房分支、等级分支本身是业务表达，X 应保留。

---

## 三、对 X 的建议最小字段集

### operating_room 最小业务字段集（第一版）
- `room_name`
- `type_id = operating_room`
- `surgery_room_type`
- `clean_class / level_name`
- `surgery_aux_room`
- `surgery_aux_clean_class`
- `basis`
- `judgement`
- `summary`

---

## 四、当前阶段建议

先在 X 中把 `operating_room` 做成：
1. 可切换房型
2. 可表达主房型 / 辅房型差异
3. 可输出最小 business context
4. 不复制 T 的旧脏状态字段

---

_创建时间：2026-04-14 19:38 GMT+8_
