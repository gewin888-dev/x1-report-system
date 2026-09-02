"""
草稿导出跟踪工具
在导出成功时更新草稿的导出状态，支持多房间项目的增量导出
"""
import sqlite3
from pathlib import Path

def update_draft_export_status(draft_id: str, room_index: int, export_id: str, BASE_DIR: Path, PATHS: dict):
    """
    更新草稿中某个房间的导出状态
    
    Args:
        draft_id: 草稿ID
        room_index: 房间索引（从0开始）
        export_id: 导出ID
        BASE_DIR: 项目根目录
        PATHS: 路径配置
    
    Returns:
        dict: {
            'success': bool,
            'draft_id': str,
            'all_exported': bool,  # 是否全部房间已导出
            'exported_count': int,  # 已导出房间数
            'total_count': int      # 总房间数
        }
    """
    db_path = BASE_DIR / PATHS.get('database', 'data/x1_data.db')
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 检查草稿是否存在
        cursor.execute("SELECT id, room_count FROM draft_records WHERE draft_id = ?", (draft_id,))
        draft = cursor.fetchone()
        
        if not draft:
            conn.close()
            return {'success': False, 'error': f'草稿 {draft_id} 不存在'}
        
        total_count = draft['room_count']
        
        # 更新房间导出状态
        from datetime import datetime
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        cursor.execute("""
            UPDATE draft_export_tracking
            SET exported = 1, export_id = ?, exported_at = ?, updated_at = ?
            WHERE draft_id = ? AND room_index = ?
        """, (export_id, now, now, draft_id, room_index))
        
        # 统计已导出房间数
        cursor.execute("""
            SELECT COUNT(*) as exported_count
            FROM draft_export_tracking
            WHERE draft_id = ? AND exported = 1
        """, (draft_id,))
        
        exported_count = cursor.fetchone()['exported_count']
        all_exported = (exported_count >= total_count)
        
        # 更新草稿记录的统计
        cursor.execute("""
            UPDATE draft_records
            SET exported_room_count = ?, all_exported = ?, updated_at = ?
            WHERE draft_id = ?
        """, (exported_count, all_exported, now, draft_id))
        
        conn.commit()
        conn.close()
        
        return {
            'success': True,
            'draft_id': draft_id,
            'all_exported': all_exported,
            'exported_count': exported_count,
            'total_count': total_count
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def check_draft_export_status(draft_id: str, BASE_DIR: Path, PATHS: dict):
    """
    查询草稿的导出状态
    
    Returns:
        dict: {
            'success': bool,
            'draft_id': str,
            'room_count': int,
            'exported_count': int,
            'all_exported': bool,
            'rooms': [{'room_index': int, 'room_name': str, 'exported': bool, 'export_id': str}, ...]
        }
    """
    db_path = BASE_DIR / PATHS.get('database', 'data/x1_data.db')
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询草稿基本信息
        cursor.execute("""
            SELECT draft_id, room_count, exported_room_count, all_exported
            FROM draft_records
            WHERE draft_id = ?
        """, (draft_id,))
        
        draft = cursor.fetchone()
        if not draft:
            conn.close()
            return {'success': False, 'error': f'草稿 {draft_id} 不存在'}
        
        # 查询各房间导出状态
        cursor.execute("""
            SELECT room_index, room_name, exported, export_id, exported_at
            FROM draft_export_tracking
            WHERE draft_id = ?
            ORDER BY room_index
        """, (draft_id,))
        
        rooms = []
        for row in cursor.fetchall():
            rooms.append({
                'room_index': row['room_index'],
                'room_name': row['room_name'],
                'exported': bool(row['exported']),
                'export_id': row['export_id'] or '',
                'exported_at': row['exported_at'] or ''
            })
        
        conn.close()
        
        return {
            'success': True,
            'draft_id': draft['draft_id'],
            'room_count': draft['room_count'],
            'exported_count': draft['exported_room_count'],
            'all_exported': bool(draft['all_exported']),
            'rooms': rooms
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e)}


def should_delete_draft(draft_id: str, BASE_DIR: Path, PATHS: dict):
    """
    判断草稿是否应该被删除
    
    删除条件：
    1. 所有房间都已导出 (all_exported = True)
    2. 或者是auto类型草稿且超过7天
    
    Returns:
        dict: {'should_delete': bool, 'reason': str}
    """
    db_path = BASE_DIR / PATHS.get('database', 'data/x1_data.db')
    
    try:
        conn = sqlite3.connect(str(db_path))
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT draft_kind, all_exported, file_mtime
            FROM draft_records
            WHERE draft_id = ?
        """, (draft_id,))
        
        draft = cursor.fetchone()
        conn.close()
        
        if not draft:
            return {'should_delete': False, 'reason': '草稿不存在'}
        
        # 条件1：全部导出完成
        if draft['all_exported']:
            return {'should_delete': True, 'reason': '所有房间已导出完成'}
        
        # 条件2：auto类型超过7天
        if draft['draft_kind'] == 'auto':
            import time
            cutoff = time.time() - 7 * 24 * 3600
            if draft['file_mtime'] < cutoff:
                return {'should_delete': True, 'reason': 'auto草稿超过7天'}
        
        return {'should_delete': False, 'reason': '仍有房间未导出'}
        
    except Exception as e:
        return {'should_delete': False, 'reason': f'检查失败: {e}'}
