#!/usr/bin/env python3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

CASES = [
    {
        'name': 'animal_normal',
        'level_name': '普通环境',
        'room_name': '普通环境饲养室',
        'context': {'animal_environment': '普通环境'},
        'expected_key': 'biosafety/animal_room/normal',
    },
    {
        'name': 'animal_barrier_main',
        'level_name': '屏障环境',
        'room_name': '大鼠饲养室',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '主房间'},
        'expected_key': 'biosafety/animal_room/barrier-main',
    },
    {
        'name': 'animal_barrier_aux_clean_corridor',
        'level_name': '屏障环境',
        'room_name': '洁净走廊',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '洁净走廊'},
        'expected_key': 'biosafety/animal_room/barrier-aux/洁净走廊',
    },
    {
        'name': 'animal_isolation',
        'level_name': '隔离环境',
        'room_name': '隔离检疫室',
        'context': {'animal_environment': '隔离环境'},
        'expected_key': 'biosafety/animal_room/isolation',
    },
]


def build_project(case):
    return {
        'project_name': f"回归测试-{case['name']}",
        'report_number': f"回归测试-{case['name']}",
        'client_name': '测试动物中心',
        'contact_info': '13800000000',
        'project_address': '测试地址',
        'inspection_area': '动物房回归区',
        'detection_date': '2026-05-02',
        'domain': 'biosafety',
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': 'animal_room',
            'type_name': '动物房',
            'level_name': case['level_name'],
            'clean_class': case['level_name'],
            'basis': ['GB 14925-2023'],
            'judgement': ['GB 14925-2023'],
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
        facts = template_rule.get('facts', {})

        actual_key = template_rule.get('template_key')
        assert actual_key == case['expected_key'], f"{case['name']} template_key mismatch: {actual_key} != {case['expected_key']}"
        assert template_resource.get('resource_status') == 'confirmed', f"{case['name']} resource_status != confirmed"
        assert template_resource.get('template_found') is True, f"{case['name']} template_found != True"
        assert facts.get('animal_environment') == case['context'].get('animal_environment', ''), f"{case['name']} animal_environment mismatch"
        if 'barrier_room_class' in case['context']:
            assert facts.get('barrier_room_class') == case['context']['barrier_room_class'], f"{case['name']} barrier_room_class mismatch"
        if 'barrier_aux_room' in case['context']:
            assert facts.get('barrier_aux_room') == case['context']['barrier_aux_room'], f"{case['name']} barrier_aux_room mismatch"
        print(f"PASS {case['name']} -> {actual_key}")
        passed += 1

    print(f"SUMMARY {passed}/{len(CASES)}")


if __name__ == '__main__':
    main()
