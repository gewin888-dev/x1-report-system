#!/usr/bin/env python3
"""X1系统完整端到端测试 - 13个已完成对象"""
import requests
import json
import os
from datetime import datetime

BASE_URL = "http://localhost:8082"

SCENARIOS = {
    "operating_room": {
        "domain": "hospital",
        "rooms": [{
            "type_id": "operating_room",
            "room_name": "手术室1",
            "level_name": "Ⅰ级",
            "clean_class": "Ⅰ级",
            "context": {
                "surgery_room_type": "I级",
                "换气次数": "≥30次/h",
                "静压差": "≥8Pa",
                "送风高效过滤器检漏": "合格",
                "≥0.5μm": "3520",
                "≥5μm": "0",
                "温度": "22.5",
                "相对湿度": "45",
                "平均照度": "350",
                "噪声": "55",
                "沉降菌": "0.2",
                "浮游菌": "5"
            }
        }]
    },
    "clean_function_room": {
        "domain": "hospital",
        "rooms": [{
            "type_id": "clean_function_room",
            "room_name": "ICU病房1",
            "level_name": "7级",
            "clean_class": "7级",
            "context": {
                "clean_function_subroom": "ICU病房",
                "换气次数": "≥15次/h",
                "静压差": "≥5Pa",
                "≥0.5μm": "352000",
                "≥5μm": "2900",
                "温度": "22.0",
                "相对湿度": "50",
                "平均照度": "300",
                "噪声": "50"
            }
        }]
    },
    "bsl": {
        "domain": "biosafety",
        "rooms": [{
            "type_id": "bsl",
            "room_name": "P2实验室",
            "level_name": "8级",
            "clean_class": "8级",
            "context": {
                "bsl_level": "BSL-2（P2）",
                "换气次数": "≥10次/h",
                "静压差": "-10Pa",
                "≥0.5μm": "3520000",
                "≥5μm": "29000",
                "温度": "20.0",
                "相对湿度": "55"
            }
        }]
    },
    "animal_room": {
        "domain": "biosafety",
        "rooms": [{
            "type_id": "animal_room",
            "room_name": "屏障环境饲养室",
            "level_name": "7级",
            "clean_class": "屏障环境",
            "context": {
                "animal_environment": "屏障环境",
                "barrier_room_class": "饲养室",
                "换气次数": "≥15次/h",
                "静压差": "≥20Pa",
                "≥0.5μm": "352000",
                "≥5μm": "2900",
                "温度": "22.0",
                "相对湿度": "50",
                "氨浓度": "10",
                "噪声": "55"
            }
        }]
    },
    "negative_pressure": {
        "domain": "hospital",
        "rooms": [{
            "type_id": "negative_pressure",
            "room_name": "负压隔离病房1",
            "level_name": "负压病房",
            "clean_class": "负压病房",
            "context": {
                "negative_pressure_mode": "ward-pressure-driven",
                "静压差": "-8",
                "airchange_polluted": "12",
                "airchange_clean": "8",
                "≥0.5μm": "3520000",
                "≥5μm": "29000",
                "温度": "22.0",
                "相对湿度": "50"
            }
        }]
    },
    "laminar_hood": {
        "domain": "pharma",
        "rooms": [{
            "type_id": "laminar_hood",
            "room_name": "垂直流洁净工作台1",
            "context": {
                "平均风速": "0.45",
                "风速不均匀度": "15",
                "≥0.5μm": "3520",
                "≥5μm": "0",
                "噪声": "60",
                "照度": "500"
            }
        }]
    },
    "gmp_workshop": {
        "domain": "pharma",
        "rooms": [{
            "type_id": "gmp_workshop",
            "room_name": "A级核心区",
            "level_name": "A级",
            "clean_class": "A级",
            "context": {
                "gmp_grade": "A级",
                "换气次数": "≥30次/h",
                "静压差": "≥10Pa",
                "≥0.5μm": "3520",
                "≥5μm": "0",
                "温度": "22.0",
                "相对湿度": "45",
                "浮游菌": "1",
                "沉降菌": "1"
            }
        }]
    },
    "food_workshop": {
        "domain": "food",
        "rooms": [{
            "type_id": "food_workshop",
            "room_name": "食品车间Ⅰ级区",
            "level_name": "Ⅰ级",
            "clean_class": "Ⅰ级",
            "context": {
                "food_grade": "Ⅰ级",
                "换气次数": "≥30次/h",
                "静压差": "≥10Pa",
                "≥0.5μm": "3520",
                "≥5μm": "0",
                "温度": "22.0",
                "相对湿度": "50"
            }
        }]
    },
    "bsc": {
        "domain": "biosafety",
        "rooms": [{
            "type_id": "bsc",
            "room_name": "生物安全柜1",
            "context": {
                "下降气流平均风速": "0.35",
                "流入气流平均风速": "0.55",
                "≥0.5μm": "3520",
                "≥5μm": "0",
                "噪声": "60",
                "照度": "500"
            }
        }]
    },
    "clean_bench": {
        "domain": "biosafety",
        "rooms": [{
            "type_id": "clean_bench",
            "room_name": "洁净工作台1",
            "context": {
                "平均风速": "0.45",
                "风速不均匀度": "15",
                "≥0.5μm": "3520",
                "≥5μm": "0",
                "噪声": "60",
                "照度": "500"
            }
        }]
    },
    "ivc": {
        "domain": "biosafety",
        "rooms": [{
            "type_id": "ivc",
            "room_name": "IVC笼具1",
            "context": {
                "笼内换气次数": "≥60次/h",
                "笼内静压差": "≥20Pa",
                "≥0.5μm": "3520",
                "≥5μm": "0",
                "氨浓度": "5",
                "噪声": "55"
            }
        }]
    },
    "pass_box": {
        "domain": "pharma",
        "rooms": [{
            "type_id": "pass_box",
            "room_name": "传递窗1",
            "context": {
                "inner_length": "1200",
                "inner_width": "800",
                "inner_height": "800",
                "紫外灯辐照强度": "120",
                "照度": "300"
            }
        }]
    },
    "veterinary_gmp_workshop": {
        "domain": "pharma",
        "rooms": [{
            "type_id": "veterinary_gmp_workshop",
            "room_name": "兽药车间万级区",
            "level_name": "万级",
            "clean_class": "万级",
            "context": {
                "gmp_grade": "万级",
                "换气次数": "≥20次/h",
                "静压差": "≥5Pa",
                "≥0.5μm": "352000",
                "≥5μm": "2900",
                "温度": "22.0",
                "相对湿度": "50"
            }
        }]
    },
    "electronics_workshop": {
        "domain": "electronics",
        "rooms": [{
            "type_id": "electronics_workshop",
            "room_name": "电子车间ISO6级",
            "level_name": "ISO6级",
            "clean_class": "ISO6级",
            "context": {
                "iso_level": "ISO6级",
                "换气次数": "≥25次/h",
                "静压差": "≥5Pa",
                "≥0.5μm": "35200",
                "≥5μm": "290",
                "温度": "22.0",
                "相对湿度": "45"
            }
        }]
    }
}

def test_scenario(name, payload):
    ts = int(datetime.now().timestamp())
    payload["record_id"] = f"test_{name}_{ts}"
    payload["report_date"] = "2026-04-29"
    
    print(f"\n{'='*60}")
    print(f"测试场景: {name}")
    print(f"{'='*60}")
    
    # 1. 保存草稿
    r = requests.post(f"{BASE_URL}/api/x/save_draft", json=payload)
    draft_id = r.json().get("draft_id")
    print(f"1. 草稿保存: {draft_id}")
    
    # 2. 加载草稿
    r = requests.get(f"{BASE_URL}/api/x/load_draft/{draft_id}")
    loaded = r.json().get("draft", {})
    print(f"2. 草稿加载: ✅ (saved_at: {loaded.get('saved_at', '')[:19]})")
    
    # 3. 提交导出
    r = requests.post(f"{BASE_URL}/api/x/submit_export", json=payload)
    result = r.json()
    export_id = result.get("export_id")
    template_ready = result.get("template_ready")
    filled_path = result.get("filled_docx_path", "")
    
    print(f"3. 导出提交: {export_id}")
    print(f"   template_ready: {template_ready}")
    
    # 4. 验证文件
    if template_ready and filled_path and os.path.exists(filled_path):
        size = os.path.getsize(filled_path)
        print(f"   ✅ filled.docx: {size:,} bytes")
    elif template_ready:
        print(f"   ❌ filled.docx 不存在")
    else:
        bound_path = f"reports_x1/{export_id}.bound.docx"
        if os.path.exists(bound_path):
            size = os.path.getsize(bound_path)
            print(f"   ⚠️  仅生成 bound.docx: {size:,} bytes (模板未就绪)")
        else:
            print(f"   ❌ 无导出文件")
    
    return {
        "name": name,
        "draft_id": draft_id,
        "export_id": export_id,
        "template_ready": template_ready,
        "success": template_ready and filled_path and os.path.exists(filled_path)
    }

if __name__ == "__main__":
    print("X1系统完整端到端测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试对象: {len(SCENARIOS)} 个")
    
    results = []
    for name, payload in SCENARIOS.items():
        try:
            result = test_scenario(name, payload)
            results.append(result)
        except Exception as e:
            print(f"❌ {name} 测试失败: {e}")
            results.append({"name": name, "success": False, "error": str(e)})
    
    print(f"\n{'='*60}")
    print("测试汇总")
    print(f"{'='*60}")
    success_count = sum(1 for r in results if r.get("success"))
    print(f"成功: {success_count}/{len(results)}")
    
    for r in results:
        status = "✅" if r.get("success") else "❌"
        print(f"{status} {r['name']}")
    
    if success_count == len(results):
        print("\n🎉 所有测试通过！")
    else:
        print(f"\n⚠️  {len(results) - success_count} 个测试失败")
