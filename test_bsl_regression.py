#!/usr/bin/env python3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

CASES = [
    {
        'name': 'bsl_p2',
        'bsl_level': 'BSL-2（P2）',
        'room_name': 'P2实验室主实验间',
        'expected_key': 'biosafety/bsl/p2',
    },
    {
        'name': 'bsl_p3',
        'bsl_level': 'BSL-3（P3）',
        'room_name': 'P3实验室主实验间',
        'expected_key': 'biosafety/bsl/p3',
    },
]


def build_project(case):
    return {
        'project_name': f"回归测试-{case['name']}",
        'report_number': f"回归测试-{case['name']}",
        'client_name': '测试研究所',
        'contact_info': '13800000000',
        'project_address': '测试地址',
        'inspection_area': case['bsl_level'],
        'detection_date': '2026-05-02',
        'domain': 'biosafety',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': 'bsl',
            'type_name': '生物安全实验室',
            'level_name': 'ISO 7',
            'clean_class': 'ISO 7',
            'basis': ['GB 50346-2011', 'GB 19489-2008'],
            'judgement': ['GB 50346-2011'],
            'summary': {'result_state': '合格'},
            'params': [],
            'context': {'bsl_level': case['bsl_level']},
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
        assert facts.get('bsl_level') == case['bsl_level'], f"{case['name']} bsl_level mismatch"
        print(f"PASS {case['name']} -> {actual_key}")
        passed += 1

    print(f"SUMMARY {passed}/{len(CASES)}")


if __name__ == '__main__':
    main()
