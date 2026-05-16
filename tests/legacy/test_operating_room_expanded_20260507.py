#!/usr/bin/env python3
"""
X1 医院洁净部 12 场景扩展哨兵检查（2026-05-07）
覆盖：main / eye / aux 各 4 个等级
目标：验证 semantic key 与 template key 全量闭合
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

CASES = [
    # main
    {"case_id":"main_l1","label":"主手术室 L1","room_name":"百级手术室","level_name":"Ⅰ级","clean_class":"Ⅰ级","context":{"room_type":"main-room","clean_class_code":"level1","surgery_room_type":"手术室"},"expected_semantic_key":"hospital.operating_room.main.level1","expected_template_key":"hospital/operating_room/main/level1"},
    {"case_id":"main_l2","label":"主手术室 L2","room_name":"千级手术室","level_name":"Ⅱ级","clean_class":"Ⅱ级","context":{"room_type":"main-room","clean_class_code":"level2","surgery_room_type":"手术室"},"expected_semantic_key":"hospital.operating_room.main.level2","expected_template_key":"hospital/operating_room/main/level2"},
    {"case_id":"main_l3","label":"主手术室 L3","room_name":"万级手术室","level_name":"Ⅲ级","clean_class":"Ⅲ级","context":{"room_type":"main-room","clean_class_code":"level3","surgery_room_type":"手术室"},"expected_semantic_key":"hospital.operating_room.main.level3","expected_template_key":"hospital/operating_room/main/level3"},
    {"case_id":"main_l4","label":"主手术室 L4","room_name":"十万级手术室","level_name":"Ⅳ级","clean_class":"Ⅳ级","context":{"room_type":"main-room","clean_class_code":"level4","surgery_room_type":"手术室"},"expected_semantic_key":"hospital.operating_room.main.level4","expected_template_key":"hospital/operating_room/main/level4"},

    # eye
    {"case_id":"eye_l1","label":"眼科手术室 L1","room_name":"眼科手术室1","level_name":"Ⅰ级","clean_class":"Ⅰ级","context":{"room_type":"main-room","clean_class_code":"level1","surgery_room_type":"眼科手术室"},"expected_semantic_key":"hospital.operating_room.eye.level1","expected_template_key":"hospital/operating_room/main/level1"},
    {"case_id":"eye_l2","label":"眼科手术室 L2","room_name":"眼科手术室2","level_name":"Ⅱ级","clean_class":"Ⅱ级","context":{"room_type":"main-room","clean_class_code":"level2","surgery_room_type":"眼科手术室"},"expected_semantic_key":"hospital.operating_room.eye.level2","expected_template_key":"hospital/operating_room/main/level2"},
    {"case_id":"eye_l3","label":"眼科手术室 L3","room_name":"眼科手术室3","level_name":"Ⅲ级","clean_class":"Ⅲ级","context":{"room_type":"main-room","clean_class_code":"level3","surgery_room_type":"眼科手术室"},"expected_semantic_key":"hospital.operating_room.eye.level3","expected_template_key":"hospital/operating_room/main/level3"},
    {"case_id":"eye_l4","label":"眼科手术室 L4","room_name":"眼科手术室4","level_name":"Ⅳ级","clean_class":"Ⅳ级","context":{"room_type":"main-room","clean_class_code":"level4","surgery_room_type":"眼科手术室"},"expected_semantic_key":"hospital.operating_room.eye.level4","expected_template_key":"hospital/operating_room/main/level4"},

    # aux
    {"case_id":"aux_l1","label":"洁净辅房 L1","room_name":"体外循环室","level_name":"Ⅰ级（局部5级其他6级）","clean_class":"Ⅰ级（局部5级其他6级）","context":{"surgery_room_type":"辅房","surgery_aux_room":"体外循环室","surgery_aux_clean_class":"Ⅰ级辅房"},"expected_semantic_key":"hospital.operating_room.aux.level1","expected_template_key":"hospital/operating_room/aux/level1-local5-surround6"},
    {"case_id":"aux_l2","label":"洁净辅房 L2","room_name":"刷手间","level_name":"Ⅱ级（7级）","clean_class":"Ⅱ级（7级）","context":{"surgery_room_type":"辅房","surgery_aux_room":"刷手间","surgery_aux_clean_class":"Ⅱ级辅房"},"expected_semantic_key":"hospital.operating_room.aux.level2","expected_template_key":"hospital/operating_room/aux/level2-iso7"},
    {"case_id":"aux_l3","label":"洁净辅房 L3","room_name":"术前准备室","level_name":"Ⅲ级（8级）","clean_class":"Ⅲ级（8级）","context":{"surgery_room_type":"辅房","surgery_aux_room":"术前准备室","surgery_aux_clean_class":"Ⅲ级辅房"},"expected_semantic_key":"hospital.operating_room.aux.level3","expected_template_key":"hospital/operating_room/aux/level3-iso8"},
    {"case_id":"aux_l4","label":"洁净辅房 L4","room_name":"恢复室","level_name":"Ⅳ级（8.5级）","clean_class":"Ⅳ级（8.5级）","context":{"surgery_room_type":"辅房","surgery_aux_room":"恢复室","surgery_aux_clean_class":"Ⅳ级辅房"},"expected_semantic_key":"hospital.operating_room.aux.level4","expected_template_key":"hospital/operating_room/aux/level4-iso85"},
]


def build_project(case):
    return {
        "project_name": f"终验扩展-{case['case_id']}",
        "report_number": f"TVX-{case['case_id']}",
        "client_name": "测试医院",
        "contact_info": "13800000000",
        "project_address": "测试地址",
        "inspection_area": "医院洁净部",
        "detection_date": "2026-05-07",
        "domain": "hospital",
        "rooms": [{
            "room_id": "r1",
            "room_name": case["room_name"],
            "type_id": "operating_room",
            "type_name": "手术室",
            "level_name": case["level_name"],
            "clean_class": case["clean_class"],
            "basis": ["GB 50333-2013"],
            "judgement": ["GB 50333-2013"],
            "summary": {"result_state": "合格"},
            "params": [
                {"key": "temperature", "value": "23"},
                {"key": "humidity", "value": "55"},
                {"key": "pressure", "value": "12"},
                {"key": "noise", "value": "58"},
                {"key": "illumination_main_room", "value": "350"},
                {"key": "illumination_aux_room", "value": "220"},
            ],
            "context": case["context"],
        }]
    }


def inspect_case(case):
    payload = _build_export_payload(build_project(case))
    rule = payload.get("template_rule") or {}
    resource = payload.get("template_resource") or {}
    semantics = payload.get("clean_class_semantics") or {}
    return {
        "case_id": case["case_id"],
        "label": case["label"],
        "expected_semantic_key": case["expected_semantic_key"],
        "actual_semantic_key": semantics.get("level_semantic_key", ""),
        "expected_template_key": case["expected_template_key"],
        "actual_template_key": rule.get("template_key", ""),
        "template_path": resource.get("template_path", ""),
        "checks": {
            "semantic_key_match": semantics.get("level_semantic_key", "") == case["expected_semantic_key"],
            "template_key_match": rule.get("template_key", "") == case["expected_template_key"],
            "resource_confirmed": resource.get("resource_status") == "confirmed",
            "template_found": resource.get("template_found") is True,
            "template_path_exists": bool(resource.get("template_path") and Path(resource.get("template_path")).exists()),
        }
    }


def main():
    rows = [inspect_case(case) for case in CASES]
    for row in rows:
        row["all_pass"] = all(row["checks"].values())
    out_path = BASE_DIR / "logs_x1" / "operating_room_expanded_20260507.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    passed = 0
    for row in rows:
        print(f"\n=== {row['label']} ===")
        print(f"semantic: {row['actual_semantic_key']}")
        print(f"template: {row['actual_template_key']}")
        for k, v in row['checks'].items():
            print(f"  - {k}: {'PASS' if v else 'FAIL'}")
        print(f"RESULT: {'PASS' if row['all_pass'] else 'FAIL'}")
        if row['all_pass']:
            passed += 1
    print(f"\nSUMMARY {passed}/{len(rows)}")
    print(f"JSON: {out_path}")


if __name__ == '__main__':
    main()
