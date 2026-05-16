#!/usr/bin/env python3
"""
X1 系统 P0-4 可信测试基线脚本
覆盖 14 个 type_id，使用 Canonical Payload V1.1 标准口径
"""
import requests
from pathlib import Path
from zipfile import ZipFile
import sys
import json
from datetime import datetime

BASE_URL = "http://localhost:8082"
REPORTS_DIR = Path("/Users/fuwuqi/检测报告生成系统_X1/reports_x1")

# 全局session，保持登录状态
session = requests.Session()

def login():
    """登录获取session cookie"""
    session.get(f"{BASE_URL}/login", timeout=10)
    resp = session.post(
        f"{BASE_URL}/login",
        data={"username": "admin", "password": "pudi2026"},
        allow_redirects=True,
        timeout=10,
    )
    if resp.status_code == 200 and (resp.url.rstrip('/') == BASE_URL or '退出' in resp.text):
        print("✅ 登录成功")
        return True
    print(f"❌ 登录失败: {resp.status_code}")
    return False

# 14 个 type_id 标准测试数据（Canonical Payload V1.1）
TEST_OBJECTS = {
    "operating_room": {
        "schema_version": "1.1",
        "project_name": "测试项目-手术室",
        "report_number": "TEST-OR-001",
        "client_name": "测试医院",
        "contact_info": "张医生 13800000001",
        "project_address": "北京市测试区",
        "inspection_area": "手术部",
        "detection_date": "2026-05-02",
        "domain": "hospital",
        "domain_name": "医院洁净部",
        "rooms": [{
            "room_id": "r1",
            "room_name": "百级手术室",
            "type_id": "operating_room",
            "type_name": "手术室",
            "level_name": "Ⅰ级（百级）",
            "clean_class": "Ⅰ级（百级）",
            "basis": ["GB 50333-2013"],
            "judgement": ["GB 50333-2013"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"surgery_room_type": "手术室"}
        }]
    },
    "clean_function_room": {
        "schema_version": "1.1",
        "project_name": "测试项目-ICU",
        "report_number": "TEST-ICU-001",
        "client_name": "测试医院ICU",
        "contact_info": "李护士 13800000002",
        "project_address": "上海市测试区",
        "inspection_area": "ICU病房",
        "detection_date": "2026-05-02",
        "domain": "hospital",
        "domain_name": "医院洁净部",
        "rooms": [{
            "room_id": "r1",
            "room_name": "ICU病房1",
            "type_id": "clean_function_room",
            "type_name": "洁净功能用房",
            "level_name": "Ⅲ级（万级）",
            "clean_class": "Ⅲ级（万级）",
            "basis": ["GB 50333-2013"],
            "judgement": ["GB 50333-2013"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"clean_function_subroom": "ICU病房"}
        }]
    },
    "negative_pressure": {
        "schema_version": "1.1",
        "project_name": "测试项目-负压病房",
        "report_number": "TEST-NEG-001",
        "client_name": "测试医院负压",
        "contact_info": "王医生 13800000003",
        "project_address": "广州市测试区",
        "inspection_area": "负压隔离病房",
        "detection_date": "2026-05-02",
        "domain": "hospital",
        "domain_name": "医院洁净部",
        "rooms": [{
            "room_id": "r1",
            "room_name": "负压隔离病房1",
            "type_id": "negative_pressure",
            "type_name": "负压病房",
            "level_name": "默认",
            "clean_class": "默认",
            "basis": ["GB 50849-2014"],
            "judgement": ["GB 50849-2014"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {}
        }]
    },
    "bsl": {
        "schema_version": "1.1",
        "project_name": "测试项目-生物安全实验室",
        "report_number": "TEST-BSL-001",
        "client_name": "测试研究所",
        "contact_info": "赵研究员 13800000004",
        "project_address": "深圳市测试区",
        "inspection_area": "P2实验室",
        "detection_date": "2026-05-02",
        "domain": "biosafety",
        "domain_name": "生物安全",
        "rooms": [{
            "room_id": "r1",
            "room_name": "P2实验室主实验间",
            "type_id": "bsl",
            "type_name": "生物安全实验室",
            "level_name": "ISO-7",
            "clean_class": "ISO-7",
            "basis": ["GB 50346-2011"],
            "judgement": ["GB 19489-2008"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"bsl_level": "BSL-2（P2）"}
        }]
    },
    "animal_room": {
        "schema_version": "1.1",
        "project_name": "测试项目-动物房",
        "report_number": "TEST-ANIMAL-001",
        "client_name": "测试动物中心",
        "contact_info": "钱主任 13800000005",
        "project_address": "杭州市测试区",
        "inspection_area": "屏障环境动物房",
        "detection_date": "2026-05-02",
        "domain": "biosafety",
        "domain_name": "生物安全",
        "rooms": [{
            "room_id": "r1",
            "room_name": "屏障环境饲养间",
            "type_id": "animal_room",
            "type_name": "动物房",
            "level_name": "屏障环境",
            "clean_class": "屏障环境",
            "basis": ["GB 14925-2023"],
            "judgement": ["GB 14925-2023"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"animal_environment": "屏障环境", "barrier_room_class": "主房间"}
        }]
    },
    "bsc": {
        "schema_version": "1.1",
        "project_name": "测试项目-生物安全柜",
        "report_number": "TEST-BSC-001",
        "client_name": "测试实验室",
        "contact_info": "孙工 13800000006",
        "project_address": "武汉市测试区",
        "inspection_area": "P2实验室",
        "detection_date": "2026-05-02",
        "domain": "biosafety",
        "domain_name": "生物安全",
        "rooms": [{
            "room_id": "r1",
            "room_name": "II级A2型生物安全柜",
            "type_id": "bsc",
            "type_name": "生物安全柜",
            "level_name": "默认",
            "clean_class": "默认",
            "basis": ["YY 0569-2011"],
            "judgement": ["YY 0569-2011"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {}
        }]
    },
    "clean_bench": {
        "schema_version": "1.1",
        "project_name": "测试项目-洁净工作台",
        "report_number": "TEST-CB-001",
        "client_name": "测试制药厂",
        "contact_info": "周工 13800000007",
        "project_address": "成都市测试区",
        "inspection_area": "QC实验室",
        "detection_date": "2026-05-02",
        "domain": "biosafety",
        "domain_name": "生物安全",
        "rooms": [{
            "room_id": "r1",
            "room_name": "垂直流洁净工作台",
            "type_id": "clean_bench",
            "type_name": "洁净工作台",
            "level_name": "默认",
            "clean_class": "默认",
            "basis": ["JG/T 292-2010"],
            "judgement": ["JG/T 292-2010"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {}
        }]
    },
    "ivc": {
        "schema_version": "1.1",
        "project_name": "测试项目-IVC笼具",
        "report_number": "TEST-IVC-001",
        "client_name": "测试动物中心IVC",
        "contact_info": "吴主任 13800000008",
        "project_address": "南京市测试区",
        "inspection_area": "SPF级动物房",
        "detection_date": "2026-05-02",
        "domain": "biosafety",
        "domain_name": "生物安全",
        "rooms": [{
            "room_id": "r1",
            "room_name": "IVC笼具系统",
            "type_id": "ivc",
            "type_name": "IVC笼具",
            "level_name": "默认",
            "clean_class": "默认",
            "basis": ["GB 14925-2023"],
            "judgement": ["GB 14925-2023"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {}
        }]
    },
    "gmp_workshop": {
        "schema_version": "1.1",
        "project_name": "测试项目-GMP车间",
        "report_number": "TEST-GMP-001",
        "client_name": "测试药业公司",
        "contact_info": "郑总 13800000009",
        "project_address": "长沙市测试区",
        "inspection_area": "C级洁净区",
        "detection_date": "2026-05-02",
        "domain": "pharma",
        "domain_name": "制药工业",
        "rooms": [{
            "room_id": "r1",
            "room_name": "C级配液间",
            "type_id": "gmp_workshop",
            "type_name": "GMP车间",
            "level_name": "C级",
            "clean_class": "C级",
            "basis": ["GB 50591-2010"],
            "judgement": ["GB 50457-2019"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"gmp_grade": "C级", "gmp_context_mode": "grade-driven"}
        }]
    },
    "veterinary_gmp_workshop": {
        "schema_version": "1.1",
        "project_name": "测试项目-兽药车间",
        "report_number": "TEST-VET-001",
        "client_name": "测试兽药公司",
        "contact_info": "冯经理 13800000010",
        "project_address": "西安市测试区",
        "inspection_area": "C级兽药生产区",
        "detection_date": "2026-05-02",
        "domain": "pharma",
        "domain_name": "制药工业",
        "rooms": [{
            "room_id": "r1",
            "room_name": "C级兽药配制间",
            "type_id": "veterinary_gmp_workshop",
            "type_name": "兽药车间",
            "level_name": "C级",
            "clean_class": "C级",
            "basis": ["GB 50591-2010"],
            "judgement": ["农业农村部令2020年第3号"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"gmp_grade": "C级", "gmp_context_mode": "grade-driven", "pharma_context_variant": "veterinary-gmp"}
        }]
    },
    "pass_box": {
        "schema_version": "1.1",
        "project_name": "测试项目-传递窗",
        "report_number": "TEST-PASS-001",
        "client_name": "测试制药企业",
        "contact_info": "陈工 13800000011",
        "project_address": "天津市测试区",
        "inspection_area": "洁净区传递窗",
        "detection_date": "2026-05-02",
        "domain": "pharma",
        "domain_name": "制药工业",
        "rooms": [{
            "room_id": "r1",
            "room_name": "D级传递窗",
            "type_id": "pass_box",
            "type_name": "传递窗",
            "level_name": "无等级要求",
            "clean_class": "无等级要求",
            "basis": ["GB 50591-2010"],
            "judgement": ["JG/T 382-2012"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {}
        }]
    },
    "laminar_hood": {
        "schema_version": "1.1",
        "project_name": "测试项目-层流罩",
        "report_number": "TEST-HOOD-001",
        "client_name": "测试制药厂层流",
        "contact_info": "褚工 13800000012",
        "project_address": "重庆市测试区",
        "inspection_area": "灌装车间",
        "detection_date": "2026-05-02",
        "domain": "pharma",
        "domain_name": "制药工业",
        "rooms": [{
            "room_id": "r1",
            "room_name": "灌装线层流罩",
            "type_id": "laminar_hood",
            "type_name": "层流罩",
            "level_name": "无等级要求",
            "clean_class": "无等级要求",
            "basis": ["GB 50591-2010"],
            "judgement": ["JG/T 382-2012"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {}
        }]
    },
    "food_workshop": {
        "schema_version": "1.1",
        "project_name": "测试项目-食品车间",
        "report_number": "TEST-FOOD-001",
        "client_name": "测试食品厂",
        "contact_info": "卫厂长 13800000013",
        "project_address": "青岛市测试区",
        "inspection_area": "十万级灌装车间",
        "detection_date": "2026-05-02",
        "domain": "food",
        "domain_name": "食品加工",
        "rooms": [{
            "room_id": "r1",
            "room_name": "十万级灌装间",
            "type_id": "food_workshop",
            "type_name": "食品车间",
            "level_name": "Ⅲ级（十万级）",
            "clean_class": "Ⅲ级（十万级）",
            "basis": ["GB 50591-2010"],
            "judgement": ["GB 50687-2011"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"food_grade": "Ⅲ级（十万级）", "food_context_mode": "grade-driven"}
        }]
    },
    "electronics_workshop": {
        "schema_version": "1.1",
        "project_name": "测试项目-电子车间",
        "report_number": "TEST-ELEC-001",
        "client_name": "测试电子厂",
        "contact_info": "蒋总 13800000014",
        "project_address": "苏州市测试区",
        "inspection_area": "ISO 7级洁净车间",
        "detection_date": "2026-05-02",
        "domain": "electronics",
        "domain_name": "电子工业",
        "rooms": [{
            "room_id": "r1",
            "room_name": "ISO 7级组装车间",
            "type_id": "electronics_workshop",
            "type_name": "电子车间",
            "level_name": "ISO 7",
            "clean_class": "ISO 7",
            "basis": ["GB 50591-2010"],
            "judgement": ["GB 50591-2010"],
            "params": [],
            "summary": {"result_state": "合格"},
            "context": {"iso_level": "ISO 7", "electronics_context_mode": "iso-driven"}
        }]
    }
}

def test_object(type_id, payload):
    """测试单个对象，区分异常类型"""
    print(f"\n{'='*80}")
    print(f"测试对象: {type_id}")
    print(f"{'='*80}")
    
    result = {
        "type_id": type_id,
        "status": "❌失败",
        "error_type": None,
        "details": {}
    }
    
    try:
        # 提交导出请求
        print(f"\n[1/3] 提交导出请求...")
        response = session.post(
            f"{BASE_URL}/api/x/submit_export",
            json={"project": payload},
            timeout=30
        )
        
        # 登录异常
        if response.status_code == 302 or '/login' in response.url:
            result['error_type'] = "登录异常"
            result['details']['error'] = "302 跳转登录页"
            print(f"   ❌ 登录异常")
            return result
        
        # 接口异常
        if response.status_code != 200:
            result['error_type'] = "接口异常"
            result['details']['http_status'] = response.status_code
            print(f"   ❌ 接口异常: HTTP {response.status_code}")
            return result
        
        data = response.json()
        if not data.get('success'):
            result['error_type'] = "接口异常"
            result['details']['api_error'] = data.get('error', 'Unknown')
            print(f"   ❌ 接口返回失败: {data.get('error')}")
            return result
        
        export_id = data.get('export_id')
        template_ready = data.get('template_ready', False)
        filled_docx_path = data.get('filled_docx_path', '')
        
        print(f"   ✅ 导出ID: {export_id}")
        result['details']['export_id'] = export_id
        result['details']['template_ready'] = template_ready
        
        # 检查导出结果 JSON
        print(f"\n[2/3] 检查导出结果...")
        export_json_path = REPORTS_DIR / f"{export_id}.json"
        if not export_json_path.exists():
            result['error_type'] = "文档生成异常"
            result['details']['error'] = "导出JSON不存在"
            print(f"   ❌ 导出JSON不存在")
            return result
        
        with open(export_json_path, 'r', encoding='utf-8') as f:
            export_data = json.load(f)
        
        # 对象识别异常
        export_type = export_data.get('export_type')
        if export_type != type_id:
            result['error_type'] = "对象识别异常"
            result['details']['expected_type'] = type_id
            result['details']['actual_type'] = export_type
            print(f"   ❌ 对象识别错误: 期望 {type_id}, 实际 {export_type}")
            return result
        
        # 关键字段检查
        project_name = export_data.get('export_payload', {}).get('project_name')
        client_name = export_data.get('export_payload', {}).get('client_name')
        if not project_name or not client_name:
            result['error_type'] = "对象识别异常"
            result['details']['error'] = "关键字段缺失"
            print(f"   ❌ 关键字段缺失: project_name={project_name}, client_name={client_name}")
            return result
        
        print(f"   ✅ 对象识别正确: {export_type}")
        print(f"   ✅ 关键字段完整")
        
        # 检查 .filled.docx
        print(f"\n[3/3] 检查文档生成...")
        filled_path = Path(filled_docx_path) if filled_docx_path else REPORTS_DIR / f"{export_id}.filled.docx"
        
        if not filled_path.exists():
            if not template_ready:
                result['error_type'] = "模板映射异常"
                result['details']['error'] = "template_ready=False"
                print(f"   ⚠️  模板未配置")
                result['status'] = "⚠️部分通过"
                return result
            else:
                result['error_type'] = "文档生成异常"
                result['details']['error'] = "filled.docx不存在"
                print(f"   ❌ 文档不存在")
                return result
        
        print(f"   ✅ 文档生成成功: {filled_path.name}")
        result['status'] = "✅通过"
        result['error_type'] = None
        
    except Exception as e:
        result['error_type'] = "脚本异常"
        result['details']['exception'] = str(e)
        print(f"\n   ❌ 脚本异常: {e}")
    
    return result

def main():
    print("="*80)
    print("X1 系统 P0-4 可信测试基线（14 个 type_id）")
    print("="*80)
    
    # 登录
    if not login():
        print("\n❌ 登录失败，无法继续测试")
        sys.exit(1)
    
    # 执行测试
    results = []
    for type_id, payload in TEST_OBJECTS.items():
        result = test_object(type_id, payload)
        results.append(result)
    
    # 生成测试报告
    print("\n" + "="*80)
    print("测试报告汇总")
    print("="*80)
    
    # 按异常类型分组
    by_error_type = {}
    for r in results:
        error_type = r['error_type'] or "通过"
        by_error_type.setdefault(error_type, []).append(r)
    
    for error_type, items in sorted(by_error_type.items()):
        print(f"\n## {error_type} ({len(items)}项)")
        for r in items:
            print(f"  {r['status']} {r['type_id']}")
            if r['details']:
                for k, v in r['details'].items():
                    if k not in ['export_id', 'template_ready']:
                        print(f"      {k}: {v}")
    
    # 统计
    print("\n" + "="*80)
    print("总体评估")
    print("="*80)
    
    passed = sum(1 for r in results if r['status'] == "✅通过")
    partial = sum(1 for r in results if r['status'] == "⚠️部分通过")
    failed = sum(1 for r in results if r['status'] == "❌失败")
    
    print(f"✅ 通过: {passed}/14")
    print(f"⚠️  部分通过: {partial}/14")
    print(f"❌ 失败: {failed}/14")
    
    # 保存结果
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    result_file = Path(f"/Users/fuwuqi/检测报告生成系统_X1/test_baseline_{timestamp}.json")
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {result_file}")
    
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
