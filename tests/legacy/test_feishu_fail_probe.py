#!/usr/bin/env python3
"""
X1 飞书上传失败态最小核查脚本
目标：在不修改正式配置的前提下，受控制造“拿不到 folder token”场景，验证导出 JSON 是否仍落账 feishu.report/export 的失败状态。
"""
import json
from pathlib import Path
from datetime import datetime

ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
REPORTS = ROOT / 'reports_x1'


def main():
    import app_x1

    app = app_x1.app
    client = app.test_client()

    # 先走真实登录态
    login_resp = client.post('/login', data={'username': 'admin', 'password': 'pudi2026'}, follow_redirects=True)
    assert login_resp.status_code == 200, f'login failed: {login_resp.status_code}'

    original = app_x1.get_feishu_yearly_folder

    def fake_get_feishu_yearly_folder(prefix, year=None):
        return None

    app_x1.get_feishu_yearly_folder = fake_get_feishu_yearly_folder
    try:
        case_id = f'feishu_fail_probe_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        project = {
            'project_name': case_id,
            'report_number': case_id[:40],
            'client_name': '飞书失败核查测试单位',
            'detection_date': '2026-05-03',
            'domain': 'biosafety',
            'rooms': [{
                'type_id': 'ivc',
                'room_name': 'IVC飞书失败核查样本',
                'level_name': '默认',
                'clean_class': '默认',
                'params': [
                    {'key': 'airchange', 'value': '30'}
                ],
                'summary': {'result_state': '合格'}
            }]
        }

        resp = client.post('/api/x/submit_export', json={'project': project})
        body = resp.get_json()
        export_id = body.get('export_id', '')
        json_path = Path(body.get('json_path', ''))
        result = {
            'case_id': case_id,
            'http_status': resp.status_code,
            'success': body.get('success'),
            'export_id': export_id,
            'json_path': str(json_path),
            'json_exists': json_path.exists(),
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
            result['ok'] = (
                'report' in feishu and 'export' in feishu and
                report.get('success') is False and export.get('success') is False
            )

        ts = datetime.now().strftime('%Y%m%d_%H%M%S')
        out_json = REPORTS / f'feishu_fail_probe_{ts}.json'
        out_md = REPORTS / f'feishu_fail_probe_{ts}.md'
        out_json.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        lines = [
            '# X1 飞书上传失败态最小核查',
            '',
            f'- case_id: {result["case_id"]}',
            f'- http_status: {result["http_status"]}',
            f'- export_id: {result["export_id"]}',
            f'- json_path: {result["json_path"]}',
            f'- json_exists: {result["json_exists"]}',
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
    finally:
        app_x1.get_feishu_yearly_folder = original


if __name__ == '__main__':
    main()
