"""
导出记录数据库同步工具
在导出成功时插入/更新export_records表
"""
import sqlite3
from pathlib import Path

def sync_export_to_db(export_data: dict, BASE_DIR: Path, PATHS: dict):
    """
    将导出记录同步到export_records表
    
    Args:
        export_data: 包含导出信息的字典，应包含：
            - export_id
            - export_payload (包含project和room信息)
            - template_ready, report_success, raw_record_success等状态
            - feishu上传信息
        BASE_DIR: 项目根目录
        PATHS: 路径配置字典
    """
    db_path = BASE_DIR / PATHS.get('database', 'data/x1_data.db')
    
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        export_id = export_data.get('export_id', '')
        ep = export_data.get('export_payload', {})
        proj = ep.get('project', {})
        room = ep.get('room', {})
        
        # 基本信息
        project_name = proj.get('project_name', '')
        report_number = proj.get('report_number', '')
        client_name = proj.get('client_name', '')
        inspection_area = proj.get('inspection_area', '')
        operator = proj.get('operator', '') or proj.get('inspector', '')
        detection_date = proj.get('detection_date', '')
        detection_state = proj.get('detection_state', '')
        domain = proj.get('domain_name', '') or proj.get('domain', '')
        room_name = room.get('room_name', '')
        
        # 文件路径
        REPORTS_DIR = BASE_DIR / PATHS.get('reports', 'reports_x1')
        json_path = str(REPORTS_DIR / f"{export_id}.json")
        xlsx_path = str(REPORTS_DIR / f"{export_id}.xlsx")
        
        # docx文件优先级：filled > bound > normal
        filled_docx = REPORTS_DIR / f"{export_id}.filled.docx"
        bound_docx = REPORTS_DIR / f"{export_id}.bound.docx"
        normal_docx = REPORTS_DIR / f"{export_id}.docx"
        
        if filled_docx.exists():
            docx_path = str(filled_docx)
        elif bound_docx.exists():
            docx_path = str(bound_docx)
        elif normal_docx.exists():
            docx_path = str(normal_docx)
        else:
            docx_path = ''
        
        pdf_path = str(BASE_DIR / "preview_pdf" / f"{export_id}.pdf")
        
        # 状态
        template_ready = bool(export_data.get('template_ready', False))
        report_success = bool(export_data.get('report_success', True))
        raw_record_success = bool(export_data.get('raw_record_success', True))
        overall_status = export_data.get('overall_status', 'success')
        
        # 飞书信息
        feishu = export_data.get('feishu', {}) or {}
        feishu_report = feishu.get('report', {}) or {}
        feishu_export = feishu.get('export', {}) or {}
        feishu_report_url = feishu_report.get('feishu_url', '') or feishu_report.get('feishu_open_url', '')
        feishu_export_url = feishu_export.get('feishu_url', '') or feishu_export.get('feishu_open_url', '')
        feishu_report_status = 'success' if feishu_report.get('success') else ('failed' if feishu_report.get('error') else 'pending')
        feishu_export_status = 'success' if feishu_export.get('success') else ('failed' if feishu_export.get('error') else 'pending')
        
        # 时间戳
        saved_at = export_data.get('saved_at', '')
        
        # 尝试关联project_id
        cursor.execute("SELECT id FROM business_projects WHERE project_name = ? LIMIT 1", (project_name,))
        row = cursor.fetchone()
        project_id = row[0] if row else None
        
        # 检查记录是否已存在
        cursor.execute("SELECT id FROM export_records WHERE export_id = ?", (export_id,))
        existing = cursor.fetchone()
        
        if existing:
            # 更新
            cursor.execute("""
                UPDATE export_records SET
                    project_id = ?, project_name = ?, report_number = ?, client_name = ?,
                    inspection_area = ?, operator = ?, detection_date = ?, detection_state = ?,
                    domain = ?, room_name = ?, room_count = ?,
                    json_path = ?, xlsx_path = ?, docx_path = ?, pdf_path = ?,
                    template_ready = ?, report_success = ?, raw_record_success = ?, overall_status = ?,
                    feishu_report_url = ?, feishu_export_url = ?,
                    feishu_report_status = ?, feishu_export_status = ?,
                    updated_at = ?
                WHERE export_id = ?
            """, (
                project_id, project_name, report_number, client_name,
                inspection_area, operator, detection_date, detection_state,
                domain, room_name, 1,
                json_path, xlsx_path, docx_path, pdf_path,
                template_ready, report_success, raw_record_success, overall_status,
                feishu_report_url, feishu_export_url,
                feishu_report_status, feishu_export_status,
                saved_at,
                export_id
            ))
        else:
            # 插入
            cursor.execute("""
                INSERT INTO export_records (
                    export_id, project_id, project_name, report_number, client_name,
                    inspection_area, operator, detection_date, detection_state, domain,
                    room_name, room_count,
                    json_path, xlsx_path, docx_path, pdf_path,
                    template_ready, report_success, raw_record_success, overall_status,
                    feishu_report_url, feishu_export_url,
                    feishu_report_status, feishu_export_status,
                    voided, voided_at, voided_by, void_reason,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                export_id, project_id, project_name, report_number, client_name,
                inspection_area, operator, detection_date, detection_state, domain,
                room_name, 1,
                json_path, xlsx_path, docx_path, pdf_path,
                template_ready, report_success, raw_record_success, overall_status,
                feishu_report_url, feishu_export_url,
                feishu_report_status, feishu_export_status,
                False, '', '', '',
                saved_at, saved_at
            ))
        
        conn.commit()
        conn.close()
        return {'success': True, 'export_id': export_id}
        
    except Exception as e:
        return {'success': False, 'error': str(e)}
