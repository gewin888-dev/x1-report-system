#!/usr/bin/env python3
"""
X1 医院洁净部 3 个哨兵样本终验执行脚本（2026-05-07）
- main L1
- eye L1
- aux L1

目标：
1. 验证 semantic 场景是否命中预期分支
2. 验证 template key / template path 是否命中预期模板链
3. 验证导出 payload 是否生成且资源存在
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

CASES = [
    {
        "case_id": "operating_room_main_L1_sentinel",
        "label": "主手术室 L1",
        "room_name": "百级手术室",
        "level_name": "Ⅰ级",
        "clean_class": "Ⅰ级",
        "context": {"room_type": "main-room", "clean_class_code": "level1", "surgery_room_type": "手术室"},
        "expected_template_key": "hospital/operating_room/main/level1",
        "expected_keywords": ["手术室", "Ⅰ级"],
    },
    {
        "case_id": "operating_room_eye_L1_sentinel",
        "label": "眼科手术室 L1",
        "room_name": "眼科手术室1",
        "level_name": "Ⅰ级",
        "clean_class": "Ⅰ级",
        "context": {"room_type": "main-room", "clean_class_code": "level1", "surgery_room_type": "眼科手术室"},
        "expected_template_key": "hospital/operating_room/main/level1",
        "expected_keywords": ["手术室", "Ⅰ级"],
        "expected_semantic_note_contains": "eye",
    },
    {
        "case_id": "operating_room_aux_L1_sentinel",
        "label": "洁净辅房 L1",
        "room_name": "体外循环室",
        "level_name": "Ⅰ级（局部5级其他6级）",
        "clean_class": "Ⅰ级（局部5级其他6级）",
        "context": {"surgery_room_type": "辅房", "surgery_aux_room": "体外循环室", "surgery_aux_clean_class": "Ⅰ级辅房"},
        "expected_template_key": "hospital/operating_room/aux/level1-local5-surround6",
        "expected_keywords": ["辅房", "体外循环室"],
    },
]


def build_project(case):
    return {
        "project_name": f"终验哨兵-{case['case_id']}",
        "report_number": f"TV-{case['case_id']}",
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
    room = payload.get("room") or {}
    room_ctx = room.get("context") or {}
    actual_key = rule.get("template_key")
    template_path = resource.get("template_path")
    template_name = Path(template_path).name if template_path else ""
    semantic_key = semantics.get("level_semantic_key") or semantics.get("semantic_key") or ""
    semantic_note = semantics.get("semantic_note") or ""

    checks = {
        "template_key_match": actual_key == case["expected_template_key"],
        "resource_confirmed": resource.get("resource_status") == "confirmed",
        "template_found": resource.get("template_found") is True,
        "template_path_exists": bool(template_path and Path(template_path).exists()),
    }
    if case.get("expected_semantic_note_contains"):
        checks["semantic_note_hint"] = case["expected_semantic_note_contains"] in semantic_note.lower()

    return {
        "case_id": case["case_id"],
        "label": case["label"],
        "room_name": case["room_name"],
        "expected_template_key": case["expected_template_key"],
        "actual_template_key": actual_key,
        "semantic_key": semantic_key,
        "semantic_note": semantic_note,
        "room_context": room_ctx,
        "template_path": template_path,
        "template_name": template_name,
        "checks": checks,
        "all_pass": all(checks.values()) if checks else False,
    }


def main():
    rows = [inspect_case(case) for case in CASES]
    out_path = BASE_DIR / "logs_x1" / "operating_room_sentinel_20260507.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    passed = 0
    for row in rows:
        print(f"\n=== {row['label']} ===")
        print(f"room_name: {row['room_name']}")
        print(f"semantic_key: {row['semantic_key']}")
        print(f"actual_template_key: {row['actual_template_key']}")
        print(f"template_name: {row['template_name']}")
        for k, v in row['checks'].items():
            print(f"  - {k}: {'PASS' if v else 'FAIL'}")
        print(f"RESULT: {'PASS' if row['all_pass'] else 'FAIL'}")
        if row['all_pass']:
            passed += 1

    print(f"\nSUMMARY {passed}/{len(rows)}")
    print(f"JSON: {out_path}")


if __name__ == '__main__':
    main()
