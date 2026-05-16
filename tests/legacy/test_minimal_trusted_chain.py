#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BASE = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(BASE))

from payload_normalizer import normalize_project_payload, validate_normalized_project  # noqa: E402
from app_x1 import _build_export_payload  # noqa: E402

CASES = [
    {
        'name': 'operating_room_aux',
        'raw': {
            'project_name': '最小可信验证-手术辅房',
            'report_number': 'VT-001',
            'client': '测试单位',
            'date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{
                'type': 'operating_room',
                'name': '刷手间1',
                'subtype': '辅房',
                'clean_class': 'Ⅳ级（十万级）'
            }]
        }
    },
    {
        'name': 'animal_room_barrier',
        'raw': {
            'project_name': '最小可信验证-动物房',
            'report_number': 'VT-002',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'biosafety',
            'rooms': [{
                'type_id': 'animal_room',
                'room_name': '洁净辅房A',
                'subtype': '屏障环境-传递间',
                'level_name': '屏障环境'
            }]
        }
    },
    {
        'name': 'bsl_p2',
        'raw': {
            'project_name': '最小可信验证-BSL',
            'report_number': 'VT-003',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'biosafety',
            'rooms': [{
                'type_id': 'bsl',
                'room_name': 'P2实验室',
                'subtype': 'P2'
            }]
        }
    },
    {
        'name': 'gmp_grade_c',
        'raw': {
            'project_name': '最小可信验证-GMP',
            'report_number': 'VT-004',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'pharma',
            'rooms': [{
                'type_id': 'gmp_workshop',
                'room_name': 'GMP车间1',
                'subtype': 'C级'
            }]
        }
    },
    {
        'name': 'electronics_iso7',
        'raw': {
            'project_name': '最小可信验证-电子车间',
            'report_number': 'VT-005',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'electronics',
            'rooms': [{
                'type_id': 'electronics_workshop',
                'room_name': '电子车间1',
                'subtype': 'ISO 7'
            }]
        }
    },
    {
        'name': 'clean_function_room_icu',
        'raw': {
            'project_name': '最小可信验证-洁净功能用房',
            'report_number': 'VT-006',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{
                'type_id': 'clean_function_room',
                'room_name': 'ICU病房1',
                'subtype': 'ICU病房',
                'clean_class': 'Ⅲ级（万级）'
            }]
        }
    },
    {
        'name': 'food_workshop_grade_iii',
        'raw': {
            'project_name': '最小可信验证-食品车间',
            'report_number': 'VT-007',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'food',
            'rooms': [{
                'type_id': 'food_workshop',
                'room_name': '食品车间1',
                'subtype': 'Ⅲ级'
            }]
        }
    },
    {
        'name': 'negative_pressure_basic',
        'raw': {
            'project_name': '最小可信验证-负压病房',
            'report_number': 'VT-008',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{
                'type_id': 'negative_pressure',
                'room_name': '负压病房1',
                'clean_class': '无洁净等级要求'
            }]
        }
    },
    {
        'name': 'laminar_hood_basic',
        'raw': {
            'project_name': '最小可信验证-层流罩',
            'report_number': 'VT-009',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'pharma',
            'rooms': [{
                'type_id': 'laminar_hood',
                'room_name': '层流罩1',
                'clean_class': '无等级要求'
            }]
        }
    },
    {
        'name': 'pass_box_basic',
        'raw': {
            'project_name': '最小可信验证-传递窗',
            'report_number': 'VT-010',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'pharma',
            'rooms': [{
                'type_id': 'pass_box',
                'room_name': '传递窗1',
                'clean_class': '无等级要求'
            }]
        }
    },
]

results = []
for case in CASES:
    normalized = normalize_project_payload(case['raw'], source='verification')
    error = validate_normalized_project(normalized)
    payload = None
    payload_error = None
    if not error:
        try:
            payload = _build_export_payload(normalized)
        except Exception as exc:
            payload_error = str(exc)
    room = (normalized.get('rooms') or [{}])[0]
    export_room = ((payload or {}).get('room') or {})
    results.append({
        'name': case['name'],
        'validation_error': error,
        'payload_error': payload_error,
        'type_id': room.get('type_id'),
        'export_type': (payload or {}).get('export_type'),
        'room_name': room.get('room_name'),
        'context': room.get('context'),
        'level_name': room.get('level_name'),
        'clean_class': room.get('clean_class'),
        'template_key': ((payload or {}).get('template_rule') or {}).get('template_key'),
        'export_room_type_id': export_room.get('type_id'),
        'ok': (error is None) and (payload_error is None) and ((payload or {}).get('export_type') == room.get('type_id')),
    })

print(json.dumps(results, ensure_ascii=False, indent=2))
