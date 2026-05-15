#!/usr/bin/env python3
"""防回退：报告管理 asset_state 应优先使用 filled.docx 作为本地报告。"""
from app_x1 import _compute_record_asset_state


def test_prefers_filled_over_bound():
    record = {
        'type': 'export',
        'files': [
            {'name': 'X1EXPORT_demo.bound.docx', 'path': '/tmp/X1EXPORT_demo.bound.docx'},
            {'name': 'X1EXPORT_demo.filled.docx', 'path': '/tmp/X1EXPORT_demo.filled.docx'},
            {'name': 'X1EXPORT_demo.docx', 'path': '/tmp/X1EXPORT_demo.docx'},
            {'name': 'X1EXPORT_demo.xlsx', 'path': '/tmp/X1EXPORT_demo.xlsx'},
        ],
        'report_info': {},
        'export_info': {},
        'feishu_report_status': '',
        'feishu_export_status': '',
    }
    state = _compute_record_asset_state(record)
    assert state['local_report_ok'] is True
    assert state['report_file']['name'].endswith('.filled.docx'), state['report_file']
    assert state['raw_excel']['name'].endswith('.xlsx'), state['raw_excel']


def test_falls_back_to_bound_when_filled_missing():
    record = {
        'type': 'export',
        'files': [
            {'name': 'X1EXPORT_demo.bound.docx', 'path': '/tmp/X1EXPORT_demo.bound.docx'},
            {'name': 'X1EXPORT_demo.xlsx', 'path': '/tmp/X1EXPORT_demo.xlsx'},
        ],
        'report_info': {},
        'export_info': {},
        'feishu_report_status': '',
        'feishu_export_status': '',
    }
    state = _compute_record_asset_state(record)
    assert state['report_file']['name'].endswith('.bound.docx'), state['report_file']


if __name__ == '__main__':
    test_prefers_filled_over_bound()
    test_falls_back_to_bound_when_filled_missing()
    print('PASS test_record_asset_state_regression')
