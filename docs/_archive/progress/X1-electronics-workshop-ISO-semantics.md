# electronics_workshop ISO 语义层

更新时间：2026-04-29 00:30 GMT+8

---

## 一、ISO 等级语义特征

### 1. 电子行业 ISO 等级体系

electronics_workshop 使用 **ISO 5 ~ ISO 9** 五级洁净等级体系，遵循 GB 50472-2008《电子工业洁净厂房设计规范》。

**关键语义特征：**
- ISO 5：**单向流洁净室**（使用 `wind_speed` 截面风速）
- ISO 6~9：**乱流洁净室**（使用 `airchange` 换气次数）

这是电子行业与其他行业（医院、制药、食品）的核心区别：
- 医院：Ⅰ级（百级）~ Ⅳ级（十万级）
- 制药：A级 ~ D级
- 食品：Ⅰ级（百级）~ Ⅳ级（三十万级）
- 生物安全：ISO-5 ~ ISO-9（带连字符，与电子行业 ISO 5 ~ ISO 9 不同）

---

## 二、参数模板结构

### ISO 5（单向流）

```javascript
{
  key: 'wind_speed',           // 截面风速（单向流特征参数）
  key: 'pressure',             // 静压差
  key: 'hepa_leak',            // 送风高效过滤器检漏
  key: 'particle',             // 洁净度级别
  key: 'temperature',          // 温度
  key: 'humidity',             // 相对湿度
  key: 'noise',                // 噪声
  key: 'illumination_main',    // 主房间照度
  key: 'illumination_aux',     // 辅房间照度
  key: 'airflow_pattern'       // 气流流型
}
```

### ISO 6 ~ ISO 9（乱流）

```javascript
{
  key: 'airchange',            // 换气次数（乱流特征参数）
  key: 'pressure',             // 静压差
  key: 'hepa_leak',            // 送风高效过滤器检漏
  key: 'particle',             // 洁净度级别
  key: 'temperature',          // 温度
  key: 'humidity',             // 相对湿度
  key: 'noise',                // 噪声
  key: 'illumination_main',    // 主房间照度
  key: 'illumination_aux',     // 辅房间照度
  key: 'airflow_pattern'       // 气流流型
}
```

---

## 三、标准范围映射

### GB 50472-2008（电子工业专用标准）

| ISO 等级 | particle | wind_speed / airchange | pressure | noise | temperature | humidity | illumination_main | illumination_aux |
|---------|----------|----------------------|----------|-------|-------------|----------|-------------------|------------------|
| ISO 5   | ≥0.5μm≤3520, ≥5μm≤29 | 0.20～0.45 m/s | ≥5 Pa | ≤65 dB(A) | 22～24 ℃ | 45～65 % | 300～500 lx | 200～300 lx |
| ISO 6   | ≥0.5μm≤35200, ≥5μm≤293 | 50～60 次/h | ≥5 Pa | ≤60 dB(A) | 21～25 ℃ | 45～65 % | 300～500 lx | 200～300 lx |
| ISO 7   | ≥0.5μm≤352000, ≥5μm≤2930 | 15～25 次/h | ≥5 Pa | ≤60 dB(A) | 22～26 ℃ | 45～65 % | 300～500 lx | 200～300 lx |
| ISO 8   | ≥0.5μm≤3520000, ≥5μm≤29300 | 10～15 次/h | ≥5 Pa | ≤60 dB(A) | 22～26 ℃ | 45～70 % | 300～500 lx | 200～300 lx |
| ISO 9   | ≥0.5μm≤35200000, ≥5μm≤293000 | 10～15 次/h | ≥5 Pa | ≤60 dB(A) | 22～26 ℃ | 45～70 % | 300～500 lx | 200～300 lx |

### GB 50073-2013（通用洁净厂房标准）

仅提供 particle 和 pressure 的通用范围，作为 GB 50472-2008 的补充判定标准：

| ISO 等级 | particle | pressure |
|---------|----------|----------|
| ISO 5   | ≥0.5μm≤3520, ≥5μm≤29 | ≥5 Pa |
| ISO 6   | ≥0.5μm≤35200, ≥5μm≤293 | ≥5 Pa |
| ISO 7   | ≥0.5μm≤352000, ≥5μm≤2930 | ≥5 Pa |
| ISO 8   | ≥0.5μm≤3520000, ≥5μm≤29300 | ≥5 Pa |
| ISO 9   | ≥0.5μm≤35200000, ≥5μm≤293000 | ≥5 Pa |

---

## 四、与其他行业的语义区别

### 1. 与生物安全（bsl）的区别

| 维度 | electronics_workshop | bsl |
|-----|---------------------|-----|
| 等级表达 | ISO 5 ~ ISO 9（无连字符） | ISO-5 ~ ISO-9（带连字符） |
| 等级语义 | 洁净等级 | 洁净等级（与 BSL 等级分离） |
| 领域标准 | GB 50472-2008 | GB 50346-2011 |
| 特征参数 | illumination_main / illumination_aux | 无照度分区 |

**关键语义说明：**
- 生物安全对象中，BSL 等级（BSL-1 ~ BSL-4）与洁净等级（ISO-5 ~ ISO-9）不是同一概念
- electronics_workshop 的 ISO 等级是纯洁净等级，不涉及生物安全等级

### 2. 与制药（gmp_workshop）的区别

| 维度 | electronics_workshop | gmp_workshop |
|-----|---------------------|--------------|
| 等级表达 | ISO 5 ~ ISO 9 | A级 ~ D级 |
| 领域标准 | GB 50472-2008 | GB 50457-2019 |
| 照度参数 | illumination_main / illumination_aux | illumination（单一） |
| 温湿度范围 | 较窄（22～26℃） | 较宽（18～26℃） |

### 3. 与食品（food_workshop）的区别

| 维度 | electronics_workshop | food_workshop |
|-----|---------------------|---------------|
| 等级表达 | ISO 5 ~ ISO 9 | Ⅰ级（百级）~ Ⅳ级（三十万级） |
| 领域标准 | GB 50472-2008 | GB 14881-2013 |
| 特征参数 | 无微生物参数 | settling / floating（沉降菌/浮游菌） |

---

## 五、前端交互特征

### 1. 等级选择器

```javascript
cleanClassOptions: {
    electronics: ['ISO 5', 'ISO 6', 'ISO 7', 'ISO 8', 'ISO 9']
}
```

### 2. 参数动态切换

- 用户选择 ISO 5 时，前端显示 `wind_speed`（截面风速）
- 用户选择 ISO 6~9 时，前端显示 `airchange`（换气次数）
- 这个切换逻辑由 `levelParams` 结构自动承接

### 3. 照度分区

electronics_workshop 特有的照度分区：
- `illumination_main`：主房间照度（生产区）
- `illumination_aux`：辅房间照度（辅助区）

这与医院手术室的 `illumination` / `illumination_aux` 类似，但语义不同：
- 医院：手术区 / 周边区
- 电子：主房间 / 辅房间

---

## 六、当前接入状态

### 已完成

1. ✅ standards_db.js 中 ISO 5~9 的完整参数模板定义
2. ✅ standards_ranges.json 中 GB 50472-2008 和 GB 50073-2013 的完整范围映射
3. ✅ cleanClassOptions 中 electronics 等级选项定义
4. ✅ levelParams 中 ISO 5~9 的参数动态切换结构

### 待接入

1. ❌ 后端 Python 对象模型（`models/electronics_workshop.py`）
2. ❌ 后端路由与 API 端点（`routes/electronics_workshop.py`）
3. ❌ Word 模板文件（`templates/electronics_workshop.docx`）
4. ❌ 前端 record.js 中 electronics_workshop 的完整业务逻辑
5. ❌ 真实 `.filled.docx` 导出验收

---

## 七、下一步接入计划

按照 X1 统一对象接入流程：

1. **后端对象模型**：创建 `models/electronics_workshop.py`，继承 `BaseDetectionObject`
2. **后端路由**：创建 `routes/electronics_workshop.py`，实现 CRUD + 导出接口
3. **Word 模板**：创建 `templates/electronics_workshop.docx`，定义 ISO 5~9 的报告结构
4. **前端业务逻辑**：补全 record.js 中 electronics_workshop 的参数计算、范围更新、状态同步
5. **真实数据验收**：使用真实电子车间检测数据，完成 `.filled.docx` 导出验收

---

## 八、语义层总结

electronics_workshop 的 ISO 语义层核心要点：

1. **ISO 等级不是普通字符串**：ISO 5 与 ISO 6~9 的参数结构不同（wind_speed vs airchange）
2. **行业独立性**：不能与 gmp_workshop / food_workshop 混做一个通用对象
3. **标准双轨制**：GB 50472-2008（行业专用）+ GB 50073-2013（通用补充）
4. **照度分区语义**：illumination_main / illumination_aux 是电子行业特有的空间分区表达
5. **与生物安全的区别**：ISO 5（无连字符）≠ ISO-5（带连字符），前者是电子行业，后者是生物安全

---

_本文档作为 electronics_workshop 接入 X1 主链的语义层基础，后续对象模型、模板设计、前端逻辑均应参考本文档的语义定义。_
