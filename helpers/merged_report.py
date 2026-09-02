"""
整体项目报告生成工具
将多个单房间导出记录合并为一份完整的项目报告
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

def get_project_export_records(project_name: str, report_number: str, BASE_DIR: Path, PATHS: dict):
    """
    获取某个项目的所有导出记录
    
    Returns:
        list: [{export_id, room_name, inspection_area, docx_path, xlsx_path, ...}, ...]
    """
    db_path = BASE_DIR / PATHS.get('database', 'data/x1_data.db')
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            export_id, room_name, inspection_area,
            docx_path, xlsx_path, pdf_path,
            detection_date, operator, domain,
            created_at
        FROM export_records
        WHERE project_name = ? AND report_number = ? AND voided = 0
        ORDER BY created_at ASC
    """, (project_name, report_number))
    
    records = []
    for row in cursor.fetchall():
        records.append({
            'export_id': row['export_id'],
            'room_name': row['room_name'],
            'inspection_area': row['inspection_area'],
            'docx_path': row['docx_path'],
            'xlsx_path': row['xlsx_path'],
            'pdf_path': row['pdf_path'],
            'detection_date': row['detection_date'],
            'operator': row['operator'],
            'domain': row['domain'],
            'created_at': row['created_at']
        })
    
    conn.close()
    return records


def create_merged_report_metadata(project_name: str, report_number: str, BASE_DIR: Path, PATHS: dict):
    """
    创建合并报告的元数据记录
    
    Returns:
        dict: {
            'success': bool,
            'merged_report_id': str,  # MERGED_PROJECT_YYYYMMDDHHMMSS
            'project_name': str,
            'report_number': str,
            'room_count': int,
            'export_ids': [str, ...],  # 包含的导出记录ID
            'metadata_path': str
        }
    """
    records = get_project_export_records(project_name, report_number, BASE_DIR, PATHS)
    
    if not records:
        return {'success': False, 'error': '未找到该项目的导出记录'}
    
    # 生成合并报告ID
    merged_id = f"MERGED_PROJECT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # 构建元数据
    metadata = {
        'merged_report_id': merged_id,
        'merge_type': 'project_complete',  # 整体项目报告
        'project_name': project_name,
        'report_number': report_number,
        'room_count': len(records),
        'export_records': records,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'status': 'metadata_created'  # 状态：metadata_created -> generating -> completed
    }
    
    # 保存元数据
    MERGED_DIR = BASE_DIR / "merged_reports"
    MERGED_DIR.mkdir(parents=True, exist_ok=True)
    
    metadata_file = MERGED_DIR / f"{merged_id}.json"
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    return {
        'success': True,
        'merged_report_id': merged_id,
        'project_name': project_name,
        'report_number': report_number,
        'room_count': len(records),
        'export_ids': [r['export_id'] for r in records],
        'metadata_path': str(metadata_file)
    }


def list_mergeable_projects(BASE_DIR: Path, PATHS: dict):
    """
    列出可以合并的项目（有多条导出记录的项目）
    
    Returns:
        list: [{
            'project_name': str,
            'report_number': str,
            'export_count': int,
            'client_name': str,
            'detection_date': str
        }, ...]
    """
    db_path = BASE_DIR / PATHS.get('database', 'data/x1_data.db')
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            project_name,
            report_number,
            client_name,
            detection_date,
            COUNT(*) as export_count
        FROM export_records
        WHERE voided = 0
        GROUP BY project_name, report_number
        HAVING COUNT(*) > 1
        ORDER BY export_count DESC, detection_date DESC
    """)
    
    projects = []
    for row in cursor.fetchall():
        projects.append({
            'project_name': row['project_name'],
            'report_number': row['report_number'],
            'client_name': row['client_name'],
            'detection_date': row['detection_date'],
            'export_count': row['export_count']
        })
    
    conn.close()
    return projects


if __name__ == '__main__':
    # 测试：列出可合并的项目
    import sys
    from pathlib import Path
    
    BASE_DIR = Path(__file__).parent.parent
    sys.path.insert(0, str(BASE_DIR))
    
    from config_loader import load_x1_config
    
    BASE_DIR = Path(__file__).parent.parent
    CFG = load_x1_config(BASE_DIR)
    PATHS = CFG.get('paths', {})
    
    print("="*80)
    print("可合并为整体项目报告的项目列表")
    print("="*80)
    
    projects = list_mergeable_projects(BASE_DIR, PATHS)
    
    print(f"\n找到 {len(projects)} 个可合并的项目:\n")
    
    for i, proj in enumerate(projects[:10], 1):  # 只显示前10个
        print(f"{i}. {proj['project_name']}")
        print(f"   报告编号: {proj['report_number']}")
        print(f"   委托单位: {proj['client_name']}")
        print(f"   房间数: {proj['export_count']} 个")
        print(f"   检测日期: {proj['detection_date']}")
        print()
    
    if len(projects) > 10:
        print(f"... 还有 {len(projects) - 10} 个项目")
    
    print("="*80)
