#!/usr/bin/env python3
"""防回退：记录接口与前端消费层必须优先使用 filled.docx。"""
from pathlib import Path
from app_x1 import _compute_record_asset_state


def test_api_asset_state_prefers_filled():
    record = {
        'type': 'export',
        'files': [
            {'name': 'demo.bound.docx', 'path': '/tmp/demo.bound.docx'},
            {'name': 'demo.filled.docx', 'path': '/tmp/demo.filled.docx'},
            {'name': 'demo.xlsx', 'path': '/tmp/demo.xlsx'},
        ],
        'report_info': {},
        'export_info': {},
        'feishu_report_status': '',
        'feishu_export_status': '',
    }
    asset = _compute_record_asset_state(record)
    assert asset['report_file']['name'] == 'demo.filled.docx', asset


def test_frontend_render_uses_asset_state_report_file():
    html = Path('templates/admin.html').read_text(encoding='utf-8')
    assert "var asset = r.asset_state || {};" in html
    assert "var reportFile = asset.report_file || null;" in html
    assert "buildRecordAssetButton('本地报告', localReportOk, 'local', reportFile ? reportFile.name : ''" in html
    assert "filledDoc =" not in html, '旧的前端本地报告文件猜测逻辑仍残留，存在回退风险'


if __name__ == '__main__':
    test_api_asset_state_prefers_filled()
    test_frontend_render_uses_asset_state_report_file()
    print('PASS test_record_asset_state_api_regression')
