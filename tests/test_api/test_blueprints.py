"""
tests/test_api/test_blueprints.py - Blueprint 路由回归测试
验证所有 Blueprint 路由可达（返回 200 或 302）
"""
import requests

BASE = 'http://localhost:8082'

# 无需登录即可访问的路由
PUBLIC_ROUTES = [
    ('/api/x/health', 200),
    ('/login', 200),
]

# 需要登录的路由（未登录应返回 302 重定向到登录页）
AUTH_ROUTES = [
    '/admin/api/settings',
    '/admin/api/business_projects',
    '/admin/api/records',
    '/admin/api/templates',
    '/admin/api/stats',
    '/admin/api/logs',
    '/admin/api/users',
    '/api/x/list_drafts',
    '/api/x/list_exports',
    '/api/notifications',
    '/api/x/inspectors',
    '/admin/api/standards',
]


def test_public_routes():
    """公开路由应返回预期状态码"""
    for path, expected in PUBLIC_ROUTES:
        resp = requests.get(f'{BASE}{path}', timeout=5, allow_redirects=False)
        assert resp.status_code == expected, f'{path}: expected {expected}, got {resp.status_code}'


def test_auth_routes_require_login():
    """需认证路由未登录应返回 302"""
    for path in AUTH_ROUTES:
        resp = requests.get(f'{BASE}{path}', timeout=5, allow_redirects=False)
        assert resp.status_code == 302, f'{path}: expected 302, got {resp.status_code}'


def test_health_response_format():
    """/api/x/health 返回正确的 JSON 结构"""
    resp = requests.get(f'{BASE}/api/x/health', timeout=5)
    data = resp.json()
    assert data['success'] is True
    assert data['app'] == 'X1'
    assert 'version' in data
    assert 'system' in data
    assert 'cpu_percent' in data['system']


def test_login_rate_limiting():
    """登录暴力破解防护生效"""
    s = requests.Session()
    # 先清除可能的旧限流状态（等待足够时间或用不同 IP）
    # 连续 5 次错误密码
    for i in range(5):
        s.post(f'{BASE}/login', json={'username': 'test_rate', 'password': 'wrong'})
    
    # 第 6 次应被限流
    resp = s.post(f'{BASE}/login', json={'username': 'test_rate', 'password': 'wrong'})
    assert resp.status_code == 429


def test_404_for_nonexistent():
    """不存在的路由返回 404"""
    resp = requests.get(f'{BASE}/api/nonexistent_route_xyz', timeout=5)
    assert resp.status_code == 404
