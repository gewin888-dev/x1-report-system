#!/usr/bin/env python3
import sys
import urllib.request
import urllib.error

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://127.0.0.1:8082'


def fetch(path):
    req = urllib.request.Request(BASE + path)
    opener = urllib.request.build_opener(urllib.request.HTTPRedirectHandler())
    try:
        with opener.open(req, timeout=8) as resp:
            return resp.getcode(), resp.read().decode('utf-8', errors='replace'), str(resp.geturl())
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        return e.code, body, str(e.geturl())


def protected_login_redirect(path):
    status, text, final_url = fetch(path)
    ok = status == 200 and '/login' in final_url
    return ok, f'{status} {final_url}'


checks = []
status, text, final_url = fetch('/api/x/health')
checks.append(('health', status == 200 and 'success' in text, f'{status} {final_url}'))

status, text, final_url = fetch('/login')
checks.append(('login_page', status == 200 and '检测报告管理系统' in text, f'{status} {final_url}'))

for name, path in [
    ('admin_standards_protected', '/admin/standards'),
    ('admin_monitor_protected', '/admin/monitor'),
    ('records_api_protected', '/admin/api/records'),
    ('records_summary_protected', '/admin/api/records/summary'),
    ('templates_api_protected', '/admin/api/templates'),
    ('settings_api_protected', '/admin/api/settings'),
    ('settings_backups_protected', '/admin/api/settings/backups'),
]:
    ok, detail = protected_login_redirect(path)
    checks.append((name, ok, detail))

print('X1 smoke test')
print('=' * 50)
failed = 0
for name, ok, detail in checks:
    print(f'[{"OK" if ok else "FAIL"}] {name} -> {detail}')
    if not ok:
        failed += 1
print('=' * 50)
print(f'总计 {len(checks)} 项，失败 {failed} 项')
sys.exit(1 if failed else 0)
