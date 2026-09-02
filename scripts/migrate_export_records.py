#!/usr/bin/env python3
"""
将现有的导出记录JSON文件迁移到export_records表
"""
import json
import sqlite3
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
REPORTS_DIR = BASE_DIR / "reports_x1"
DB_PATH = BASE_DIR / "data" / "x1_data.db"

def migrate_exports():
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()
    
    # 清空旧数据（如果重新迁移）
    cursor.execute("DELETE FROM export_records")
    
    export_files = list(REPORTS_DIR.glob("X1EXPORT_*.json"))
    print(f"找到 {len(export_files)} 个导出记录文件")
    
    success_count = 0
    error_count = 0
    
    for export_file in export_files:
        try:
            export_id = export_file.stem
            with open(export_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            ep = data.get('export_payload', {})
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
            json_path = str(export_file)
            xlsx_path = str(REPORTS_DIR / f"{export_id}.xlsx") if (REPORTS_DIR / f"{export_id}.xlsx").exists() else ''
            
            # 检查各种docx文件
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
            
            pdf_path = str(BASE_DIR / "preview_pdf" / f"{export_id}.pdf") if (BASE_DIR / "preview_pdf" / f"{export_id}.pdf").exists() else ''
            
            # 状态
            template_ready = bool(data.get('template_ready', False))
            report_success = bool(data.get('report_success'))
            raw_record_success = bool(data.get('raw_record_success'))
            overall_status = data.get('overall_status', 'unknown')
            
            # 飞书信息
            feishu = data.get('feishu', {}) or {}
            feishu_report = feishu.get('report', {}) or {}
            feishu_export = feishu.get('export', {}) or {}
            feishu_report_url = feishu_report.get('feishu_url', '') or feishu_report.get('feishu_open_url', '')
            feishu_export_url = feishu_export.get('feishu_url', '') or feishu_export.get('feishu_open_url', '')
            feishu_report_status = 'success' if feishu_report.get('success') else ('failed' if feishu_report.get('error') else '')
            feishu_export_status = 'success' if feishu_export.get('success') else ('failed' if feishu_export.get('error') else '')
            
            # 作废信息
            voided = bool(data.get('voided', False))
            voided_at = data.get('voided_at', '')
            voided_by = data.get('voided_by', '')
            void_reason = data.get('void_reason', '')
            
            # 时间戳
            saved_at = data.get('saved_at', '')
            if not saved_at:
                saved_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # 尝试关联project_id（通过project_name匹配）
            cursor.execute("SELECT id FROM business_projects WHERE project_name = ? LIMIT 1", (project_name,))
            row = cursor.fetchone()
            project_id = row[0] if row else None
            
            # 插入记录
            cursor.execute("""
                INSERT INTO export_records (
                    export_id, project_id, project_name, report_number, client_name,
                    inspection_area, operator, detection_date, detection_state, domain,
                    room_name, room_count,
                    json_path, xlsx_path, docx_path, pdf_path,
                    template_ready, report_success, raw_record_success, overall_status,
                    feishu_report_url, feishu_export_url, feishu_report_status, feishu_export_status,
                    voided, voided_at, voided_by, void_reason,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                export_id, project_id, project_name, report_number, client_name,
                inspection_area, operator, detection_date, detection_state, domain,
                room_name, 1,
                json_path, xlsx_path, docx_path, pdf_path,
                template_ready, report_success, raw_record_success, overall_status,
                feishu_report_url, feishu_export_url, feishu_report_status, feishu_export_status,
                voided, voided_at, voided_by, void_reason,
                saved_at, saved_at
            ))
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"❌ 处理失败 {export_file.name}: {e}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 迁移完成:")
    print(f"   成功: {success_count} 条")
    print(f"   失败: {error_count} 条")
    
    return success_count, error_count

if __name__ == '__main__':
    migrate_exports()
