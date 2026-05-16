#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X1系统14个对象全量参数测试脚本
测试每个对象的完整数据录入和导出功能
"""

import requests
import json
import time
from datetime import datetime

BASE_URL = "http://localhost:8082"

# 14个对象的测试配置
TEST_OBJECTS = [
    # 医院洁净部
    {"domain": "hospital", "type": "operating_room", "name": "手术室1", "subtype": "surgery_room"},
    {"domain": "hospital", "type": "clean_function_room", "name": "ICU病房1", "subtype": "icu"},
    {"domain": "hospital", "type": "negative_pressure", "name": "负压病房1", "subtype": None},
    
    # 生物安全
    {"domain": "biosafety", "type": "bsl", "name": "P2实验室1", "subtype": "p2"},
    {"domain": "biosafety", "type": "animal_room", "name": "屏障环境主房间1", "subtype": "barrier_main"},
    {"domain": "biosafety", "type": "bsc", "name": "生物安全柜1", "subtype": None},
    {"domain": "biosafety", "type": "clean_bench", "name": "超净台1", "subtype": None},
    {"domain": "biosafety", "type": "ivc", "name": "IVC笼具1", "subtype": None},
    
    # 食品加工
    {"domain": "food", "type": "food_workshop", "name": "食品车间1", "subtype": None},
    
    # 制药工业
    {"domain": "pharma", "type": "pass_box", "name": "传递窗1", "subtype": None},
    {"domain": "pharma", "type": "laminar_hood", "name": "层流罩1", "subtype": None},
    {"domain": "pharma", "type": "gmp_workshop", "name": "GMP车间A级", "subtype": "A"},
    {"domain": "pharma", "type": "veterinary_gmp_workshop", "name": "兽药车间A级", "subtype": "A"},
    
    # 精密制造/电子
    {"domain": "electronics", "type": "electronics_workshop", "name": "电子车间ISO5", "subtype": "ISO5"},
]

def login():
    """登录系统"""
    session = requests.Session()
    login_data = {"username": "admin", "password": "pudi2026"}
    r = session.post(f"{BASE_URL}/login", data=login_data, allow_redirects=False)
    return session

def create_minimal_record(session, obj_config):
    """创建最小化测试记录"""
    
    # 基础项目信息
    project_data = {
        "project_name": f"全量测试-{obj_config['name']}",
        "report_number": f"TEST-{int(time.time())}",
        "client": "测试单位",
        "contact": "测试人员 13800138000",
        "address": "测试地址",
        "area": "测试区域",
        "test_date": datetime.now().strftime("%Y-%m-%d"),
        "state": "static",
        "temperature": "22",
        "humidity": "55",
        "pressure": "1013",
        "domain": obj_config["domain"]
    }
    
    # 房间/设备数据
    room_data = {
        "name": obj_config["name"],
        "type": obj_config["type"],
        "length": "6",
        "width": "5",
        "height": "3"
    }
    
    if obj_config["subtype"]:
        room_data["subtype"] = obj_config["subtype"]
    
    # 最小化参数数据（根据对象类型填充）
    params = generate_minimal_params(obj_config["type"], obj_config["subtype"])
    room_data["params"] = params
    
    # 组装完整数据
    full_data = {
        **project_data,
        "rooms": [room_data]
    }
    
    return full_data

def generate_minimal_params(obj_type, subtype):
    """生成最小化参数数据"""
    
    # 通用参数
    common_params = {
        "temperature": ["22.1", "22.2", "22.3"],
        "humidity": ["54", "55", "56"],
        "pressure": ["1012", "1013", "1014"],
        "wind_speed": ["0.35", "0.36", "0.37"],
        "airchange": ["18", "19", "20"],
        "illumination": ["320", "330", "340"],
        "noise": ["58", "59", "60"]
    }
    
    # 洁净度参数
    particle_params = {
        "particle_0_5": ["100", "110", "120"],
        "particle_5_0": ["5", "6", "7"]
    }
    
    # 微生物参数
    bio_params = {
        "settling": ["2", "3", "4"],
        "floating": ["5", "6", "7"],
        "surface": ["3", "4", "5"]
    }
    
    # 根据对象类型返回相应参数
    if obj_type in ["operating_room", "clean_function_room", "bsl", "animal_room", 
                     "gmp_workshop", "veterinary_gmp_workshop", "food_workshop", "electronics_workshop"]:
        return {**common_params, **particle_params, **bio_params}
    elif obj_type in ["bsc", "clean_bench", "ivc"]:
        return {**common_params, **particle_params}
    elif obj_type in ["pass_box", "laminar_hood"]:
        return {**common_params, **particle_params}
    elif obj_type == "negative_pressure":
        return {**common_params, "pressure_diff": ["-8", "-9", "-10"]}
    else:
        return common_params

def test_object(session, obj_config, index, total):
    """测试单个对象"""
    print(f"\n{'='*60}")
    print(f"[{index}/{total}] 测试对象: {obj_config['name']} ({obj_config['type']})")
    print(f"{'='*60}")
    
    try:
        # 1. 创建记录数据
        record_data = create_minimal_record(session, obj_config)
        print(f"✓ 生成测试数据")
        
        # 2. 提交导出请求
        r = session.post(f"{BASE_URL}/export", json=record_data)
        
        if r.status_code == 200:
            result = r.json()
            if result.get("success"):
                print(f"✓ 导出成功")
                print(f"  报告文件: {result.get('report_file', 'N/A')}")
                print(f"  原始记录: {result.get('record_file', 'N/A')}")
                return True
            else:
                print(f"✗ 导出失败: {result.get('error', '未知错误')}")
                return False
        else:
            print(f"✗ HTTP错误: {r.status_code}")
            print(f"  响应: {r.text[:200]}")
            return False
            
    except Exception as e:
        print(f"✗ 异常: {e}")
        return False

def main():
    """主测试流程"""
    print("="*60)
    print("X1系统 14个对象全量参数测试")
    print("="*60)
    print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"测试对象数量: {len(TEST_OBJECTS)}")
    
    # 登录
    print("\n登录系统...")
    session = login()
    print("✓ 登录成功")
    
    # 测试统计
    results = []
    
    # 逐个测试
    for i, obj_config in enumerate(TEST_OBJECTS, 1):
        success = test_object(session, obj_config, i, len(TEST_OBJECTS))
        results.append({
            "name": obj_config["name"],
            "type": obj_config["type"],
            "success": success
        })
        time.sleep(1)  # 避免请求过快
    
    # 输出汇总
    print("\n" + "="*60)
    print("测试汇总")
    print("="*60)
    
    success_count = sum(1 for r in results if r["success"])
    fail_count = len(results) - success_count
    
    print(f"\n总计: {len(results)} 个对象")
    print(f"成功: {success_count} 个")
    print(f"失败: {fail_count} 个")
    
    if fail_count > 0:
        print("\n失败对象:")
        for r in results:
            if not r["success"]:
                print(f"  ✗ {r['name']} ({r['type']})")
    
    print(f"\n结束时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

if __name__ == "__main__":
    main()
