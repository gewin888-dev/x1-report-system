"""
合并报告API路由
支持将多个单房间导出记录合并为一份完整的项目报告
"""
from flask import Blueprint, jsonify, request
from flask_login import login_required
from auth import require_permission
from helpers.merged_report import (
    list_mergeable_projects,
    get_project_export_records,
    create_merged_report_metadata
)
from pathlib import Path

merged_bp = Blueprint('merged', __name__)

# 这些变量会在app_x1.py中注入
BASE_DIR = None
PATHS = None

def init_merged_routes(base_dir: Path, paths: dict):
    """初始化路由（注入配置）"""
    global BASE_DIR, PATHS
    BASE_DIR = base_dir
    PATHS = paths


@merged_bp.route('/admin/api/merged_reports/candidates', methods=['GET'])
@login_required
@require_permission('record.view')
def api_list_mergeable_projects():
    """
    列出可以合并的项目（有多条导出记录的项目）
    """
    try:
        projects = list_mergeable_projects(BASE_DIR, PATHS)
        return jsonify({
            'success': True,
            'count': len(projects),
            'projects': projects
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@merged_bp.route('/admin/api/merged_reports/project_exports', methods=['GET'])
@login_required
@require_permission('record.view')
def api_get_project_exports():
    """
    获取某个项目的所有导出记录
    
    Query params:
        project_name: 项目名称
        report_number: 报告编号
    """
    project_name = request.args.get('project_name', '')
    report_number = request.args.get('report_number', '')
    
    if not project_name or not report_number:
        return jsonify({'success': False, 'error': '缺少project_name或report_number参数'}), 400
    
    try:
        records = get_project_export_records(project_name, report_number, BASE_DIR, PATHS)
        return jsonify({
            'success': True,
            'project_name': project_name,
            'report_number': report_number,
            'count': len(records),
            'records': records
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@merged_bp.route('/admin/api/merged_reports/create_metadata', methods=['POST'])
@login_required
@require_permission('record.export')
def api_create_merged_metadata():
    """
    创建合并报告的元数据（第一步：准备合并）
    
    POST body:
        {
            "project_name": "项目名称",
            "report_number": "报告编号"
        }
    """
    data = request.get_json(silent=True) or {}
    project_name = data.get('project_name', '')
    report_number = data.get('report_number', '')
    
    if not project_name or not report_number:
        return jsonify({'success': False, 'error': '缺少project_name或report_number'}), 400
    
    try:
        result = create_merged_report_metadata(project_name, report_number, BASE_DIR, PATHS)
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@merged_bp.route('/admin/api/merged_reports/generate', methods=['POST'])
@login_required
@require_permission('record.export')
def api_generate_merged_report():
    """
    生成合并报告（第二步：实际生成Word/PDF）
    
    POST body:
        {
            "merged_report_id": "MERGED_PROJECT_20260902123456"
        }
    
    Note: 此功能尚未实现，需要后续开发Word文档合并逻辑
    """
    data = request.get_json(silent=True) or {}
    merged_report_id = data.get('merged_report_id', '')
    
    if not merged_report_id:
        return jsonify({'success': False, 'error': '缺少merged_report_id'}), 400
    
    return jsonify({
        'success': False,
        'error': '合并报告生成功能开发中，请联系技术支持',
        'todo': 'Word文档合并逻辑待实现'
    }), 501  # 501 Not Implemented
