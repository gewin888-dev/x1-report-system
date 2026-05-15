# operating_room 业务规则提炼（第三步）

## 本轮目标
继续按既定目标推进 `operating_room`，把 T 中真实存在的业务规则继续抽出来，但仍然不复制 T 的旧状态脏机制。

---

## 本轮新增提炼

### 1. 洁净辅房等级不应简单套用主手术室等级
从 T 的 `selSurgeryAuxCleanClass(...)` 与 `renderParamsForRoom(...)` 可确认：

洁净辅房链并不是简单的：
- 房型 = 辅房
- 等级 = 万级/十万级

而是存在更细的业务规则：
- `Ⅰ级（局部5级其他6级）`
- `Ⅱ级（7级）`
- `Ⅲ级（8级）`
- `Ⅳ级（8.5级）`

说明：
- 辅房链有自己的洁净等级体系
- 该体系与主手术室 `Ⅰ/Ⅱ/Ⅲ/Ⅳ级（百/千/万/十万级）` 不是同一套页面表达

---

### 2. 辅房等级会触发参数覆盖规则
T 中实际存在的覆盖方向包括：
- `particle` 的 inputType / range 覆盖
- `bacteria` 的 inputType / range 覆盖
- I级场景下分为局部 / 其他区域

这说明：
`operating_room` 的辅房链不仅影响显示等级，还影响后续参数结构与判定表达。

---

## 本轮对 X 的处理

### 已纳入 X 注册层
文件：`static/x-model.js`

新增：
- `surgeryAuxCleanClassOptions` 改为更贴近 T 的四档：
  - `Ⅰ级（局部5级其他6级）`
  - `Ⅱ级（7级）`
  - `Ⅲ级（8级）`
  - `Ⅳ级（8.5级）`
- `surgeryAuxCleanMap`
  - 用于保存从 T 提炼出的辅房等级覆盖规则骨架

说明：
开始把“辅房等级规则”从页面控制器进一步收向对象注册/配置层。

---

### 已纳入 X export payload
文件：`app_x1.py`

当 `type_id = operating_room` 且存在 `surgery_aux_clean_class` 时：
- `business_context` 中新增：
  - `aux_clean_rule.source = t-business-logic-extracted`
  - `aux_clean_rule.clean_override_key = 当前辅房等级`

说明：
X 已开始承认：辅房等级不仅是显示值，也是后续参数/规则分支的线索。

---

## 当前判断
这一步仍然是“业务规则提炼期”，不是正式参数链接入期；
但方向已经从“手术室字段接入”推进到“手术室业务规则接入”。

---

## 下一步
1. 继续提炼 `operating_room` 中哪些参数覆盖规则值得进入 adapter/config 层
2. 避免把这些规则重新塞回工作区控制器
3. 为后续真正做参数链/导出链扩展准备结构位置

---

_更新时间：2026-04-14 20:13 GMT+8_
