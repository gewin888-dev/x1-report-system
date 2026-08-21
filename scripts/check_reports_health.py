#!/usr/bin/env python3
"""
X1系统报告健康检查脚本
- 检测异常小报告文件
- 检测损坏的DOCX文件
- 生成健康报告
- 可通过cron定期执行
"""

import os
from pathlib import Path
from datetime import datetime
import zipfile

BASE_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BASE_DIR / "reports_x1"

def check_reports_health(verbose=False):
    """
    检查报告文件健康状况
    
    Args:
        verbose: 是否显示详细信息
    """
    if not REPORTS_DIR.exists():
        print(f"报告目录不存在: {REPORTS_DIR}")
        return
    
    print(f"=== X1报告健康检查 ===")
    print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"报告目录: {REPORTS_DIR}")
    
    # 扫描所有DOCX文件
    docx_files = list(REPORTS_DIR.glob("*.docx"))
    print(f"\nDOCX报告总数: {len(docx_files)}")
    
    # 分类统计
    small_files = []  # <10KB
    corrupted_files = []  # 损坏文件
    healthy_files = []
    
    for docx_file in docx_files:
        size = docx_file.stat().st_size
        
        # 检查文件大小
        if size < 10240:  # <10KB
            small_files.append((docx_file, size))
            continue
        
        # 检查DOCX文件完整性（DOCX实际是ZIP文件）
        try:
            with zipfile.ZipFile(docx_file, 'r') as zf:
                # 尝试读取基本结构
                namelist = zf.namelist()
                if 'word/document.xml' not in namelist:
                    corrupted_files.append((docx_file, '缺少document.xml'))
                else:
                    healthy_files.append(docx_file)
        except zipfile.BadZipFile:
            corrupted_files.append((docx_file, 'ZIP格式损坏'))
        except Exception as e:
            corrupted_files.append((docx_file, str(e)))
    
    # 输出结果
    print(f"\n【健康状态】")
    print(f"  健康文件: {len(healthy_files)} ({len(healthy_files)/len(docx_files)*100:.1f}%)")
    print(f"  异常小文件 (<10KB): {len(small_files)}")
    print(f"  损坏文件: {len(corrupted_files)}")
    
    if small_files:
        print(f"\n【异常小文件】")
        print(f"  总数: {len(small_files)}")
        if verbose:
            for f, size in small_files[:10]:
                print(f"    {f.name} ({size} bytes)")
            if len(small_files) > 10:
                print(f"    ... 还有 {len(small_files) - 10} 个")
    
    if corrupted_files:
        print(f"\n【损坏文件】")
        print(f"  总数: {len(corrupted_files)}")
        for f, reason in corrupted_files[:10]:
            print(f"    {f.name}: {reason}")
        if len(corrupted_files) > 10:
            print(f"    ... 还有 {len(corrupted_files) - 10} 个")
    
    # 建议操作
    print(f"\n【建议操作】")
    if small_files:
        print(f"  • 运行 python3 scripts/clean_small_reports.py --execute 清理异常小文件")
    if corrupted_files:
        print(f"  • 联系管理员检查损坏文件原因")
    if not small_files and not corrupted_files:
        print(f"  ✅ 所有报告健康，无需操作")
    
    # 生成健康报告JSON
    health_report = {
        'check_time': datetime.now().isoformat(),
        'total_files': len(docx_files),
        'healthy_files': len(healthy_files),
        'small_files': len(small_files),
        'corrupted_files': len(corrupted_files),
        'health_rate': f"{len(healthy_files)/len(docx_files)*100:.1f}%",
    }
    
    report_path = BASE_DIR / f"reports_health_{datetime.now().strftime('%Y%m%d')}.json"
    import json
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(health_report, f, ensure_ascii=False, indent=2)
    
    print(f"\n健康报告已保存: {report_path}")
    
    return health_report

if __name__ == '__main__':
    import sys
    verbose = '--verbose' in sys.argv or '-v' in sys.argv
    check_reports_health(verbose=verbose)
