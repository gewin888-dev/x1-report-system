#!/usr/bin/env python3
"""
X1系统摘要数据准确性校验脚本
验证所有摘要API统计数据的准确性

用法:
    python scripts/verify_summary_accuracy.py [--check TYPE]
    
参数:
    --check TYPE  指定检查类型: projects, records, all (默认: all)
    
返回码:
    0 - 数据一致
    1 - 发现不一致
"""

import sys
import sqlite3
import urllib.request
import http.cookiejar
import json
import argparse
from pathlib import Path

# 配置
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / 'data' / 'x1_data.db'
API_BASE = 'http://localhost:8082'
USERNAME = 'admin'
PASSWORD = 'admin123'


def get_projects_db_stats():
    """从数据库直接统计"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    
    stats = {}
    
    # 总项目数
    row = conn.execute('SELECT COUNT(*) AS total FROM business_projects').fetchone()
    stats['project_count'] = row['total']
    
    # 检测中
    row = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE inspection_stage='检测中'").fetchone()
    stats['detecting_count'] = row['c']
    
    # 待出报告
    row = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE report_status='报告编制中'").fetchone()
    stats['pending_report_count'] = row['c']
    
    # 已完成
    row = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE inspection_stage='检测完成' AND report_status='已出报告'").fetchone()
    stats['done_count'] = row['c']
    
    # 未开票
    row = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE invoice_status='未开票'").fetchone()
    stats['pending_invoice_count'] = row['c']
    
    # 有应收款
    row = conn.execute("SELECT COUNT(*) AS c FROM business_projects WHERE (contract_amount - COALESCE(paid_amount, 0)) > 0.01").fetchone()
    stats['pending_payment_count'] = row['c']
    
    # 财务汇总
    row = conn.execute("SELECT COALESCE(SUM(contract_amount), 0) AS contract_total, COALESCE(SUM(paid_amount), 0) AS paid_total FROM business_projects").fetchone()
    stats['contract_total'] = round(row['contract_total'], 2)
    stats['receivable_amount'] = round(row['contract_total'] - row['paid_total'], 2)
    
    conn.close()
    return stats


def get_projects_api_stats():
    """从项目摘要API获取统计"""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    
    # 登录
    login_data = json.dumps({"username": USERNAME, "password": PASSWORD}).encode()
    login_req = urllib.request.Request(
        f"{API_BASE}/login",
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    opener.open(login_req)
    
    # 获取项目摘要
    summary_req = urllib.request.Request(f"{API_BASE}/admin/api/business_projects/summary")
    with opener.open(summary_req) as resp:
        summary_data = json.loads(resp.read())
    
    return summary_data


def get_records_file_stats():
    """从文件系统统计记录数据"""
    records_dir = BASE_DIR / 'records_x1'
    reports_dir = BASE_DIR / 'reports_x1'
    
    stats = {
        'total_draft_files': 0,
        'total_export_files': 0,
        'valid_drafts': 0,
        'valid_exports': 0
    }
    
    # 统计草稿
    if records_dir.exists():
        draft_files = [f for f in records_dir.glob('*.json') if not f.stem.startswith('X1EXPORT_')]
        stats['total_draft_files'] = len(draft_files)
        
        for draft_file in draft_files:
            try:
                with open(draft_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    project = data.get('project', {})
                    if project.get('project_name') or project.get('client_name') or project.get('rooms'):
                        stats['valid_drafts'] += 1
            except:
                pass
    
    # 统计导出记录
    if reports_dir.exists():
        export_files = list(reports_dir.glob('X1EXPORT_*.json'))
        stats['total_export_files'] = len(export_files)
        
        for export_file in export_files:
            try:
                with open(export_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    ep = data.get('export_payload', data)
                    proj = ep.get('project', {}) or {}
                    if proj.get('project_name') or proj.get('client_name') or proj.get('report_number'):
                        stats['valid_exports'] += 1
            except:
                pass
    
    stats['total_valid'] = stats['valid_drafts'] + stats['valid_exports']
    return stats


def get_records_api_stats():
    """从记录摘要API获取统计"""
    jar = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    
    # 登录
    login_data = json.dumps({"username": USERNAME, "password": PASSWORD}).encode()
    login_req = urllib.request.Request(
        f"{API_BASE}/login",
        data=login_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    opener.open(login_req)
    
    # 获取记录摘要
    summary_req = urllib.request.Request(f"{API_BASE}/admin/api/records/summary")
    with opener.open(summary_req) as resp:
        data = json.loads(resp.read())
    
    return data.get('summary', {}) if data.get('success') else {}


def get_api_stats():
    """从API获取统计（兼容旧函数名）"""
    return get_projects_api_stats()


def compare_stats(db_stats, api_stats):
    """比较统计数据"""
    fields = [
        'project_count',
        'detecting_count',
        'pending_report_count',
        'done_count',
        'pending_invoice_count',
        'pending_payment_count',
        'contract_total',
        'receivable_amount',
    ]
    
    mismatches = []
    
    for field in fields:
        db_val = db_stats.get(field, 0)
        api_val = api_stats.get(field, 0)
        
        if db_val != api_val:
            mismatches.append({
                'field': field,
                'db_value': db_val,
                'api_value': api_val
            })
    
    return mismatches


def main():
    parser = argparse.ArgumentParser(description='X1系统摘要数据准确性校验')
    parser.add_argument('--check', choices=['projects', 'records', 'all'], default='all',
                        help='检查类型: projects(项目), records(记录), all(全部)')
    args = parser.parse_args()
    
    print("=== X1摘要数据一致性校验 ===\n")
    
    has_error = False
    
    # 检查项目摘要
    if args.check in ['projects', 'all']:
        print("📊 检查项目摘要数据...")
        
        # 检查数据库文件
        if not DB_PATH.exists():
            print(f"❌ 数据库文件不存在: {DB_PATH}")
            return 1
        
        try:
            # 获取数据库统计
            db_stats = get_projects_db_stats()
            
            # 获取API统计
            api_stats = get_projects_api_stats()
            
            # 比较
            mismatches = compare_stats(db_stats, api_stats)
            
            if not mismatches:
                print("✅ 项目摘要数据一致！")
                print(f"  总项目数: {api_stats['project_count']}")
                print(f"  检测中: {api_stats['detecting_count']}")
                print(f"  已完成: {api_stats['done_count']}")
                print(f"  待出报告: {api_stats['pending_report_count']}")
                print(f"  合同总额: ¥{api_stats['contract_total']:,.2f}")
                print(f"  应收款: ¥{api_stats['receivable_amount']:,.2f}")
            else:
                has_error = True
                print(f"❌ 项目摘要发现 {len(mismatches)} 项不一致:\n")
                for m in mismatches:
                    print(f"  字段: {m['field']}")
                    print(f"    数据库值: {m['db_value']}")
                    print(f"    API返回值: {m['api_value']}")
                    print()
                    
        except Exception as e:
            has_error = True
            print(f"❌ 项目摘要校验失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 检查记录摘要
    if args.check in ['records', 'all']:
        if args.check == 'all':
            print()
        
        print("📁 检查记录摘要数据...")
        
        try:
            # 获取文件统计
            file_stats = get_records_file_stats()
            
            # 获取API统计
            api_stats = get_records_api_stats()
            
            # 比较（允许小范围差异，因为是实时统计）
            tolerance = 5
            draft_diff = abs(file_stats['valid_drafts'] - api_stats.get('draft_count', 0))
            export_diff = abs(file_stats['valid_exports'] - api_stats.get('export_count', 0))
            total_diff = abs(file_stats['total_valid'] - api_stats.get('total', 0))
            
            if draft_diff <= tolerance and export_diff <= tolerance and total_diff <= tolerance:
                print("✅ 记录摘要数据一致！")
                print(f"  总记录数: {api_stats.get('total', 0)}")
                print(f"  草稿记录: {api_stats.get('draft_count', 0)}")
                print(f"  导出记录: {api_stats.get('export_count', 0)}")
                print(f"  已生成报告: {api_stats.get('report_count', 0)}")
            else:
                has_error = True
                print(f"❌ 记录摘要数据不一致:\n")
                print(f"  草稿记录: API={api_stats.get('draft_count', 0)}, 文件={file_stats['valid_drafts']}, 差异={draft_diff}")
                print(f"  导出记录: API={api_stats.get('export_count', 0)}, 文件={file_stats['valid_exports']}, 差异={export_diff}")
                print(f"  总记录数: API={api_stats.get('total', 0)}, 计算={file_stats['total_valid']}, 差异={total_diff}")
                
        except Exception as e:
            has_error = True
            print(f"❌ 记录摘要校验失败: {e}")
            import traceback
            traceback.print_exc()
    
    return 1 if has_error else 0


if __name__ == '__main__':
    sys.exit(main())
