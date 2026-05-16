#!/usr/bin/env python3
"""
X1系统深度测试脚本
测试9个对象的完整导出流程（带登录认证）
"""
import requests
from pathlib import Path
from zipfile import ZipFile
import sys

BASE_URL = "http://localhost:8082"
REPORTS_DIR = Path("/Users/fuwuqi/检测报告生成系统_X1/reports_x1")

# 全局session，保持登录状态
session = requests.Session()

def login():
    """登录获取session cookie"""
    # 先取登录页，建立初始 cookie
    session.get(f"{BASE_URL}/login", timeout=10)
    resp = session.post(
        f"{BASE_URL}/login",
        data={"username": "admin", "password": "pudi2026"},
        allow_redirects=True,
        timeout=10,
    )
    if resp.status_code == 200 and resp.url.rstrip('/') == f"{BASE_URL}":
        print("✅ 登录成功")
        return True
    if '退出' in resp.text or '管理员' in resp.text or '检测系统' in resp.text:
        print("✅ 登录成功")
        return True
    print(f"❌ 登录失败: {resp.status_code} {resp.text[:120]}")
    return False

# 测试数据定义
TEST_OBJECTS = {
    "operating_room": {
        "name": "洁净手术部",
        "payload": {
            "project_name": "测试项目-手术室",
            "report_number": "TEST-OR-001",
            "client_name": "测试医院",
            "contact_info": "张医生 13800000001",
            "project_address": "北京市测试区",
            "inspection_area": "手术部",
            "detection_date": "2026-04-28",
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
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["GB 50333-2013"],
                    "basis_primary": "GB 50333-2013",
                    "judgement_primary": "GB 50333-2013"
                },
                "context": {
                    "surgery_room_type": "手术室"
                }
            }]
        },
        "keywords": ["测试项目-手术室", "测试医院", "百级手术室", "GB 50333-2013", "合格"]
    },
    "clean_function_room": {
        "name": "洁净功能用房-ICU",
        "payload": {
            "project_name": "测试项目-ICU",
            "report_number": "TEST-ICU-001",
            "client_name": "测试医院ICU",
            "contact_info": "李护士 13800000002",
            "project_address": "上海市测试区",
            "inspection_area": "ICU病房",
            "detection_date": "2026-04-28",
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
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["GB 50333-2013"],
                    "basis_primary": "GB 50333-2013",
                    "judgement_primary": "GB 50333-2013"
                },
                "context": {
                    "clean_function_subroom": "ICU病房"
                }
            }]
        },
        "keywords": ["测试项目-ICU", "测试医院ICU", "ICU病房1", "GB 50333-2013", "合格"]
    },
    "bsl": {
        "name": "实验室",
        "payload": {
            "project_name": "测试项目-生物安全实验室",
            "report_number": "TEST-BSL-001",
            "client_name": "测试研究所",
            "contact_info": "王研究员 13800000003",
            "project_address": "广州市测试区",
            "inspection_area": "P2实验室",
            "detection_date": "2026-04-28",
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
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["GB 19489-2008"],
                    "basis_primary": "GB 50346-2011",
                    "judgement_primary": "GB 19489-2008"
                },
                "context": {
                    "bsl_level": "BSL-2（P2）"
                }
            }]
        },
        "keywords": ["测试项目-生物安全实验室", "测试研究所", "P2实验室主实验间", "GB 19489-2008", "合格"]
    },
    "animal_room": {
        "name": "动物房",
        "payload": {
            "project_name": "测试项目-动物房",
            "report_number": "TEST-ANIMAL-001",
            "client_name": "测试动物中心",
            "contact_info": "赵主任 13800000004",
            "project_address": "深圳市测试区",
            "inspection_area": "屏障环境动物房",
            "detection_date": "2026-04-28",
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
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["GB 14925-2023"],
                    "basis_primary": "GB 14925-2023",
                    "judgement_primary": "GB 14925-2023"
                },
                "context": {
                    "animal_environment": "屏障环境",
                    "barrier_room_class": "主房间"
                }
            }]
        },
        "keywords": ["测试项目-动物房", "测试动物中心", "屏障环境饲养间", "GB 14925-2023", "合格"]
    },
    "laminar_hood": {
        "name": "层流罩",
        "payload": {
            "project_name": "测试项目-层流罩",
            "report_number": "TEST-HOOD-001",
            "client_name": "测试制药厂",
            "contact_info": "钱工 13800000005",
            "project_address": "杭州市测试区",
            "inspection_area": "灌装车间",
            "detection_date": "2026-04-28",
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
                "judgement": ["JG/T 382-2012", "GB 50591-2010"],
                "params": [],
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["JG/T 382-2012"],
                    "basis_primary": "GB 50591-2010",
                    "judgement_primary": "JG/T 382-2012"
                },
                "context": {}
            }]
        },
        "keywords": ["测试项目-层流罩", "测试制药厂", "灌装线层流罩", "JG/T 382-2012", "合格"]
    },
    "gmp_workshop": {
        "name": "GMP车间",
        "payload": {
            "project_name": "测试项目-GMP车间",
            "report_number": "TEST-GMP-001",
            "client_name": "测试药业公司",
            "contact_info": "孙经理 13800000006",
            "project_address": "南京市测试区",
            "inspection_area": "C级洁净区",
            "detection_date": "2026-04-28",
            "domain": "pharma",
            "domain_name": "制药工业",
            "rooms": [{
                "room_id": "r1",
                "room_name": "C级配液间",
                "type_id": "gmp_workshop",
                "type_name": "GMP车间",
                "level_name": "C级",
                "clean_class": "C级",
                "basis": ["GB 50591-2010", "GB/T 16292-2010"],
                "judgement": ["GB 50457-2019", "GB 50591-2010", "GMP 2010"],
                "params": [],
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["GB 50457-2019"],
                    "basis_primary": "GB 50591-2010",
                    "judgement_primary": "GB 50457-2019"
                },
                "context": {
                    "gmp_grade": "C级",
                    "gmp_context_mode": "grade-driven"
                }
            }]
        },
        "keywords": ["测试项目-GMP车间", "测试药业公司", "C级配液间", "GB 50457-2019", "合格"]
    },
    "food_workshop": {
        "name": "食品洁净车间",
        "payload": {
            "project_name": "测试项目-食品车间",
            "report_number": "TEST-FOOD-001",
            "client_name": "测试食品厂",
            "contact_info": "周厂长 13800000007",
            "project_address": "成都市测试区",
            "inspection_area": "十万级灌装车间",
            "detection_date": "2026-04-28",
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
                "judgement": ["GB 50591-2010", "GB 50687-2011"],
                "params": [],
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["GB 50687-2011"],
                    "basis_primary": "GB 50591-2010",
                    "judgement_primary": "GB 50687-2011"
                },
                "context": {
                    "food_grade": "Ⅲ级（十万级）",
                    "food_context_mode": "grade-driven"
                }
            }]
        },
        "keywords": ["测试项目-食品车间", "测试食品厂", "十万级灌装间", "GB 50687-2011", "合格"]
    },
    "pass_box": {
        "name": "传递窗",
        "payload": {
            "project_name": "测试项目-传递窗",
            "report_number": "TEST-PASS-001",
            "client_name": "测试制药企业",
            "contact_info": "吴工 13800000008",
            "project_address": "武汉市测试区",
            "inspection_area": "洁净区传递窗",
            "detection_date": "2026-04-28",
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
                "judgement": ["JG/T 382-2012", "GB 50591-2010"],
                "params": [],
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["JG/T 382-2012"],
                    "basis_primary": "GB 50591-2010",
                    "judgement_primary": "JG/T 382-2012"
                },
                "context": {}
            }]
        },
        "keywords": ["测试项目-传递窗", "测试制药企业", "D级传递窗", "JG/T 382-2012", "合格"]
    },
    "veterinary_gmp_workshop": {
        "name": "兽药车间",
        "payload": {
            "project_name": "测试项目-兽药车间",
            "report_number": "TEST-VET-001",
            "client_name": "测试兽药公司",
            "contact_info": "郑总 13800000009",
            "project_address": "长沙市测试区",
            "inspection_area": "C级兽药生产区",
            "detection_date": "2026-04-28",
            "domain": "pharma",
            "domain_name": "制药工业",
            "rooms": [{
                "room_id": "r1",
                "room_name": "C级兽药配制间",
                "type_id": "veterinary_gmp_workshop",
                "type_name": "兽药车间",
                "level_name": "C级",
                "clean_class": "C级",
                "basis": ["GB 50591-2010", "GB/T 16292-2010"],
                "judgement": ["GB 50457-2019", "农业农村部令2020年第3号"],
                "params": [],
                "summary": {
                    "result_state": "合格",
                    "judgement_active": ["农业农村部令2020年第3号"],
                    "basis_primary": "GB 50591-2010",
                    "judgement_primary": "农业农村部令2020年第3号"
                },
                "context": {
                    "gmp_grade": "C级",
                    "gmp_context_mode": "grade-driven",
                    "pharma_context_variant": "veterinary-gmp"
                }
            }]
        },
        "keywords": ["测试项目-兽药车间", "测试兽药公司", "C级兽药配制间", "农业农村部令2020年第3号", "合格"]
    }
}

def test_object(obj_id, obj_data):
    """测试单个对象"""
    print(f"\n{'='*80}")
    print(f"测试对象: {obj_data['name']} ({obj_id})")
    print(f"{'='*80}")
    
    result = {
        "object_id": obj_id,
        "object_name": obj_data['name'],
        "status": "❌失败",
        "details": {}
    }
    
    try:
        # 1. 提交导出请求
        print(f"\n[1/4] 提交导出请求...")
        response = session.post(
            f"{BASE_URL}/api/x/submit_export",
            json={"project": obj_data['payload']},
            timeout=30
        )
        
        if response.status_code != 200:
            result['details']['api_error'] = f"HTTP {response.status_code}"
            print(f"   ❌ API调用失败: HTTP {response.status_code}")
            return result
        
        data = response.json()
        if not data.get('success'):
            result['details']['api_error'] = data.get('error', 'Unknown error')
            print(f"   ❌ API返回失败: {data.get('error')}")
            return result
        
        export_id = data.get('export_id')
        template_ready = data.get('template_ready', False)
        filled_docx_path = data.get('filled_docx_path', '')
        
        print(f"   ✅ 导出ID: {export_id}")
        print(f"   ℹ️  template_ready: {template_ready}")
        print(f"   ℹ️  filled_docx_path: {filled_docx_path}")
        
        result['details']['export_id'] = export_id
        result['details']['template_ready'] = template_ready
        
        # 2. 检查 .filled.docx 是否存在
        print(f"\n[2/4] 检查 .filled.docx 文件...")
        filled_path = Path(filled_docx_path) if filled_docx_path else REPORTS_DIR / f"{export_id}.filled.docx"
        
        if not filled_path.exists():
            result['details']['file_missing'] = str(filled_path)
            print(f"   ❌ 文件不存在: {filled_path}")
            if not template_ready:
                print(f"   ⚠️  原因: template_ready=False (模板未配置)")
                result['status'] = "⚠️部分通过"
                result['details']['reason'] = "模板未配置，无法生成filled.docx"
            return result
        
        print(f"   ✅ 文件存在: {filled_path}")
        result['details']['file_exists'] = True
        
        # 3. 检查文件内容
        print(f"\n[3/4] 检查文档内容...")
        try:
            with ZipFile(filled_path, 'r') as docx:
                # 读取 document.xml
                doc_xml = docx.read('word/document.xml').decode('utf-8')
                
                # 检查关键字段
                keywords_found = []
                keywords_missing = []
                
                for keyword in obj_data['keywords']:
                    if keyword in doc_xml:
                        keywords_found.append(keyword)
                        print(f"   ✅ 找到: {keyword}")
                    else:
                        keywords_missing.append(keyword)
                        print(f"   ❌ 缺失: {keyword}")
                
                result['details']['keywords_found'] = keywords_found
                result['details']['keywords_missing'] = keywords_missing
                
                # 检查是否有占位符残留
                placeholders = []
                placeholder_patterns = ['{{', '}}', '【', '】待填']
                for pattern in placeholder_patterns:
                    if pattern in doc_xml:
                        placeholders.append(pattern)
                
                if placeholders:
                    result['details']['placeholders_found'] = placeholders
                    print(f"   ⚠️  发现占位符残留: {placeholders}")
                
        except Exception as e:
            result['details']['content_check_error'] = str(e)
            print(f"   ❌ 内容检查失败: {e}")
            return result
        
        # 4. 综合评估
        print(f"\n[4/4] 综合评估...")
        if len(keywords_missing) == 0:
            result['status'] = "✅通过"
            print(f"   ✅ 所有关键字段已填入")
        elif len(keywords_found) >= len(obj_data['keywords']) * 0.7:
            result['status'] = "⚠️部分通过"
            print(f"   ⚠️  部分字段填入 ({len(keywords_found)}/{len(obj_data['keywords'])})")
        else:
            result['status'] = "❌失败"
            print(f"   ❌ 大部分字段缺失 ({len(keywords_found)}/{len(obj_data['keywords'])})")
        
    except Exception as e:
        result['details']['exception'] = str(e)
        print(f"\n   ❌ 测试异常: {e}")
    
    return result

def main():
    print("="*80)
    print("X1系统深度测试 - 9个对象完整测试")
    print("="*80)
    
    # 检查服务是否运行
    try:
        response = requests.get(f"{BASE_URL}/api/x/health", timeout=5)
        if response.status_code == 200:
            print(f"✅ X1服务运行正常: {BASE_URL}")
        else:
            print(f"❌ X1服务异常: HTTP {response.status_code}")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 无法连接X1服务: {e}")
        sys.exit(1)
    
    # 登录
    if not login():
        sys.exit(1)

    # 执行测试
    results = []
    for obj_id, obj_data in TEST_OBJECTS.items():
        result = test_object(obj_id, obj_data)
        results.append(result)
    
    # 生成测试报告
    print("\n" + "="*80)
    print("测试报告汇总")
    print("="*80)
    
    for result in results:
        print(f"\n{result['status']} {result['object_name']} ({result['object_id']})")
        
        if result['details'].get('export_id'):
            print(f"   导出ID: {result['details']['export_id']}")
        
        if result['details'].get('template_ready') is not None:
            print(f"   模板状态: {'✅已配置' if result['details']['template_ready'] else '❌未配置'}")
        
        if result['details'].get('file_exists'):
            print(f"   文件生成: ✅")
        elif result['details'].get('file_missing'):
            print(f"   文件生成: ❌ (路径: {result['details']['file_missing']})")
        
        if result['details'].get('keywords_found'):
            print(f"   关键字段: {len(result['details']['keywords_found'])}/{len(result['details'].get('keywords_found', [])) + len(result['details'].get('keywords_missing', []))} 已填入")
        
        if result['details'].get('keywords_missing'):
            print(f"   缺失字段: {', '.join(result['details']['keywords_missing'][:3])}{'...' if len(result['details']['keywords_missing']) > 3 else ''}")
        
        if result['details'].get('placeholders_found'):
            print(f"   ⚠️  占位符残留: {result['details']['placeholders_found']}")
        
        if result['details'].get('api_error'):
            print(f"   ❌ API错误: {result['details']['api_error']}")
        
        if result['details'].get('exception'):
            print(f"   ❌ 异常: {result['details']['exception']}")
        
        if result['details'].get('reason'):
            print(f"   说明: {result['details']['reason']}")
    
    # 统计
    print("\n" + "="*80)
    print("总体评估")
    print("="*80)
    
    passed = sum(1 for r in results if r['status'] == "✅通过")
    partial = sum(1 for r in results if r['status'] == "⚠️部分通过")
    failed = sum(1 for r in results if r['status'] == "❌失败")
    
    print(f"✅ 通过: {passed}/{len(results)}")
    print(f"⚠️  部分通过: {partial}/{len(results)}")
    print(f"❌ 失败: {failed}/{len(results)}")
    
    if passed == len(results):
        print("\n🎉 所有对象测试通过！")
    elif passed + partial == len(results):
        print("\n⚠️  部分对象需要完善模板配置")
    else:
        print("\n❌ 存在失败的测试，需要修复")

if __name__ == "__main__":
    main()
