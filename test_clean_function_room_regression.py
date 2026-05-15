#!/usr/bin/env python3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

CASES = [
    {
        'name': 'clean_function_icu',
        'subroom': 'ICU病房',
        'room_name': 'ICU病房1',
        'expected_key': 'hospital/clean_function_room/icu',
    },
    {
        'name': 'clean_function_cssd',
        'subroom': '消毒供应中心',
        'room_name': '消毒供应中心1',
        'expected_key': 'hospital/clean_function_room/cssd',
    },
    {
        'name': 'clean_function_dialysis',
        'subroom': '透析室',
        'room_name': '透析室1',
        'expected_key': 'hospital/clean_function_room/dialysis',
    },
    {
        'name': 'clean_function_general',
        'subroom': '通用洁净功能用房',
        'room_name': '通用洁净功能用房1',
        'expected_key': 'hospital/clean_function_room/general',
    },
]


def build_project(case):
    return {
        'project_name': f"回归测试-{case['name']}",
        'report_number': f"回归测试-{case['name']}",
        'client_name': '测试医院',
        'contact_info': '13800000000',
        'project_address': '测试地址',
        'inspection_area': case['subroom'],
        'detection_date': '2026-05-02',
        'domain': 'hospital',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': 'clean_function_room',
            'type_name': '洁净功能用房',
            'level_name': 'Ⅲ级（万级）',
            'clean_class': 'Ⅲ级（万级）',
            'basis': ['GB 50333-2013'],
            'judgement': ['GB 50333-2013'],
            'summary': {'result_state': '合格'},
            'params': [],
            'context': {'clean_function_subroom': case['subroom']},
        }]
    }


def main():
    passed = 0
    for case in CASES:
        payload = _build_export_payload(build_project(case))
        template_rule = payload.get('template_rule', {})
        template_resource = payload.get('template_resource', {})
        facts = template_rule.get('facts', {})

        actual_key = template_rule.get('template_key')
        assert actual_key == case['expected_key'], f"{case['name']} template_key mismatch: {actual_key} != {case['expected_key']}"
        assert template_resource.get('resource_status') == 'confirmed', f"{case['name']} resource_status != confirmed"
        assert template_resource.get('template_found') is True, f"{case['name']} template_found != True"
        assert facts.get('clean_function_subroom') == case['subroom'], f"{case['name']} clean_function_subroom mismatch"
        print(f"PASS {case['name']} -> {actual_key}")
        passed += 1

    print(f"SUMMARY {passed}/{len(CASES)}")


if __name__ == '__main__':
    main()
