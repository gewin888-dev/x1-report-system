#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BASE = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(BASE))

from payload_normalizer import normalize_project_payload  # noqa: E402

CASES = [
    {
        'name': 'clean_function_room_icu',
        'raw': {
            'project_name': '闭环最小验证-洁净功能用房',
            'report_number': 'LOOP-001',
            'client': '测试单位',
            'date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{
                'type': 'clean_function_room',
                'name': 'ICU病房1',
                'subtype': 'ICU病房',
                'clean_class': 'Ⅲ级（万级）'
            }]
        },
        'expect': {
            'type_id': 'clean_function_room',
            'context_key': 'clean_function_subroom',
            'context_value': 'ICU病房',
            'clean_class': 'Ⅲ级（万级）',
        }
    },
    {
        'name': 'animal_room_barrier_aux',
        'raw': {
            'project_name': '闭环最小验证-动物房',
            'report_number': 'LOOP-002',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'biosafety',
            'rooms': [{
                'type_id': 'animal_room',
                'room_name': '传递间A',
                'subtype': '屏障环境-传递间',
                'level_name': '屏障环境'
            }]
        },
        'expect': {
            'type_id': 'animal_room',
            'context_key': 'barrier_aux_room',
            'context_value': '传递间',
            'clean_class': '屏障环境',
        }
    },
    {
        'name': 'bsl_p2',
        'raw': {
            'project_name': '闭环最小验证-BSL',
            'report_number': 'LOOP-003',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'biosafety',
            'rooms': [{
                'type_id': 'bsl',
                'room_name': 'P2实验室',
                'subtype': 'P2'
            }]
        },
        'expect': {
            'type_id': 'bsl',
            'context_key': 'bsl_level',
            'context_value': 'BSL-2（P2）',
            'clean_class': 'BSL-2（P2）',
        }
    },
    {
        'name': 'operating_room_aux',
        'raw': {
            'project_name': '闭环最小验证-手术辅房',
            'report_number': 'LOOP-004',
            'client': '测试单位',
            'date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{
                'type': 'operating_room',
                'name': '刷手间1',
                'subtype': '辅房',
                'clean_class': 'Ⅳ级（十万级）'
            }]
        },
        'expect': {
            'type_id': 'operating_room',
            'context_key': 'surgery_room_type',
            'context_value': '辅房',
            'clean_class': 'Ⅳ级（十万级）',
        }
    },
    {
        'name': 'gmp_grade_c',
        'raw': {
            'project_name': '闭环最小验证-GMP',
            'report_number': 'LOOP-005',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'pharma',
            'rooms': [{
                'type_id': 'gmp_workshop',
                'room_name': 'GMP车间1',
                'subtype': 'C级'
            }]
        },
        'expect': {
            'type_id': 'gmp_workshop',
            'context_key': 'gmp_grade',
            'context_value': 'C级',
            'clean_class': 'C级',
        }
    }
]

results = []
for case in CASES:
    saved = normalize_project_payload(case['raw'], source='draft')
    loaded = normalize_project_payload(saved, source='draft-load')
    room = (loaded.get('rooms') or [{}])[0]
    expect = case['expect']
    ok = (
        loaded.get('project_name', '').startswith('闭环最小验证')
        and loaded.get('detection_date') == '2026-05-02'
        and room.get('type_id') == expect['type_id']
        and room.get('clean_class') == expect['clean_class']
        and room.get('context', {}).get(expect['context_key']) == expect['context_value']
    )
    results.append({
        'name': case['name'],
        'project_name': loaded.get('project_name'),
        'client_name': loaded.get('client_name'),
        'detection_date': loaded.get('detection_date'),
        'room_type_id': room.get('type_id'),
        'room_name': room.get('room_name'),
        'clean_class': room.get('clean_class'),
        'context': room.get('context'),
        'ok': ok,
    })

print(json.dumps(results, ensure_ascii=False, indent=2))
