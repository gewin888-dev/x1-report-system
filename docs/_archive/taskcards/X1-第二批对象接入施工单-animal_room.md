# X1 第二批对象接入施工单 - animal_room

更新时间：2026-04-14 22:39 GMT+8
状态：待施工
优先级：P1

---

## 一、当前目标

为 `animal_room`（动物房）建立 X1 接入蓝图，避免把它误当成普通设备类或普通实验室对象。

---

## 二、业务边界

### 业务领域
- `biosafety`
- 中文名称：`动物房`

### 对象形态
- 复杂空间类
- 上下文驱动类
- 环境分支驱动类

### 当前业务特征（来自 T1）
来源：`/Users/fuwuqi/检测报告生成系统_T1/static/standards_db.js`

当前核心上下文包括：
- 环境选择：
  - 普通环境
  - 屏障环境
  - 隔离环境
- 房间类别：
  - 主房间
  - 洁净辅房
- 洁净辅房名称：
  - 洁物储存室
  - 灭菌后室/区
  - 洁净走廊
  - 污物走廊
  - 缓冲间
  - 二更
  - 清洗消毒室
  - 一更

### 当前判断
`animal_room` 本质上是：
- 环境等级链
- 房间类别链
- 辅房链
- 参数差异链

它比 `bsl` 更复杂，不能直接按普通实验室对象复制。

---

## 三、canonical model 最小字段集（第一版建议）

```json
{
  "type_id": "animal_room",
  "type_name": "动物房",
  "domain": "biosafety",
  "room_name": "",
  "level_name": "屏障环境",
  "clean_class": "屏障环境",
  "basis": [],
  "judgement": [],
  "params": [],
  "summary": {},
  "context": {
    "animal_environment": "屏障环境",
    "barrier_room_class": "主房间",
    "barrier_aux_room": "",
    "animal_context_mode": "environment-driven"
  }
}
```

### 当前最小关键字段
- `animal_environment`
- `barrier_room_class`
- `barrier_aux_room`
- `animal_context_mode`

---

## 四、语义层设计（第一版建议）

### 当前建议
```json
{
  "domain": "biosafety",
  "standard_code": "GB 14925-2023",
  "object_type": "animal_room",
  "object_branch": "屏障环境/主房间",
  "level_raw": "屏障环境",
  "level_semantic_key": "biosafety.animal_room.environment.屏障环境",
  "semantic_note": "动物房的环境表达需结合普通/屏障/隔离环境与房间类别共同理解。",
  "impacts": ["template_rule", "report_context", "parameter_profile"]
}
```

---

## 五、模板规则层设计（第一版建议）

### 当前建议
第一阶段先按“环境选择”驱动，不急于把主房间/辅房全部拆开：
```python
'biosafety.animal_room': {
    'environment-default': {
        '普通环境': {...},
        '屏障环境': {...},
        '隔离环境': {...},
    }
}
```

后续再叠加：
- 主房间 / 洁净辅房
- 辅房名称分支

---

## 六、模板资源层设计（第一版建议）

### 当前模板线索
已确认生物安全目录存在：
- `动物房检测报告模板.docx`

### 第一版建议
统一先映射到：
- `生物安全/动物房检测报告模板.docx`

---

## 七、前台录入设计（第一版建议）

### 最小前台业务区
新增：
- `动物房业务字段`
- 环境选择
- 房间类别
- 辅房名称

### 第一阶段目标
先跑：
- 环境选择
- 房间类别
- 辅房名称
- 进入 draft / rule / resource / export stage

先不急着把所有参数细枝末节一次铺完。

---

## 八、验收标准

1. 模型层存在 `animal_room`
2. 前台可切换到 `animal_room`
3. 可录入：
   - 环境选择
   - 房间类别
   - 辅房名称
4. 规则层能命中动物房模板规则
5. 资源层能命中 `动物房检测报告模板.docx`
6. 前台导出阶段能进入 `template-bound-ready`

---

## 九、当前结论

`animal_room` 是第二批里复杂度最高的对象之一。
建议放在 `gmp_workshop`、`negative_pressure` 之后再进正式编码，但施工蓝图必须先立起来。
