"""
X1系统全变体系统性测试
覆盖所有48个模板资源，每个变体独立测试草稿保存+导出生成
"""
import requests
import json
import os

BASE = "http://localhost:8082"

# ============================================================
# 公共context字段
# ============================================================
COMMON_CTX = {
    "换气次数": "≥15次/h",
    "静压差": "≥10Pa",
    "≥0.5μm": "3520000",
    "≥5μm": "29000",
    "温度": "22.0",
    "相对湿度": "50",
}

# ============================================================
# 所有变体定义
# 格式: (scenario_id, domain, type_id, room_name, level_name, clean_class, extra_context)
# ============================================================
VARIANTS = [
    # --- hospital.operating_room main-room (4个等级) ---
    ("operating_room_main_L1", "hospital", "operating_room", "百级手术室", "Ⅰ级", "Ⅰ级",
     {"room_type": "main-room", "clean_class_code": "level1"}),
    ("operating_room_main_L2", "hospital", "operating_room", "千级手术室", "Ⅱ级", "Ⅱ级",
     {"room_type": "main-room", "clean_class_code": "level2"}),
    ("operating_room_main_L3", "hospital", "operating_room", "万级手术室", "Ⅲ级", "Ⅲ级",
     {"room_type": "main-room", "clean_class_code": "level3"}),
    ("operating_room_main_L4", "hospital", "operating_room", "十万级手术室", "Ⅳ级", "Ⅳ级",
     {"room_type": "main-room", "clean_class_code": "level4"}),

    # --- hospital.operating_room auxiliary-room (4个等级) ---
    ("operating_room_aux_L1", "hospital", "operating_room", "辅房I级", "Ⅰ级（局部5级其他6级）", "Ⅰ级（局部5级其他6级）",
     {"room_type": "auxiliary-room"}),
    ("operating_room_aux_L2", "hospital", "operating_room", "辅房II级", "Ⅱ级（7级）", "Ⅱ级（7级）",
     {"room_type": "auxiliary-room"}),
    ("operating_room_aux_L3", "hospital", "operating_room", "辅房III级", "Ⅲ级（8级）", "Ⅲ级（8级）",
     {"room_type": "auxiliary-room"}),
    ("operating_room_aux_L4", "hospital", "operating_room", "辅房IV级", "Ⅳ级（8.5级）", "Ⅳ级（8.5级）",
     {"room_type": "auxiliary-room"}),

    # --- hospital.clean_function_room (4个子类型) ---
    ("clean_function_icu", "hospital", "clean_function_room", "ICU病房", "ICU病房", "ICU病房",
     {"clean_function_subroom": "ICU病房"}),
    ("clean_function_cssd", "hospital", "clean_function_room", "消毒供应中心", "消毒供应中心", "消毒供应中心",
     {"clean_function_subroom": "消毒供应中心"}),
    ("clean_function_dialysis", "hospital", "clean_function_room", "透析室", "透析室", "透析室",
     {"clean_function_subroom": "透析室"}),
    ("clean_function_general", "hospital", "clean_function_room", "通用洁净功能用房", "通用洁净功能用房", "通用洁净功能用房",
     {"clean_function_subroom": "通用洁净功能用房"}),

    # --- hospital.negative_pressure ---
    ("negative_pressure", "hospital", "negative_pressure", "负压隔离病房", "负压病房", "负压病房",
     {"negative_pressure_mode": "ward-pressure-driven", "静压差": "-8"}),

    # --- biosafety.bsl (2个等级) ---
    ("bsl_p2", "biosafety", "bsl", "BSL-2实验室", "BSL-2（P2）", "BSL-2",
     {"bsl_level": "BSL-2（P2）", "静压差": "-10Pa"}),
    ("bsl_p3", "biosafety", "bsl", "BSL-3实验室", "BSL-3（P3）", "BSL-3",
     {"bsl_level": "BSL-3（P3）", "静压差": "-15Pa"}),

    # --- biosafety.bsc ---
    ("bsc", "biosafety", "bsc", "生物安全柜1", "A2型", "A2型", {}),

    # --- biosafety.clean_bench ---
    ("clean_bench", "biosafety", "clean_bench", "洁净工作台1", "水平流", "水平流", {}),

    # --- biosafety.ivc ---
    ("ivc", "biosafety", "ivc", "IVC笼架1", "IVC", "IVC", {}),

    # --- biosafety.animal_room 普通环境 ---
    ("animal_room_normal", "biosafety", "animal_room", "普通环境饲养室", "普通环境", "普通环境",
     {"animal_environment": "普通环境", "barrier_room_class": "饲养室", "氨浓度": "10", "噪声": "55"}),

    # --- biosafety.animal_room 屏障环境主房间 ---
    ("animal_room_barrier_main", "biosafety", "animal_room", "屏障环境饲养室", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "饲养室", "氨浓度": "10", "噪声": "55"}),

    # --- biosafety.animal_room 屏障环境洁净辅房 (8个子类型) ---
    ("animal_room_barrier_aux_洁物储存室", "biosafety", "animal_room", "洁物储存室", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "洁物储存室"}),
    ("animal_room_barrier_aux_灭菌后室区", "biosafety", "animal_room", "灭菌后室区", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "灭菌后室区"}),
    ("animal_room_barrier_aux_洁净走廊", "biosafety", "animal_room", "洁净走廊", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "洁净走廊"}),
    ("animal_room_barrier_aux_污物走廊", "biosafety", "animal_room", "污物走廊", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "污物走廊"}),
    ("animal_room_barrier_aux_缓冲间", "biosafety", "animal_room", "缓冲间", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "缓冲间"}),
    ("animal_room_barrier_aux_二更", "biosafety", "animal_room", "二更", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "二更"}),
    ("animal_room_barrier_aux_清洗消毒室", "biosafety", "animal_room", "清洗消毒室", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "清洗消毒室"}),
    ("animal_room_barrier_aux_一更", "biosafety", "animal_room", "一更", "屏障环境", "屏障环境",
     {"animal_environment": "屏障环境", "barrier_room_class": "洁净辅房", "barrier_aux_room": "一更"}),

    # --- biosafety.animal_room 隔离环境 ---
    ("animal_room_isolation", "biosafety", "animal_room", "隔离环境饲养室", "隔离环境", "隔离环境",
     {"animal_environment": "隔离环境", "barrier_room_class": "饲养室", "氨浓度": "10", "噪声": "55"}),

    # --- pharma.pass_box ---
    ("pass_box", "pharma", "pass_box", "传递窗1", "", "", {}),

    # --- pharma.laminar_hood ---
    ("laminar_hood", "pharma", "laminar_hood", "垂直流洁净工作台1", "", "",
     {"平均风速": "0.45", "风速不均匀度": "15"}),

    # --- pharma.gmp_workshop (4个等级) ---
    ("gmp_workshop_A", "pharma", "gmp_workshop", "GMP车间A级", "A级", "A级", {}),
    ("gmp_workshop_B", "pharma", "gmp_workshop", "GMP车间B级", "B级", "B级", {}),
    ("gmp_workshop_C", "pharma", "gmp_workshop", "GMP车间C级", "C级", "C级", {}),
    ("gmp_workshop_D", "pharma", "gmp_workshop", "GMP车间D级", "D级", "D级", {}),

    # --- pharma.veterinary_gmp_workshop (4个等级) ---
    ("veterinary_gmp_A", "pharma", "veterinary_gmp_workshop", "兽药GMP车间A级", "A级", "A级", {}),
    ("veterinary_gmp_B", "pharma", "veterinary_gmp_workshop", "兽药GMP车间B级", "B级", "B级", {}),
    ("veterinary_gmp_C", "pharma", "veterinary_gmp_workshop", "兽药GMP车间C级", "C级", "C级", {}),
    ("veterinary_gmp_D", "pharma", "veterinary_gmp_workshop", "兽药GMP车间D级", "D级", "D级", {}),

    # --- food.food_workshop (4个等级) ---
    ("food_workshop_1", "food", "food_workshop", "食品车间Ⅰ级", "Ⅰ级", "Ⅰ级", {}),
    ("food_workshop_2", "food", "food_workshop", "食品车间Ⅱ级", "Ⅱ级", "Ⅱ级", {}),
    ("food_workshop_3", "food", "food_workshop", "食品车间Ⅲ级", "Ⅲ级", "Ⅲ级", {}),
    ("food_workshop_4", "food", "food_workshop", "食品车间Ⅳ级", "Ⅳ级", "Ⅳ级", {}),

    # --- electronics.electronics_workshop (5个ISO等级) ---
    ("electronics_iso5", "electronics", "electronics_workshop", "电子车间ISO5级", "ISO5级", "ISO5级", {}),
    ("electronics_iso6", "electronics", "electronics_workshop", "电子车间ISO6级", "ISO6级", "ISO6级", {}),
    ("electronics_iso7", "electronics", "electronics_workshop", "电子车间ISO7级", "ISO7级", "ISO7级", {}),
    ("electronics_iso8", "electronics", "electronics_workshop", "电子车间ISO8级", "ISO8级", "ISO8级", {}),
    ("electronics_iso9", "electronics", "electronics_workshop", "电子车间ISO9级", "ISO9级", "ISO9级", {}),
]


def build_payload(domain, type_id, room_name, level_name, clean_class, extra_ctx):
    ctx = dict(extra_ctx or {})
    explicit_context = dict(ctx.get('context') or {})

    room = {
        "room_id": "r1",
        "type_id": type_id,
        "room_name": room_name,
        "type_name": type_id,
        "level_name": level_name,
        "clean_class": clean_class,
        "basis": [],
        "judgement": [],
        "params": [],
        "summary": {
            "result_state": "合格",
            "judgement_active": [],
            "basis_primary": "",
            "judgement_primary": "",
        },
        "context": {},
    }

    if type_id == "operating_room":
        if explicit_context:
            room["context"] = explicit_context
        elif ctx.get("room_type") == "auxiliary-room":
            room["context"] = {"surgery_room_type": "辅房"}
        else:
            room["context"] = {"surgery_room_type": "手术室"}
    elif type_id == "clean_function_room":
        room["context"] = {"clean_function_subroom": extra_ctx.get("clean_function_subroom", room_name)}
    elif type_id == "negative_pressure":
        room["context"] = {"negative_pressure_mode": extra_ctx.get("negative_pressure_mode", "standard")}
    elif type_id == "bsl":
        room["context"] = {"bsl_level": extra_ctx.get("bsl_level", clean_class or level_name)}
    elif type_id == "animal_room":
        room["context"] = {
            k: v for k, v in {
                "animal_environment": extra_ctx.get("animal_environment"),
                "barrier_room_class": extra_ctx.get("barrier_room_class"),
                "barrier_aux_room": extra_ctx.get("barrier_aux_room"),
            }.items() if v
        }
    elif type_id in ("gmp_workshop", "veterinary_gmp_workshop"):
        room["context"] = {"gmp_grade": clean_class or level_name}
    elif type_id == "food_workshop":
        room["context"] = {"food_grade": clean_class or level_name}
    elif type_id == "electronics_workshop":
        iso = (clean_class or level_name or '').replace('级', '').replace('ISO', 'ISO ').replace('  ', ' ').strip()
        room["context"] = {"iso_level": iso}
        room["clean_class"] = iso
        room["level_name"] = iso
    elif type_id == "pass_box":
        room = {
            "room_id": "r1",
            "type_id": "pass_box",
            "room_name": room_name,
            "type_name": "pass_box",
            "level_name": "无等级要求",
            "clean_class": "无等级要求",
            "basis": [],
            "judgement": [],
            "params": [],
            "summary": {
                "result_state": "合格",
                "judgement_active": [],
                "basis_primary": "",
                "judgement_primary": "",
            },
            "context": {
                "inner_length": "600",
                "inner_width": "500",
                "inner_height": "500",
            }
        }
    elif type_id == "laminar_hood":
        room["level_name"] = room["level_name"] or "无等级要求"
        room["clean_class"] = room["clean_class"] or "无等级要求"

    basis_map = {
        "operating_room": ["GB 50333-2013"],
        "clean_function_room": ["GB 50333-2013"],
        "negative_pressure": ["GB/T 35428-2017"],
        "bsl": ["GB 50346-2011"],
        "animal_room": ["GB 14925-2023"],
        "bsc": ["NSF/ANSI 49-2019"],
        "clean_bench": ["JG/T 292-2010"],
        "ivc": ["GB 14925-2023"],
        "food_workshop": ["GB 50591-2010"],
        "laminar_hood": ["GB 50591-2010"],
        "pass_box": ["GB 50591-2010"],
        "gmp_workshop": ["GB 50591-2010"],
        "veterinary_gmp_workshop": ["GB 50591-2010"],
        "electronics_workshop": ["GB 50591-2010"],
    }
    judgement_map = {
        "operating_room": ["GB 50333-2013"],
        "clean_function_room": ["GB 50333-2013"],
        "negative_pressure": ["GB/T 35428-2017"],
        "bsl": ["GB 19489-2008"],
        "animal_room": ["GB 14925-2023"],
        "bsc": ["NSF/ANSI 49-2019"],
        "clean_bench": ["JG/T 292-2010"],
        "ivc": ["GB 14925-2023"],
        "food_workshop": ["GB 50687-2011"],
        "laminar_hood": ["JG/T 382-2012"],
        "pass_box": ["JG/T 382-2012"],
        "gmp_workshop": ["GB 50457-2019"],
        "veterinary_gmp_workshop": ["农业农村部令2020年第3号"],
        "electronics_workshop": ["GB 50472-2008"],
    }
    room["basis"] = basis_map.get(type_id, [])
    room["judgement"] = judgement_map.get(type_id, [])
    room["summary"]["judgement_active"] = room["judgement"][:1]
    room["summary"]["basis_primary"] = room["basis"][0] if room["basis"] else ""
    room["summary"]["judgement_primary"] = room["judgement"][0] if room["judgement"] else ""

    # 最小可判定参数：优先保证 deep test 能进入 judgement_engine，而不只是“能导出”
    minimal_params_map = {
        "operating_room": [{"key": "temperature", "value": "23"}],
        "clean_function_room": [{"key": "temperature", "value": "23"}],
        "negative_pressure": [{"key": "temperature", "value": "24"}],
        "bsl": [{"key": "temperature", "value": "22"}],
        "animal_room": [{"key": "temperature", "value": "22"}],
        "bsc": [{"key": "downflow_speed", "value": "0.35"}],
        "clean_bench": [{"key": "wind_speed", "value": "0.4"}],
        "ivc": [{"key": "airchange", "value": "30"}],
        "food_workshop": [{"key": "temperature", "value": "22"}],
        "laminar_hood": [{"key": "avg_speed", "value": "0.45"}],
        "pass_box": [{"key": "airchange_b12", "value": "15"}],
        "gmp_workshop": [{"key": "pressure", "value": "12"}],
        "veterinary_gmp_workshop": [{"key": "pressure", "value": "12"}],
        "electronics_workshop": [{"key": "pressure", "value": "8"}],
    }
    if not room.get("params"):
        room["params"] = minimal_params_map.get(type_id, [])

    return {
        "project_name": f"全变体测试-{type_id}-{room_name}",
        "report_number": f"VAR-{type_id.upper()}-001",
        "client_name": "X1全变体测试单位",
        "contact_info": "测试联系人 13800000000",
        "project_address": "测试地址",
        "inspection_area": room_name,
        "detection_date": "2026-05-02",
        "domain": domain,
        "domain_name": domain,
        "rooms": [room],
    }


def run_variant(scenario_id, payload):
    # 1. 保存草稿
    r = requests.post(f"{BASE}/api/x/save_draft", json=payload, timeout=15)
    if r.status_code != 200:
        return False, f"save_draft HTTP {r.status_code}"
    draft_id = r.json().get("draft_id")
    if not draft_id:
        return False, "no draft_id"

    # 2. 提交导出（直接传payload，submit_export不接受draft_id）
    r = requests.post(f"{BASE}/api/x/submit_export", json=payload, timeout=30)
    if r.status_code != 200:
        return False, f"submit_export HTTP {r.status_code}"
    data = r.json()
    export_id = data.get("export_id")
    template_ready = data.get("template_ready", False)
    template_key = data.get("template_rule", {}).get("template_key", "N/A")

    if not template_ready:
        return False, f"template_ready=False, template_key={template_key}"

    # 3. 检查filled.docx
    filled_path = f"reports_x1/{export_id}.filled.docx"
    if not os.path.exists(filled_path):
        return False, f"filled.docx not found: {filled_path}"
    size = os.path.getsize(filled_path)
    if size < 10000:
        return False, f"filled.docx too small: {size} bytes"

    return True, f"template_key={template_key}, size={size:,}B"


def main():
    passed = []
    failed = []

    print(f"X1全变体系统性测试 — 共{len(VARIANTS)}个变体\n")
    print(f"{'序号':<4} {'变体ID':<45} {'结果':<6} {'详情'}")
    print("-" * 110)

    for i, (scenario_id, domain, type_id, room_name, level_name, clean_class, extra_ctx) in enumerate(VARIANTS, 1):
        payload = build_payload(domain, type_id, room_name, level_name, clean_class, extra_ctx)
        ok, detail = run_variant(scenario_id, payload)
        status = "✅" if ok else "❌"
        print(f"{i:<4} {scenario_id:<45} {status}     {detail}")
        if ok:
            passed.append(scenario_id)
        else:
            failed.append((scenario_id, detail))

    print("-" * 110)
    print(f"\n测试汇总: {len(passed)}/{len(VARIANTS)} 通过")
    if failed:
        print(f"\n失败列表:")
        for sid, reason in failed:
            print(f"  ❌ {sid}: {reason}")
    else:
        print("\n🎉 全部通过！")


if __name__ == "__main__":
    main()
