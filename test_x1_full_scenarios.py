#!/usr/bin/env python3
"""X1 全场景端到端测试 - 模拟真人使用流程"""
import requests, json, time, sys
from datetime import datetime

BASE_URL = "http://localhost:8082"
session = requests.Session()

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# 测试场景配置
SCENARIOS = [
    {
        "name": "手术室-I级",
        "domain": "hospital",
        "type_id": "operating_room",
        "room_name": "手术室1",
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
    },
    {
        "name": "BSL-2实验室",
        "domain": "biosafety",
        "type_id": "bsl",
        "room_name": "BSL-2生物安全实验室",
        "context": {
            "bsl_level": "BSL-2",
            "换气次数": "≥12次/h",
            "静压差": "≥-10Pa",
            "送风高效过滤器检漏": "合格",
            "排风高效过滤器检漏": "合格",
            "≥0.5μm": "352000",
            "≥5μm": "2930",
            "温度": "22.0",
            "相对湿度": "50",
            "平均照度": "300",
            "噪声": "60"
        }
    },
    {
        "name": "GMP车间-C级",
        "domain": "pharma",
        "type_id": "gmp_workshop",
        "room_name": "GMP洁净车间C级",
        "context": {
            "gmp_grade": "C级",
            "换气次数": "≥25次/h",
            "静压差": "≥10Pa",
            "送风高效过滤器检漏": "合格",
            "≥0.5μm": "352000",
            "≥5μm": "2930",
            "温度": "22.5",
            "相对湿度": "45",
            "平均照度": "300",
            "噪声": "65"
        }
    },
    {
        "name": "生物安全柜",
        "domain": "biosafety",
        "type_id": "bsc",
        "room_name": "II级A2型生物安全柜",
        "context": {
            "bsc_type": "II级A2型",
            "下降气流平均风速": "0.38",
            "流入气流平均风速": "0.52",
            "≥0.5μm": "3.5",
            "噪声": "58"
        }
    },
    {
        "name": "传递窗",
        "domain": "pharma",
        "type_id": "pass_box",
        "room_name": "传递窗PB-01",
        "context": {
            "inner_length": "1200",
            "inner_width": "800",
            "inner_height": "800",
            "紫外灯辐照强度": "120"
        }
    }
]

def test_scenario(scenario):
    """测试单个场景的完整流程"""
    log(f"\n{'='*60}")
    log(f"测试场景: {scenario['name']}")
    log(f"{'='*60}")
    
    # 1. 保存草稿
    draft_payload = {
        "record_id": f"test_{scenario['type_id']}_{int(time.time())}",
        "report_date": datetime.now().strftime("%Y-%m-%d"),
        "domain": scenario["domain"],
        "rooms": [{
            "type_id": scenario["type_id"],
            "room_name": scenario["room_name"],
            "context": scenario["context"]
        }]
    }
    
    log(f"1️⃣  保存草稿...")
    r = session.post(f"{BASE_URL}/api/x/save_draft", json=draft_payload, timeout=10)
    if r.status_code != 200:
        log(f"❌ 保存草稿失败: {r.status_code}")
        return False
    draft_data = r.json()
    draft_id = draft_data.get("draft_id")
    log(f"✅ 草稿已保存: {draft_id}")
    
    # 2. 列出草稿
    log(f"2️⃣  列出草稿...")
    r = session.get(f"{BASE_URL}/api/x/list_drafts", timeout=10)
    if r.status_code != 200:
        log(f"❌ 列出草稿失败")
        return False
    drafts = r.json().get("drafts", [])
    found = any(d.get("draft_id") == draft_id for d in drafts)
    log(f"✅ 草稿列表包含当前草稿: {found}")
    
    # 3. 加载草稿
    log(f"3️⃣  加载草稿...")
    r = session.get(f"{BASE_URL}/api/x/load_draft/{draft_id}", timeout=10)
    if r.status_code != 200:
        log(f"❌ 加载草稿失败")
        return False
    loaded = r.json()
    log(f"✅ 草稿已加载: {loaded.get('record_id')}")
    
    # 4. 提交并导出
    log(f"4️⃣  提交并导出...")
    r = session.post(f"{BASE_URL}/api/x/submit_export", json=draft_payload, timeout=30)
    if r.status_code != 200:
        log(f"❌ 导出失败: {r.status_code}")
        return False
    export_data = r.json()
    export_id = export_data.get("export_id")
    log(f"✅ 导出成功: {export_id}")
    
    # 5. 列出导出记录
    log(f"5️⃣  列出导出记录...")
    r = session.get(f"{BASE_URL}/api/x/list_exports", timeout=10)
    if r.status_code != 200:
        log(f"❌ 列出导出记录失败")
        return False
    exports = r.json().get("exports", [])
    found = any(e.get("export_id") == export_id for e in exports)
    log(f"✅ 导出列表包含当前记录: {found}")
    
    # 6. 保存正式记录
    log(f"6️⃣  保存正式记录...")
    r = session.post(f"{BASE_URL}/api/save", json=draft_payload, timeout=10)
    if r.status_code != 200:
        log(f"❌ 保存记录失败")
        return False
    log(f"✅ 正式记录已保存")
    
    # 7. 获取记录
    log(f"7️⃣  获取记录...")
    r = session.get(f"{BASE_URL}/api/get/{draft_payload['record_id']}", timeout=10)
    if r.status_code != 200:
        log(f"❌ 获取记录失败")
        return False
    record = r.json()
    log(f"✅ 记录已获取: {record.get('record_id')}")
    
    log(f"\n✅ 场景 [{scenario['name']}] 全流程测试通过\n")
    return True

def main():
    log("开始X1全场景端到端测试")
    log(f"测试场景数: {len(SCENARIOS)}")
    
    results = []
    for scenario in SCENARIOS:
        try:
            success = test_scenario(scenario)
            results.append((scenario['name'], success))
            time.sleep(1)
        except Exception as e:
            log(f"❌ 场景 [{scenario['name']}] 测试异常: {e}")
            results.append((scenario['name'], False))
    
    log(f"\n{'='*60}")
    log("测试汇总")
    log(f"{'='*60}")
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        log(f"{status} - {name}")
    
    passed = sum(1 for _, s in results if s)
    log(f"\n总计: {passed}/{len(results)} 通过")
    
    return 0 if passed == len(results) else 1

if __name__ == "__main__":
    sys.exit(main())
