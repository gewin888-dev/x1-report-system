#!/usr/bin/env python3
"""
清理异常小报告文件脚本
- 清理 .bound.docx 临时文件
- 清理小于10KB的X1EXPORT文件（导出失败）
- 移动到trash/目录而非直接删除
"""

import shutil
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports_x1"
TRASH_DIR = BASE_DIR / "trash"
TRASH_DIR.mkdir(exist_ok=True)

def clean_small_reports(dry_run=True):
    """
    清理异常小报告文件
    
    Args:
        dry_run: True=仅统计不删除，False=实际删除
    """
    # 创建专门的trash子目录
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    trash_subdir = TRASH_DIR / f"small_reports_{timestamp}"
    
    if not dry_run:
        trash_subdir.mkdir(exist_ok=True)
    
    # 查找所有DOCX文件
    docx_files = list(REPORTS_DIR.glob("*.docx"))
    
    # 分类统计
    bound_files = []
    small_export_files = []
    
    for f in docx_files:
        size = f.stat().st_size
        name = f.name
        
        # .bound.docx临时文件
        if name.endswith('.bound.docx'):
            bound_files.append(f)
        # 小于10KB的X1EXPORT文件
        elif name.startswith('X1EXPORT_') and size < 10240:
            small_export_files.append(f)
    
    total_files = len(bound_files) + len(small_export_files)
    total_size = sum(f.stat().st_size for f in bound_files + small_export_files)
    
    print(f"=== 报告清理统计 ===")
    print(f"模式: {'预览模式' if dry_run else '实际清理'}")
    print(f"\n待清理文件:")
    print(f"  .bound.docx临时文件: {len(bound_files)} 个")
    print(f"  小X1EXPORT文件 (<10KB): {len(small_export_files)} 个")
    print(f"  总计: {total_files} 个")
    print(f"  释放空间: {total_size / 1024:.2f} KB")
    
    if dry_run:
        print(f"\n⚠️  预览模式，未实际删除文件")
        print(f"执行清理: clean_small_reports(dry_run=False)")
        return
    
    # 实际移动文件
    moved_count = 0
    for f in bound_files + small_export_files:
        try:
            dest = trash_subdir / f.name
            shutil.move(str(f), str(dest))
            moved_count += 1
        except Exception as e:
            print(f"⚠️  移动失败: {f.name} - {e}")
    
    print(f"\n✅ 清理完成:")
    print(f"  已移动: {moved_count} 个文件")
    print(f"  目标位置: {trash_subdir}")
    print(f"  如需恢复，可从trash目录中找回")
    
    return moved_count

if __name__ == '__main__':
    import sys
    
    # 默认预览模式
    dry_run = True
    if len(sys.argv) > 1 and sys.argv[1] == '--execute':
        dry_run = False
    
    clean_small_reports(dry_run=dry_run)
