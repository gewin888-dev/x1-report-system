#!/usr/bin/env python3
"""
将现有的草稿JSON文件迁移到draft_records表
并初始化draft_export_tracking表
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
RECORDS_DIR = BASE_DIR / "records_x1"
DB_PATH = BASE_DIR / "data" / "x1_data.db"

def _draft_has_visible_content(project: dict) -> bool:
    """判断草稿是否有有效内容（复用原逻辑）"""
    if not isinstance(project, dict):
        return False
    rooms = project.get('rooms') or []
    strong_fields = [
        project.get('project_name', ''),
        project.get('client_name', ''),
        project.get('contact_info', ''),
        project.get('project_address', ''),
        project.get('inspection_area', ''),
        project.get('detection_type', ''),
        project.get('detection_type_name', ''),
        project.get('remarks', ''),
    ]
    if any(str(v).strip() for v in strong_fields if v is not None):
        return True
    if project.get('detection_date'):
        return True
    if rooms:
        return True
    return False

def migrate_drafts():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 清空旧数据
    cursor.execute("DELETE FROM draft_records")
    cursor.execute("DELETE FROM draft_export_tracking")
    
    draft_files = list(RECORDS_DIR.glob("*.json"))
    print(f"找到 {len(draft_files)} 个草稿文件")
    
    success_count = 0
    error_count = 0
    
    for draft_file in draft_files:
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            project = data.get('project', {})
            
            # 跳过无效草稿
            if not _draft_has_visible_content(project):
                continue
            
            draft_id = data.get('draft_id', draft_file.stem)
            draft_kind = str(data.get('draft_kind', '')).strip().lower() or 'manual'
            
            # 基本信息
            project_name = project.get('project_name', '')
            report_number = project.get('report_number', '')
            client_name = project.get('client_name', '')
            operator = project.get('operator', '') or project.get('inspector', '')
            detection_date = project.get('detection_date', '')
            domain = project.get('domain_name', '') or project.get('domain', '')
            
            # 房间信息
            rooms = project.get('rooms', []) if isinstance(project.get('rooms', []), list) else []
            room_count = len(rooms)
            
            # 时间戳
            save_time = data.get('updated_at', '') or data.get('created_at', '') or data.get('saved_at', '')
            if not save_time:
                save_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            file_mtime = draft_file.stat().st_mtime
            
            # 尝试关联project_id
            cursor.execute("SELECT id FROM business_projects WHERE project_name = ? LIMIT 1", (project_name,))
            row = cursor.fetchone()
            project_id = row[0] if row else None
            
            # 插入draft_records
            cursor.execute("""
                INSERT INTO draft_records (
                    draft_id, draft_kind, project_id, project_name, report_number, client_name,
                    operator, detection_date, domain,
                    room_count, exported_room_count,
                    json_path, all_exported, is_valid,
                    created_at, updated_at, file_mtime
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                draft_id, draft_kind, project_id, project_name, report_number, client_name,
                operator, detection_date, domain,
                room_count, 0,  # exported_room_count初始为0
                str(draft_file), False, True,
                save_time, save_time, file_mtime
            ))
            
            # 为每个房间创建跟踪记录
            for i, room in enumerate(rooms):
                room_name = room.get('room_name', '') if isinstance(room, dict) else ''
                cursor.execute("""
                    INSERT INTO draft_export_tracking (
                        draft_id, room_index, room_name, exported, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    draft_id, i, room_name, False, save_time, save_time
                ))
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"❌ 处理失败 {draft_file.name}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 迁移完成:")
    print(f"   成功: {success_count} 个草稿")
    print(f"   失败: {error_count} 个")
    
    return success_count, error_count

if __name__ == '__main__':
    migrate_drafts()
