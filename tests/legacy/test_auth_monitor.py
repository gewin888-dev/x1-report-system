#!/usr/bin/env python3
"""
测试X1系统的认证和监控功能
"""

import requests
import json

BASE_URL = 'http://127.0.0.1:8082'

def test_login():
    """测试登录"""
    print('测试登录...')
    resp = requests.post(f'{BASE_URL}/login', json={
        'username': 'admin',
        'password': 'pudi2026'
    })
    print(f'状态码: {resp.status_code}')
    if resp.status_code == 200:
        print('✅ 登录成功')
        return resp.cookies
    else:
        print('❌ 登录失败')
        return None

def test_user_info(cookies):
    """测试获取用户信息"""
    print('\n测试获取用户信息...')
    resp = requests.get(f'{BASE_URL}/api/user', cookies=cookies)
    data = resp.json()
    print(f'用户: {data.get("display_name")} ({data.get("role")})')
    print('✅ 用户信息获取成功')

def test_health_check(cookies):
    """测试健康检查"""
    print('\n测试系统健康检查...')
    resp = requests.get(f'{BASE_URL}/api/system/health', cookies=cookies)
    if resp.status_code == 200:
        data = resp.json()
        print(f'系统状态: {data.get("health", {}).get("status")}')
        print(f'最近错误: {data.get("health", {}).get("recent_errors")}')
        print('✅ 健康检查成功')
    else:
        print(f'❌ 健康检查失败: {resp.status_code}')

def test_logout(cookies):
    """测试登出"""
    print('\n测试登出...')
    resp = requests.get(f'{BASE_URL}/logout', cookies=cookies, allow_redirects=False)
    if resp.status_code in [302, 303]:
        print('✅ 登出成功')
    else:
        print(f'❌ 登出失败: {resp.status_code}')

if __name__ == '__main__':
    print('X1系统认证和监控功能测试')
    print('=' * 50)
    
    # 测试登录
    cookies = test_login()
    if not cookies:
        print('\n❌ 登录失败，无法继续测试')
        exit(1)
    
    # 测试其他功能
    test_user_info(cookies)
    test_health_check(cookies)
    test_logout(cookies)
    
    print('\n' + '=' * 50)
    print('✅ 所有测试完成')
