#!/usr/bin/env python3
"""
草稿清理任务
定期清理以下草稿：
1. 所有房间都已导出完成的草稿（保留7天后删除）
2. auto类型草稿超过7天的
3. 孤立草稿（数据库中不存在但文件存在）
"""
import sqlite3
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
RECORDS_DIR = BASE_DIR / "records_x1"
DB_PATH = BASE_DIR / "data" / "x1_data.db"
TRASH_DIR = BASE_DIR / "trash" / "drafts"

def cleanup_drafts(dry_run=False):
    """
    清理草稿文件
    
    Args:
        dry_run: 如果为True，只统计不删除
    
    Returns:
        dict: 清理统计结果
    """
    TRASH_DIR.mkdir(parents=True, exist_ok=True)
    
    stats = {
        'total_checked': 0,
        'all_exported_deleted': 0,
        'auto_expired_deleted': 0,
        'orphan_deleted': 0,
        'errors': []
    }
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # 获取所有草稿记录
    cursor.execute("""
        SELECT draft_id, draft_kind, all_exported, file_mtime, json_path
        FROM draft_records
    """)
    
    draft_map = {}
    for row in cursor.fetchall():
        draft_map[row['draft_id']] = {
            'draft_kind': row['draft_kind'],
            'all_exported': bool(row['all_exported']),
            'file_mtime': row['file_mtime'],
            'json_path': row['json_path']
        }
    
    conn.close()
    
    # 遍历文件系统中的草稿文件
    draft_files = list(RECORDS_DIR.glob("*.json"))
    stats['total_checked'] = len(draft_files)
    
    now = time.time()
    auto_cutoff = now - 7 * 24 * 3600
    all_exported_cutoff = now - 7 * 24 * 3600  # 全部导出完成后保留7天
    
    for draft_file in draft_files:
        try:
            draft_id = draft_file.stem
            
            # 情况1：数据库中不存在（孤立文件）
            if draft_id not in draft_map:
                print(f"🗑️  孤立草稿: {draft_id}")
                if not dry_run:
                    trash_target = TRASH_DIR / draft_file.name
                    draft_file.rename(trash_target)
                stats['orphan_deleted'] += 1
                continue
            
            draft_info = draft_map[draft_id]
            file_mtime = draft_file.stat().st_mtime
            
            # 情况2：所有房间已导出完成，且超过7天
            if draft_info['all_exported']:
                if file_mtime < all_exported_cutoff:
                    print(f"✅ 全部导出完成且超过7天: {draft_id}")
                    if not dry_run:
                        trash_target = TRASH_DIR / draft_file.name
                        draft_file.rename(trash_target)
                    stats['all_exported_deleted'] += 1
                    continue
                else:
                    print(f"📌 全部导出完成但未满7天，保留: {draft_id}")
            
            # 情况3：auto类型草稿超过7天
            if draft_info['draft_kind'] == 'auto':
                if file_mtime < auto_cutoff:
                    print(f"⏰ auto草稿超过7天: {draft_id}")
                    if not dry_run:
                        trash_target = TRASH_DIR / draft_file.name
                        draft_file.rename(trash_target)
                    stats['auto_expired_deleted'] += 1
                    continue
            
        except Exception as e:
            stats['errors'].append(f"{draft_file.name}: {e}")
            print(f"❌ 处理失败 {draft_file.name}: {e}")
    
    return stats


if __name__ == '__main__':
    import sys
    
    dry_run = '--dry-run' in sys.argv
    
    if dry_run:
        print("=" * 80)
        print("🔍 草稿清理预览（dry-run模式，不会实际删除）")
        print("=" * 80)
    else:
        print("=" * 80)
        print("🗑️  草稿清理任务")
        print("=" * 80)
    
    stats = cleanup_drafts(dry_run=dry_run)
    
    print("\n" + "=" * 80)
    print("清理统计:")
    print(f"  检查草稿数: {stats['total_checked']}")
    print(f"  全部导出完成删除: {stats['all_exported_deleted']}")
    print(f"  auto超期删除: {stats['auto_expired_deleted']}")
    print(f"  孤立文件删除: {stats['orphan_deleted']}")
    print(f"  总删除数: {stats['all_exported_deleted'] + stats['auto_expired_deleted'] + stats['orphan_deleted']}")
    
    if stats['errors']:
        print(f"\n错误:")
        for err in stats['errors']:
            print(f"  - {err}")
    
    print("=" * 80)
    
    if dry_run:
        print("✅ 预览完成，使用不带--dry-run参数运行以实际删除")
    else:
        print("✅ 清理完成")
