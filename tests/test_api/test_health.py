"""
tests/test_api/test_health.py - 基础 API 健康检查测试
"""
import requests


def test_health_endpoint():
    """验证健康检查接口可达"""
    resp = requests.get('http://localhost:8082/api/x/health', timeout=5)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get('success') is True
    assert data.get('app') == 'X1'


def test_login_page_accessible():
    """验证登录页面可达"""
    resp = requests.get('http://localhost:8082/login', timeout=5)
    assert resp.status_code == 200
