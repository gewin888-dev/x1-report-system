#!/usr/bin/env python3
"""
医院洁净部字段级内容终验（细项版）
对 main/eye/aux 的 filled.docx 做更细的字段落位检查。
"""
import json
import sys
from pathlib import Path
from zipfile import ZipFile

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload, build_template_filled_docx  # noqa: E402

OUT_DIR = BASE_DIR / 'reports_x1' / 'sentinel_20260507_fields'
OUT_DIR.mkdir(parents=True, exist_ok=True)

CASES = [
    {
        "case_id":"main_l1_fields",
        "label":"主手术室 L1 字段级终验",
        "room_name":"百级手术室",
        "level_name":"Ⅰ级",
        "clean_class":"Ⅰ级",
        "context":{"room_type":"main-room","clean_class_code":"level1","surgery_room_type":"手术室"},
        "expected_template_key":"hospital/operating_room/main/level1"
    },
    {
        "case_id":"eye_l1_fields",
        "label":"眼科手术室 L1 字段级终验",
        "room_name":"眼科手术室1",
        "level_name":"Ⅰ级",
        "clean_class":"Ⅰ级",
        "context":{"room_type":"main-room","clean_class_code":"level1","surgery_room_type":"眼科手术室"},
        "expected_template_key":"hospital/operating_room/main/level1"
    },
    {
        "case_id":"aux_l1_fields",
        "label":"洁净辅房 L1 字段级终验",
        "room_name":"体外循环室",
        "level_name":"Ⅰ级（局部5级其他6级）",
        "clean_class":"Ⅰ级（局部5级其他6级）",
        "context":{"surgery_room_type":"辅房","surgery_aux_room":"体外循环室","surgery_aux_clean_class":"Ⅰ级辅房"},
        "expected_template_key":"hospital/operating_room/aux/level1-local5-surround6"
    },
]

COMMON_VALUES = {
    "project_name": "终验细查项目",
    "report_number": "XC-20260507-001",
    "client_name": "上海终验医院",
    "contact_info": "13812345678",
    "project_address": "上海市浦东新区终验路88号",
    "inspection_area": "医院洁净部",
    "detection_date": "2026-05-07",
}

PARAM_VALUES = {
    "temperature": "23",
    "humidity": "55",
    "pressure": "12",
    "noise": "58",
    "illumination_main_room": "350",
    "illumination_aux_room": "220",
}


def build_project(case):
    return {
        **COMMON_VALUES,
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
                {"key": "temperature", "value": PARAM_VALUES["temperature"]},
                {"key": "humidity", "value": PARAM_VALUES["humidity"]},
                {"key": "pressure", "value": PARAM_VALUES["pressure"]},
                {"key": "noise", "value": PARAM_VALUES["noise"]},
                {"key": "illumination_main_room", "value": PARAM_VALUES["illumination_main_room"]},
                {"key": "illumination_aux_room", "value": PARAM_VALUES["illumination_aux_room"]},
            ],
            "context": case["context"],
        }]
    }


def extract_text(docx_path: Path) -> str:
    with ZipFile(docx_path, 'r') as zf:
        xml = zf.read('word/document.xml').decode('utf-8', errors='ignore')
    return xml


def count_contains(text: str, needle: str) -> int:
    return text.count(needle) if needle else 0


def inspect_case(case):
    payload = _build_export_payload(build_project(case))
    out_path = OUT_DIR / f"{case['case_id']}.filled.docx"
    built = build_template_filled_docx(payload, str(out_path))
    built_path = Path(built or out_path)
    text = extract_text(built_path) if built_path.exists() else ''

    detail_counts = {
        "project_name_count": count_contains(text, COMMON_VALUES["project_name"]),
        "report_number_count": count_contains(text, COMMON_VALUES["report_number"]),
        "client_name_count": count_contains(text, COMMON_VALUES["client_name"]),
        "contact_info_count": count_contains(text, COMMON_VALUES["contact_info"]),
        "project_address_count": count_contains(text, COMMON_VALUES["project_address"]),
        "detection_date_count": count_contains(text, COMMON_VALUES["detection_date"]),
        "room_name_count": count_contains(text, case["room_name"]),
        "temperature_count": count_contains(text, PARAM_VALUES["temperature"]),
        "humidity_count": count_contains(text, PARAM_VALUES["humidity"]),
        "pressure_count": count_contains(text, PARAM_VALUES["pressure"]),
        "noise_count": count_contains(text, PARAM_VALUES["noise"]),
        "illumination_main_room_count": count_contains(text, PARAM_VALUES["illumination_main_room"]),
        "illumination_aux_room_count": count_contains(text, PARAM_VALUES["illumination_aux_room"]),
    }

    checks = {
        "file_exists": built_path.exists(),
        "template_key_match": (payload.get('template_rule') or {}).get('template_key') == case['expected_template_key'],
        "project_name_written": detail_counts['project_name_count'] > 0,
        "report_number_written": detail_counts['report_number_count'] > 0,
        "client_name_written": detail_counts['client_name_count'] > 0,
        "contact_info_written": detail_counts['contact_info_count'] > 0,
        "project_address_written": detail_counts['project_address_count'] > 0,
        "detection_date_written": detail_counts['detection_date_count'] > 0,
        "room_name_written": detail_counts['room_name_count'] > 0,
        "temperature_written": detail_counts['temperature_count'] > 0,
        "humidity_written": detail_counts['humidity_count'] > 0,
        "pressure_written": detail_counts['pressure_count'] > 0,
        "noise_written": detail_counts['noise_count'] > 0,
        "illumination_main_written": detail_counts['illumination_main_room_count'] > 0,
        "illumination_aux_written": detail_counts['illumination_aux_room_count'] > 0,
    }

    return {
        "case_id": case['case_id'],
        "label": case['label'],
        "semantic_key": (payload.get('clean_class_semantics') or {}).get('level_semantic_key'),
        "template_key": (payload.get('template_rule') or {}).get('template_key'),
        "filled_docx": str(built_path),
        "detail_counts": detail_counts,
        "checks": checks,
        "all_pass": all(checks.values()),
    }


def main():
    rows = [inspect_case(case) for case in CASES]
    out_json = OUT_DIR / 'field_probe_summary.json'
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    passed = 0
    for row in rows:
        print(f"\n=== {row['label']} ===")
        print(f"semantic_key: {row['semantic_key']}")
        print(f"template_key: {row['template_key']}")
        print(f"filled_docx: {row['filled_docx']}")
        for k, v in row['checks'].items():
            print(f"  - {k}: {'PASS' if v else 'FAIL'}")
        print('  counts:', json.dumps(row['detail_counts'], ensure_ascii=False))
        print(f"RESULT: {'PASS' if row['all_pass'] else 'FAIL'}")
        if row['all_pass']:
            passed += 1
    print(f"\nSUMMARY {passed}/{len(rows)}")
    print(f"JSON: {out_json}")


if __name__ == '__main__':
    main()
