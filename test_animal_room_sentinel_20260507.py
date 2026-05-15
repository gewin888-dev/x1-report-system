#!/usr/bin/env python3
"""
动物房真实样本终验 - 哨兵验证（2026-05-07）
验证 semantic/template 命中链是否闭合。
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

OUT_JSON = BASE_DIR / 'logs_x1' / 'animal_room_sentinel_20260507.json'

CASES = [
    {
        'case_id': 'animal_normal',
        'label': '普通环境',
        'level_name': '普通环境',
        'room_name': '普通环境饲养室',
        'context': {'animal_environment': '普通环境'},
        'expected_semantic_key': 'biosafety.animal_room.normal',
        'expected_template_key': 'biosafety/animal_room/normal',
    },
    {
        'case_id': 'animal_barrier_main',
        'label': '屏障环境主房间',
        'level_name': '屏障环境',
        'room_name': '大鼠饲养室',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '主房间'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_main',
        'expected_template_key': 'biosafety/animal_room/barrier-main',
    },
    {
        'case_id': 'animal_isolation',
        'label': '隔离环境',
        'level_name': '隔离环境',
        'room_name': '隔离检疫室',
        'context': {'animal_environment': '隔离环境'},
        'expected_semantic_key': 'biosafety.animal_room.isolation',
        'expected_template_key': 'biosafety/animal_room/isolation',
    },
]


def build_project(case):
    return {
        'project_name': f"动物房哨兵-{case['case_id']}",
        'report_number': f"AR-SENTINEL-{case['case_id']}",
        'client_name': '测试动物中心',
        'contact_info': '13800000000',
        'project_address': '上海市动物实验基地',
        'inspection_area': '动物房哨兵区',
        'detection_date': '2026-05-07',
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
    rows = []
    passed = 0
    for case in CASES:
        payload = _build_export_payload(build_project(case))
        sem = (payload.get('clean_class_semantics') or {}).get('level_semantic_key', '')
        rule = payload.get('template_rule') or {}
        res = payload.get('template_resource') or {}
        row = {
            'case_id': case['case_id'],
            'label': case['label'],
            'expected_semantic_key': case['expected_semantic_key'],
            'actual_semantic_key': sem,
            'expected_template_key': case['expected_template_key'],
            'actual_template_key': rule.get('template_key', ''),
            'template_path': res.get('template_path', ''),
            'checks': {
                'semantic_key_match': sem == case['expected_semantic_key'],
                'template_key_match': rule.get('template_key', '') == case['expected_template_key'],
                'resource_confirmed': res.get('resource_status') == 'confirmed',
                'template_found': res.get('template_found') is True,
                'template_path_exists': bool(res.get('template_path_exists')),
            },
        }
        row['all_pass'] = all(row['checks'].values())
        rows.append(row)
        print(f"PASS {case['case_id']} -> sem={sem} tpl={rule.get('template_key','')}") if row['all_pass'] else print(f"FAIL {case['case_id']} -> {row['checks']}")
        if row['all_pass']:
            passed += 1
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"SUMMARY {passed}/{len(rows)}")
    print(f"JSON: {OUT_JSON}")


if __name__ == '__main__':
    main()
