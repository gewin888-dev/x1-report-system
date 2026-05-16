#!/usr/bin/env python3
"""
测试数据库功能
"""

import sys
from database import get_db, init_database
from auth import create_user, get_user, verify_password, update_user, delete_user
from monitor import log_action, log_error, log_performance, get_error_logs, get_performance_stats

def test_database():
    print("=" * 60)
    print("数据库功能测试")
    print("=" * 60)
    
    # 测试用户管理
    print("\n1. 测试用户管理")
    print("-" * 60)
    
    # 创建测试用户
    success, msg = create_user('test_user', 'test123', '测试员', 'inspector', '检测部')
    print(f"创建用户: {msg}")
    
    # 验证密码
    if verify_password('test_user', 'test123'):
        print("密码验证: ✅ 通过")
    else:
        print("密码验证: ❌ 失败")
    
    # 获取用户
    user = get_user('test_user')
    if user:
        print(f"获取用户: ✅ {user.display_name} ({user.role})")
    else:
        print("获取用户: ❌ 失败")
    
    # 更新用户
    success, msg = update_user('test_user', display_name='测试员A', department='质检部')
    print(f"更新用户: {msg}")
    
    # 删除用户
    success, msg = delete_user('test_user')
    print(f"删除用户: {msg}")
    
    # 测试日志记录
    print("\n2. 测试日志记录")
    print("-" * 60)
    
    # 操作日志
    log_action('admin', 'test_action', 'test_target', '测试操作')
    print("操作日志: ✅ 已记录")
    
    # 错误日志
    try:
        raise ValueError("测试错误")
    except Exception as e:
        log_error('test_error', str(e), 'test context')
        print("错误日志: ✅ 已记录")
    
    # 性能日志
    log_performance('test_operation', 1.234, 'test details')
    print("性能日志: ✅ 已记录")
    
    # 查询日志
    print("\n3. 测试日志查询")
    print("-" * 60)
    
    errors = get_error_logs(limit=5)
    print(f"错误日志数量: {len(errors)}")
    
    stats = get_performance_stats(hours=24)
    if stats:
        print(f"性能统计: 平均{stats['avg']}秒, 最大{stats['max']}秒, 最小{stats['min']}秒")
    
    # 测试数据库统计
    print("\n4. 数据库统计")
    print("-" * 60)
    
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        print(f"用户数量: {user_count}")
        
        cursor.execute('SELECT COUNT(*) FROM action_logs')
        action_count = cursor.fetchone()[0]
        print(f"操作日志: {action_count}")
        
        cursor.execute('SELECT COUNT(*) FROM error_logs')
        error_count = cursor.fetchone()[0]
        print(f"错误日志: {error_count}")
        
        cursor.execute('SELECT COUNT(*) FROM performance_logs')
        perf_count = cursor.fetchone()[0]
        print(f"性能日志: {perf_count}")
    
    print("\n" + "=" * 60)
    print("测试完成 ✅")
    print("=" * 60)

if __name__ == '__main__':
    test_database()
