"""
优化后的记录列表API - 使用数据库查询导出记录
"""
import json
import time
import sqlite3
from pathlib import Path
from flask import request, jsonify
from flask_login import current_user

from auth import can_view_record
from helpers.record_utils import _compute_record_asset_state

def admin_api_records_v2(BASE_DIR, RECORDS_DIR, PATHS):
    """
    记录列表 v2 - 使用export_records表 + 文件系统草稿
    性能优化：导出记录从数据库查询，草稿仍从文件读取
    """
    records = []
    
    def _draft_has_visible_content(project: dict, data: dict) -> bool:
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
    
    # ========== 1. 读取草稿记录（从文件系统，保持原逻辑）==========
    auto_draft_cutoff = time.time() - 7 * 24 * 3600
    for draft_file in RECORDS_DIR.glob('*.json'):
        try:
            with open(draft_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                project = data.get('project', {})
                if not _draft_has_visible_content(project, data):
                    continue
                
                # 严格过滤auto类型草稿：超过7天的不显示
                draft_kind = str(data.get('draft_kind', '')).strip().lower()
                if draft_kind == 'auto':
                    file_mtime = draft_file.stat().st_mtime
                    if file_mtime < auto_draft_cutoff:
                        continue
                
                save_time = data.get('updated_at', '') or data.get('created_at', '') or data.get('saved_at', '')
                room_count = len(project.get('rooms', []) if isinstance(project.get('rooms', []), list) else data.get('rooms', []))
                records.append({
                    'id': data.get('draft_id', draft_file.stem),
                    'type': 'draft',
                    'project_name': project.get('project_name', ''),
                    'report_number': project.get('report_number', ''),
                    'client_name': project.get('client_name', ''),
                    'inspection_area': project.get('inspection_area', ''),
                    'operator': project.get('operator', '') or project.get('inspector', ''),
                    'detection_date': project.get('detection_date', ''),
                    'detection_state': project.get('detection_state', ''),
                    'domain': project.get('domain_name', '') or project.get('domain', ''),
                    'room_count': room_count,
                    'save_time': save_time,
                    'save_time_min': (save_time.replace('T',' ')[:16] if save_time else ''),
                    'created': data.get('created_at', '') or data.get('saved_at', ''),
                    'modified': data.get('updated_at', '') or data.get('saved_at', ''),
                    'status': 'draft',
                    'draft_kind': draft_kind,
                    'has_report': False,
                    'has_export': False,
                    'report_info': {},
                    'export_info': {},
                    'report_download_url': '',
                    'export_download_url': ''
                })
        except:
            pass
    
    # ========== 2. 读取导出记录（从数据库）==========
    db_path = BASE_DIR / PATHS.get('database', 'data/x1_data.db')
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT 
            export_id, project_id, project_name, report_number, client_name,
            inspection_area, operator, detection_date, detection_state, domain,
            room_name, room_count,
            json_path, xlsx_path, docx_path, pdf_path,
            template_ready, report_success, raw_record_success, overall_status,
            feishu_report_url, feishu_export_url, feishu_report_status, feishu_export_status,
            voided, voided_at, voided_by, void_reason,
            created_at, updated_at
        FROM export_records
        ORDER BY created_at DESC
    """)
    
    for row in cursor.fetchall():
        # 构建asset_state（文件存在性检查）
        report_file = None
        raw_excel = None
        
        docx_path = row['docx_path']
        if docx_path and Path(docx_path).exists():
            report_file = {'name': Path(docx_path).name, 'path': docx_path}
        
        xlsx_path = row['xlsx_path']
        if xlsx_path and Path(xlsx_path).exists():
            raw_excel = {'name': Path(xlsx_path).name, 'path': xlsx_path}
        
        asset_state = {
            'report_file': report_file,
            'raw_excel': raw_excel,
            'local_report_ok': bool(report_file),
            'local_record_ok': bool(raw_excel),
            'feishu_report_ok': row['feishu_report_status'] == 'success',
            'feishu_record_ok': row['feishu_export_status'] == 'success',
            'healthy': True,
            'issues': []
        }
        
        records.append({
            'id': row['export_id'],
            'type': 'export',
            'project_name': row['project_name'],
            'report_number': row['report_number'],
            'client_name': row['client_name'],
            'inspection_area': row['inspection_area'],
            'operator': row['operator'],
            'detection_date': row['detection_date'],
            'detection_state': row['detection_state'],
            'domain': row['domain'],
            'room_count': row['room_count'],
            'save_time': row['created_at'],
            'save_time_min': (row['created_at'].replace('T',' ')[:16] if row['created_at'] else ''),
            'created': row['created_at'],
            'modified': row['updated_at'],
            'status': 'generated',
            'overall_status': row['overall_status'],
            'report_success': bool(row['report_success']),
            'raw_record_success': bool(row['raw_record_success']),
            'template_ready': bool(row['template_ready']),
            'has_report': bool(report_file) or bool(row['feishu_report_url']),
            'has_export': bool(raw_excel) or bool(row['feishu_export_url']),
            'report_info': {'feishu_url': row['feishu_report_url']},
            'export_info': {'feishu_url': row['feishu_export_url']},
            'feishu_report_url': row['feishu_report_url'],
            'feishu_export_url': row['feishu_export_url'],
            'feishu_report_status': row['feishu_report_status'],
            'feishu_export_status': row['feishu_export_status'],
            'voided': bool(row['voided']),
            'voided_at': row['voided_at'],
            'voided_by': row['voided_by'],
            'void_reason': row['void_reason'],
            'asset_state': asset_state,
            'pdf_preview': row['pdf_path'] if row['pdf_path'] and Path(row['pdf_path']).exists() else ''
        })
    
    conn.close()
    
    # ========== 3. 权限过滤 ==========
    records = [r for r in records if can_view_record(current_user, {'inspector_name': r.get('operator', '')})]
    
    # ========== 4. 收集领域列表 ==========
    all_domains = sorted(set(r.get('domain', '') for r in records if r.get('domain', '')))
    
    # ========== 5. 筛选 ==========
    keyword = request.args.get('keyword', '').strip().lower()
    domain_filter = request.args.get('domain', '').strip()
    type_filter = request.args.get('type', '').strip()
    
    if domain_filter:
        records = [r for r in records if r.get('domain', '') == domain_filter]
    if type_filter:
        if type_filter == 'report':
            records = [r for r in records if r.get('type', '') == 'export' and (r.get('report_success') or r.get('has_report'))]
        elif type_filter == 'draft':
            records = [r for r in records if r.get('type', '') == 'draft']
        elif type_filter == 'voided':
            records = [r for r in records if bool(r.get('voided'))]
        elif type_filter == 'all':
            pass
        else:
            records = [r for r in records if r.get('type', '') == type_filter]
    if keyword:
        parts = keyword.split()
        def match_keyword(r):
            s = ' '.join([
                r.get('project_name', ''),
                r.get('report_number', ''),
                r.get('client_name', ''),
                r.get('operator', '')
            ]).lower()
            return all(p in s for p in parts)
        records = [r for r in records if match_keyword(r)]
    
    # ========== 6. 排序 ==========
    records.sort(key=lambda r: r.get('save_time', '') or '', reverse=True)
    
    # ========== 7. 分页 ==========
    total = len(records)
    page = max(1, int(request.args.get('page', 1)))
    page_size = max(1, min(200, int(request.args.get('page_size', 50))))
    total_pages = max(1, (total + page_size - 1) // page_size)
    if page > total_pages:
        page = total_pages
    start = (page - 1) * page_size
    paged_records = records[start:start + page_size]
    
    return jsonify({
        'records': paged_records,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
        'domains': all_domains
    })
