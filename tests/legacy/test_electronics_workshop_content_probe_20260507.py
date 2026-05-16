#!/usr/bin/env python3
"""
电子车间内容级抽样终验（2026-05-07）
"""
import json
import sys
from pathlib import Path
from zipfile import ZipFile

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload, build_template_filled_docx  # noqa: E402

OUT_DIR = BASE_DIR / 'reports_x1' / 'electronics_workshop_probe_20260507'
OUT_DIR.mkdir(parents=True, exist_ok=True)

CASES = [
    {'case_id': 'iso5', 'label': 'ISO 5', 'level_name': 'ISO 5', 'room_name': 'ISO5电子装配间', 'context': {'iso_level': 'ISO 5'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.5', 'expected_template_key': 'electronics/electronics_workshop/iso/5'},
    {'case_id': 'iso7', 'label': 'ISO 7', 'level_name': 'ISO 7', 'room_name': 'ISO7电子装配间', 'context': {'iso_level': 'ISO 7'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.7', 'expected_template_key': 'electronics/electronics_workshop/iso/7'},
    {'case_id': 'iso9', 'label': 'ISO 9', 'level_name': 'ISO 9', 'room_name': 'ISO9电子装配间', 'context': {'iso_level': 'ISO 9'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.9', 'expected_template_key': 'electronics/electronics_workshop/iso/9'},
]

COMMON = {
    'project_name': '电子车间终验项目',
    'report_number': 'ELEC-20260507-001',
    'client_name': '上海测试电子车间',
    'contact_info': '13912345678',
    'project_address': '上海市精密制造园8号',
    'inspection_area': '电子洁净检测区',
    'detection_date': '2026-05-07',
}

PARAMS = [
    {'key': 'temperature', 'value': '23'},
    {'key': 'humidity', 'value': '55'},
    {'key': 'noise', 'value': '58'},
    {'key': 'illumination_main_room', 'value': '300'},
]


def build_project(case):
    return {
        **COMMON,
        'domain': 'electronics',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': 'electronics_workshop',
            'type_name': '电子车间',
            'level_name': case['level_name'],
            'clean_class': case['level_name'],
            'basis': ['GB 50472-2008'],
            'judgement': ['GB 50472-2008'],
            'summary': {'result_state': '合格'},
            'params': PARAMS,
            'context': case['context'],
        }]
    }


def extract_text(docx_path: Path) -> str:
    with ZipFile(docx_path, 'r') as zf:
        return zf.read('word/document.xml').decode('utf-8', errors='ignore')


def inspect_case(case):
    payload = _build_export_payload(build_project(case))
    out_path = OUT_DIR / f"{case['case_id']}.filled.docx"
    built = build_template_filled_docx(payload, str(out_path))
    built_path = Path(built or out_path)
    text = extract_text(built_path) if built_path.exists() else ''

    checks = {
        'file_exists': built_path.exists(),
        'semantic_key_match': (payload.get('clean_class_semantics') or {}).get('level_semantic_key') == case['expected_semantic_key'],
        'template_key_match': (payload.get('template_rule') or {}).get('template_key') == case['expected_template_key'],
        'project_name_written': COMMON['project_name'] in text,
        'report_number_written': COMMON['report_number'] in text,
        'client_name_written': COMMON['client_name'] in text,
        'room_name_written': case['room_name'] in text,
        'temperature_written': '23' in text,
        'humidity_written': '55' in text,
        'noise_written': '58' in text,
        'illumination_written': '300' in text,
    }

    return {
        'case_id': case['case_id'],
        'label': case['label'],
        'filled_docx': str(built_path),
        'semantic_key': (payload.get('clean_class_semantics') or {}).get('level_semantic_key'),
        'template_key': (payload.get('template_rule') or {}).get('template_key'),
        'checks': checks,
        'all_pass': all(checks.values()),
    }


def main():
    rows = [inspect_case(case) for case in CASES]
    passed = 0
    for row in rows:
        print(f"\n=== {row['label']} ===")
        print(f"semantic_key: {row['semantic_key']}")
        print(f"template_key: {row['template_key']}")
        print(f"filled_docx: {row['filled_docx']}")
        for k, v in row['checks'].items():
            print(f"  - {k}: {'PASS' if v else 'FAIL'}")
        print(f"RESULT: {'PASS' if row['all_pass'] else 'FAIL'}")
        if row['all_pass']:
            passed += 1
    out_json = OUT_DIR / 'content_probe_summary.json'
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSUMMARY {passed}/{len(rows)}")
    print(f"JSON: {out_json}")


if __name__ == '__main__':
    main()
