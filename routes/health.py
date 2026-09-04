"""
系统健康监控路由
提供数据完整性、统计准确性等监控端点
"""

from flask import Blueprint, jsonify
from flask_login import login_required
from auth import require_permission
from helpers.data_integrity import (
    get_data_health_report, 
    verify_projects_summary,
    verify_records_summary
)

health_bp = Blueprint('health', __name__)


@health_bp.route('/admin/api/health/data_integrity')
@login_required
@require_permission('admin.system.view')
def data_integrity_check():
    """
    数据完整性健康检查
    
    返回:
    {
        "success": true,
        "report": {
            "projects_summary_accurate": true,
            "records_summary_accurate": true,
            "projects_stats": {...},
            "records_stats": {...},
            "orphaned_tasks_count": 0,
            "orphaned_feedback": {...},
            "total_projects": 53,
            "total_records": 268,
            "timestamp": "2026-09-04T15:30:00"
        }
    }
    """
    try:
        report = get_data_health_report()
        return jsonify({
            'success': True,
            'report': report
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'健康检查失败: {str(e)}'
        }), 500


@health_bp.route('/admin/api/health/projects_summary_accuracy')
@login_required
@require_permission('admin.projects.view')
def projects_summary_accuracy_check():
    """
    项目摘要统计准确性检查
    
    返回:
    {
        "success": true,
        "accurate": true,
        "stats": {...},
        "mismatches": []
    }
    """
    try:
        result = verify_projects_summary()
        return jsonify({
            'success': True,
            'accurate': result['accurate'],
            'stats': result['db_stats'],
            'mismatches': result['mismatches']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'准确性检查失败: {str(e)}'
        }), 500


@health_bp.route('/admin/api/health/records_summary_accuracy')
@login_required
@require_permission('admin.records.view')
def records_summary_accuracy_check():
    """
    记录摘要统计准确性检查
    
    返回:
    {
        "success": true,
        "accurate": true,
        "file_stats": {
            "total_draft_files": 194,
            "total_export_files": 76,
            "valid_drafts": 192,
            "valid_exports": 76,
            "total_valid": 268
        },
        "api_would_return": {
            "total": 268,
            "draft_count": 192,
            "export_count": 76
        }
    }
    """
    try:
        result = verify_records_summary()
        return jsonify({
            'success': True,
            'accurate': result['accurate'],
            'file_stats': result['file_stats'],
            'api_would_return': result['api_would_return'],
            'mismatches': result['mismatches']
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': f'准确性检查失败: {str(e)}'
        }), 500


# 保留旧端点以兼容
@health_bp.route('/admin/api/health/summary_accuracy')
@login_required
@require_permission('admin.projects.view')
def summary_accuracy_check():
    """
    摘要统计准确性检查（兼容旧端点，调用项目摘要检查）
    """
    return projects_summary_accuracy_check()
