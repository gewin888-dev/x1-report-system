#!/usr/bin/env python3
"""
X1系统超范围值判定测试
验证：提交含超标/正常实测值的payload，result_state字段是否正确传递并生成文件
"""
import json, os, warnings
warnings.filterwarnings('ignore')
import requests

BASE = "http://localhost:8082"
PASS = "\033[32m✅\033[0m"
FAIL = "\033[31m❌\033[0m"
WARN = "\033[33m⚠️\033[0m"

results = []

def submit(domain, rooms):
    r = requests.post(f"{BASE}/api/x/submit_export",
                      json={"domain": domain, "rooms": rooms}, timeout=30)
    r.raise_for_status()
    return r.json()

def check(label, domain, rooms, expected_result_state):
    try:
        d = submit(domain, rooms)
        ep = d.get("export_payload") or {}
        room_data = ep.get("room") or {}
        summary = room_data.get("summary") or {}
        result_state = summary.get("result_state") or ""
        filled_path = d.get("filled_docx_path") or ""
        bound_path  = d.get("bound_docx_path") or ""
        filled_size = os.path.getsize(filled_path) if filled_path and os.path.exists(filled_path) else 0
        bound_size  = os.path.getsize(bound_path)  if bound_path  and os.path.exists(bound_path)  else 0

        if result_state == expected_result_state:
            icon = PASS
            status = f"PASS  result={result_state}  filled={filled_size:,}B  bound={bound_size:,}B"
        else:
            icon = FAIL
            status = f"MISMATCH got={result_state!r} want={expected_result_state!r}"
    except Exception as e:
        icon = WARN
        status = f"ERROR: {str(e)[:80]}"

    results.append((icon, label, status))
    print(f"{icon}  {label:<52} {status}")

# ============================================================
# 超标 → 不合格
# ============================================================
check("operating_room_L1_温度超标(30>25)", "hospital", [{
    "type_id": "operating_room", "level_name": "Ⅰ级（百级）",
    "room_name": "手术室01", "clean_class": "Ⅰ级（百级）",
    "summary": {"result_state": "不合格"},
    "params": {"temperature": {"type": "numeric", "values": ["30"], "result": "30 ❌"}}
}], "不合格")

check("operating_room_L2_噪声超标(55>49)", "hospital", [{
    "type_id": "operating_room", "level_name": "Ⅱ级（千级）",
    "room_name": "手术室02", "clean_class": "Ⅱ级（千级）",
    "summary": {"result_state": "不合格"},
    "params": {"noise": {"type": "numeric", "values": ["55"], "result": "55 ❌"}}
}], "不合格")

check("operating_room_L3_换气不足(10<18)", "hospital", [{
    "type_id": "operating_room", "level_name": "Ⅲ级（万级）",
    "room_name": "手术室03", "clean_class": "Ⅲ级（万级）",
    "summary": {"result_state": "不合格"},
    "params": {"airchange": {"type": "numeric", "values": ["10"], "result": "10 ❌"}}
}], "不合格")

check("operating_room_L4_压差不足(2<5)", "hospital", [{
    "type_id": "operating_room", "level_name": "Ⅳ级（十万级）",
    "room_name": "手术室04", "clean_class": "Ⅳ级（十万级）",
    "summary": {"result_state": "不合格"},
    "params": {"pressure": {"type": "numeric", "values": ["2"], "result": "2 ❌"}}
}], "不合格")

check("negative_pressure_湿度超标(80>70)", "hospital", [{
    "type_id": "negative_pressure", "level_name": "负压病房",
    "room_name": "负压病房01",
    "summary": {"result_state": "不合格"},
    "params": {"humidity": {"type": "numeric", "values": ["80"], "result": "80 ❌"}}
}], "不合格")

check("gmp_workshop_A_温度超标(35>25)", "pharma", [{
    "type_id": "gmp_workshop", "level_name": "A级",
    "room_name": "GMP车间A01",
    "summary": {"result_state": "不合格"},
    "params": {"temperature": {"type": "numeric", "values": ["35"], "result": "35 ❌"}}
}], "不合格")

check("clean_function_room_ICU_噪声超标(70>60)", "hospital", [{
    "type_id": "clean_function_room", "level_name": "Ⅲ级（万级）",
    "clean_function_subroom": "ICU病房",
    "room_name": "ICU病房01",
    "summary": {"result_state": "不合格"},
    "params": {"noise": {"type": "numeric", "values": ["70"], "result": "70 ❌"}}
}], "不合格")

check("animal_room_barrier_温度超标(30>26)", "biosafety", [{
    "type_id": "animal_room", "level_name": "屏障环境",
    "animal_environment": "屏障环境", "barrier_room_class": "饲养室",
    "room_name": "屏障饲养室01",
    "summary": {"result_state": "不合格"},
    "params": {"temperature": {"type": "numeric", "values": ["30"], "result": "30 ❌"}}
}], "不合格")

check("bsc_风速不足(0.15<0.30)", "biosafety", [{
    "type_id": "bsc", "level_name": "II级A2型",
    "room_name": "生物安全柜01",
    "summary": {"result_state": "不合格"},
    "params": {"wind_speed": {"type": "numeric", "values": ["0.15"], "result": "0.15 ❌"}}
}], "不合格")

check("pass_box_压差不足(1<5)", "biosafety", [{
    "type_id": "pass_box", "level_name": "传递窗",
    "room_name": "传递窗01",
    "summary": {"result_state": "不合格"},
    "params": {"pressure": {"type": "numeric", "values": ["1"], "result": "1 ❌"}}
}], "不合格")

check("electronics_iso5_换气不足(20<50)", "electronics", [{
    "type_id": "electronics_workshop", "level_name": "ISO5级",
    "room_name": "电子车间ISO5-01",
    "summary": {"result_state": "不合格"},
    "params": {"airchange": {"type": "numeric", "values": ["20"], "result": "20 ❌"}}
}], "不合格")

check("operating_room_L2_混合(温度合格+湿度超标)", "hospital", [{
    "type_id": "operating_room", "level_name": "Ⅱ级（千级）",
    "room_name": "手术室混合",
    "summary": {"result_state": "不合格"},
    "params": {
        "temperature": {"type": "numeric", "values": ["23"], "result": "23 ✅"},
        "humidity":    {"type": "numeric", "values": ["75"], "result": "75 ❌"},
        "noise":       {"type": "numeric", "values": ["45"], "result": "45 ✅"},
    }
}], "不合格")

# ============================================================
# 正常值 → 合格
# ============================================================
check("operating_room_L1_温度合格(23)", "hospital", [{
    "type_id": "operating_room", "level_name": "Ⅰ级（百级）",
    "room_name": "手术室合格01", "clean_class": "Ⅰ级（百级）",
    "summary": {"result_state": "合格"},
    "params": {"temperature": {"type": "numeric", "values": ["23"], "result": "23 ✅"}}
}], "合格")

check("negative_pressure_湿度合格(50)", "hospital", [{
    "type_id": "negative_pressure", "level_name": "负压病房",
    "room_name": "负压病房合格",
    "summary": {"result_state": "合格"},
    "params": {"humidity": {"type": "numeric", "values": ["50"], "result": "50 ✅"}}
}], "合格")

check("gmp_workshop_C_温度合格(20)", "pharma", [{
    "type_id": "gmp_workshop", "level_name": "C级",
    "room_name": "GMP车间C合格",
    "summary": {"result_state": "合格"},
    "params": {"temperature": {"type": "numeric", "values": ["20"], "result": "20 ✅"}}
}], "合格")

check("animal_room_barrier_温度合格(22)", "biosafety", [{
    "type_id": "animal_room", "level_name": "屏障环境",
    "animal_environment": "屏障环境", "barrier_room_class": "饲养室",
    "room_name": "屏障饲养室合格",
    "summary": {"result_state": "合格"},
    "params": {"temperature": {"type": "numeric", "values": ["22"], "result": "22 ✅"}}
}], "合格")

# ============================================================
print()
total = len(results)
passed = sum(1 for r in results if r[0] == PASS)
failed = total - passed
print(f"测试汇总: {passed}/{total} 通过", end="")
if failed:
    print(f"  ({failed} 失败)")
    print()
    print("失败详情:")
    for icon, label, status in results:
        if icon != PASS:
            print(f"  {icon} {label}: {status}")
else:
    print()
    print("🎉 全部通过！")
