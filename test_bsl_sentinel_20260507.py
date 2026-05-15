#!/usr/bin/env python3
"""
BSL 真实样本终验 - 哨兵验证（2026-05-07）
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

OUT_JSON = BASE_DIR / 'logs_x1' / 'bsl_sentinel_20260507.json'

CASES = [
    {
        'case_id': 'p2',
        'label': 'P2 实验室',
        'level_name': 'P2',
        'room_name': 'P2实验室',
        'context': {'bsl_level': 'P2'},
        'expected_semantic_key': 'biosafety.bsl.p2',
        'expected_template_key': 'biosafety/bsl/p2',
    },
    {
        'case_id': 'p3',
        'label': 'P3 实验室',
        'level_name': 'P3',
        'room_name': 'P3实验室',
        'context': {'bsl_level': 'P3'},
        'expected_semantic_key': 'biosafety.bsl.p3',
        'expected_template_key': 'biosafety/bsl/p3',
    },
]


def build_project(case):
    return {
        'project_name': f"BSL哨兵-{case['case_id']}",
        'report_number': f"BSL-SENTINEL-{case['case_id']}",
        'client_name': '测试生物安全实验室',
        'contact_info': '13800000000',
        'project_address': '上海市生物安全园区',
        'inspection_area': 'BSL哨兵区',
        'detection_date': '2026-05-07',
        'domain': 'biosafety',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': 'bsl',
            'type_name': '生物安全实验室',
            'level_name': case['level_name'],
            'clean_class': case['level_name'],
            'basis': ['GB 50346-2011'],
            'judgement': ['GB 50346-2011'],
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
