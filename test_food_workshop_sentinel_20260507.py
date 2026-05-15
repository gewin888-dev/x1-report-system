#!/usr/bin/env python3
"""
食品车间真实样本终验 - 哨兵验证（2026-05-07）
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

OUT_JSON = BASE_DIR / 'logs_x1' / 'food_workshop_sentinel_20260507.json'

CASES = [
    {'case_id': 'grade_1', 'label': 'Ⅰ级', 'level_name': 'Ⅰ级', 'room_name': '食品Ⅰ级加工间', 'context': {'food_grade': 'Ⅰ级'}, 'expected_semantic_key': 'food.food_workshop.grade.1', 'expected_template_key': 'food/food_workshop/grade/1'},
    {'case_id': 'grade_2', 'label': 'Ⅱ级', 'level_name': 'Ⅱ级', 'room_name': '食品Ⅱ级加工间', 'context': {'food_grade': 'Ⅱ级'}, 'expected_semantic_key': 'food.food_workshop.grade.2', 'expected_template_key': 'food/food_workshop/grade/2'},
    {'case_id': 'grade_3', 'label': 'Ⅲ级', 'level_name': 'Ⅲ级', 'room_name': '食品Ⅲ级加工间', 'context': {'food_grade': 'Ⅲ级'}, 'expected_semantic_key': 'food.food_workshop.grade.3', 'expected_template_key': 'food/food_workshop/grade/3'},
    {'case_id': 'grade_4', 'label': 'Ⅳ级', 'level_name': 'Ⅳ级', 'room_name': '食品Ⅳ级加工间', 'context': {'food_grade': 'Ⅳ级'}, 'expected_semantic_key': 'food.food_workshop.grade.4', 'expected_template_key': 'food/food_workshop/grade/4'},
]


def build_project(case):
    return {
        'project_name': f"食品哨兵-{case['case_id']}",
        'report_number': f"FOOD-SENTINEL-{case['case_id']}",
        'client_name': '测试食品车间',
        'contact_info': '13800000000',
        'project_address': '上海市食品工业园',
        'inspection_area': '食品哨兵区',
        'detection_date': '2026-05-07',
        'domain': 'food',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': 'food_workshop',
            'type_name': '食品车间',
            'level_name': case['level_name'],
            'clean_class': case['level_name'],
            'basis': ['GB 50687-2011'],
            'judgement': ['GB 50687-2011'],
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
