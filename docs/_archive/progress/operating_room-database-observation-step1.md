# operating_room 数据库观察（第一轮）

## 目标
按既定目标继续推进 X，不提前大改数据库，但开始做对象级数据库支撑观察，为后续 `operating_room` 深接入做准备。

---

## 本轮观察结论

### 1. 当前不需要立刻大改标准数据库
原因：
- X 还在建立对象主链
- `operating_room` 目前仍处于业务表达接入阶段
- 现在更适合“边接对象边做数据库体检”，而不是先全面洗库

---

### 2. `operating_room` 在 T 的数据库侧是有基础支撑的
已确认文件：
- `static/standards_db.js`
- `static/standards_ranges.json`

已确认存在：
- `GB 50333-2013`
- `operating_room`
- `clean_function_room`

说明：手术室对象不是完全没数据库底座，X 可以先复用现有结构做对象接入。

---

### 3. 但 T 里仍有部分手术室/辅房逻辑带有前端映射补偿色彩
从 `record.js` 可见：
- `selSurgeryRoomType(...)`
- `selSurgeryAuxRoom(...)`
- `renderParamsForRoom(...)`

其中手术室洁净辅房链存在：
- `surgeryAuxRoomOptions`
- `surgeryAuxCleanClassOptions`
- `auxCleanMap`

这说明：
- 一部分业务逻辑已沉淀到数据库
- 另一部分仍在前端映射/补偿逻辑中

因此后续真正需要做的，不是盲目改库，而是：
1. 识别哪些规则已经能由数据库承接
2. 识别哪些规则仍是前端补偿
3. 再决定是否增量补库

---

### 4. 当前数据库观察上的一个信号
检索结果：
- `standards_db.js` 中存在：`particle_zone`、`bacteria_zone_control`
- `standards_ranges.json` 中未直接出现：`particle_zone`、`bacteria_zone_control`

说明：
- `standards_db.js` 与 `standards_ranges.json` 当前承担的角色并不完全一致
- 后续如果做 `operating_room` 深接入，需要进一步确认：
  - 哪些参数实际由 `standardRanges` 提供
  - 哪些仍是参数级/前端级映射

---

## 当前判断
对 X 当前阶段来说：
- **数据库现在不用立刻大改**
- **但必须持续做对象级数据库校核**
- `operating_room` 可以继续推进对象主链，同时顺手建立它的数据库支撑地图

---

## 下一步
1. 继续推进 `operating_room` 的 export payload 结构
2. 开始整理 `operating_room` 在 T 中的“前端业务逻辑”与“数据库支撑逻辑”边界
3. 为后续是否增量补库做依据，而不是拍脑袋改库

---

_更新时间：2026-04-14 20:01 GMT+8_
