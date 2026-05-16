#!/usr/bin/env python3
"""操作日志分类接口行为防回退。"""
import requests

BASE = 'http://127.0.0.1:8082'


def login(session):
    r = session.post(f"{BASE}/login", data={"username": "admin", "password": "pudi2026"}, allow_redirects=False)
    return r.status_code in (200, 302)


def main():
    s = requests.Session()
    assert login(s), '登录失败'
    r = s.get(f'{BASE}/admin/api/logs?month=2026-05&page=1&page_size=50', timeout=10)
    assert r.status_code == 200, f'日志接口异常: {r.status_code}'
    data = r.json()

    assert isinstance(data.get('user_options'), list), '缺少 user_options'
    assert isinstance(data.get('category_options'), list), '缺少 category_options'
    assert isinstance(data.get('action_options'), list), '缺少 action_options'
    assert isinstance(data.get('category_action_map'), dict), '缺少 category_action_map'
    assert isinstance(data.get('category_summary'), list), '缺少 category_summary'

    expected_categories = ['认证与会话', '报告记录治理', '操作日志治理', '系统设置与运维', '权限与用户管理', '模板注册与模板治理', '标准库/文档/查看类', '其他/未分类']
    assert data['category_options'] == expected_categories, data['category_options']

    summary_categories = [item.get('category') for item in data.get('category_summary', [])]
    assert summary_categories == expected_categories, summary_categories

    category_action_map = data.get('category_action_map') or {}
    assert '认证与会话' in category_action_map, category_action_map
    assert '报告记录治理' in category_action_map, category_action_map
    assert 'login' in category_action_map.get('认证与会话', []), category_action_map.get('认证与会话')
    assert 'logout' in category_action_map.get('认证与会话', []), category_action_map.get('认证与会话')
    assert '导出报告' in category_action_map.get('报告记录治理', []), category_action_map.get('报告记录治理')

    print('PASS test_log_classification_api_regression')


if __name__ == '__main__':
    main()
