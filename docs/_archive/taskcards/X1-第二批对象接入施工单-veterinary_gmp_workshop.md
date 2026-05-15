# X1-第二批对象接入施工单-veterinary_gmp_workshop

更新时间：2026-04-20 22:59 GMT+8
对象：`veterinary_gmp_workshop`
领域：制药（兽药）
优先级：P2
状态：已完成约90% / 可进入下一阶段 / 剩轻量展示尾项待后续联调收口

---

## 1. 当前目标

将 `veterinary_gmp_workshop` 从“已完成主链接入”继续推进到：
- 完成正文结果表真实落格核验
- 修正与真实 Word 模板不一致的取值来源与落格坐标
- 形成 A / B / C / D 四等级最小回归闭环
- 为后续对象级首轮收口做准备

---

## 2. 业务边界

`veterinary_gmp_workshop` 属于**兽药 GMP 车间**，不能直接等同普通 `gmp_workshop`。

当前已知必须独立对待的原因：
- 判定标准链不同，已涉及：
  - `农业农村部令2020年第3号`
  - `农业农村部公告第389号`
  - `农业农村部公告第292号`
- 虽然部分环境参数、粒子/微生物检测方法与普通 GMP 有交叉，
  但对象身份、标准归属、后续模板口径都必须独立。

因此当前原则明确：
> `veterinary_gmp_workshop` 不是 `gmp_workshop` 的别名，也不是简单复制一份普通 GMP 模板就算完成。

---

## 3. 当前已确认底座

### 3.1 标准库/模型底座
已确认 `static/standards_db.js` 中已存在：
- `id = 'veterinary_gmp_workshop'`
- 中文名：`兽药车间`
- 默认依据 / 判定依据 已单列
- 已具备基础参数链：
  - 换气次数
  - 静压差
  - 高效过滤器检漏
  - 洁净度级别
  - 温度
  - 相对湿度
  - 噪声
  - 主要工作室照度
  - 辅房照度
  - 沉降菌
  - 浮游菌
  - 自净时间
  - 气流流型
- 已具备 A / B / C / D 等级化 `levelParams`

### 3.2 范围库底座
已确认 `static/standards_ranges.json` 中已存在多处 `veterinary_gmp_workshop` 映射节点。

### 3.3 前端/记录链线索
已确认：
- `static/record.js` 中已有 `typeId === 'veterinary_gmp_workshop'` 的专门处理线索；
- 说明前端记录链不是完全空白，已经存在一定业务分支痕迹。

### 3.4 本轮已完成的主链接入（2026-04-17 06:54）
本轮已直接按 `gmp_workshop` 的成熟路径，把兽药车间的 5 层底座补到主链：

1. **模型层**
   - `static/x-model.js` 已新增：
     - `X1_OBJECT_TEMPLATES.veterinary_gmp_workshop`
     - `X1_OBJECT_REGISTRY.veterinary_gmp_workshop`
   - 已补：
     - `type_id`
     - `type_name`
     - `basis / judgement`
     - `summary`
     - `context.gmp_grade`
     - `context.pharma_context_variant = 'veterinary-gmp'`

2. **前台层**
   - `static/x-sample-workspace.js` 已新增 `兽药车间` 按钮入口；
   - 已直接复用 GMP 等级配置面板，避免重复造轮子。

3. **语义层**
   - `clean_class_semantics.py` 已新增：
     - `pharma.veterinary_gmp_workshop.grade.<grade>`
   - 已明确其标准语义为兽药独立标准链，不再混入普通 GMP 语义。

4. **规则层**
   - `template_rules.py` 已新增：
     - `pharma.veterinary_gmp_workshop`
     - A / B / C / D 四等级 `template_key`
   - 当前 `report_context_mode` 已独立为：
     - `pharma-veterinary-gmp-grade`

5. **资源层**
   - `template_resources.py` 已新增四等级模板资源映射：
     - A级 → `/Users/fuwuqi/公司资料/检测部/检测报告模板/制药工业/兽药车间A级检测报告模版.docx`
     - B/C/D级 → `/Users/fuwuqi/公司资料/检测部/检测报告模板/制药工业/兽药车间检测报告模板.docx`
   - 已实测 `template_found = true`。

6. **报告上下文层**
   - `report_context_builder.py` 已新增 `veterinary_gmp_workshop` 分支，已把：
     - `gmp_grade`
     - `gmp_context_mode`
     - `pharma_context_variant`
     纳入 `business_context`。

7. **最小真实 payload 层**
   - 已程序化生成 A / B / C / D 四份最小真实 payload：
     - `/Users/fuwuqi/检测报告生成系统_X1/temp_x1/vet_gmp_payloads/vet_gmp_A级_minimal_export_payload.json`
     - `/Users/fuwuqi/检测报告生成系统_X1/temp_x1/vet_gmp_payloads/vet_gmp_B级_minimal_export_payload.json`
     - `/Users/fuwuqi/检测报告生成系统_X1/temp_x1/vet_gmp_payloads/vet_gmp_C级_minimal_export_payload.json`
     - `/Users/fuwuqi/检测报告生成系统_X1/temp_x1/vet_gmp_payloads/vet_gmp_D级_minimal_export_payload.json`
   - 已确认四等级全部满足：
     - 独立 `template_key`
     - `template_found = true`
     - 独立 `semantic_key`
     - 独立 `report_context_mode`

8. **正文填充首轮接入层**
   - `adapters/template_fill.py` 已新增 `veterinary_gmp_workshop` 的 replacement plan 分支；
   - 已新增 `document_xml` 定点写入分支，并首轮复用 `gmp_workshop` 成熟骨架；
   - 已成功生成兽药 A / B / C / D 四等级首轮正文回归件：
     - `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/vet_gmp_regression_round1/vet_gmp_A级.filled.docx`
     - `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/vet_gmp_regression_round1/vet_gmp_B级.filled.docx`
     - `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/vet_gmp_regression_round1/vet_gmp_C级.filled.docx`
     - `/Users/fuwuqi/检测报告生成系统_X1/reports_x1/vet_gmp_regression_round1/vet_gmp_D级.filled.docx`

---

## 4. 当前已确认的问题焦点（第二轮已收敛）

当前最准确判断已经收敛为：

> `veterinary_gmp_workshop` 主链与正文链都已打通，
> 当前已不再是“大面积没写进去”，
> 而是围绕第 4 张表粒子区 `row 7~11` 的真实承载列做最后收口。

本轮已确认的关键事实：

1. **兽药正文关键结果位于第 4 张表（table index 3）**
   真实模板对应行号为：
   - `row 3`：截面风速
   - `row 4`：静压差
   - `row 6`：送风高效过滤器检漏
   - `row 7`：洁净度
   - `row 8`：`≥0.5μm`
   - `row 9`：`0.5μm UCL`
   - `row 10`：`≥5μm`
   - `row 11`：`5μm UCL`
   - `row 12`：温度
   - `row 13`：相对湿度
   - `row 14`：照度
   - `row 15`：噪声
   - `row 16`：沉降菌
   - `row 17`：浮游菌

2. **洁净等级来源优先级已经修正并生效**
   当前正文已按以下顺序取值：
   - `GMP等级`
   - `洁净等级`
   - `洁净级别`
   - `洁净度设计级别`
   - 再回退到 `洁净度`
   - 再回退到 `洁净度级别`

3. **检漏行号已按真实模板修正到 `row 6`**
   第二轮 XML 抽查已确认：
   - `送风高效过滤器检漏` 已不再落错到旧 `row 5`
   - 当前 `row 6` 写入已稳定

4. **兽药模板的 `95%UCL` 行必须保留，不能套普通 GMP 逻辑清空**
   已直接比对模板本体与生成件，确认：
   - `row 9 / row 11` 是模板原生 `95%UCL` 说明行
   - 不能再按普通 `gmp_workshop` 的“清空标签行”方案处理

5. **粒子区真实承载列已基本钉死**
   本轮在 `template_fill.py` 中继续修正后，A / B / C / D 四等级回归件已表现为：
   - `row 8`：第 5 列保留说明文字“各采样点平均值中的最大值”，第 6 列写 `≥0.5μm` 最大值，第 7 列写 `0.5μmUCL`
   - `row 9`：第 5 列保留 `95%UCL` 标签，第 6 列写 `0.5μmUCL`
   - `row 10`：第 5 列保留说明文字“各采样点平均值中的最大值”，第 6 列写 `≥5μm` 最大值，第 7 列写 `5μmUCL`
   - `row 11`：第 5 列保留 `95%UCL` 标签，第 6 列写 `5μmUCL`

6. **当前尾项已进一步收敛为“只剩 0.5μm 主行是否保留 UCL 并列展示”**
   本轮继续下刀后，A / B / C / D 四等级回归件已表现为：
   - `row 9 / row 11` 的 `95%UCL` 标签与右侧数值都稳定落格
   - `row 10 / row 11` 已基本达到“主值在主行、UCL 在说明行”的目标形态
   - `row 8 / row 9` 仍保留一处展示重复：`0.5μmUCL` 目前同时出现在 `row 8` 第 7 列与 `row 9` 第 6 列

   这说明当前系统已经不再存在“值丢失 / 写错行”的功能性问题，
   剩余仅是 0.5μm 区一处模板展示去重尾项，可视为轻量精修而非主链阻塞。

---

## 5. 下一步唯一动作

> 当前按“完成 90% 即可先过站”的原则处理。
> 兽药车间对象当前已具备进入下一阶段的条件，暂不继续为一个非阻塞展示尾项反复打磨。

当前共识：
1. 主链已通；
2. 正文关键结果已能稳定落格；
3. A / B / C / D 四等级最小回归已跑通；
4. 当前剩余仅为 `0.5μm` 区一处轻量展示去重问题，不影响对象继续推进。

因此下一步改为：
1. 先把 `veterinary_gmp_workshop` 作为“已完成约 90% 的可用对象”继续纳入后续联调；
2. 后续如果进入模板精修轮，再单独收掉 `row 8` 与 `row 9` 之间的 `0.5μmUCL` 展示重复；
3. 待与更多真实样本联调后，再决定是否做对象级首轮收口升级；
4. 当前系统级执行顺位上，`veterinary_gmp_workshop` 位于 `pass_box` 之后，仅作为恢复推进中的联调尾项对象，不阻塞主线，也不再与挂起对象混排。

---

## 6. 当前结论（按本轮口径封板）

可以先定性为：

> `veterinary_gmp_workshop` 已完成约 90%，
> 当前不再是功能链路问题，
> 只剩一个不阻塞推进的模板展示小尾项。

也就是说，后面可以先去跑后续调试，不必继续卡在这一处。

