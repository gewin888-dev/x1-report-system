#!/usr/bin/env python3
"""
动物房真实样本终验 - 扩展场景验证（2026-05-07）
重点验证 semantic/template 主链；template_path_exists 仅作观察项，不纳入主通过判定。
"""
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload  # noqa: E402

OUT_JSON = BASE_DIR / 'logs_x1' / 'animal_room_expanded_20260507.json'

CASES = [
    {
        'case_id': 'normal',
        'label': '普通环境',
        'level_name': '普通环境',
        'room_name': '普通环境饲养室',
        'context': {'animal_environment': '普通环境'},
        'expected_semantic_key': 'biosafety.animal_room.normal',
        'expected_template_key': 'biosafety/animal_room/normal',
    },
    {
        'case_id': 'barrier_main',
        'label': '屏障环境主房间',
        'level_name': '屏障环境',
        'room_name': '大鼠饲养室',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '主房间'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_main',
        'expected_template_key': 'biosafety/animal_room/barrier-main',
    },
    {
        'case_id': 'isolation',
        'label': '隔离环境',
        'level_name': '隔离环境',
        'room_name': '隔离检疫室',
        'context': {'animal_environment': '隔离环境'},
        'expected_semantic_key': 'biosafety.animal_room.isolation',
        'expected_template_key': 'biosafety/animal_room/isolation',
    },
    {
        'case_id': 'aux_clean_storage',
        'label': '屏障环境洁物储存室',
        'level_name': '屏障环境',
        'room_name': '洁物储存室',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '洁物储存室'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.clean_storage',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/洁物储存室',
    },
    {
        'case_id': 'aux_after_sterilization',
        'label': '屏障环境灭菌后室区',
        'level_name': '屏障环境',
        'room_name': '灭菌后室区',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '灭菌后室区'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.after_sterilization',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/灭菌后室区',
    },
    {
        'case_id': 'aux_clean_corridor',
        'label': '屏障环境洁净走廊',
        'level_name': '屏障环境',
        'room_name': '洁净走廊',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '洁净走廊'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.clean_corridor',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/洁净走廊',
    },
    {
        'case_id': 'aux_dirty_corridor',
        'label': '屏障环境污物走廊',
        'level_name': '屏障环境',
        'room_name': '污物走廊',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '污物走廊'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.dirty_corridor',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/污物走廊',
    },
    {
        'case_id': 'aux_buffer',
        'label': '屏障环境缓冲间',
        'level_name': '屏障环境',
        'room_name': '缓冲间',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '缓冲间'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.buffer',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/缓冲间',
    },
    {
        'case_id': 'aux_change_room_2',
        'label': '屏障环境二更',
        'level_name': '屏障环境',
        'room_name': '二更',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '二更'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.change_room_2',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/二更',
    },
    {
        'case_id': 'aux_cleaning_disinfection',
        'label': '屏障环境清洗消毒室',
        'level_name': '屏障环境',
        'room_name': '清洗消毒室',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '清洗消毒室'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.cleaning_disinfection',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/清洗消毒室',
    },
    {
        'case_id': 'aux_change_room_1',
        'label': '屏障环境一更',
        'level_name': '屏障环境',
        'room_name': '一更',
        'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '一更'},
        'expected_semantic_key': 'biosafety.animal_room.barrier_aux.change_room_1',
        'expected_template_key': 'biosafety/animal_room/barrier-aux/一更',
    },
]


def build_project(case):
    return {
        'project_name': f"动物房扩展-{case['case_id']}",
        'report_number': f"AR-EXP-{case['case_id']}",
        'client_name': '测试动物中心',
        'contact_info': '13800000000',
        'project_address': '上海市动物实验基地',
        'inspection_area': '动物房扩展区',
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
            'template_path_exists_observed': res.get('template_path_exists'),
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
