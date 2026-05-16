#!/usr/bin/env python3
"""前台后台入口防回退：按钮统一显示，但进入后台必须按权限分流。"""
from pathlib import Path


def main():
    html = Path('templates/record_index.html').read_text(encoding='utf-8')
    js = Path('static/record.js').read_text(encoding='utf-8')

    assert '⚙️后台' in html, '前台缺少后台入口按钮'
    assert "onclick=\"return handleAdminEntry(event)\"" in html, '后台入口未走统一权限分流函数'
    assert "current_user.role == 'admin'" not in html, '后台按钮仍被 admin 角色条件隐藏，存在回退风险'

    assert 'function handleAdminEntry(event)' in js, '缺少前台后台入口分流函数'
    assert "perms.includes('*')" in js, '未识别全权限用户'
    assert "perms.includes('admin.access')" in js, '未识别后台访问权限'
    assert '无权限使用后台' in js, '缺少无权限提示文案'
    assert "window.location.href='/admin'" in js, '有权限时未跳转后台'

    print('PASS test_frontend_admin_entry_regression')


if __name__ == '__main__':
    main()
