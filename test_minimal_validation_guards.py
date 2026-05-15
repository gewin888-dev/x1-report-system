#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BASE = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(BASE))

from payload_normalizer import normalize_project_payload, validate_normalized_project  # noqa: E402

CASES = [
    {
        'name': 'missing_project_name',
        'raw': {
            'report_number': 'NEG-001',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{'type_id': 'operating_room', 'room_name': '手术室1', 'clean_class': 'Ⅱ级（千级）'}]
        },
        'expect_error': 'project_name 不能为空'
    },
    {
        'name': 'missing_client_name',
        'raw': {
            'project_name': '异常样本-缺客户',
            'report_number': 'NEG-002',
            'detection_date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{'type_id': 'operating_room', 'room_name': '手术室1', 'clean_class': 'Ⅱ级（千级）'}]
        },
        'expect_error': 'client_name 不能为空'
    },
    {
        'name': 'missing_detection_date',
        'raw': {
            'project_name': '异常样本-缺日期',
            'report_number': 'NEG-003',
            'client_name': '测试单位',
            'domain': 'hospital',
            'rooms': [{'type_id': 'operating_room', 'room_name': '手术室1', 'clean_class': 'Ⅱ级（千级）'}]
        },
        'expect_error': 'detection_date 不能为空'
    },
    {
        'name': 'unknown_type_id',
        'raw': {
            'project_name': '异常样本-未知对象',
            'report_number': 'NEG-004',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{'type_id': 'mystery_room', 'room_name': '未知房间'}]
        },
        'expect_error': '未知 type_id: mystery_room'
    },
    {
        'name': 'missing_room_name',
        'raw': {
            'project_name': '异常样本-缺房间名',
            'report_number': 'NEG-005',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{'type_id': 'operating_room', 'clean_class': 'Ⅱ级（千级）'}]
        },
        'expect_error': 'room_name 不能为空'
    },
    {
        'name': 'missing_level_for_grade_object',
        'raw': {
            'project_name': '异常样本-缺等级',
            'report_number': 'NEG-006',
            'client_name': '测试单位',
            'detection_date': '2026-05-02',
            'domain': 'hospital',
            'rooms': [{'type_id': 'clean_function_room', 'room_name': 'ICU病房1'}]
        },
        'expect_error': 'clean_function_room 缺少 level_name/clean_class'
    }
]

results = []
for case in CASES:
    normalized = normalize_project_payload(case['raw'], source='negative-verification')
    error = validate_normalized_project(normalized)
    results.append({
        'name': case['name'],
        'error': error,
        'expect_error': case['expect_error'],
        'ok': error == case['expect_error']
    })

print(json.dumps(results, ensure_ascii=False, indent=2))
