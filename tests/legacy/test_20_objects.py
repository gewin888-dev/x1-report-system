#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抽检20个代表性对象 - API测试
"""
import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8082"
session = requests.Session()

# 抽检20个对象（覆盖所有领域，包含复杂类型）
TEST_CASES = [
    # 医院洁净部（5个）
    {"domain": "hospital", "type": "operating_room", "name": "手术室1", "desc": "洁净手术部-手术室"},
    {"domain": "hospital", "type": "operating_room", "name": "刷手间1", "desc": "洁净手术部-刷手间"},
    {"domain": "hospital", "type": "clean_function_room", "name": "ICU病房1", "desc": "洁净功能用房-ICU"},
    {"domain": "hospital", "type": "clean_function_room", "name": "消毒供应中心1", "desc": "洁净功能用房-消毒供应中心"},
    {"domain": "hospital", "type": "negative_pressure", "name": "负压病房1", "desc": "负压病房"},
    
    # 生物安全（8个）
    {"domain": "biosafety", "type": "bsl", "name": "BSL-2实验室", "desc": "实验室"},
    {"domain": "biosafety", "type": "animal_room", "name": "普通动物房1", "desc": "动物房-普通环境"},
    {"domain": "biosafety", "type": "animal_room", "name": "屏障主房间1", "desc": "动物房-屏障环境主房间"},
    {"domain": "biosafety", "type": "animal_room", "name": "洁净走廊1", "desc": "动物房-屏障环境洁净走廊"},
    {"domain": "biosafety", "type": "animal_room", "name": "隔离动物房1", "desc": "动物房-隔离环境"},
    {"domain": "biosafety", "type": "bsc", "name": "生物安全柜1", "desc": "生物安全柜"},
    {"domain": "biosafety", "type": "clean_bench", "name": "洁净工作台1", "desc": "洁净工作台"},
    {"domain": "biosafety", "type": "ivc", "name": "IVC笼具1", "desc": "IVC笼具"},
    
    # 食品加工（1个）
    {"domain": "food", "type": "food_workshop", "name": "食品车间1", "desc": "食品洁净车间"},
    
    # 制药工业（4个）
    {"domain": "pharma", "type": "laminar_hood", "name": "层流罩1", "desc": "层流罩"},
    {"domain": "pharma", "type": "pass_box", "name": "传递窗1", "desc": "传递窗"},
    {"domain": "pharma", "type": "gmp_workshop", "name": "GMP车间1", "desc": "GMP车间"},
    {"domain": "pharma", "type": "veterinary_gmp_workshop", "name": "兽药车间1", "desc": "兽药GMP车间"},
    
    # 精密制造/电子（2个）
    {"domain": "electronics", "type": "electronics_workshop", "name": "电子车间1", "desc": "电子洁净车间"},
    {"domain": "electronics", "type": "electronics_workshop", "name": "电子车间2", "desc": "电子洁净车间（重复测试）"},
]

issues = []

def log_issue(index, stage, message):
    """记录问题"""
    case = TEST_CASES[index]
    issues.append({
        "index": index + 1,
        "desc": case["desc"],
        "stage": stage,
        "message": message,
        "time": datetime.now().strftime("%H:%M:%S")
    })
    print(f"❌ [{index+1}/20] {stage}: {message}")

def login():
    """登录"""
    try:
        resp = session.post(f"{BASE_URL}/login", data={
            "username": "admin",
            "password": "pudi2026"
        }, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"❌ 登录失败: {e}")
        return False

def test_one(index):
    """测试单个对象"""
    case = TEST_CASES[index]
    print(f"\n{'='*60}")
    print(f"[{index+1}/20] {case['desc']}")
    print(f"{'='*60}")
    
    # 构造测试数据（符合API期望的格式）
    project_data = {
        "project_name": f"抽检{index+1:02d}-{case['desc']}",
        "report_number": f"TEST-{index+1:02d}",
        "client": "测试单位",
        "contact": "测试人 13800138000",
        "address": "测试地址",
        "area": "测试区域",
        "date": "2026-04-30",
        "state": "静态",
        "temperature": "22",
        "humidity": "50",
        "pressure": "1013",
        "domain": case["domain"],
        "rooms": [{
            "name": case["name"],
            "type": case["type"],
            "area": "50",
            "clean_class": "Ⅱ级",
            "design_air_changes": "30",
            "design_pressure": "10"
        }]
    }
    
    data = {
        "project": project_data
    }
    
    # 1. 暂存草稿
    try:
        resp = session.post(f"{BASE_URL}/api/x/save_draft", json=data, timeout=10)
        if resp.status_code != 200:
            log_issue(index, "暂存", f"HTTP {resp.status_code}")
            return False
        result = resp.json()
        if not result.get("success"):
            log_issue(index, "暂存", result.get("message", "失败"))
            return False
        draft_id = result.get("draft_id")
        print(f"✓ 暂存成功: {draft_id}")
    except Exception as e:
        log_issue(index, "暂存", str(e))
        return False
    
    time.sleep(0.3)
    
    # 2. 恢复草稿
    try:
        resp = session.get(f"{BASE_URL}/api/x/load_draft/{draft_id}", timeout=10)
        if resp.status_code != 200:
            log_issue(index, "恢复", f"HTTP {resp.status_code}")
            return False
        loaded = resp.json()
        # 检查draft字段中的project
        draft_data = loaded.get("draft", {})
        draft_project = draft_data.get("project", {})
        if draft_project.get("project_name") != project_data["project_name"]:
            log_issue(index, "恢复", f"数据不一致: 期望'{project_data['project_name']}', 实际'{draft_project.get('project_name')}'")
            return False
        print(f"✓ 恢复成功")
    except Exception as e:
        log_issue(index, "恢复", str(e))
        return False
    
    time.sleep(0.3)
    
    # 3. 导出报告
    try:
        resp = session.post(f"{BASE_URL}/api/x/submit_export", json=project_data, timeout=30)
        if resp.status_code != 200:
            log_issue(index, "导出", f"HTTP {resp.status_code}")
            return False
        result = resp.json()
        if not result.get("success"):
            log_issue(index, "导出", result.get("message", "失败"))
            return False
        
        export_id = result.get("export_id")
        print(f"✓ 导出成功: {export_id}")
        
        # 检查飞书
        feishu_report = result.get("feishu_report_url")
        feishu_export = result.get("feishu_export_url")
        
        if feishu_report:
            print(f"✓ 飞书报告: {feishu_report}")
        else:
            log_issue(index, "飞书", "报告未上传")
        
        if feishu_export:
            print(f"✓ 飞书原始记录: {feishu_export}")
        else:
            log_issue(index, "飞书", "原始记录未上传")
            
    except Exception as e:
        log_issue(index, "导出", str(e))
        return False
    
    print(f"✅ [{index+1}/20] 完成")
    return True

def main():
    print("="*60)
    print("抽检20个代表性对象 - API测试")
    print("="*60)
    
    if not login():
        return
    print("✓ 登录成功\n")
    
    passed = 0
    failed = 0
    
    for i in range(len(TEST_CASES)):
        if test_one(i):
            passed += 1
        else:
            failed += 1
        time.sleep(0.5)
    
    # 汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    print(f"总计: 20个对象")
    print(f"通过: {passed}个")
    print(f"失败: {failed}个")
    
    if issues:
        print(f"\n发现 {len(issues)} 个问题：")
        print("-"*60)
        for issue in issues:
            print(f"[{issue['index']}/20] {issue['desc']}")
            print(f"  阶段: {issue['stage']}")
            print(f"  问题: {issue['message']}")
            print(f"  时间: {issue['time']}")
            print()
        
        # 保存到文件
        with open("测试问题汇总.md", "a", encoding="utf-8") as f:
            f.write(f"\n\n## 测试结果 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})\n\n")
            f.write(f"- 总计: 20个对象\n")
            f.write(f"- 通过: {passed}个\n")
            f.write(f"- 失败: {failed}个\n\n")
            f.write(f"### 发现的问题 ({len(issues)}个)\n\n")
            for issue in issues:
                f.write(f"**[{issue['index']}/20] {issue['desc']}**\n")
                f.write(f"- 阶段: {issue['stage']}\n")
                f.write(f"- 问题: {issue['message']}\n")
                f.write(f"- 时间: {issue['time']}\n\n")
        
        print(f"\n问题已保存到: 测试问题汇总.md")
    else:
        print("\n✅ 所有测试通过，未发现问题")

if __name__ == "__main__":
    main()
