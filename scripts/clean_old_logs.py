#!/usr/bin/env python3
"""
X1系统日志清理脚本
- 保留最近90天的日志
- 自动归档旧日志到logs_archive/
- 可通过cron定期执行
"""

import os
import shutil
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs_x1"
ARCHIVE_DIR = BASE_DIR / "logs_archive"

def clean_old_logs(days_to_keep=90, dry_run=True):
    """
    清理旧日志文件
    
    Args:
        days_to_keep: 保留最近多少天的日志
        dry_run: True=仅预览，False=实际清理
    """
    if not LOGS_DIR.exists():
        print(f"日志目录不存在: {LOGS_DIR}")
        return
    
    # 计算截止日期
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    
    # 扫描所有日志文件
    log_files = list(LOGS_DIR.glob("*.log"))
    
    old_files = []
    total_size = 0
    
    for log_file in log_files:
        mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
        if mtime < cutoff_date:
            old_files.append(log_file)
            total_size += log_file.stat().st_size
    
    print(f"=== 日志清理 ===")
    print(f"模式: {'预览模式' if dry_run else '实际清理'}")
    print(f"日志目录: {LOGS_DIR}")
    print(f"总日志文件: {len(log_files)}")
    print(f"保留天数: {days_to_keep}")
    print(f"截止日期: {cutoff_date.strftime('%Y-%m-%d')}")
    print(f"\n待清理文件: {len(old_files)}")
    print(f"释放空间: {total_size / (1024*1024):.2f} MB")
    
    if not old_files:
        print("\n✅ 无需清理")
        return
    
    if dry_run:
        print(f"\n⚠️  预览模式，未实际删除")
        print(f"前10个文件:")
        for f in old_files[:10]:
            mtime = datetime.fromtimestamp(f.stat().st_mtime)
            print(f"  {f.name} ({mtime.strftime('%Y-%m-%d')})")
        return
    
    # 创建归档目录
    ARCHIVE_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_subdir = ARCHIVE_DIR / f"logs_{timestamp}"
    archive_subdir.mkdir(exist_ok=True)
    
    # 移动文件到归档
    moved_count = 0
    for log_file in old_files:
        try:
            dest = archive_subdir / log_file.name
            shutil.move(str(log_file), str(dest))
            moved_count += 1
        except Exception as e:
            print(f"⚠️  移动失败: {log_file.name} - {e}")
    
    print(f"\n✅ 清理完成:")
    print(f"  已归档: {moved_count} 个文件")
    print(f"  归档位置: {archive_subdir}")
    print(f"  释放空间: {total_size / (1024*1024):.2f} MB")

if __name__ == '__main__':
    import sys
    
    # 默认预览模式
    dry_run = True
    days = 90
    
    if '--execute' in sys.argv:
        dry_run = False
    if '--days' in sys.argv:
        idx = sys.argv.index('--days')
        if idx + 1 < len(sys.argv):
            days = int(sys.argv[idx + 1])
    
    clean_old_logs(days_to_keep=days, dry_run=dry_run)
