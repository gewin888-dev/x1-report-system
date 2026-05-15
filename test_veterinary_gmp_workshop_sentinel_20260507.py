#!/usr/bin/env python3
"""
兽药 GMP 车间真实样本终验 - 哨兵验证（2026-05-07）
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

OUT_JSON = BASE_DIR / 'logs_x1' / 'veterinary_gmp_workshop_sentinel_20260507.json'

CASES = [
    {'case_id': 'grade_a', 'label': 'A级', 'level_name': 'A级', 'room_name': '兽药A级配液间', 'context': {'gmp_grade': 'A级'}, 'expected_semantic_key': 'pharma.veterinary_gmp_workshop.grade.a', 'expected_template_key': 'pharma/veterinary_gmp_workshop/grade/a'},
    {'case_id': 'grade_b', 'label': 'B级', 'level_name': 'B级', 'room_name': '兽药B级灌装间', 'context': {'gmp_grade': 'B级'}, 'expected_semantic_key': 'pharma.veterinary_gmp_workshop.grade.b', 'expected_template_key': 'pharma/veterinary_gmp_workshop/grade/b'},
    {'case_id': 'grade_c', 'label': 'C级', 'level_name': 'C级', 'room_name': '兽药C级配制间', 'context': {'gmp_grade': 'C级'}, 'expected_semantic_key': 'pharma.veterinary_gmp_workshop.grade.c', 'expected_template_key': 'pharma/veterinary_gmp_workshop/grade/c'},
    {'case_id': 'grade_d', 'label': 'D级', 'level_name': 'D级', 'room_name': '兽药D级准备间', 'context': {'gmp_grade': 'D级'}, 'expected_semantic_key': 'pharma.veterinary_gmp_workshop.grade.d', 'expected_template_key': 'pharma/veterinary_gmp_workshop/grade/d'},
]


def build_project(case):
    return {
        'project_name': f"兽药GMP哨兵-{case['case_id']}",
        'report_number': f"VGMP-SENTINEL-{case['case_id']}",
        'client_name': '测试兽药车间',
        'contact_info': '13800000000',
        'project_address': '上海市兽药工业园',
        'inspection_area': '兽药GMP哨兵区',
        'detection_date': '2026-05-07',
        'domain': 'pharma',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': 'veterinary_gmp_workshop',
            'type_name': '兽药GMP车间',
            'level_name': case['level_name'],
            'clean_class': case['level_name'],
            'basis': ['GB 50457-2019'],
            'judgement': ['GB 50457-2019'],
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
