#!/usr/bin/env python3
"""
X1 飞书上传最小核查脚本
目标：真实走一次 submit_export，核查导出 JSON 是否无论成功/失败都落账 feishu.report / feishu.export 结果。
"""
import json
import requests
from pathlib import Path
from datetime import datetime
import sys

BASE = 'http://localhost:8082'
ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
REPORTS = ROOT / 'reports_x1'
s = requests.Session()
sys.path.insert(0, str(ROOT))
from feishu_utils import get_feishu_folder_meta


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def main():
    assert login(), 'login failed'
    case_id = f'feishu_probe_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
    project = {
        'project_name': case_id,
        'report_number': case_id[:40],
        'client_name': '飞书核查测试单位',
        'detection_date': '2026-05-03',
        'domain': 'biosafety',
        'rooms': [{
            'type_id': 'ivc',
            'room_name': 'IVC飞书核查样本',
            'level_name': '默认',
            'clean_class': '默认',
            'params': [
                {'key': 'airchange', 'value': '30'}
            ],
            'summary': {'result_state': '合格'}
        }]
    }

    s.post(f'{BASE}/api/x/save_draft', json={'project': project}, timeout=30)
    r = s.post(f'{BASE}/api/x/submit_export', json={'project': project}, timeout=120)
    body = r.json()
    export_id = body.get('export_id', '')
    json_path = Path(body.get('json_path', ''))
    result = {
        'case_id': case_id,
        'http_status': r.status_code,
        'success': body.get('success'),
        'export_id': export_id,
        'json_path': str(json_path),
        'json_exists': json_path.exists(),
        'reports_meta': get_feishu_folder_meta('reports'),
        'exports_meta': get_feishu_folder_meta('exports'),
        'feishu': None,
        'report_success': None,
        'report_error': None,
        'export_success': None,
        'export_error': None,
        'ok': False,
    }

    if json_path.exists():
        data = json.loads(json_path.read_text(encoding='utf-8'))
        feishu = data.get('feishu') or {}
        report = feishu.get('report') or {}
        export = feishu.get('export') or {}
        result['feishu'] = feishu
        result['report_success'] = report.get('success')
        result['report_error'] = report.get('error')
        result['export_success'] = export.get('success')
        result['export_error'] = export.get('error')
        result['ok'] = ('report' in feishu and 'export' in feishu)

    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    out_json = REPORTS / f'feishu_probe_{ts}.json'
    out_md = REPORTS / f'feishu_probe_{ts}.md'
    out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    lines = [
        '# X1 飞书上传最小核查',
        '',
        f'- case_id: {result["case_id"]}',
        f'- http_status: {result["http_status"]}',
        f'- export_id: {result["export_id"]}',
        f'- json_path: {result["json_path"]}',
        f'- json_exists: {result["json_exists"]}',
        f'- reports_mode: {result["reports_meta"].get("mode")}',
        f'- reports_resolved_token: {result["reports_meta"].get("resolved_token")}',
        f'- exports_mode: {result["exports_meta"].get("mode")}',
        f'- exports_resolved_token: {result["exports_meta"].get("resolved_token")}',
        f'- report_success: {result["report_success"]}',
        f'- report_error: {result["report_error"]}',
        f'- export_success: {result["export_success"]}',
        f'- export_error: {result["export_error"]}',
        f'- ok: {result["ok"]}',
    ]
    out_md.write_text('\n'.join(lines), encoding='utf-8')
    print(out_json)
    print(out_md)
    print('SUMMARY', 'PASS' if result['ok'] else 'FAIL')
    if not result['ok']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
