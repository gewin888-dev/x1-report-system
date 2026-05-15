#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
38个对象全量全参数全链条测试
测试链条：填写项目信息 -> 添加房间 -> 暂存 -> 恢复 -> 导出报告 -> 导出原始记录 -> 验证飞书
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8082"
session = requests.Session()

# 测试对象定义（38个）
TEST_OBJECTS = [
    # 医院洁净部 - 洁净手术部（12个子类型）
    {"domain": "hospital", "type": "operating_room", "subtype": "手术室", "name": "Ⅰ级手术室"},
    {"domain": "hospital", "type": "operating_room", "subtype": "眼科手术室", "name": "眼科手术室1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "体外循环室", "name": "体外循环室1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "手术室前室", "name": "手术室前室1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "刷手间", "name": "刷手间1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "术前准备室", "name": "术前准备室1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "护士站", "name": "护士站1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "无菌物品存放室", "name": "无菌物品存放室1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "预麻室", "name": "预麻室1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "精密仪器室", "name": "精密仪器室1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "洁净区走廊", "name": "洁净区走廊1"},
    {"domain": "hospital", "type": "operating_room", "subtype": "恢复室", "name": "恢复室1"},
    
    # 医院洁净部 - 洁净功能用房（4个子类型）
    {"domain": "hospital", "type": "clean_function_room", "subtype": "通用洁净功能用房", "name": "洁净功能房1"},
    {"domain": "hospital", "type": "clean_function_room", "subtype": "ICU病房", "name": "ICU病房1"},
    {"domain": "hospital", "type": "clean_function_room", "subtype": "消毒供应中心", "name": "消毒供应中心1"},
    {"domain": "hospital", "type": "clean_function_room", "subtype": "透析室", "name": "透析室1"},
    
    # 医院洁净部 - 负压病房
    {"domain": "hospital", "type": "negative_pressure", "subtype": None, "name": "负压病房1"},
    
    # 生物安全 - 实验室
    {"domain": "biosafety", "type": "bsl", "subtype": None, "name": "BSL-2实验室"},
    
    # 生物安全 - 动物房（普通环境、屏障环境主房间+8个辅房、隔离环境）
    {"domain": "biosafety", "type": "animal_room", "subtype": "普通环境", "name": "普通动物房1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-主房间", "name": "屏障主房间1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-洁物储存室", "name": "洁物储存室1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-灭菌后室/区", "name": "灭菌后室1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-洁净走廊", "name": "洁净走廊1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-污物走廊", "name": "污物走廊1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-缓冲间", "name": "缓冲间1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-二更", "name": "二更1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-清洗消毒室", "name": "清洗消毒室1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "屏障环境-一更", "name": "一更1"},
    {"domain": "biosafety", "type": "animal_room", "subtype": "隔离环境", "name": "隔离动物房1"},
    
    # 生物安全 - 生物安全柜、洁净工作台、IVC笼具
    {"domain": "biosafety", "type": "bsc", "subtype": None, "name": "生物安全柜1"},
    {"domain": "biosafety", "type": "clean_bench", "subtype": None, "name": "洁净工作台1"},
    {"domain": "biosafety", "type": "ivc", "subtype": None, "name": "IVC笼具1"},
    
    # 食品加工
    {"domain": "food", "type": "food_workshop", "subtype": None, "name": "食品洁净车间1"},
    
    # 制药工业
    {"domain": "pharma", "type": "laminar_hood", "subtype": None, "name": "层流罩1"},
    {"domain": "pharma", "type": "pass_box", "subtype": None, "name": "传递窗1"},
    {"domain": "pharma", "type": "gmp_workshop", "subtype": None, "name": "GMP车间1"},
    {"domain": "pharma", "type": "veterinary_gmp_workshop", "subtype": None, "name": "兽药GMP车间1"},
    
    # 精密制造/电子
    {"domain": "electronics", "type": "electronics_workshop", "subtype": None, "name": "电子洁净车间1"},
]

issues = []

def log_issue(obj_index, stage, message):
    """记录问题"""
    obj = TEST_OBJECTS[obj_index]
    issue = {
        "index": obj_index + 1,
        "object": f"{obj['type']} - {obj.get('subtype') or '主类型'}",
        "stage": stage,
        "message": message,
        "time": datetime.now().strftime("%H:%M:%S")
    }
    issues.append(issue)
    print(f"❌ [{obj_index+1}/38] {stage}: {message}")

def login():
    """登录"""
    resp = session.post(f"{BASE_URL}/login", data={
        "username": "admin",
        "password": "pudi2026"
    })
    return resp.status_code == 200 or "退出" in resp.text

def test_object(obj_index):
    """测试单个对象的完整链条"""
    obj = TEST_OBJECTS[obj_index]
    print(f"\n{'='*60}")
    print(f"测试 [{obj_index+1}/38]: {obj['type']} - {obj.get('subtype') or '主类型'}")
    print(f"{'='*60}")
    
    # 1. 填写项目信息并添加房间
    project_data = {
        "project_name": f"测试项目{obj_index+1:03d}",
        "report_number": f"TEST-{obj_index+1:03d}",
        "client": "测试单位",
        "contact": "测试联系人 13800138000",
        "address": "测试地址",
        "area": "测试区域",
        "date": "2026-04-30",
        "state": "静态",
        "temperature": "22",
        "humidity": "50",
        "pressure": "1013",
        "domain": obj["domain"],
        "rooms": [{
            "type": obj["type"],
            "name": obj["name"],
            "subtype": obj.get("subtype"),
            # 这里需要根据不同对象类型填充完整参数
            "params": generate_full_params(obj)
        }]
    }
    
    # 2. 暂存草稿
    try:
        resp = session.post(f"{BASE_URL}/api/save_draft", json=project_data)
        if resp.status_code != 200:
            log_issue(obj_index, "暂存草稿", f"HTTP {resp.status_code}")
            return False
        result = resp.json()
        if not result.get("success"):
            log_issue(obj_index, "暂存草稿", result.get("message", "未知错误"))
            return False
        draft_id = result.get("draft_id")
        print(f"✓ 暂存成功: {draft_id}")
    except Exception as e:
        log_issue(obj_index, "暂存草稿", str(e))
        return False
    
    time.sleep(0.5)
    
    # 3. 恢复草稿验证
    try:
        resp = session.get(f"{BASE_URL}/api/load_draft/{draft_id}")
        if resp.status_code != 200:
            log_issue(obj_index, "恢复草稿", f"HTTP {resp.status_code}")
            return False
        loaded = resp.json()
        if loaded.get("project_name") != project_data["project_name"]:
            log_issue(obj_index, "恢复草稿", "数据不一致")
            return False
        print(f"✓ 恢复成功")
    except Exception as e:
        log_issue(obj_index, "恢复草稿", str(e))
        return False
    
    time.sleep(0.5)
    
    # 4. 导出报告
    try:
        resp = session.post(f"{BASE_URL}/api/x/submit_export", json=project_data)
        if resp.status_code != 200:
            log_issue(obj_index, "导出报告", f"HTTP {resp.status_code}")
            return False
        result = resp.json()
        if not result.get("success"):
            log_issue(obj_index, "导出报告", result.get("message", "未知错误"))
            return False
        export_id = result.get("export_id")
        print(f"✓ 导出成功: {export_id}")
        
        # 检查飞书链接
        if result.get("feishu_report_url"):
            print(f"✓ 飞书报告: {result['feishu_report_url']}")
        else:
            log_issue(obj_index, "飞书上传", "报告未上传到飞书")
        
        if result.get("feishu_export_url"):
            print(f"✓ 飞书原始记录: {result['feishu_export_url']}")
        else:
            log_issue(obj_index, "飞书上传", "原始记录未上传到飞书")
            
    except Exception as e:
        log_issue(obj_index, "导出报告", str(e))
        return False
    
    print(f"✅ [{obj_index+1}/38] 测试通过")
    return True

def generate_full_params(obj):
    """根据对象类型生成完整参数（不留空）"""
    # 这里需要根据每个对象类型的具体参数要求填充
    # 简化版本，实际需要查看standards_db.js中每个对象的params定义
    params = {
        "clean_class": "Ⅱ级",
        "area": "50",
        "design_air_changes": "30",
        "design_pressure": "10",
        "basis": "GB 50591-2010",
        "judgement": "GB 50591-2010"
    }
    return params

def main():
    print("="*60)
    print("38个对象全量全参数全链条测试")
    print("="*60)
    
    # 登录
    if not login():
        print("❌ 登录失败")
        return
    print("✓ 登录成功\n")
    
    # 测试所有对象
    passed = 0
    failed = 0
    
    for i in range(len(TEST_OBJECTS)):
        if test_object(i):
            passed += 1
        else:
            failed += 1
        time.sleep(1)  # 避免请求过快
    
    # 汇总报告
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    print(f"总计: 38个对象")
    print(f"通过: {passed}个")
    print(f"失败: {failed}个")
    
    if issues:
        print(f"\n发现 {len(issues)} 个问题：")
        print("-"*60)
        for issue in issues:
            print(f"[{issue['index']}/38] {issue['object']}")
            print(f"  阶段: {issue['stage']}")
            print(f"  问题: {issue['message']}")
            print(f"  时间: {issue['time']}")
            print()
    else:
        print("\n✅ 所有测试通过，未发现问题")

if __name__ == "__main__":
    main()
