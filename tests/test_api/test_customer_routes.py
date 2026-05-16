"""
tests/test_api/test_customer_routes.py - 客户路由回归测试
"""
import requests
import pytest

BASE = 'http://localhost:8082'


def test_customer_page_requires_auth():
    """/customer 需要登录"""
    resp = requests.get(f'{BASE}/customer', allow_redirects=False)
    assert resp.status_code == 302


def test_customer_api_profile_requires_auth():
    """/customer/api/profile 需要登录"""
    resp = requests.get(f'{BASE}/customer/api/profile', allow_redirects=False)
    assert resp.status_code == 302


def test_customer_admin_list_requires_auth():
    """/admin/api/customer_management/list 需要登录"""
    resp = requests.get(f'{BASE}/admin/api/customer_management/list', allow_redirects=False)
    assert resp.status_code == 302

