#!/usr/bin/env python3
"""
清理孤立记录 - 删除数据库中指向不存在文件的导出记录
"""
import sqlite3
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / 'x1_data.db'
REPORTS_DIR = BASE_DIR / 'reports_x1'
RECORDS_DIR = BASE_DIR / 'records_x1'

def cleanup_orphaned_export_records():
    """清理export_records表中的孤立记录"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有导出记录
    cursor.execute('SELECT id, export_id FROM export_records')
    rows = cursor.fetchall()
    
    orphaned = []
    valid = []
    
    for row in rows:
        export_id = row['export_id']
        # 检查是否存在相关文件
        has_files = False
        
        # 检查是否有导出文件（任何以export_id开头的文件）
        matching_files = list(REPORTS_DIR.glob(f"{export_id}*"))
        if matching_files:
            has_files = True
        
        if has_files:
            valid.append(export_id)
        else:
            orphaned.append((row['id'], export_id))
    
    print(f"📊 统计信息：")
    print(f"  总记录数: {len(rows)}")
    print(f"  有效记录: {len(valid)}")
    print(f"  孤立记录: {len(orphaned)}")
    
    if orphaned:
        print(f"\n🗑️  孤立记录列表（前20条）：")
        for db_id, export_id in orphaned[:20]:
            print(f"  - {export_id} (DB ID: {db_id})")
        
        if len(orphaned) > 20:
            print(f"  ... 还有 {len(orphaned) - 20} 条")
        
        confirm = input(f"\n⚠️  确认删除这 {len(orphaned)} 条孤立记录吗？(yes/no): ")
        if confirm.lower() == 'yes':
            for db_id, export_id in orphaned:
                cursor.execute('DELETE FROM export_records WHERE id = ?', (db_id,))
                print(f"  ✓ 已删除: {export_id}")
            
            conn.commit()
            print(f"\n✅ 成功清理 {len(orphaned)} 条孤立记录")
        else:
            print("❌ 取消清理")
    else:
        print("\n✅ 没有发现孤立记录，数据库状态良好")
    
    conn.close()

if __name__ == '__main__':
    print("=" * 60)
    print("清理孤立记录工具")
    print("=" * 60)
    cleanup_orphaned_export_records()
