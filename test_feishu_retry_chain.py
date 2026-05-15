#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(ROOT))

import app_x1  # noqa: E402

REPORTS = ROOT / 'reports_x1'


def main():
    app = app_x1.app
    client = app.test_client()

    login_resp = client.post('/login', data={'username': 'admin', 'password': 'pudi2026'}, follow_redirects=True)
    assert login_resp.status_code == 200, f'login failed: {login_resp.status_code}'

    original_get_folder = app_x1.get_feishu_yearly_folder
    case_name = f'feishu_retry_chain_{datetime.now().strftime("%Y%m%d_%H%M%S")}'

    project = {
        'project_name': case_name,
        'report_number': case_name[:40],
        'client_name': '飞书重试链路测试单位',
        'contact_info': '13800000000',
        'project_address': '上海市测试路9号',
        'inspection_area': '电子车间飞书重试样本',
        'detection_date': '2026-05-04',
        'domain': 'electronics',
        'domain_name': '电子工业',
        'rooms': [{
            'type_id': 'electronics_workshop',
            'room_name': '电子车间飞书重试样本',
            'type_name': '洁净车间',
            'clean_class': 'ISO 6',
            'context': {'iso_level': 'ISO 6'},
            'summary': {
                'result_state': '不合格',
                'input_result_state': '合格',
                'judgement_engine': 'electronics_workshop_v1',
                'judgement_reason': '飞书重试链路测试',
                'judgement_overridden': True,
                'abnormal_items': [{'item_name': '压差', 'result': '不合格'}]
            },
            'params': {
                'pressure': {
                    'pairs': [{'refRoom': '相对房间1', 'range': '≥5', 'values': ['3']}],
                    'primarySummary': '相对房间1:3.0 Pa[数据库:≥5]',
                    'result': '不合格'
                }
            }
        }]
    }

    export_id = None
    json_path = None
    out = {
        'case_name': case_name,
        'export_id': None,
        'failed_export_http': None,
        'retry_http': None,
        'admin_records_found': False,
        'admin_failed_visible': False,
        'retry_success': False,
        'admin_retry_visible': False,
        'before': {},
        'after_retry': {},
        'ok': False,
    }

    def fake_get_feishu_yearly_folder(prefix, year=None):
        return None

    try:
        # 第一次：强制失败落账
        app_x1.get_feishu_yearly_folder = fake_get_feishu_yearly_folder
        resp = client.post('/api/x/submit_export', json={'project': project})
        body = resp.get_json(silent=True) or {}
        export_id = body.get('export_id')
        json_path = Path(body.get('json_path', '')) if body.get('json_path') else None
        out['export_id'] = export_id
        out['failed_export_http'] = resp.status_code

        if json_path and json_path.exists():
            data = json.loads(json_path.read_text(encoding='utf-8'))
            out['before'] = data.get('feishu') or {}

        records_resp = client.get('/admin/api/records')
        records_json = records_resp.get_json(silent=True) or {}
        records = records_json.get('records') or []
        target = next((r for r in records if r.get('id') == export_id), None)
        out['admin_records_found'] = bool(target)
        out['admin_failed_visible'] = bool(target and target.get('feishu_report_status') == 'failed' and target.get('feishu_export_status') == 'failed')

        # 第二次：恢复真实 folder，重试飞书上传
        app_x1.get_feishu_yearly_folder = original_get_folder
        retry_resp = client.post(f'/admin/api/records/{export_id}/retry_feishu')
        retry_json = retry_resp.get_json(silent=True) or {}
        out['retry_http'] = retry_resp.status_code
        out['retry_success'] = bool(retry_json.get('success') and retry_json.get('report_success') and retry_json.get('export_success'))

        if json_path and json_path.exists():
            data = json.loads(json_path.read_text(encoding='utf-8'))
            out['after_retry'] = data.get('feishu') or {}

        records_resp2 = client.get('/admin/api/records')
        records_json2 = records_resp2.get_json(silent=True) or {}
        records2 = records_json2.get('records') or []
        target2 = next((r for r in records2 if r.get('id') == export_id), None)
        out['admin_retry_visible'] = bool(target2 and target2.get('feishu_report_status') == 'success' and target2.get('feishu_export_status') == 'success')

        out['ok'] = all([
            resp.status_code == 200,
            export_id,
            out['before'].get('report', {}).get('success') is False,
            out['before'].get('export', {}).get('success') is False,
            out['admin_records_found'],
            out['admin_failed_visible'],
            retry_resp.status_code == 200,
            out['retry_success'],
            out['after_retry'].get('report', {}).get('success') is True,
            out['after_retry'].get('export', {}).get('success') is True,
            out['admin_retry_visible'],
        ])

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_json = REPORTS / f'feishu_retry_chain_{ts}.json'
        out_md = REPORTS / f'feishu_retry_chain_{ts}.md'
        out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
        out_md.write_text('\n'.join([
            '# X1 飞书失败→重试恢复链路专项',
            '',
            f'- case_name: {out["case_name"]}',
            f'- export_id: {out["export_id"]}',
            f'- failed_export_http: {out["failed_export_http"]}',
            f'- admin_records_found: {out["admin_records_found"]}',
            f'- admin_failed_visible: {out["admin_failed_visible"]}',
            f'- retry_http: {out["retry_http"]}',
            f'- retry_success: {out["retry_success"]}',
            f'- admin_retry_visible: {out["admin_retry_visible"]}',
            f'- ok: {out["ok"]}',
        ]), encoding='utf-8')
        print(out_json)
        print(out_md)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        if not out['ok']:
            raise SystemExit(1)
    finally:
        app_x1.get_feishu_yearly_folder = original_get_folder


if __name__ == '__main__':
    main()
