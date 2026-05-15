#!/usr/bin/env python3
"""
电子车间真实样本终验 - 哨兵验证（2026-05-07）
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

OUT_JSON = BASE_DIR / 'logs_x1' / 'electronics_workshop_sentinel_20260507.json'

CASES = [
    {'case_id': 'iso5', 'label': 'ISO 5', 'level_name': 'ISO 5', 'room_name': 'ISO5电子装配间', 'context': {'iso_level': 'ISO 5'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.5', 'expected_template_key': 'electronics/electronics_workshop/iso/5'},
    {'case_id': 'iso6', 'label': 'ISO 6', 'level_name': 'ISO 6', 'room_name': 'ISO6电子装配间', 'context': {'iso_level': 'ISO 6'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.6', 'expected_template_key': 'electronics/electronics_workshop/iso/6'},
    {'case_id': 'iso7', 'label': 'ISO 7', 'level_name': 'ISO 7', 'room_name': 'ISO7电子装配间', 'context': {'iso_level': 'ISO 7'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.7', 'expected_template_key': 'electronics/electronics_workshop/iso/7'},
    {'case_id': 'iso8', 'label': 'ISO 8', 'level_name': 'ISO 8', 'room_name': 'ISO8电子装配间', 'context': {'iso_level': 'ISO 8'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.8', 'expected_template_key': 'electronics/electronics_workshop/iso/8'},
    {'case_id': 'iso9', 'label': 'ISO 9', 'level_name': 'ISO 9', 'room_name': 'ISO9电子装配间', 'context': {'iso_level': 'ISO 9'}, 'expected_semantic_key': 'electronics.electronics_workshop.iso.9', 'expected_template_key': 'electronics/electronics_workshop/iso/9'},
]


def build_project(case):
    return {
        'project_name': f"电子车间哨兵-{case['case_id']}",
        'report_number': f"ELEC-SENTINEL-{case['case_id']}",
        'client_name': '测试电子车间',
        'contact_info': '13800000000',
        'project_address': '上海市精密制造园',
        'inspection_area': '电子车间哨兵区',
        'detection_date': '2026-05-07',
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
            'params': [],
            'context': case['context'],
        }]
    }


def main():
    rows = []
    passed = 0
    for case in CASES:
        payload = _build_export_payload(build_project(case))
        sem = (payload.get('clean_class_semantics') or {}).get('level_semantic_key', '')
        rule = payload.get('template_rule') or {}
        res = payload.get('template_resource') or {}
        checks = {
            'semantic_key_match': sem == case['expected_semantic_key'],
            'template_key_match': rule.get('template_key', '') == case['expected_template_key'],
            'resource_confirmed': res.get('resource_status') == 'confirmed',
            'template_found': res.get('template_found') is True,
        }
        row = {
            'case_id': case['case_id'],
            'label': case['label'],
            'expected_semantic_key': case['expected_semantic_key'],
            'actual_semantic_key': sem,
            'expected_template_key': case['expected_template_key'],
            'actual_template_key': rule.get('template_key', ''),
            'template_path': res.get('template_path', ''),
            'checks': checks,
            'all_pass': all(checks.values()),
        }
        rows.append(row)
        print(("PASS" if row['all_pass'] else "FAIL"), case['case_id'], '->', sem, '|', rule.get('template_key', ''))
        if row['all_pass']:
            passed += 1
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"SUMMARY {passed}/{len(rows)}")
    print(f"JSON: {OUT_JSON}")


if __name__ == '__main__':
    main()
