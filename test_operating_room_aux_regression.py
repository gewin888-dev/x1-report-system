#!/usr/bin/env python3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

CASES = [
    {
        'name': 'aux_L1_room_type_legacy',
        'level_name': 'Ⅰ级（局部5级其他6级）',
        'context': {'room_type': 'auxiliary-room'},
        'expected_key': 'hospital/operating_room/aux/level1-local5-surround6',
    },
    {
        'name': 'aux_L2_surgery_room_type',
        'level_name': 'Ⅱ级（7级）',
        'context': {'surgery_room_type': '辅房'},
        'expected_key': 'hospital/operating_room/aux/level2-iso7',
    },
    {
        'name': 'aux_L3_legacy_alias',
        'level_name': 'Ⅲ级（8级）',
        'context': {'room_type': 'auxiliary-room', 'surgery_aux_clean_class': 'Ⅲ级辅房'},
        'expected_key': 'hospital/operating_room/aux/level3-iso8',
    },
    {
        'name': 'aux_L4_surgery_room_type',
        'level_name': 'Ⅳ级（8.5级）',
        'context': {'surgery_room_type': '辅房'},
        'expected_key': 'hospital/operating_room/aux/level4-iso85',
    },
]


def build_project(case):
    return {
        'project_name': f"回归测试-{case['name']}",
        'report_number': f"回归测试-{case['name']}",
        'client_name': '测试医院',
        'contact_info': '13800000000',
        'project_address': '测试地址',
        'inspection_area': '手术部辅房',
        'detection_date': '2026-05-02',
        'domain': 'hospital',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['name'],
            'type_id': 'operating_room',
            'type_name': '手术室',
            'level_name': case['level_name'],
            'clean_class': case['level_name'],
            'basis': ['GB 50333-2013'],
            'judgement': ['GB 50333-2013'],
            'summary': {'result_state': '合格'},
            'params': [],
            'context': case['context'],
        }]
    }


def main():
    passed = 0
    for case in CASES:
        payload = _build_export_payload(build_project(case))
        template_rule = payload.get('template_rule', {})
        template_resource = payload.get('template_resource', {})
        room_context = payload.get('room', {}).get('context', {})

        actual_key = template_rule.get('template_key')
        assert actual_key == case['expected_key'], f"{case['name']} template_key mismatch: {actual_key} != {case['expected_key']}"
        assert template_resource.get('resource_status') == 'confirmed', f"{case['name']} resource_status != confirmed"
        assert template_resource.get('template_found') is True, f"{case['name']} template_found != True"
        assert room_context.get('surgery_room_type') == '辅房', f"{case['name']} surgery_room_type not normalized"
        assert room_context.get('surgery_aux_clean_class'), f"{case['name']} surgery_aux_clean_class empty"
        print(f"PASS {case['name']} -> {actual_key}")
        passed += 1

    print(f"SUMMARY {passed}/{len(CASES)}")


if __name__ == '__main__':
    main()
