# X1 第二批对象接入施工单 - negative_pressure

更新时间：2026-04-14 22:39 GMT+8
状态：待施工
优先级：P1

---

## 一、当前目标

为 `negative_pressure`（负压病房）建立 X1 接入蓝图，先明确业务边界与最小可施工方案。

---

## 二、业务边界

### 业务领域
- `hospital`
- 中文名称：`负压病房`

### 对象形态
- 复杂空间类
- 压差链驱动类
- 医院特殊对象类

### 当前业务特征（来自 T1）
来源：`/Users/fuwuqi/检测报告生成系统_T1/static/standards_db.js`

当前关键参数包括：
- 污染区换气次数
- 清洁区换气次数
- 排风口风速
- 高效过滤器检漏
- 静压差
- 气流流向
- 温度
- 湿度
- 噪声
- 照度
- 细菌浓度（沉降法）
- 物体表面微生物

### 当前判断
它不是普通洁净功能用房，也不是手术室分支。
它应该作为医院领域独立对象进入 X1。

---

## 三、canonical model 最小字段集（第一版建议）

```json
{
  "type_id": "negative_pressure",
  "type_name": "负压病房",
  "domain": "hospital",
  "room_name": "",
  "level_name": "无洁净等级要求",
  "clean_class": "无洁净等级要求",
  "basis": [],
  "judgement": [],
  "params": [],
  "summary": {},
  "context": {
    "negative_pressure_mode": "ward-pressure-driven"
  }
}
```

### 当前关键点
- 负压病房当前不以洁净等级为核心
- 更像是“压差/流向/区域换气”驱动对象

---

## 四、语义层设计（第一版建议）

### 当前建议
```json
{
  "domain": "hospital",
  "standard_code": "GB/T 35428-2017 + WS/T 368-2012",
  "object_type": "negative_pressure",
  "object_branch": "ward-pressure-driven",
  "level_raw": "无洁净等级要求",
  "level_semantic_key": "hospital.negative_pressure.no-clean-class",
  "semantic_note": "负压病房对象核心不在洁净等级，而在压差、气流流向、换气与感染控制要求。",
  "impacts": ["template_rule", "report_context", "pressure_chain"]
}
```

---

## 五、模板规则层设计（第一版建议）

### 当前建议
先走单规则：
```python
'hospital.negative_pressure': {
    'default': {
        'default': {
            'template_key': 'hospital/negative_pressure/default',
            'template_name': '负压病房',
        }
    }
}
```

### 当前理由
- 第一阶段不需要过度分裂分支
- 先把对象链立起来

---

## 六、模板资源层设计（第一版建议）

### 当前模板线索
已确认医院洁净部目录存在：
- `负压病房检测报告模板.docx`

### 第一版建议
统一映射到：
- `医院洁净部/负压病房检测报告模板.docx`

---

## 七、前台录入设计（第一版建议）

### 第一版最小前台字段
- 对象名称
- 检测依据
- 判定标准
- 结果状态

### 前台业务区建议
新增：
- `负压病房业务字段`
- 说明当前对象以压差/流向链为核心

第一阶段不必先把全部压差点位前台复杂结构做完，先跑主链。

---

## 八、验收标准

1. 模型层存在 `negative_pressure`
2. 前台能切换到 `negative_pressure`
3. 规则层能命中 `hospital/negative_pressure/default`
4. 资源层能命中 `负压病房检测报告模板.docx`
5. 前台导出阶段能进入 `template-bound-ready`

---

## 九、当前结论

`negative_pressure` 是医院领域里当前最容易被遗漏、但业务上不能缺位的正式对象。
它适合在 `gmp_workshop` 之后尽快接入。
