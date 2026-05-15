# X3 后端判定引擎状态说明（当前版）

**⚠️ 本文件已按 2026-05-02 晚口径收骨架，仅保留当前真实状态与仍未彻底分层的问题。5 月 2 日之前的“缺口分析”历史展开已删除。**

更新时间：2026-05-03 00:01 GMT+8
结论级别：**✅ 判定引擎对象覆盖已补齐，转入回归维护态**

---

## 一、当前结论

当前真实状态：
- `judgement_engine.py` 已完成并提供统一入口 `judge_room`
- 后端判定已接入导出链路，并强制覆盖前端传入的 `summary.result_state`
- `laminar_hood` 判定函数已确认存在并已完成专项回归 **6/6 通过**
- 当前不存在“对象级后端判定缺失”这一主线缺口

---

## 二、当前已确认事实

### 代码事实
- `judgement_engine.py` 提供统一判定入口
- `app_x1.py` 在导出链路中调用后端判定并回写 `room_summary`
- 已记录 `judgement_engine` / `judgement_overridden` 等状态字段

### 覆盖事实
已覆盖对象：
- `operating_room`
- `negative_pressure`
- `clean_function_room`
- `gmp_workshop`
- `veterinary_gmp_workshop`
- `electronics_workshop`
- `food_workshop`
- `animal_room`
- `bsc`
- `clean_bench`
- `ivc`
- `pass_box`
- `bsl`
- `laminar_hood`

### 当前判断
- “后端判定缺失”已不是当前主线
- 当前更需要防止的是：**文档仍停留在旧阶段，导致对真实状态误判**

---

## 三、当前唯一仍值得保留的问题

### 导出通过 / 后端判定通过 / 真人验收通过 仍未彻底字段化分层

当前已部分完成：
- 后端判定状态可通过 `judgement_engine` 字段标记
- 是否覆盖前端输入可通过 `judgement_overridden` 字段标记

当前仍未彻底完成：
- 真人验收状态尚未独立字段化
- 台账层仍需要持续区分：
  1. 导出链路通过
  2. 后端判定通过
  3. 真人验收通过

这不是“判定引擎缺口”，而是**状态分层表达问题**。

---

## 四、使用说明

- 如需判断“判定引擎是否已完成”，直接以本文件为准
- 如需判断“对象当前处于维护态 / 尾项 / 挂起”，改读：
  - `docs/X1_当前真实状态_单页总览_2026-05-02.md`
  - `docs/X1_统一思想开发计划未完成项执行清单_2026-05-03.md`
- 如需判断“具体测试通过情况”，改读：
  - `docs/TEST_LEDGER.md`
  - `docs/X1_真实全量测试记录台账_2026-05-03.md`
- 如需判断“前台浏览器级真验是否已拿到”，改读：
  - `docs/X1_前台回填链验收摘要_2026-05-03.md`

---

## 五、历史残留说明（保留最小必要）

本文件曾长期承担“缺口分析”角色，旧版里包含大量阶段性推演、已完成缺口、已失效优先级与过时下一步建议。

截至 2026-05-03，当前有效结论已经收敛为：
- 判定引擎对象覆盖已补齐
- `laminar_hood` 不再是缺口
- 当前真正剩余的是**状态分层表达问题**，而不是对象级判定缺失

因此：
- 旧版中凡涉及“尚缺对象判定函数”“优先补 laminar_hood”“对象级判定未接入主链”等表述，均应视为**历史口径**
- 如历史章节与本文件前四部分冲突，**以前四部分为准**

---

### ~~风险~~
- ~~标准存在 ≠ 判定真正生效~~
- ~~容易出现"看起来很完整，实际上没真判"的假完成~~

### **【更新】风险已解除**
标准库已闭环接入判定引擎，判定结果强制覆盖前端传入值。

### 优先级
~~**P0**~~ → **✅ 已完成**

---

## 3.3 缺口三：~~对象级规则没有统一抽象~~ ✅ 基本完成

### ~~现状~~
~~不同对象的参数结构并不完全一样，例如：~~
- ~~`operating_room`：风速 / 换气次数 / 压差 / 温湿度 / 粒子 / 沉降菌~~
- ~~`negative_pressure`：负压、送排风、压差、温湿度、细菌~~
- ~~`bsc`：下降气流、流入气流、检漏、噪声、照度~~
- ~~`pass_box`：联锁、检漏、粒子、换气次数~~
- ~~`electronics_workshop`：ISO 等级下风速或换气次数、压差、粒子等~~

### ~~当前问题~~
~~虽然模板规则、语义规则、报告上下文规则已经分别存在，但**"判定规则层"还没有被系统性抽象出来**。~~

### **【更新】实际状态（2026-05-01 23:42）：✅ 基本完成**
- 已实现 12 个对象专项判定函数
- 通用判定逻辑抽象为 `_judge_by_rules` 函数
- 参数键映射通过 `PARAM_KEY_MAP` 统一处理
- 范围解析通过 `_parse_range` 统一处理
- 判定逻辑通过 `_within` 统一处理

### 唯一缺口
**`laminar_hood`（层流罩）判定函数已补齐并通过专项回归**

### 优先级
~~**P1**~~ → **✅ 已完成，转入回归维护态**

---

## 3.4 缺口四：台账里"导出通过"和"业务判定通过"还没彻底分层

### 现状
目前我们已经在台账里补充了说明，但系统层面还没有形成明确字段区分：
- 导出链路状态
- 后端判定状态
- 真人验收状态

### **【更新】实际状态（2026-05-01 23:42）：部分完成**
- 后端判定状态已通过 `judgement_engine` 字段标记
- `judgement_overridden` 字段标记是否覆盖前端传入值
- 但"真人验收状态"仍未独立字段化

### 风险
管理层看到"48/48 通过"，容易误解为"业务已完全可发布"。

### 优先级
**P1**

---

## 四、按对象域拆分的缺口清单

**【更新】以下章节保留作为历史记录，实际状态见上方更新。**

## 4.1 医院洁净部
覆盖对象：
- `operating_room` ✅ 已完成
- `clean_function_room` ✅ 已完成
- `negative_pressure` ✅ 已完成
- `auxiliary_room` ✅ 已完成（包含在 operating_room 判定中）
- `eye_operating_room` ⚠️ 未单独实现（可能包含在 operating_room 中）

### ~~当前状态~~
- ~~模板 / 导出：大体可用~~
- ~~后端自动判定：**缺失**~~

### **【更新】当前状态（2026-05-01 23:42）：✅ 已完成**
- 模板 / 导出：已完成
- 后端自动判定：✅ 已完成

### ~~特别风险点~~
- ~~手术室不同等级参数差异大~~
- ~~辅房与主房判定口径不同~~
- ~~负压病房存在压差方向性问题，不能只看数值大小~~

### **【更新】风险已解除**
- 手术室等级通过 `_normalize_operating_room_level` 处理
- 辅房与主房通过 `is_aux` 标志分别处理
- 负压病房已有专项判定函数

### ~~建议动作~~
1. ~~先做 `operating_room` 全等级~~
2. ~~再做 `negative_pressure`~~
3. ~~再做 `clean_function_room`~~
4. ~~最后补 `auxiliary_room` / `eye_operating_room`~~

### **【更新】建议动作：无，已完成**

---

## 4.2 生物安全
覆盖对象：
- `bsl` ✅ 已完成
- `animal_room` ✅ 已完成
- `bsc` ✅ 已完成
- `clean_bench` ✅ 已完成
- `ivc` ✅ 已完成

### ~~当前状态~~
- ~~导出与模板链路已通~~
- ~~自动判定仍缺失~~

### **【更新】当前状态（2026-05-01 23:42）：✅ 已完成**
- 导出与模板链路：已完成
- 后端自动判定：✅ 已完成

### ~~特别风险点~~
- ~~动物房分普通/屏障/隔离，每种环境参数不同~~
- ~~屏障环境下还有主房间 vs 洁净辅房的区分~~
- ~~生物安全柜、洁净工作台、IVC 是设备，不是房间，判定口径可能不同~~

### **【更新】风险已解除**
- 动物房通过 `judge_animal_room` 处理，支持普通/屏障/隔离/辅房
- 设备类对象已有专项判定函数（bsc、clean_bench、ivc）

---

## 4.3 制药工业
覆盖对象：
- `gmp_workshop` ✅ 已完成
- `veterinary_gmp_workshop` ✅ 已完成
- `pass_box` ✅ 已完成
- `laminar_hood` ✅ 已完成

### ~~当前状态~~
- ~~导出链路已通~~
- ~~自动判定缺失~~

### **【更新】当前状态（2026-05-01 23:42）：部分完成**
- 导出链路：已完成
- 后端自动判定：✅ gmp_workshop、veterinary_gmp_workshop、pass_box 已完成
- `laminar_hood` 判定函数已补齐，无剩余对象级判定缺口。

---

## 4.4 精密制造
覆盖对象：
- `electronics_workshop` ✅ 已完成

### ~~当前状态~~
- ~~导出链路已通~~
- ~~自动判定缺失~~

### **【更新】当前状态（2026-05-01 23:42）：✅ 已完成**
- 导出链路：已完成
- 后端自动判定：✅ 已完成

---

## 4.5 食品工业
覆盖对象：
- `food_workshop` ✅ 已完成

### ~~当前状态~~
- ~~导出链路已通~~
- ~~自动判定缺失~~

### **【更新】当前状态（2026-05-01 23:42）：✅ 已完成**
- 导出链路：已完成
- 后端自动判定：✅ 已完成

---

## 五、下一步建议

### ~~原建议（已过时）~~
1. ~~先建立统一判定引擎框架~~
2. ~~优先实现 `operating_room` 作为样板~~
3. ~~逐步覆盖其他对象~~
4. ~~补充测试用例~~

### **【更新】下一步建议（2026-05-01 23:42）**
1. **补齐 `laminar_hood` 判定函数**（P1）
2. 验证判定引擎在真实场景下的准确性
3. 补充边界值测试用例
4. 更新台账《X3_38业务对象测试台账.md》，标记判定引擎状态
5. 考虑是否需要独立"真人验收状态"字段

---

## 六、附录：判定引擎实现清单（2026-05-01 23:42）

| 对象 | 判定函数 | 标准 | 测试文件 | 状态 |
|---|---|---|---|---|
| operating_room | `judge_operating_room` | GB 50333-2013 | test_operating_room_judgement.py | ✅ |
| negative_pressure | `judge_negative_pressure` | GB/T 35428-2017 | test_negative_pressure_judgement.py | ✅ |
| clean_function_room | `judge_clean_function_room` | WS 310.1-2016 | test_clean_function_room_judgement.py | ✅ |
| gmp_workshop | `judge_gmp_workshop` | GB 50457-2019 | test_gmp_judgement.py | ✅ |
| veterinary_gmp_workshop | `judge_gmp_workshop` | GB 50457-2019 | test_gmp_judgement.py | ✅ |
| electronics_workshop | `judge_electronics_workshop` | GB 50472-2008 | test_electronics_judgement.py | ✅ |
| food_workshop | `judge_food_workshop` | GB 50687-2011 | test_food_judgement.py | ✅ |
| animal_room | `judge_animal_room` | GB 14925-2023 | test_animal_room_judgement.py | ✅ |
| bsc | `judge_bsc` | GB 41918-2022 | test_bsc_judgement.py | ✅ |
| clean_bench | `judge_clean_bench` | JG/T 292-2010 | test_equipment_judgement.py | ✅ |
| ivc | `judge_ivc` | DB32/T972-2006 | test_equipment_judgement.py | ✅ |
| pass_box | `judge_pass_box` | JG/T 382-2012 | test_pass_box_judgement.py | ✅ |
| bsl | `judge_bsl` | GB 50346-2011 | test_bsl_judgement.py | ✅ |
| laminar_hood | `judge_laminar_hood` | GB 50591-2010 + 项目内控规则 | test_laminar_hood_judgement.py | ✅ |

---

**文档结束**

## 七、判定引擎与判定标准对应关系（2026-05-01 23:56）

| 对象 type_id | 判定函数 | 适用标准 | 备注 |
|---|---|---|---|
| `operating_room` | `judge_operating_room` | GB 50333-2013 | 主手术室 + 辅房分支处理 |
| `negative_pressure` | `judge_negative_pressure` | GB/T 35428-2017 | |
| `clean_function_room` | `judge_clean_function_room` | WS 310.1-2016（主）+ 国家卫生健康委办公厅（补充） | 双标准合并，WS 310.1 优先 |
| `gmp_workshop` | `judge_gmp_workshop` | GB 50457-2019 | |
| `veterinary_gmp_workshop` | `judge_gmp_workshop`（veterinary=True） | GB 50457-2019 | 与 gmp 共用函数，不同规则集 |
| `electronics_workshop` | `judge_electronics_workshop` | GB 50472-2008 | 按 ISO 等级分发 |
| `food_workshop` | `judge_food_workshop` | GB 50687-2011 | |
| `animal_room` | `judge_animal_room` | GB 14925-2023 | 普通/屏障/隔离/洁净辅房四分支 |
| `bsc` | `judge_bsc` | GB 41918-2022 | |
| `clean_bench` | `judge_clean_bench` | JG/T 292-2010 | |
| `ivc` | `judge_ivc` | DB32/T972-2006 | |
| `pass_box` | `judge_pass_box` | JG/T 382-2012 | 按传递窗模式分发 |
| `bsl` | `judge_bsl` | GB 50346-2011 | 按 BSL 等级映射到 ISO 等级 |
| `laminar_hood` | `judge_laminar_hood` | GB 50591-2010 + 项目内控规则 | 设备类默认规则，已完成专项回归 |

**统一入口：** `judge_room(project, room)` → 按 `type_id` 分发  
**接入位置：** `app_x1.py` 第1082行，后端结果强制覆盖前端传入的 `result_state`
