// X1 检测系统核心数据 版本跟随 x1_config.json
// 重构：基于刘总反馈的详细参数录入规则
// inputType说明：
//   'numeric' - 普通数值（默认3个录入点+可扩展）
//   'airchange' - 换气次数（风速仪法/风量仪法切换）
//   'particle_zone' - 洁净度（分手术区/周边区，各4个值）
//   'particle_4' - 洁净度（4个值：0.5μm最大值+UCL，5μm最大值+UCL）
//   'bacteria_zone_control' - 细菌浓度（分手术区/周边区，采样点数+采样总数+平均值）
//   'bacteria_zone_control_control' - 细菌浓度（分手术区/周边区，每区3个数据点+扩展+空白对照+阴性对照）
//   'bacteria_control' - 细菌浓度（3个数据点+扩展+空白对照+阴性对照）
//   'settling' - 沉降菌（采样点数+采样总数+平均值）
//   'settling_control' - 沉降菌（3个数据点+扩展+空白对照+阴性对照）
//   'floating' - 浮游菌（采样量+采样总数+采样点数→平均浓度）
//   'floating_control' - 浮游菌（采样量+采样点数+3个采样总数+扩展+空白对照+阴性对照）
//   'wind_uniformity' - 风速不均匀度（自动从关联风速参数计算）
//   'illumination_uniformity' - 照度均匀度（最小值/平均值，自动从照度数据计算）
//   'text' - 文本观察结果

const SYSTEM_DB = {
    domains: [
        { id: 'hospital', name: '医院洁净部', icon: '🏥' },
        { id: 'biosafety', name: '生物安全', icon: '🧬' },
        { id: 'food', name: '食品加工', icon: '🍞' },
        { id: 'pharma', name: '制药工业', icon: '💊' },
        { id: 'electronics', name: '精密制造/电子', icon: '⚡' }
    ],

    basis: {
        hospital: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB 50333-2013', name: '医院洁净手术部建筑技术规范' },
            { code: 'GB/T 16292-2010', name: '医药工业洁净室悬浮粒子的测试方法' },
            { code: 'GB/T 16293-2010', name: '医药工业洁净室浮游菌的测试方法' },
            { code: 'GB/T 16294-2010', name: '医药工业洁净室沉降菌的测试方法' },
            { code: 'GB/T 35428-2017', name: '医院负压隔离病房环境控制要求' }
        ],
        biosafety: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB 50346-2011', name: '生物安全实验室建筑技术规范' },
            { code: 'GB 41918-2022', name: '生物安全柜' },
            { code: 'JG/T 292-2010', name: '洁净工作台' },
            { code: 'GB 14925-2023', name: '实验动物 环境及设施' }
        ],
        food: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' }
        ],
        pharma: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB/T 16292-2010', name: '医药工业洁净室悬浮粒子的测试方法' },
            { code: 'GB/T 16293-2010', name: '医药工业洁净室浮游菌的测试方法' },
            { code: 'GB/T 16294-2010', name: '医药工业洁净室沉降菌的测试方法' },
            { code: 'GB/T25915.3-2010', name: '洁净室及相关受控环境 第3部分：检测方法' },
            { code: 'JG/T 382-2012', name: '传递窗' }
        ],
        electronics: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB 50472-2008', name: '电子工业洁净厂房设计规范' }
        ]
    },

    // 判定标准
    judgement: {
        hospital: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB 50073-2013', name: '洁净厂房设计规范' },
            { code: 'GB 50457-2019', name: '医药工业洁净厂房设计标准' },
            { code: 'GB 50333-2013', name: '医院洁净手术部建筑技术规范', star: true },
            { code: 'WS/T 368-2012', name: '医院空气净化管理规范' },
            { code: 'WS 310.1-2016', name: '医院消毒供应中心 第一部分：管理规范' },
            { code: '国家卫生健康委办公厅', name: '静脉用药调配中心建设与管理指南（试行）及附件' },
            { code: 'GB/T 35428-2017', name: '医院负压隔离病房环境控制要求' }
        ],
        biosafety: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB 50346-2011', name: '生物安全实验室建筑技术规范', star: true },
            { code: 'GB 41918-2022', name: '生物安全柜' },
            { code: 'JG/T 292-2010', name: '洁净工作台' },
            { code: 'GB 50073-2013', name: '洁净厂房设计规范' },
            { code: 'GB 14925-2023', name: '实验动物 环境及设施' },
            { code: 'DB32/T972-2006', name: '实验动物笼器具 独立通气笼盒（IVC）系统' },
            { code: 'DB15/T4291-2026', name: '实验用牛羊 环境与设施' },
            { code: 'GB/T 16294-2010', name: '医药工业洁净室（区）沉降菌的测试方法' },
            { code: 'GB/T 16293-2010', name: '医药工业洁净室（区）浮游菌的测试方法' }
        ],
        food: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范', star: true },
            { code: 'GB 50687-2011', name: '食品工业洁净用房建筑技术规范' },
            { code: 'GB17405-1998', name: '保健食品良好生产规范' },
            { code: '保健食品生产许可审查细则', name: '保健食品生产许可审查细则' }
        ],
        pharma: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB 50073-2013', name: '洁净厂房设计规范' },
            { code: 'GB 50457-2019', name: '医药工业洁净厂房设计标准', star: true },
            { code: '农业农村部令2020年第3号', name: '兽药生产质量管理规范（2020年修订）' },
            { code: '农业农村部公告第389号', name: '兽药生产企业洁净区静态检测相关要求' },
            { code: '农业农村部公告第292号', name: '兽药生产质量管理规范（2020年修订）配套文件 附件1' },
            { code: 'GMP 2010', name: '药品生产质量管理规范（2010年修订）' },
            { code: 'JG/T 382-2012', name: '传递窗' },
            { code: 'GB/T 16294-2010', name: '医药工业洁净室（区）沉降菌的测试方法' },
            { code: 'GB/T 16293-2010', name: '医药工业洁净室（区）浮游菌的测试方法' }
        ],
        electronics: [
            { code: 'GB 50591-2010', name: '洁净室施工及验收规范' },
            { code: 'GB 50073-2013', name: '洁净厂房设计规范' },
            { code: 'GB 50472-2008', name: '电子工业洁净厂房设计规范', star: true }
        ]
    },

    // 各领域的洁净等级选项
        // 检测类型配置
    detectionTypes: {
        hospital: [
            { id: 'operating_room', name: '洁净手术部', defaultBasis: ['GB 50333-2013', 'GB 50591-2010'], defaultJudgement: ['GB 50333-2013', 'GB 50591-2010'], surgeryRoomTypeLabel: '房间类型', surgeryRoomTypeOptions: ['手术室', '眼科手术室', '洁净辅房'], surgeryAuxRoomLabel: '辅房名称', surgeryAuxRoomOptions: ['需要无菌操作的特殊用房','体外循环室','手术室前室','刷手间','术前准备室','护士站','无菌物品存放室','预麻室','精密仪器室','洁净区走廊','恢复室'], surgeryAuxCleanClassOptions: ['Ⅰ级（局部5级其他6级）','Ⅱ级（7级）','Ⅲ级（8级）','Ⅳ级（8.5级）'], params: [
                            // 医院洁净部说明：当前主要依赖标准映射承接温湿度/噪声/照度/细菌等判定范围，前端侧保留少量结构化等级与分区表达
                            // 第一批软收口：眼科手术室视为 operating_room 主房间体系中的内部特殊映射分支，不作为平级正式检测类型
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.20～0.25' },
                            { key: 'wind_uniformity', name: '风速不均匀度', inputType: 'wind_uniformity', sourceKey: 'wind_speed', calc: '标准偏差/平均值', unit: '', range: '≤0.24' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', unit: '粒/m³', range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'particle_door', name: '开门后门内0.6m处洁净度', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤35200, ≥5μm≤293' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤0.2', range_surr: '≤0.4' }
                        ] , levelParams: {
                'Ⅰ级（百级）': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.20～0.25' },
                            { key: 'wind_uniformity', name: '风速不均匀度', inputType: 'wind_uniformity', sourceKey: 'wind_speed', calc: '标准偏差/平均值', unit: '', range: '≤0.24' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', unit: '粒/m³', range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤35200, ≥5μm≤293' },
                            { key: 'particle_door', name: '开门后门内0.6m处洁净度', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤35200, ≥5μm≤293' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤0.2', range_surr: '≤0.4' }
                        ],
                'Ⅱ级（千级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥24' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', unit: '粒/m³', range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤35200, ≥5μm≤293' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤0.5', range_surr: '≤1.0' }
                        ],
                'Ⅲ级（万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥18' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', unit: '粒/m³', range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤2', range_surr: '≤4' }
                        ],
                'Ⅳ级（十万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥12' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_control', unit: 'cfu/m³', range: '' }
                        ]
            }, surgeryAuxRoomParams: {
                '需要无菌操作的特殊用房': [
                    { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.20～0.25' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', calc: '', unit: '粒/m³', range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤35200, ≥5μm≤293' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤0.2', range_surr: '≤0.4' }
                ],
                '体外循环室': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥12' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '≥150' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '手术室前室': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥8' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '刷手间': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥8' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'work_illumination', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '术前准备室': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥18' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '护士站': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '无菌物品存放室': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '预麻室': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '精密仪器室': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '洁净区走廊': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥8' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ],
                '恢复室': [
                    { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥8' },
                    { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                    { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                    { key: 'particle', name: '洁净度级别', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                    { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                    { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                    { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                    { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                    { key: 'bacteria', name: '细菌浓度', inputType: 'settling_control', calc: '平均值', unit: 'cfu/30min·Φ90mm' }
                ]
            }, eyeLevelParams: {
                'Ⅰ级（百级）': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.15～0.20' },
                            { key: 'wind_uniformity', name: '风速不均匀度', inputType: 'wind_uniformity', sourceKey: 'wind_speed', calc: '标准偏差/平均值', unit: '', range: '≤0.24' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', unit: '粒/m³', range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'particle_door', name: '开门后门内0.6m处洁净度', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤0.2', range_surr: '≤0.4' }
                        ],
                'Ⅱ级（千级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥24' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', unit: '粒/m³', range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤0.5', range_surr: '≤1.0' }
                        ],
                'Ⅲ级（万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥18' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_zone', unit: '粒/m³', range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_zone_control', unit: 'cfu/m³', range_op: '≤2', range_surr: '≤4' }
                        ],
                'Ⅳ级（十万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥12' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'airtightness', name: '严密性', inputType: 'pass_fail', calc: '/', unit: '', range: '除门缝外，所有缝隙无可见泄漏' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'illumination_uniformity', name: '照度均匀度', inputType: 'illumination_uniformity', sourceKey: 'illumination_min', calc: '最小值/平均值', unit: '', range: '≥0.7' },
                            { key: 'bacteria', name: '细菌浓度', inputType: 'bacteria_control', unit: 'cfu/m³', range: '≤6' }
                        ]
            } },
            { id: 'clean_function_room', name: '洁净功能用房', defaultBasis: ['GB 50333-2013', 'GB 50591-2010'], defaultJudgement: ['GB 50333-2013', 'GB 50591-2010'], subroomLabel: '子房间类型', subroomOptions: ['通用洁净功能用房', 'ICU病房', '消毒供应中心', '透析室'], cleanClassOptions: ['Ⅰ级（百级）', 'Ⅱ级（千级）', 'Ⅲ级（万级）', 'Ⅳ级（十万级）'], params: [
                            // 医院洁净功能用房：当前已进入标准映射主导阶段，前端侧主要保留检测结构与少量等级化粒子/微生物表达
                            // 第一批软收口：ICU病房/消毒供应中心/透析室 仅视为 clean_function_room 下的子房间映射，不作为平级正式检测类型
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'bacteria', name: '细菌浓度（沉降法）', inputType: 'settling_control', unit: 'cfu/30min·Φ90皿', range: '≤4' }
                        ], levelParams: {
                'Ⅰ级（百级）': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.20～0.25' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520, ≥5μm≤29' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'bacteria', name: '细菌浓度（沉降法）', inputType: 'settling_control', unit: 'cfu/30min·Φ90皿', range: '≤0.4' }
                        ],
                'Ⅱ级（千级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥18' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤35200, ≥5μm≤293' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'bacteria', name: '细菌浓度（沉降法）', inputType: 'settling_control', unit: 'cfu/30min·Φ90皿', range: '≤1.5' }
                        ],
                'Ⅲ级（万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'bacteria', name: '细菌浓度（沉降法）', inputType: 'settling_control', unit: 'cfu/30min·Φ90皿', range: '≤4' }
                        ],
                'Ⅳ级（十万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥12' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'bacteria', name: '细菌浓度（沉降法）', inputType: 'settling_control', unit: 'cfu/30min·Φ90皿', range: '≤5' }
                        ]
            } },
            { id: 'negative_pressure', name: '负压病房', defaultBasis: ['GB/T 35428-2017'], defaultJudgement: ['GB/T 35428-2017', 'WS/T 368-2012'], cleanClassOptions: ['无洁净等级要求'], params: [
                            { key: 'airchange', name: '污染区换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '10～15' },
                            { key: 'airchange_clean', name: '清洁区换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '6～10' },
                            { key: 'exhaust_speed', name: '排风口风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '≤1.5' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airflow_direction', name: '气流流向', inputType: 'pass_fail', calc: '/', unit: '', range: '由清洁区→半污染区→污染区' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30~70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'bacteria', name: '细菌浓度（沉降法）', inputType: 'settling_control', unit: 'cfu/(5min·9cm平皿)' },
                            { key: 'surface_bacteria', name: '物体表面微生物', inputType: 'numeric', calc: '平均值', unit: 'cfu/cm²', range: '≤10' }
                        ] }
        ],
        biosafety: [
            { id: 'bsl', name: '实验室', defaultBasis: ['GB 50346-2011', 'GB 50591-2010'], defaultJudgement: ['GB 50346-2011', 'GB 50591-2010', 'GB/T 16294-2010', 'GB/T 16293-2010'] , params: [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airflow_direction', name: '气流流向', inputType: 'pass_fail', calc: '/', unit: '', range: '由清洁区→半污染区→污染区' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～27' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³' }
                        ], levelParams: {
                'ISO-5': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.2～0.4' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airflow_direction', name: '气流流向', inputType: 'pass_fail', calc: '/', unit: '', range: '由清洁区→半污染区→污染区' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520, ≥5μm≤29' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～27' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³' }
                        ],
                'ISO-6': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥12' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airflow_direction', name: '气流流向', inputType: 'pass_fail', calc: '/', unit: '', range: '由清洁区→半污染区→污染区' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤35200, ≥5μm≤293' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～27' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³' }
                        ],
                'ISO-7': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥12' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airflow_direction', name: '气流流向', inputType: 'pass_fail', calc: '/', unit: '', range: '由清洁区→半污染区→污染区' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～27' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³' }
                        ],
                'ISO-8': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥12' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airflow_direction', name: '气流流向', inputType: 'pass_fail', calc: '/', unit: '', range: '由清洁区→半污染区→污染区' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～27' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³' }
                        ],
                'ISO-9': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥6' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airflow_direction', name: '气流流向', inputType: 'pass_fail', calc: '/', unit: '', range: '由清洁区→半污染区→污染区' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤35200000, ≥5μm≤293000' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～27' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³' }
                        ]
            } },
            { id: 'animal_room', name: '动物房', cleanClassLabel: '环境选择', defaultBasis: ['GB 14925-2023'], defaultJudgement: ['GB 14925-2023'], cleanClassOptions: ['普通环境', '屏障环境', '隔离环境'], barrierRoomClassLabel: '房间类别', barrierRoomClassOptions: ['主房间', '洁净辅房'], barrierAuxRoomLabel: '洁净辅房名称', barrierAuxRoomOptions: ['洁物储存室', '灭菌后室/区', '洁净走廊', '污物走廊', '缓冲间', '二更', '清洗消毒室', '一更'], params: [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥8' },
                            { key: 'cage_airspeed', name: '动物笼具处气流速度', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '≤0.2' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'temp_diff', name: '最大日温差', inputType: 'temp_diff', calc: '最高温度-最低温度', unit: '℃', range: '≤4' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'work_illumination', name: '工作照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥150' },
                            { key: 'animal_illumination', name: '动物照度', inputType: 'numeric_range_manual', calc: '平均值', unit: 'lx', range: '100～200' }
                        ], levelParams: {
                '普通环境': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥8' },
                            { key: 'cage_airspeed', name: '动物笼具处气流速度', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '≤0.2' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'temp_diff', name: '最大日温差', inputType: 'temp_diff', calc: '最高温度-最低温度', unit: '℃', range: '≤4' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'work_illumination', name: '工作照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥150' },
                            { key: 'animal_illumination', name: '动物照度', inputType: 'numeric_range_manual', calc: '平均值', unit: 'lx', range: '100～200' }
                        ],
                '屏障环境': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'cage_airspeed', name: '动物笼具处气流速度', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '≤0.2' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '空气洁净度等级（7级）', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'temp_diff', name: '最大日温差', inputType: 'temp_diff', calc: '最高温度-最低温度', unit: '℃', range: '≤4' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'work_illumination', name: '工作照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥150' },
                            { key: 'animal_illumination', name: '动物照度', inputType: 'numeric_range_manual', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'settling', name: '沉降菌平均浓度', inputType: 'settling_control', unit: 'cfu/皿' }
                        ],
                '隔离环境': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'cage_airspeed', name: '动物笼具处气流速度', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '≤0.2' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '空气洁净度等级（5级，正压）', inputType: 'particle_4_051', calc: '', unit: '粒/m³', range: '' },
                            { key: 'particle_negative', name: '空气洁净度等级（7级，负压）', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'temp_diff', name: '最大日温差', inputType: 'temp_diff', calc: '最高温度-最低温度', unit: '℃', range: '≤4' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'work_illumination', name: '工作照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '200～300' },
                            { key: 'animal_illumination', name: '动物照度', inputType: 'numeric_range_manual', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'settling', name: '沉降菌平均浓度', inputType: 'settling_control', unit: 'cfu/皿' }
                        ]
            }, barrierAuxParams: {
                '洁物储存室': [
                            { key: 'particle', name: '空气洁净度等级（7级）', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' }
                        ],
                '灭菌后室/区': [
                            { key: 'particle', name: '空气洁净度等级（7级）', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' }
                        ],
                '洁净走廊': [
                            { key: 'particle', name: '空气洁净度等级（7级）', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' }
                        ],
                '污物走廊': [
                            { key: 'particle', name: '空气洁净度等级（8级）', inputType: 'particle_4_8', calc: '', unit: '粒/m³', range: '' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' }
                        ],
                '缓冲间': [
                            { key: 'particle', name: '空气洁净度等级（8级）', inputType: 'particle_4_8', calc: '', unit: '粒/m³', range: '' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' }
                        ],
                '二更': [
                            { key: 'particle', name: '空气洁净度等级（7级）', inputType: 'particle_4', calc: '', unit: '粒/m³', range: '' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' }
                        ],
                '清洗消毒室': [
                            { key: 'particle', name: '空气洁净度等级', inputType: 'text', calc: '/', unit: '', range: '—' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥4' },
                            { key: 'pressure', name: '静压差', inputType: 'text', calc: '/', unit: '', range: '—' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' }
                        ],
                '一更': [
                            { key: 'particle', name: '空气洁净度等级', inputType: 'text', calc: '/', unit: '', range: '—' },
                            { key: 'airchange', name: '换气次数', inputType: 'text', calc: '/', unit: '', range: '—' },
                            { key: 'pressure', name: '静压差', inputType: 'text', calc: '/', unit: '', range: '—' },
                            { key: 'temperature_aux', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～28' },
                            { key: 'humidity_aux', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '≤70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '≥100' }
                        ]
            } },
            { id: 'bsc', name: '生物安全柜', defaultBasis: ['GB 41918-2022'], defaultJudgement: ['GB 41918-2022'], cleanClassOptions: [], bslClassOptions: [], params: [
                            // 设备类 bsc：除 numeric_range_manual 合法手工场景外，当前已主要由标准映射承担判定范围
                            { key: 'appearance', name: '外观', inputType: 'pass_fail', calc: '/', unit: '', range: '柜体表面无明显划伤、锈斑、压痕，表面光洁，外形平整规矩；说明功能的文字和图形符号标志应正确、清晰、端正、牢固；焊接应牢固，焊接表面应光滑' },
                            { key: 'alarm_interlock', name: '报警和连锁系统', inputType: 'pass_fail', calc: '/', unit: '', range: '安全柜前窗开启高度超过或低于前窗操作口标称高度时，声音报警器报警，联锁系统启动。当开启高度回到标称高度，报警声音和联锁系统应自动解除' },
                            { key: 'downflow_speed', name: '下降气流流速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '' },
                            { key: 'speed_uniformity', name: '风速不均匀度', inputType: 'wind_uniformity', sourceKey: 'downflow_speed', calc: '标准偏差/平均值', unit: '', range: '' },
                            { key: 'inflow_speed', name: '流入气流流速', inputType: 'numeric_range_manual', calc: '平均值', unit: 'm/s', range: '' },
                            { key: 'airflow_pattern', name: '气流模式', inputType: 'pass_fail', calc: '/', unit: '', range: '' },
                            { key: 'hepa_integrity', name: '高效过滤器完整性', inputType: 'numeric', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '工作区洁净度', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric_range_manual', calc: '平均值', unit: 'lx', range: '平均≥650' },
                            { key: 'illumination_min', name: '最低照度', inputType: 'numeric', calc: '最小值', unit: 'lx', range: '' },
                            { key: 'uv_intensity', name: '紫外灯辐照强度', inputType: 'numeric', calc: '/', unit: 'μW/cm²', range: '' }
                        ] },
            { id: 'clean_bench', name: '洁净工作台', defaultBasis: ['JG/T 292-2010'], defaultJudgement: ['JG/T 292-2010'], cleanClassOptions: [], bslClassOptions: [], params: [
                            // 设备类 clean_bench：当前静态范围已大部收口，主要由 _default 映射承担判定范围
                            { key: 'appearance', name: '外观', inputType: 'pass_fail', calc: '/', unit: '', range: '箱体表面、工作区侧壁及台面应无划伤、压痕，表面应光洁，外形应平整规则；机箱焊接牢固且表面光滑，不应有烧穿、漏孔、裂缝、焊疤残留或残渣等' },
                            { key: 'function', name: '功能', inputType: 'pass_fail', calc: '/', unit: '', range: '前窗开启与关闭应轻便，在行程范围内滑动应顺畅，并不应有明显的左右或前后晃动现象；开关、按键的操作应灵活可靠；洁净工作台正常工作状态时，不应有明显的机振声' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'avg_speed', name: '垂直气流平均风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '' },
                            { key: 'speed_uniformity', name: '风速不均匀度', inputType: 'wind_uniformity', sourceKey: 'avg_speed', calc: '标准偏差/平均值', unit: '', range: '' },
                            { key: 'particle', name: '工作区洁净度', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'airflow_state', name: '气流状态', inputType: 'pass_fail', calc: '/', unit: '', range: '' },
                            { key: 'settling', name: '沉降菌浓度', inputType: 'settling_control', unit: 'cfu/皿', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination', name: '照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' }
                        ] },
            { id: 'ivc', name: 'IVC笼具', defaultBasis: ['GB 14925-2023'], defaultJudgement: ['GB 14925-2023', 'DB32/T972-2006'], cleanClassOptions: [], bslClassOptions: [], params: [
                            // 设备类 ivc：当前前端参数边界已基本让位于设备映射，后续重点核查多判定标准下的承接一致性
                            { key: 'airflow_speed', name: '气流流速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '' },
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'pressure', name: '箱体静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'airtightness', name: '笼盒气密性', inputType: 'pass_fail', calc: '/', unit: '', range: '' },
                            { key: 'hepa_integrity', name: '高效过滤器完整性', inputType: 'numeric', calc: '/', unit: '%', range: '' }
                        ] }
        ],
        food: [
            { id: 'food_workshop', name: '洁净车间', defaultBasis: ['GB 50591-2010'], defaultJudgement: ['GB 50591-2010', 'GB 50687-2011'] , params: [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%', range: '' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～65' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_general_processing', name: '加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'illumination_mixed_processing', name: '加工场所工作面混合照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥500' },
                            { key: 'illumination_non_processing', name: '非加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥100' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³' }
                        ], levelParams: {
                'Ⅰ级（百级）': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.20～0.50' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520, ≥5μm≤29' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～25' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～65' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_general_processing', name: '加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'illumination_mixed_processing', name: '加工场所工作面混合照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥500' },
                            { key: 'illumination_non_processing', name: '非加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥100' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤0.2' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤5' }
                        ],
                'Ⅱ级（万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～25' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～65' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_general_processing', name: '加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'illumination_mixed_processing', name: '加工场所工作面混合照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥500' },
                            { key: 'illumination_non_processing', name: '非加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥100' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤1.5' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤50' }
                        ],
                'Ⅲ级（十万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_general_processing', name: '加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'illumination_mixed_processing', name: '加工场所工作面混合照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥500' },
                            { key: 'illumination_non_processing', name: '非加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥100' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤4' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤150' }
                        ],
                'Ⅳ级（三十万级）': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥10' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤35200000, ≥5μm≤293000' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '30～70' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_general_processing', name: '加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'illumination_mixed_processing', name: '加工场所工作面混合照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥500' },
                            { key: 'illumination_non_processing', name: '非加工场所工作面一般照明', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥100' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤150' }
                        ]
            } }
        ],
        pharma: [
            { id: 'laminar_hood', name: '层流罩', defaultBasis: ['GB 50591-2010'], defaultJudgement: ['GB 50591-2010'], cleanClassOptions: [], params: [
                            { key: 'avg_speed', name: '垂直气流平均风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '' },
                            { key: 'speed_uniformity', name: '风速不均匀度', inputType: 'wind_uniformity', sourceKey: 'avg_speed', calc: '标准偏差/平均值', unit: '', range: '' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '' }
                        ] },
            { id: 'pass_box', name: '传递窗', defaultBasis: ['GB 50591-2010'], defaultJudgement: ['JG/T 382-2012', 'GB 50591-2010'], cleanClassOptions: [], params: [
                            { key: 'appearance', name: '外观检验', inputType: 'pass_fail', calc: '/', unit: '', range: '外形应平整光洁，表面色泽均匀、无明显划伤、锈斑、压痕；说明功能的文字和图形符号标志应正确、清晰、端正、牢固；外部配件位置应合理，接头、管道封堵应可靠' },
                            { key: 'door_interlock', name: '门互锁功能', inputType: 'pass_fail', calc: '/', unit: '', range: '打开传递窗任意一端的门，则另一端门不能打开；当传递窗断电或门的自锁功能失灵时，两端门应能手动开启' },
                            { key: 'box_inner_size', name: '箱体内尺寸', inputType: 'pass_box_volume', calc: '内长×内宽×内高', unit: 'm³', range: '' },
                            { key: 'airchange_b12', name: 'B1、B2型换气次数', inputType: 'airchange_speed_only', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'airchange_b3', name: 'B3型换气次数', inputType: 'airchange_speed_only', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'particle', name: '洁净度', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'hepa_leak', name: '高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' }
                        ] },
            { id: 'gmp_workshop', name: 'GMP车间', defaultBasis: ['GB 50591-2010', 'GB/T 16292-2010'], defaultJudgement: ['GB 50457-2019', 'GB 50591-2010', 'GMP 2010', 'GB/T 16294-2010', 'GB/T 16293-2010'] , params: [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～65' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤10' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤500' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '气流垂直向下、无旋涡' }
                        ],
                        levelParams: {
                'A级': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.36～0.54' },
                            { key: 'wind_speed_uniformity', name: '不均匀度', inputType: 'wind_uniformity', sourceKey: 'wind_speed', calc: '(最大值-最小值)/(最大值+最小值)', unit: '', range: '≤0.20' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520, ≥5μm≤20' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～24' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～60' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤1' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤5' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ],
                'B级': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '40～60' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520, ≥5μm≤29' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～24' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～60' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤3' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤10' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ],
                'C级': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '20～40' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2900' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～24' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～60' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤3' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤100' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ],
                'D级': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '10～20' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～65' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤10' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤500' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ]
            } },
            { id: 'veterinary_gmp_workshop', name: '兽药车间', defaultBasis: ['GB 50591-2010', 'GB/T 16292-2010'], defaultJudgement: ['GB 50457-2019', 'GB 50591-2010', '农业农村部令2020年第3号', '农业农村部公告第389号', '农业农村部公告第292号', 'GB/T 16294-2010', 'GB/T 16293-2010'] , params: [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '≥15' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2930' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～65' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤10' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤500' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ], levelParams: {
                'A级': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '0.36～0.54' },
                            { key: 'wind_speed_uniformity', name: '不均匀度', inputType: 'wind_uniformity', sourceKey: 'wind_speed', calc: '(最大值-最小值)/(最大值+最小值)', unit: '', range: '≤0.20' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520, ≥5μm≤20' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～24' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～60' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤1' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤5' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ],
                'B级': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '40～60' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520, ≥5μm≤29' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～24' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～60' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤3' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤10' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ],
                'C级': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '20～40' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤352000, ≥5μm≤2900' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '20～24' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～60' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤3' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤100' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ],
                'D级': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '10～20' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                            { key: 'temperature', name: '温度', inputType: 'numeric', calc: '平均值', unit: '℃', range: '18～26' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric', calc: '平均值', unit: '%', range: '45～65' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '≤65' },
                            { key: 'illumination_main_room', name: '主要工作室照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥300' },
                            { key: 'illumination_aux_room', name: '辅房照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '≥200' },
                            { key: 'settling', name: '沉降菌', inputType: 'settling_control', unit: 'cfu/皿', range: '≤10' },
                            { key: 'floating', name: '浮游菌', inputType: 'floating_control', unit: 'cfu/m³', range: '≤500' },
                            { key: 'self_clean', name: '自净时间', inputType: 'numeric', calc: '/', unit: 'min', range: '15～20' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '符合要求' }
                        ]
            } },
        ],
        electronics: [
            { id: 'electronics_workshop', name: '洁净车间', defaultBasis: ['GB 50591-2010', 'GB 50472-2008'], defaultJudgement: ['GB 50472-2008', 'GB 50591-2010'], params: [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main', name: '主房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'illumination_aux', name: '辅房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '气流垂直向下、无旋涡' }
                        ], levelParams: {
                'ISO 5': [
                            { key: 'wind_speed', name: '截面风速', inputType: 'numeric', calc: '平均值', unit: 'm/s', range: '' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main', name: '主房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'illumination_aux', name: '辅房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '气流垂直向下、无旋涡' }
                        ],
                'ISO 6': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main', name: '主房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'illumination_aux', name: '辅房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '气流垂直向下、无旋涡' }
                        ],
                'ISO 7': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main', name: '主房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'illumination_aux', name: '辅房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '气流垂直向下、无旋涡' }
                        ],
                'ISO 8': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main', name: '主房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'illumination_aux', name: '辅房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '气流垂直向下、无旋涡' }
                        ],
                'ISO 9': [
                            { key: 'airchange', name: '换气次数', inputType: 'airchange', calc: '总风量/房间体积', unit: '次/h', range: '' },
                            { key: 'pressure', name: '静压差', inputType: 'pressure_bsl', calc: '', unit: 'Pa', range: '' },
                            { key: 'hepa_leak', name: '送风高效过滤器检漏', inputType: 'hepa_leak_multi', calc: '/', unit: '%' },
                            { key: 'particle', name: '洁净度级别', inputType: 'particle_4', unit: '粒/m³', range: '' },
                            { key: 'temperature', name: '温度', inputType: 'numeric_range_manual', calc: '平均值', unit: '℃', range: '' },
                            { key: 'humidity', name: '相对湿度', inputType: 'numeric_range_manual', calc: '平均值', unit: '%', range: '' },
                            { key: 'noise', name: '噪声', inputType: 'noise_corrected', calc: '平均值', unit: 'dB(A)', range: '' },
                            { key: 'illumination_main', name: '主房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'illumination_aux', name: '辅房间照度', inputType: 'numeric', calc: '平均值', unit: 'lx', range: '' },
                            { key: 'airflow_pattern', name: '气流流型', inputType: 'pass_fail', calc: '/', unit: '', range: '气流垂直向下、无旋涡' }
                        ]
            } }
        ]
    },

cleanClassOptions: {
        hospital: ['Ⅰ级（百级）', 'Ⅱ级（千级）', 'Ⅲ级（万级）', 'Ⅳ级（十万级）'],
        biosafety: ['ISO-5', 'ISO-6', 'ISO-7', 'ISO-8', 'ISO-9'],
        food: ['Ⅰ级（百级）', 'Ⅱ级（万级）', 'Ⅲ级（十万级）', 'Ⅳ级（三十万级）'],
        pharma: ['A级', 'B级', 'C级', 'D级'],
        electronics: ['ISO 5', 'ISO 6', 'ISO 7', 'ISO 8', 'ISO 9']
    },
    
    // 生物安全等级选项
    bslOptions: {
        biosafety: ['BSL-1（P1）', 'BSL-2（P2）', 'BSL-3（P3）', 'BSL-4（P4）']
    },

    // 判定标准的range映射（用于切换判定标准时更新判定范围）
    // 判定标准的range映射（用于切换判定标准时更新判定范围）
    // 结构：standardRanges[标准代码][检测类型ID][洁净等级] = { 参数key: { range/range_op/range_surr } }
    // 内部映射保留节点说明：
    // - eye_operating_room 当前仅作为 operating_room -> 眼科手术室 分支的内部映射数据节点保留
    // - 其数据仍由 getParamRange()/updateRoomRanges() 按 operating_room 的内部路径承接
    // - 当前不作为正式独立检测类型，不单独暴露正式入口
    // 设备类说明：
    // - bsc / clean_bench / ivc 已使用 _default 设备映射承担主要范围来源
    // - laminar_hood / pass_box 已进入数据库接管边界梳理阶段，当前保留映射用于回归核验
    // - electronics_workshop 已完成基础块 + ISO 5~ISO 9 静态 range 收口，当前以标准映射为主
    standardRanges: {

        // ============================================================
        // GB 50333-2013 医院洁净手术部建筑技术规范
        // 适用：operating_room, clean_function_room
        // 说明：医院洁净部当前进入映射主导阶段，前端保留的分区/辅房/等级结构主要用于表达检测结构，不再作为唯一范围来源
        // ============================================================
        'GB 50333-2013': {

            'operating_room': {
                'Ⅰ级（百级）': {
                    'wind_speed': { range: '0.20～0.25' }, 'wind_uniformity': { range: '≤0.24' },
                    'pressure': { range: '5～20' },
                    'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'particle_door': { range: '≥0.5μm≤35200, ≥5μm≤293' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤51' }, 'illumination_min': { range: '≥350' },
                    'illumination': { range: '≥300' }, 'temp_diff': { range: '≤2' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range_op: '≤0.2', range_surr: '≤0.4' }
                },
                'Ⅱ级（千级）': {
                    'airchange': { range: '≥24' }, 'pressure': { range: '5～15' },
                    'particle': { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'illumination': { range: '≥300' }, 'temp_diff': { range: '≤2' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range_op: '≤0.5', range_surr: '≤1.0' }
                },
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥18' }, 'pressure': { range: '5～10' },
                    'particle': { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'illumination': { range: '≥300' }, 'temp_diff': { range: '≤2' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range_op: '≤2', range_surr: '≤4' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '≥5' },
                    'particle': { range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'illumination': { range: '≥300' }, 'temp_diff': { range: '≤2' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range: '≤6' }
                },
                '辅房': {
                    '需要无菌操作的特殊用房': {
                        'wind_speed': { range: '0.20～0.25' },
                        'temperature': { range: '21～25' },
                        'humidity': { range: '30～60' },
                        'noise': { range: '≤51' }, 'illumination_min': { range: '≥350' },
                        'bacteria': { range: '≤0.75' }
                    },
                    '体外循环室': {
                        'airchange': { range: '≥12' },
                        'temperature': { range: '21～27' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤60' }, 'work_illumination': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '手术室前室': {
                        'airchange': { range: '≥8' },
                        'temperature': { range: '21～27' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤60' }, 'illumination_main': { range: '300～500' }, 'illumination_aux': { range: '200～300' }, 'illumination_min': { range: '≥200' },
                        'bacteria': { range: '≤6' }
                    },
                    '刷手间': {
                        'airchange': { range: '≥8' },
                        'temperature': { range: '21～27' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤55' }, 'work_illumination': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '术前准备室': {
                        'airchange': { range: '≥18' },
                        'temperature': { range: '21～25' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤50' }, 'illumination_min': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '护士站': {
                        'airchange': { range: '≥10' },
                        'temperature': { range: '21～27' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤55' }, 'illumination_min': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '无菌物品存放室': {
                        'airchange': { range: '≥10' },
                        'temperature': { range: '≤27' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '预麻室': {
                        'airchange': { range: '≥10' },
                        'temperature': { range: '23～26' },
                        'humidity': { range: '30～60' },
                        'noise': { range: '≤55' }, 'illumination_min': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '精密仪器室': {
                        'airchange': { range: '≥10' },
                        'temperature': { range: '≤27' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '洁净区走廊': {
                        'airchange': { range: '≥8' },
                        'temperature': { range: '21～27' },
                        'humidity': { range: '≤60' },
                        'noise': { range: '≤52' }, 'illumination_min': { range: '≥150' },
                        'bacteria': { range: '≤2' }
                    },
                    '恢复室': {
                        'airchange': { range: '≥8' },
                        'temperature': { range: '22～26' },
                        'humidity': { range: '25～60' },
                        'noise': { range: '≤48' }, 'illumination_main': { range: '300～500' }, 'illumination_aux': { range: '200～300' }, 'illumination_min': { range: '≥200' },
                        'bacteria': { range: '≤2' }
                    }
                },
                '辅房等级': {
                    'Ⅰ级（局部5级其他6级）': {
                        'wind_speed': { range: '0.20～0.25' },
                        'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤35200, ≥5μm≤293' },
                        'bacteria': { range_op: '≤0.2', range_surr: '≤0.4' }
                    },
                    'Ⅱ级（7级）': {
                        'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' },
                        'bacteria': { range: '≤1.5' }
                    },
                    'Ⅲ级（8级）': {
                        'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                        'bacteria': { range: '≤4' }
                    },
                    'Ⅳ级（8.5级）': {
                        'particle': { range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' },
                        'bacteria': { range: '≤6' }
                    }
                }
            },
            // 内部映射保留节点：仅供 operating_room -> 眼科手术室 分支承接，不作为正式独立检测类型入口
            'eye_operating_room': {
                'Ⅰ级（百级）': {
                    'wind_speed': { range: '0.15～0.20' }, 'wind_uniformity': { range: '≤0.24' },
                    'pressure': { range: '5～20' },
                    'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'particle_door': { range: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤51' }, 'illumination_min': { range: '≥350' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range_op: '≤0.2', range_surr: '≤0.4' }
                },
                'Ⅱ级（千级）': {
                    'airchange': { range: '≥24' }, 'pressure': { range: '5～20' },
                    'particle': { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range_op: '≤0.75', range_surr: '≤1.5' }
                },
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥18' }, 'pressure': { range: '5～20' },
                    'particle': { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range_op: '≤2', range_surr: '≤4' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '5～20' },
                    'particle': { range: '3520000＞0.5μm≤11120000, 29300＞5μm≤92500' },
                    'temperature': { range: '21～25' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'illumination_uniformity': { range: '≥0.7' },
                    'bacteria': { range: '≤6' }
                }
            },
            'clean_function_room': {
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥10' }, 'pressure': { range: '5～10' },
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'temperature': { range: '20～23' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤60' }, 'illumination': { range: '≥100' },
                    'settling': { range: '≤4' }, 'floating': { range: '≤500' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '≥5' },
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'temperature': { range: '20～23' }, 'humidity': { range: '30～60' },
                    'noise': { range: '≤60' }, 'illumination': { range: '≥150' },
                    'settling': { range: '≤5' }, 'floating': { range: '≤500' }
                }
            }
        },

        // ============================================================
        // GB 50591-2010 洁净室施工及验收规范（通用标准）
        // 适用：所有有等级的检测类型
        // ============================================================
        // ============================================================
        // GB 50591-2010 洁净室施工及验收规范（通用标准，兜底用）
        // 不分领域，按ISO洁净度等级统一提供粒子浓度判定范围
        // ============================================================
        'GB 50591-2010': {
            '_universal': {
                'ISO 5':        { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' } },
                'ISO 6':        { 'particle': { range: '≥0.5μm≤35200, ≥5μm≤293' } },
                'ISO 7':        { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' } },
                'ISO 8':        { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' } },
                'ISO 9':        { 'particle': { range: '≥0.5μm≤35200000, ≥5μm≤293000' } },
                'Ⅰ级（百级）':  { 'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤35200, ≥5μm≤293' } },
                'Ⅱ级（千级）':  { 'particle': { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' } },
                'Ⅲ级（万级）':  { 'particle': { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' } },
                'Ⅳ级（十万级）':{ 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' } },
                'Ⅰ级（百级）食品': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' } },
                'Ⅱ级（万级）':  { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' } },
                'Ⅲ级（十万级）':{ 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' } },
                'Ⅳ级（三十万级）':{ 'particle': { range: '≥0.5μm≤35200000, ≥5μm≤293000' } },
                'A级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' } },
                'B级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' } },
                'C级': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' } },
                'D级': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' } },
                '_default': {
                    // 设备类 clean_bench 的 hepa_leak 已由标准数据库接管，保留静态定义仅作为配置可读性标识
                    'hepa_leak': { range: '≤0.01%' }
                }
            },
            'operating_room': {
                'Ⅰ级（百级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅱ级（千级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅲ级（万级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅳ级（十万级）': { 'hepa_leak': { range: '≤0.01%' } },
                '辅房': {
                    '需要无菌操作的特殊用房': { 'hepa_leak': { range: '≤0.01%' } },
                    '体外循环室': { 'hepa_leak': { range: '≤0.01%' } },
                    '手术室前室': { 'hepa_leak': { range: '≤0.01%' } },
                    '刷手间': { 'hepa_leak': { range: '≤0.01%' } },
                    '术前准备室': { 'hepa_leak': { range: '≤0.01%' } },
                    '护士站': { 'hepa_leak': { range: '≤0.01%' } },
                    '无菌物品存放室': { 'hepa_leak': { range: '≤0.01%' } },
                    '预麻室': { 'hepa_leak': { range: '≤0.01%' } },
                    '精密仪器室': { 'hepa_leak': { range: '≤0.01%' } },
                    '洁净区走廊': { 'hepa_leak': { range: '≤0.01%' } },
                    '恢复室': { 'hepa_leak': { range: '≤0.01%' } }
                }
            },
            'eye_operating_room': {
                'Ⅰ级（百级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅱ级（千级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅲ级（万级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅳ级（十万级）': { 'hepa_leak': { range: '≤0.01%' } }
            },
            'clean_function_room': {
                'Ⅰ级（百级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅱ级（千级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅲ级（万级）': { 'hepa_leak': { range: '≤0.01%' } },
                'Ⅳ级（十万级）': { 'hepa_leak': { range: '≤0.01%' } }
            }
        },

        // ============================================================
        // GB 50346-2011 生物安全实验室建筑技术规范
        // 适用：bsl
        // ============================================================
        'GB 50346-2011': {
            'bsl': {
                'ISO-5': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'wind_speed': { range: '0.2～0.4' }, 'pressure': { range: '-10～-15' }, 'temperature': { range: '18～27' }, 'humidity': { range: '30~70' }, 'noise': { range: '≤65' }, 'illumination': { range: '≥300' }, 'settling': { range: '≤1' }, 'floating': { range: '≤5' } },
                'ISO-6': { 'particle': { range: '≥0.5μm≤35200, ≥5μm≤293' }, 'airchange': { range: '50～60' }, 'pressure': { range: '-10～-15' }, 'temperature': { range: '18～27' }, 'humidity': { range: '30-70' }, 'noise': { range: '≤60' }, 'illumination': { range: '≥300' }, 'settling': { range: '≤1' }, 'floating': { range: '≤5' } },
                'ISO-7': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' }, 'airchange': { range: '≥15' }, 'pressure': { range: '-10～-15' }, 'temperature': { range: '18～27' }, 'humidity': { range: '30～70' }, 'noise': { range: '≤60' }, 'illumination': { range: '≥300' }, 'settling': { range: '≤3' }, 'floating': { range: '≤100' } },
                'ISO-8': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'pressure': { range: '-10～-15' }, 'airchange': { range: '≥12' }, 'temperature': { range: '18～27' }, 'humidity': { range: '30～70' }, 'noise': { range: '≤60' }, 'illumination': { range: '≥300' }, 'settling': { range: '≤10' }, 'floating': { range: '≤500' } },
                'ISO-9': { 'particle': { range: '≥0.5μm≤35200000, ≥5μm≤293000' }, 'airchange': { range: '≥10' }, 'pressure': { range: '-10～-15' }, 'temperature': { range: '18～27' }, 'humidity': { range: '30～70' }, 'noise': { range: '≤60' }, 'illumination': { range: '≥300' }, 'settling': { range: '≤10' }, 'floating': { range: '≤500' } }
            }
        },

        // ============================================================
        // GB 50457-2019 医药工业洁净厂房设计标准
        // 适用：gmp_workshop
        // ============================================================
        'GB 50457-2019': {
            'gmp_workshop': {
                'A级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' }, 'wind_speed': { range: '0.36～0.54' }, 'wind_speed_uniformity': { range: '≤0.20' }, 'pressure': { range: '≥10' }, 'temperature': { range: '20～24' }, 'humidity': { range: '45～60' }, 'noise': { range: '≤65' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤1' }, 'floating': { range: '≤5' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '气流垂直向下、无旋涡' } },
                'B级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'airchange': { range: '40～60' }, 'pressure': { range: '≥10' }, 'temperature': { range: '20～24' }, 'humidity': { range: '45～60' }, 'noise': { range: '≤60' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤1' }, 'floating': { range: '≤5' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '符合要求' } },
                'C级': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' }, 'airchange': { range: '20～40' }, 'pressure': { range: '≥10' }, 'temperature': { range: '20～24' }, 'humidity': { range: '45～60' }, 'noise': { range: '≤60' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤3' }, 'floating': { range: '≤100' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '符合要求' } },
                'D级': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' }, 'airchange': { range: '10～20' }, 'pressure': { range: '≥10' }, 'temperature': { range: '18～26' }, 'humidity': { range: '45～65' }, 'noise': { range: '≤60' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤10' }, 'floating': { range: '≤500' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '符合要求' } }
            },
            'veterinary_gmp_workshop': {
                'A级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' }, 'wind_speed': { range: '0.36～0.54' }, 'wind_speed_uniformity': { range: '≤0.20' }, 'pressure': { range: '≥10' }, 'temperature': { range: '20～24' }, 'humidity': { range: '45～60' }, 'noise': { range: '≤65' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤1' }, 'floating': { range: '≤5' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '符合要求' } },
                'B级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'airchange': { range: '40～60' }, 'pressure': { range: '≥10' }, 'temperature': { range: '20～24' }, 'humidity': { range: '45～60' }, 'noise': { range: '≤65' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤3' }, 'floating': { range: '≤10' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '符合要求' } },
                'C级': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' }, 'airchange': { range: '20～40' }, 'pressure': { range: '≥10' }, 'temperature': { range: '20～24' }, 'humidity': { range: '45～60' }, 'noise': { range: '≤65' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤3' }, 'floating': { range: '≤100' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '符合要求' } },
                'D级': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' }, 'airchange': { range: '10～20' }, 'pressure': { range: '≥10' }, 'temperature': { range: '18～26' }, 'humidity': { range: '45～65' }, 'noise': { range: '≤65' }, 'illumination_main_room': { range: '≥300' }, 'illumination_aux_room': { range: '≥200' }, 'settling': { range: '≤10' }, 'floating': { range: '≤500' }, 'self_clean': { range: '15～20' }, 'airflow_pattern': { range: '符合要求' } }
            },
        },


        // ============================================================
        // GB 50591-2010 洁净室施工及验收规范（设备类层流罩收口映射）
        // 适用：laminar_hood
        // ============================================================
        'GB 50591-2010-laminar-hood': {
            'laminar_hood': {
                '_default': {
                    'avg_speed': { range: '0.36～0.54' },
                    'speed_uniformity': { range: '≤0.25' },
                    'airflow_pattern': { range: '气流垂直向下、无旋涡' },
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }
                }
            }
        },

        // ============================================================
        // GMP 2010 药品生产质量管理规范
        // 适用：gmp_workshop
        // ============================================================
        'GMP 2010': {
            'gmp_workshop': {
                'A级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' }, 'pressure': { range: '≥10' }, 'settling': { range: '≤1' }, 'floating': { range: '≤5' } },
                'B级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'pressure': { range: '≥10' }, 'settling': { range: '≤1' }, 'floating': { range: '≤5' } },
                'C级': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' }, 'pressure': { range: '≥5' }, 'temperature': { range: '18～26' }, 'humidity': { range: '45～65' }, 'settling': { range: '≤3' }, 'floating': { range: '≤100' } },
                'D级': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' }, 'pressure': { range: '≥5' }, 'settling': { range: '≤10' }, 'floating': { range: '≤500' } }
            }
        },

        // ============================================================
        // GB 50687-2011 食品工业洁净用房建筑技术规范
        // 适用：food_workshop
        // ============================================================
        'GB 50687-2011': {

            'laminar_hood': {
                '_default': {
                    // 设备类 laminar_hood：前端静态范围已完成双领域收口，当前以本映射作为主要判定范围来源
                    // 暂保留 hepa_leak 一并在映射侧维护，便于后续统一回归核验
                    'avg_speed': { range: '0.36～0.54' },
                    'speed_uniformity': { range: '≤0.25' },
                    'airflow_pattern': { range: '气流垂直向下、无旋涡' },
                    'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }
                }
            },

            'food_workshop': {
                'Ⅰ级（百级）': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'wind_speed': { range: '0.20～0.50' }, 'pressure': { range: '≥10' }, 'noise': { range: '≤65' }, 'illumination_general_processing': { range: '≥200' }, 'illumination_mixed_processing': { range: '≥500' }, 'illumination_non_processing': { range: '≥100' }, 'temperature': { range: '20～25' }, 'humidity': { range: '30～65' }, 'settling': { range: '≤0.2' }, 'floating': { range: '≤5' } },
                'Ⅱ级（万级）': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' }, 'airchange': { range: '≥20' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤60' }, 'illumination_general_processing': { range: '≥200' }, 'illumination_mixed_processing': { range: '≥500' }, 'illumination_non_processing': { range: '≥100' }, 'temperature': { range: '20～25' }, 'humidity': { range: '30～65' }, 'settling': { range: '≤1.5' }, 'floating': { range: '≤50' } },
                'Ⅲ级（十万级）': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'airchange': { range: '≥15' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤60' }, 'illumination_general_processing': { range: '≥200' }, 'illumination_mixed_processing': { range: '≥500' }, 'illumination_non_processing': { range: '≥100' }, 'temperature': { range: '18～26' }, 'humidity': { range: '30～70' }, 'settling': { range: '≤4' }, 'floating': { range: '≤150' } },
                'Ⅳ级（三十万级）': { 'particle': { range: '≥0.5μm≤35200000, ≥5μm≤293000' }, 'airchange': { range: '≥10' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤60' }, 'illumination_general_processing': { range: '≥200' }, 'illumination_mixed_processing': { range: '≥500' }, 'illumination_non_processing': { range: '≥100' }, 'temperature': { range: '18～26' }, 'humidity': { range: '30～70' }, 'settling': { range: '' }, 'floating': { range: '≤500' } }
            }
        },

        // ============================================================
        // GB 50472-2008 电子工业洁净厂房设计规范
        // 适用：electronics_workshop
        // ============================================================
        'GB 50472-2008': {
            'electronics_workshop': {
                'ISO 5': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'wind_speed': { range: '0.20～0.45' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤65' }, 'illumination_main': { range: '300～500' }, 'illumination_aux': { range: '200～300' }, 'temperature': { range: '22～24' }, 'humidity': { range: '45～65' } },
                'ISO 6': { 'particle': { range: '≥0.5μm≤35200, ≥5μm≤293' }, 'airchange': { range: '50～60' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤60' }, 'illumination_main': { range: '300～500' }, 'illumination_aux': { range: '200～300' }, 'temperature': { range: '21～25' }, 'humidity': { range: '45～65' } },
                'ISO 7': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' }, 'airchange': { range: '15～25' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤60' }, 'illumination_main': { range: '300～500' }, 'illumination_aux': { range: '200～300' }, 'temperature': { range: '22～26' }, 'humidity': { range: '45～65' } },
                'ISO 8': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'airchange': { range: '10～15' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤60' }, 'illumination_main': { range: '300～500' }, 'illumination_aux': { range: '200～300' }, 'temperature': { range: '22～26' }, 'humidity': { range: '45～70' } },
                'ISO 9': { 'particle': { range: '≥0.5μm≤35200000, ≥5μm≤293000' }, 'airchange': { range: '10～15' }, 'pressure': { range: '≥5' }, 'noise': { range: '≤60' }, 'illumination_main': { range: '300～500' }, 'illumination_aux': { range: '200～300' }, 'temperature': { range: '22～26' }, 'humidity': { range: '45～70' } }
            }
        },

        // ============================================================
        // GB 50073-2013 洁净厂房设计规范（通用）
        // 适用：多个领域
        // ============================================================
        'GB 50073-2013': {
            'operating_room': {
                'Ⅰ级（百级）': { 'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' }, 'pressure': { range: '≥5' } },
                'Ⅱ级（千级）': { 'particle': { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' }, 'pressure': { range: '≥5' } },
                'Ⅲ级（万级）': { 'particle': { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'pressure': { range: '≥5' } },
                'Ⅳ级（十万级）': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'pressure': { range: '≥5' } }
            },
            'eye_operating_room': {
                'Ⅰ级（百级）': { 'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' }, 'pressure': { range: '≥5' } },
                'Ⅱ级（千级）': { 'particle': { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'pressure': { range: '≥5' } },
                'Ⅲ级（万级）': { 'particle': { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' }, 'pressure': { range: '≥5' } },
                'Ⅳ级（十万级）': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'pressure': { range: '≥5' } }
            },
            'bsl': {
                'ISO-5': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'pressure': { range: '≥5' } },
                'ISO-6': { 'particle': { range: '≥0.5μm≤35200, ≥5μm≤293' }, 'pressure': { range: '≥5' } },
                'ISO-7': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' }, 'pressure': { range: '≥5' } },
                'ISO-8': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'pressure': { range: '≥5' } },
                'ISO-9': { 'particle': { range: '≥0.5μm≤35200000, ≥5μm≤293000' }, 'pressure': { range: '≥5' } }
            },
            'electronics_workshop': {
                'ISO 5': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'pressure': { range: '≥5' } },
                'ISO 6': { 'particle': { range: '≥0.5μm≤35200, ≥5μm≤293' }, 'pressure': { range: '≥5' } },
                'ISO 7': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' }, 'pressure': { range: '≥5' } },
                'ISO 8': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, 'pressure': { range: '≥5' } },
                'ISO 9': { 'particle': { range: '≥0.5μm≤35200000, ≥5μm≤293000' }, 'pressure': { range: '≥5' } }
            },
            'gmp_workshop': {
                'A级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' }, 'pressure': { range: '≥5' } },
                'B级': { 'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' }, 'pressure': { range: '≥5' } },
                'C级': { 'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' }, 'pressure': { range: '≥5' } },
                'D级': { 'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' }, 'pressure': { range: '≥5' } }
            }
        },

        // ============================================================
        // GB/T 35428-2017 医院负压隔离病房环境控制要求
        // 适用：negative_pressure
        // ============================================================
        'GB/T 35428-2017': {
            'negative_pressure': {
                '_default': {
                    'airchange': { range: '10～15' }, 'airchange_clean': { range: '6～10' }, 'exhaust_speed': { range: '≤1.5' },
                    'hepa_leak': { range: '≤0.01%' }, 'pressure': { range: '-5～-10' },
                    'airflow_direction': { range: '由清洁区→半污染区→污染区' },
                    'temperature': { range: '20～26' },
                    'humidity': { range: '30～70' },
                    'noise': { range: '≤50' }, 'illumination': { range: '≥50' },
                    'bacteria': { range: '≤6' }, 'surface_bacteria': { range: '≤10' }
                }
            }
        },

        // ============================================================
        // WS/T 368-2012 医院空气净化管理规范
        // 适用：negative_pressure
        // ============================================================
        'WS/T 368-2012': {
            'negative_pressure': {
                '_default': {
                    'bacteria': { range: '≤4', unit: 'cfu/(5min·9cm平皿)' }
                }
            ,
            'clean_function_room': {
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥10' }, 'pressure': { range: '5～10' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'noise': { range: '≤55' }, 'illumination': { range: '≥50' },
                    'settling': { range: '≤4' }, 'floating': { range: '≤500' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '≥5' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'noise': { range: '≤60' }, 'illumination': { range: '≥150' },
                    'settling': { range: '≤5' }, 'floating': { range: '≤500' }
                }
            }}
        },

        // ============================================================
        // GB 14925-2023 实验动物 环境及设施
        // 适用：animal_room
        // ============================================================
        'GB 14925-2023': {
            'animal_room': {
                '普通环境': {
                    'airchange': { range: '≥8' },
                    'cage_airspeed': { range: '≤0.2' },
                    'pressure': { range: '0～5' },
                    'temperature': { range: '20～26' },
                    'temp_diff': { range: '≤4' },
                    'humidity': { range: '30～70' },
                    'noise': { range: '≤60' },
                    'work_illumination': { range: '≥150' },
                    'animal_illumination': { range: '100～200' },
                    'settling': { range: '' }
                },
                '屏障环境': {
                    'airchange': { range: '≥15' }, 'cage_airspeed': { range: '≤0.2' },
                    'pressure': { range: '≥10' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '35200＜0.5μm≤352000，293＜5μm≤2930' },
                    'temperature': { range: '20～26' }, 'temp_diff': { range: '≤4' },
                    'humidity': { range: '30～70' }, 'noise': { range: '≤60' },
                    'work_illumination': { range: '≥150' }, 'animal_illumination': { range: '100～200' }, 'settling': { range: '≤3' }
                },
                '屏障环境洁净辅房': {
                    '洁物储存室': {
                        'particle': { range: '35200＜0.5μm≤352000，293＜5μm≤2930' },
                        'airchange': { range: '≥15' }, 'pressure': { range: '≥10' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '≤70' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' }
                    },
                    '灭菌后室/区': {
                        'particle': { range: '35200＜0.5μm≤352000，293＜5μm≤2930' },
                        'airchange': { range: '≥15' }, 'pressure': { range: '≥10' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '≤70' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' }
                    },
                    '洁净走廊': {
                        'particle': { range: '35200＜0.5μm≤352000，293＜5μm≤2930' },
                        'airchange': { range: '≥15' }, 'pressure': { range: '≥10' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '≤70' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' }
                    },
                    '污物走廊': {
                        'particle': { range: '352000＜0.5μm≤3520000，2930＜5μm≤29300' },
                        'airchange': { range: '≥10' }, 'pressure': { range: '≥5' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '—' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' }
                    },
                    '缓冲间': {
                        'particle': { range: '352000＜0.5μm≤3520000，2930＜5μm≤29300' },
                        'airchange': { range: '≥10' }, 'pressure': { range: '≥5' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '—' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' }
                    },
                    '二更': {
                        'particle': { range: '35200＜0.5μm≤352000，293＜5μm≤2930' },
                        'airchange': { range: '≥15' }, 'pressure': { range: '≥10' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '≤70' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' }
                    },
                    '清洗消毒室': {
                        'particle': { range: '—' }, 'airchange': { range: '≥4' }, 'pressure': { range: '—' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '—' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥150' }
                    },
                    '一更': {
                        'particle': { range: '—' }, 'airchange': { range: '' }, 'pressure': { range: '—' },
                        'temperature_aux': { range: '18～28' }, 'humidity_aux': { range: '—' },
                        'noise': { range: '≤60' }, 'illumination_min': { range: '≥100' }
                    }
                },
                '隔离环境': {
                    'airchange': { range: '≥20' }, 'cage_airspeed': { range: '≤0.2' },
                    'pressure': { range: '≥50' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '352＜0.5μm≤3520，83＜1μm≤832' },
                    'particle_negative': { range: '35200＜0.5μm≤352000，293＜5μm≤2930' },
                    'temperature': { range: '20～26' }, 'temp_diff': { range: '≤4' },
                    'humidity': { range: '30～70' }, 'noise': { range: '≤60' },
                    'work_illumination': { range: '≥150' }, 'animal_illumination': { range: '100～200' }, 'settling': { range: '≤0' }
                }
            }
        },

        // ============================================================
        // 国家卫生健康委办公厅 静脉用药调配中心建设与管理指南（试行）
        // 适用：clean_function_room（PIVAS属于洁净功能用房）
        // 数据来源：附件1 附表1 静脉用药调配中心洁净环境检测指标及标准（静态）
        // 注意：PIVAS使用C级(万级)和D级(十万级)，对应clean_function_room的Ⅲ级和Ⅳ级
        // ============================================================
        '国家卫生健康委办公厅': {
            'clean_function_room': {
                'Ⅲ级（万级）': {
                    // C级(万级)：对应二次更衣室、调配操作间
                    'airchange': { range: '≥25' },
                    'pressure': { range: '5～10' },
                    'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤350000, ≥5μm≤2000' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '35～75' },
                    'noise': { range: '≤60' },
                    'illumination': { range: '≥300' },
                    'settling': { range: '≤3' }
                },
                'Ⅳ级（十万级）': {
                    // D级(十万级)：对应一次更衣室、洗衣洁具间
                    'airchange': { range: '≥15' },
                    'pressure': { range: '≥10' },
                    'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3500000, ≥5μm≤20000' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '35～75' },
                    'noise': { range: '≤60' },
                    'illumination': { range: '≥300' },
                    'settling': { range: '≤10' }
                }
            }
        },

        // ============================================================
        // DB 11/663-2009 负压隔离病房建设配置基本要求（北京地方标准）
        // 适用：negative_pressure
        // 参数与GB/T 35428-2017基本一致，部分参数有差异
        // 待确认：该标准为北京地标，部分参数值需与原文核实
        // ============================================================

        // 适用：food_workshop
        // 该标准只规定了十万级（一般生产区和10万级区）
        // 洁净厂房设计引用GBJ73（即GB 50073前身），换气次数见表1
        // 待确认：表1为扫描件，换气次数数值需核实
        // ============================================================
        'GB17405-1998': {
            'food_workshop': {
                'Ⅳ级（十万级）': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' }, // 待确认：原文表述为10万级
                    'airchange': { range: '≥15' }, // 待确认：原文表1
                    'pressure': { range: '≥5' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '≤65' }
                }
            }
        },

        // ============================================================
        // 保健食品生产许可审查细则
        // 适用：food_workshop
        // 说明：该标准引用GB17405-1998和GB 50687-2011的参数，不需要独立映射
        // 此处仅做占位，参数与GB17405-1998一致
        // ============================================================
        '保健食品生产许可审查细则': {
            'food_workshop': {
                'Ⅳ级（十万级）': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'airchange': { range: '≥15' },
                    'pressure': { range: '≥5' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '≤65' }
                }
            }
        },


        // ============================================================
        // GB 41918-2022 生物安全柜
        // 适用：bsc
        // ============================================================
        'GB 41918-2022': {
            'bsc': {
                '_default': {
                    'appearance': { range: '柜体表面无明显划伤、锈斑、压痕，表面光洁，外形平整规矩；说明功能的文字和图形符号标志应正确、清晰、端正、牢固；焊接应牢固，焊接表面应光滑' },
                    'alarm_interlock': { range: '安全柜前窗开启高度超过或低于前窗操作口标称高度时，声音报警器报警，联锁系统启动。当开启高度回到标称高度，报警声音和联锁系统应自动解除' },
                    // 说明：inflow_speed 当前仍为 numeric_range_manual 合法手工场景，暂不并入本映射块硬编码
                    'downflow_speed': { range: '0.25～0.5' },
                    'speed_uniformity': { range: '≤0.2' },
                    'airflow_pattern': { range: '安全柜工作区内的气流应向下，应不产生旋涡和向上气流且无死点；气流应不从安全柜中逸出；安全柜前窗操作口整个周边气流应向内，无向外逸出的气流；安全柜的前窗操作口流入气流应不进入工作区' },
                    'hepa_integrity': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'noise': { range: '≤67' },
                    // 说明：illumination 在前端保留 numeric_range_manual 形态，用于承接“平均≥650”这类人工可读范围文本
                    'illumination': { range: '平均≥650' },
                    'illumination_min': { range: '≥430' },
                    'uv_intensity': { range: '≥253.7' }
                }
            }
        },


        // ============================================================
        // JG/T 292-2010 洁净工作台
        // 适用：clean_bench
        // ============================================================
        'JG/T 292-2010': {
            'clean_bench': {
                '_default': {
                    'appearance': { range: '箱体表面、工作区侧壁及台面应无划伤、压痕，表面应光洁，外形应平整规则；机箱焊接牢固且表面光滑，不应有烧穿、漏孔、裂缝、焊疤残留或残渣等' },
                    'function': { range: '前窗开启与关闭应轻便，在行程范围内滑动应顺畅，并不应有明显的左右或前后晃动现象；开关、按键的操作应灵活可靠；洁净工作台正常工作状态时，不应有明显的机振声' },
                    'hepa_leak': { range: '≤0.01%' },
                    'avg_speed': { range: '0.20～0.5' },
                    'speed_uniformity': { range: '≤0.2' },
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'airflow_state': { range: '气流流线应垂直于台面，不得有死角和回流' },
                    'settling': { range: '≤0.5' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' }
                }
            }
        },


        // ============================================================
        // DB32/T972-2006 实验动物设施设备检测规范
        // 适用：ivc
        // 两侧数值目前保持一致，用于多判定标准场景下的统一回归核查。
        // ============================================================
        'DB32/T972-2006': {
            'ivc': {
                '_default': {
                    'airflow_speed': { range: '≤0.2' },
                    'airchange': { range: '≥20' },
                    'airtightness': { range: '≥5min' },
                    'hepa_integrity': { range: '≤0.01%' }
                }
            }
        },

        // ============================================================
        // 农业农村部令2020年第3号 兽药生产质量管理规范（2020年修订）
        // 适用：gmp_workshop（兽药GMP车间）
        // 洁净区分A/B/C/D四级，压差≥10Pa
        // 悬浮粒子标准与人药GMP 2010基本一致
        // ============================================================
        '农业农村部令2020年第3号': {
            'gmp_workshop': {
                'A级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤1' },
                    'floating': { range: '≤1' }
                },
                'B级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤3' },
                    'floating': { range: '≤10' }
                },
                'C级': {
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤5' },
                    'floating': { range: '≤100' }
                },
                'D级': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤10' },
                    'floating': { range: '≤200' }
                }
            },
            'veterinary_gmp_workshop': {
                'A级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤1' },
                    'floating': { range: '≤1' }
                },
                'B级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤3' },
                    'floating': { range: '≤10' }
                },
                'C级': {
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤5' },
                    'floating': { range: '≤100' }
                },
                'D级': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤10' },
                    'floating': { range: '≤200' }
                }
            }
        },

        // ============================================================
        // DB15/T4291-2026 实验用牛羊 环境与设施（内蒙古地方标准）
        // 适用：animal_room（动物房）
        // 数据来源：表2 实验用牛、实验用羊饲养间环境指标
        // 注意：该标准为大动物（牛羊），参数与GB 14925-2023（小动物）有差异
        // ============================================================
        'DB15/T4291-2026': {
            'animal_room': {
                '_default': {
                    // 屏障环境指标
                    'airchange': { range: '≥15' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '10～28' },
                    'humidity': { range: '20～70' },
                    'noise': { range: '≤60' },
                    'illumination': { range: '≥150' }
                    // 注：该标准要求空气洁净度7级（ISO-7），日温差≤10℃
                    // 氨气浓度≤14 mg/m³（动态指标）
                }
            }
        },

        // ============================================================
                // ============================================================
        'WST 368-2012': {
            'operating_room': {
                'Ⅰ级（百级）': {
                    'wind_speed': { range: '0.20～0.25' }, 'wind_uniformity': { range: '≤0.24' },
                    'pressure': { range: '5～20' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤35200, ≥5μm≤293' },
                    'noise': { range: '≤52' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range_op: '≤0.2', range_surr: '≤0.4' }
                },
                'Ⅱ级（千级）': {
                    'airchange': { range: '≥24' }, 'pressure': { range: '5～15' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range_op: '≤0.75', range_surr: '≤1.5' }
                },
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥18' }, 'pressure': { range: '5～10' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range_op: '≤2', range_surr: '≤4' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '≥5' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range: '≤6' }
                }
            },
            'eye_operating_room': {
                'Ⅰ级（百级）': {
                    'wind_speed': { range: '0.15～0.20' }, 'wind_uniformity': { range: '≤0.24' },
                    'pressure': { range: '5～20' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range_op: '≥0.5μm≤3520, ≥5μm≤29', range_surr: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'noise': { range: '≤51' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range_op: '≤0.2', range_surr: '≤0.4' }
                },
                'Ⅱ级（千级）': {
                    'airchange': { range: '≥24' }, 'pressure': { range: '5～20' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range_op: '≥0.5μm≤35200, ≥5μm≤293', range_surr: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range_op: '≤0.5', range_surr: '≤1.0' }
                },
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥18' }, 'pressure': { range: '5～20' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range_op: '≥0.5μm≤352000, ≥5μm≤2930', range_surr: '≥0.5μm≤35200000, ≥5μm≤293000' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range_op: '≤2', range_surr: '≤4' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '5～20' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'noise': { range: '≤49' }, 'illumination_min': { range: '≥350' },
                    'bacteria': { range: '≤6' }
                }
            },
            'clean_function_room': {
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥10' }, 'pressure': { range: '5～10' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'noise': { range: '≤55' }, 'illumination': { range: '≥50' },
                    'settling': { range: '≤4' }, 'floating': { range: '≤500' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '≥5' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'noise': { range: '≤60' }, 'illumination': { range: '≥150' },
                    'settling': { range: '≤5' }, 'floating': { range: '≤500' }
                }
            }
        },

        // ============================================================
        // WS 310.1-2016 医院消毒供应中心管理规范
        // 适用：clean_function_room
        // 说明：消毒供应中心属于洁净功能用房，洁净参数引用GB 50333-2013
        // ============================================================
        'WS 310.1-2016': {
            'clean_function_room': {
                'Ⅲ级（万级）': {
                    'airchange': { range: '≥10' }, 'pressure': { range: '5～10' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'temperature': { range: '22～26' },
                    'noise': { range: '≤55' }, 'illumination': { range: '≥50' },
                    'settling': { range: '≤4' }, 'floating': { range: '≤500' }
                },
                'Ⅳ级（十万级）': {
                    'airchange': { range: '≥12' }, 'pressure': { range: '≥5' }, 'hepa_leak': { range: '≤0.01%' },
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29300' },
                    'temperature': { range: '22～26' },
                    'noise': { range: '≤60' }, 'illumination': { range: '≥150' },
                    'settling': { range: '≤5' }, 'floating': { range: '≤500' }
                }
            }
        },

        // ============================================================
        // 农业农村部公告第292号 兽药生产质量管理规范（2020年修订）配套文件
        // 适用：gmp_workshop（兽药GMP车间）
        // 悬浮粒子标准：A级3520/不规定，B级3520/不规定(静态)→352000/2900(动态)
        // C级352000/2900(静态)→3520000/29000(动态)，D级3520000/29000(静态)
        // 微生物：A级<1，B级10/5，C级100/50，D级200/100
        // ============================================================
        '农业农村部公告第292号': {
            'gmp_workshop': {
                'A级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤1' },
                    'floating': { range: '≤1' },
                    'wind_speed': { range: '0.36～0.54' },
                    'wind_uniformity': { range: '≤0.25' }
                },
                'B级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤5' },
                    'floating': { range: '≤10' }
                },
                'C级': {
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤50' },
                    'floating': { range: '≤100' }
                },
                'D级': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤100' },
                    'floating': { range: '≤200' }
                }
            },
            'veterinary_gmp_workshop': {
                'A级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤1' },
                    'floating': { range: '≤1' },
                    'wind_speed': { range: '0.36～0.54' },
                    'wind_uniformity': { range: '≤0.25' }
                },
                'B级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤5' },
                    'floating': { range: '≤10' }
                },
                'C级': {
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤50' },
                    'floating': { range: '≤100' }
                },
                'D级': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '18～26' },
                    'humidity': { range: '45～65' },
                    'settling': { range: '≤100' },
                    'floating': { range: '≤200' }
                }
            }
        },

        // ============================================================
        // 农业农村部公告第389号 兽药生产企业洁净区静态检测相关要求
        // 适用：gmp_workshop（兽药GMP车间）
        // 说明：检测方法标准，评价依据引用292号配套文件和GB 50457-2019、GB 50073-2013
        // 参数范围与292号一致
        // ============================================================
        '农业农村部公告第389号': {
            'gmp_workshop': {
                'A级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' },
                    'wind_speed': { range: '0.36～0.54' },
                    'wind_uniformity': { range: '≤0.25' }
                },
                'B级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' }
                },
                'C级': {
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' }
                },
                'D级': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                    'pressure': { range: '≥5' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' }
                }
            },
            'veterinary_gmp_workshop': {
                'A级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤20' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' },
                    'wind_speed': { range: '0.36～0.54' },
                    'wind_uniformity': { range: '≤0.25' }
                },
                'B级': {
                    'particle': { range: '≥0.5μm≤3520, ≥5μm≤29' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' }
                },
                'C级': {
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2900' },
                    'pressure': { range: '≥10' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' }
                },
                'D级': {
                    'particle': { range: '≥0.5μm≤3520000, ≥5μm≤29000' },
                    'pressure': { range: '≥5' },
                    'temperature': { range: '20～24' },
                    'humidity': { range: '45～60' },
                    'noise': { range: '≤65' },
                    'illumination': { range: '≥300' }
                }
            }
        },

        // ============================================================
        // GB/T 35428-2017 医院负压隔离病房环境控制要求
        // 适用：negative_pressure
        // ============================================================

        // ============================================================
        // DB 11/663-2009 负压隔离病房建设配置基本要求
        // 适用：negative_pressure
        // GB/T 16294-2010 医药工业洁净室（区）沉降菌的测试方法
        // 适用：bsl 沉降菌判定
        'GB/T 16294-2010': {
            'bsl': {
                'ISO-5': { 'settling': { range: '≤1' } },
                'ISO-6': { 'settling': { range: '≤1' } },
                'ISO-7': { 'settling': { range: '≤3' } },
                'ISO-8': { 'settling': { range: '≤10' } },
                'ISO-9': { 'settling': { range: '≤10' } }
            },
            'gmp_workshop': {
                'A级': { 'settling': { range: '≤1' } },
                'B级': { 'settling': { range: '≤1' } },
                'C级': { 'settling': { range: '≤3' } },
                'D级': { 'settling': { range: '≤10' } }
            },
            'veterinary_gmp_workshop': {
                'A级': { 'settling': { range: '≤1' } },
                'B级': { 'settling': { range: '≤1' } },
                'C级': { 'settling': { range: '≤3' } },
                'D级': { 'settling': { range: '≤10' } }
            },
            'food_workshop': {
                'Ⅰ级（百级）': { 'settling': { range: '≤1' } },
                'Ⅱ级（万级）': { 'settling': { range: '≤3' } },
                'Ⅲ级（十万级）': { 'settling': { range: '≤10' } },
                'Ⅳ级（三十万级）': { 'settling': { range: '≤10' } }
            }
        },

        // GB/T 16293-2010 医药工业洁净室（区）浮游菌的测试方法
        // 适用：bsl 浮游菌判定
        'GB/T 16293-2010': {
            'bsl': {
                'ISO-5': { 'floating': { range: '≤5' } },
                'ISO-6': { 'floating': { range: '≤5' } },
                'ISO-7': { 'floating': { range: '≤100' } },
                'ISO-8': { 'floating': { range: '≤500' } },
                'ISO-9': { 'floating': { range: '≤500' } }
            },
            'gmp_workshop': {
                'A级': { 'floating': { range: '≤5' } },
                'B级': { 'floating': { range: '≤5' } },
                'C级': { 'floating': { range: '≤100' } },
                'D级': { 'floating': { range: '≤500' } }
            },
            'veterinary_gmp_workshop': {
                'A级': { 'floating': { range: '≤5' } },
                'B级': { 'floating': { range: '≤5' } },
                'C级': { 'floating': { range: '≤100' } },
                'D级': { 'floating': { range: '≤500' } }
            },
            'food_workshop': {
                'Ⅰ级（百级）': { 'floating': { range: '≤1' } },
                'Ⅱ级（万级）': { 'floating': { range: '≤10' } },
                'Ⅲ级（十万级）': { 'floating': { range: '≤100' } },
                'Ⅳ级（三十万级）': { 'floating': { range: '≤500' } }
            }
        },

        // ============================================================
        // JG/T 382-2012 传递窗
        // 适用：pass_box
        // ============================================================
        'JG/T 382-2012': {
            'pass_box': {
                '_default': {
                    'appearance': { range: '外形应平整光洁，表面色泽均匀、无明显划伤、锈斑、压痕；说明功能的文字和图形符号标志应正确、清晰、端正、牢固；外部配件位置应合理，接头、管道封堵应可靠' },
                    'door_interlock': { range: '打开传递窗任意一端的门，则另一端门不能打开；当传递窗断电或门的自锁功能失灵时，两端门应能手动开启' },
                    'particle': { range: '≥0.5μm≤352000, ≥5μm≤2930' },
                    'noise': { range: '≤68' },
                    'hepa_leak': { range: '≤0.01%' }
                },
                'B1/B2型': {
                    'airchange_b12': { range: '≥50' }
                },
                'B3型': {
                    'airchange_b3': { range: '≥1000' }
                }
            }
        }
    }

};

if (typeof window !== 'undefined') {
    window.SYSTEM_DB = SYSTEM_DB;
}
if (typeof globalThis !== 'undefined') {
    globalThis.SYSTEM_DB = SYSTEM_DB;
}
if (typeof module !== 'undefined' && module.exports) {
    module.exports = SYSTEM_DB;
}
