"""
routes/export.py - 导出相关路由 Blueprint

从 app_x1.py 提取，保持原有逻辑不变。
"""

import json
import os
import shutil
import tempfile
import threading
from datetime import datetime
from pathlib import Path

from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user

from auth import require_permission
from database import get_db
from monitor import log_action, log_error, monitor_performance
from config_loader import load_x1_config
from adapters.export_docx import build_canonical_object_report
from adapters.export_excel import build_canonical_excel_report
from adapters.template_fill import build_template_bound_docx, build_mixed_report_docx
from template_rules import resolve_template_rule
from template_resources import resolve_template_resource
from report_context_builder import build_report_context
from clean_class_semantics import build_clean_class_semantics, _normalize_operating_room_context
from judgement_engine import judge_room
from payload_normalizer import normalize_project_payload, validate_normalized_project
from feishu_utils import upload_file_to_feishu, resolve_feishu_upload_folder

from helpers.export_utils import (
    _x_export_path, _x_select_template, _build_single_room_export,
    _build_export_payload, _try_advance_on_export
)
from helpers.record_utils import (
    _x_now, _resolve_active_draft_id, _delete_draft_file_if_exists
)
from helpers.project_utils import _auto_sync_project_and_task
from helpers.db import get_x1_data_conn
from helpers.settings_utils import _load_system_settings, _setting_enabled

# ============================================================
# Blueprint 定义
# ============================================================

export_bp = Blueprint('export', __name__)

# ============================================================
# 路径常量
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent
CFG = load_x1_config(BASE_DIR)
PATHS = CFG.get('paths', {})
REPORTS_DIR = BASE_DIR / PATHS.get('reports', 'reports_x1')
FORMAL_RECORDS_BASE = Path(os.path.expanduser(str((CFG.get('archive') or {}).get('formal_raw_archive') or PATHS.get('formal_raw_archive') or '~/公司资料/检测部/原始记录'))).resolve()
FORMAL_REPORTS_BASE = Path(os.path.expanduser(str((CFG.get('archive') or {}).get('formal_report_archive') or PATHS.get('formal_report_archive') or '~/公司资料/检测部/检测报告'))).resolve()


# ============================================================
# 内部辅助函数
# ============================================================

def _formal_year_dir(base: Path, year: int) -> Path:
    target = base / str(year)
    target.mkdir(parents=True, exist_ok=True)
    return target


def _safe_filename_part(value: str, fallback: str = '未命名') -> str:
    text = str(value or '').strip()
    if not text:
        text = fallback
    for ch in ['/', '\\', ':', '*', '?', '"', '<', '>', '|']:
        text = text.replace(ch, '_')
    text = text.replace('\n', '_').replace('\r', '_').replace('\t', '_')
    return text[:120].strip() or fallback


def _copy_to_formal_dir(src: Path, base: Path, year: int, target_name=None):
    if not src or not src.exists():
        return {'success': False, 'error': '源文件不存在'}
    try:
        target_dir = _formal_year_dir(base, year)
        target = target_dir / (target_name or src.name)
        shutil.copy2(src, target)
        return {'success': True, 'path': str(target), 'filename': target.name}
    except Exception as e:
        return {'success': False, 'error': str(e)}


# ============================================================
# 路由
# ============================================================

@export_bp.route('/record/api/export_excel', methods=['POST'])
@login_required
@require_permission('record.export')
def api_record_export_excel():
    """导出原始记录(Excel)，前端 record.js exportRecordExcel() 调用。"""
    data = request.get_json(silent=True) or {}
    project = data if isinstance(data, dict) else {}
    project = normalize_project_payload(project, source='export_excel')
    validation_error = validate_normalized_project(project)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    export_payload = _build_export_payload(project)
    export_id = f"X1EXCEL_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    xlsx_target = REPORTS_DIR / f"{export_id}.xlsx"
    try:
        build_canonical_excel_report(export_payload, str(xlsx_target))
    except Exception as e:
        log_error('export_excel', str(e), f'export_id={export_id}')
        return jsonify({'success': False, 'error': str(e)}), 500
    if not xlsx_target.exists():
        return jsonify({'success': False, 'error': 'Excel 文件生成失败'}), 500
    log_action(current_user.id, '导出原始记录', export_id,
               f"{export_payload.get('project', {}).get('project_name', '')} - Excel")
    return jsonify({
        'success': True,
        'export_id': export_id,
        'filename': xlsx_target.name,
        'download_url': f'/download/{xlsx_target.name}'
    })


@export_bp.route('/api/x/build_export', methods=['POST'])
@login_required
@require_permission('record.export')
def api_x_build_export():
    data = request.get_json(silent=True) or {}
    project = data.get('project') if isinstance(data.get('project'), dict) else data
    project = normalize_project_payload(project, source='build_export')
    validation_error = validate_normalized_project(project)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    payload = _build_export_payload(project)
    return jsonify({'success': True, 'export_payload': payload})


@export_bp.route('/api/submit_and_export', methods=['POST'])
@login_required
@require_permission('admin.records.export')
def api_submit_and_export_compat():
    """旧客户端兼容导出接口，复用 X1 正式导出逻辑。"""
    response = api_x_submit_export()
    if isinstance(response, tuple):
        body, status = response
        if hasattr(body, 'get_json'):
            payload = body.get_json(silent=True) or {}
            if isinstance(payload, dict):
                payload.setdefault('compat', True)
                payload.setdefault('compat_route', '/api/submit_and_export')
            return jsonify(payload), status
        return response
    payload = response.get_json(silent=True) or {}
    if isinstance(payload, dict):
        payload.setdefault('compat', True)
        payload.setdefault('compat_route', '/api/submit_and_export')
    return jsonify(payload)


@export_bp.route('/api/x/submit_export', methods=['POST'])
@login_required
@require_permission('record.export')
@monitor_performance('export_report')
def api_x_submit_export():
    data = request.get_json(silent=True) or {}
    project = data.get('project') if isinstance(data.get('project'), dict) else data
    project = normalize_project_payload(project, source='submit_export')
    source_draft_id = _resolve_active_draft_id(data, project)
    validation_error = validate_normalized_project(project)
    if validation_error:
        return jsonify({'success': False, 'error': validation_error}), 400
    export_payload = _build_export_payload(project)
    if export_payload.get('export_type') != (project.get('rooms') or [{}])[0].get('type_id'):
        return jsonify({'success': False, 'error': 'export_type 与 room.type_id 不一致'}), 400
    export_id = f"X1EXPORT_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    json_target = _x_export_path(export_id)
    xlsx_target = REPORTS_DIR / f"{export_id}.xlsx"
    docx_target = REPORTS_DIR / f"{export_id}.docx"
    bound_docx_target = REPORTS_DIR / f"{export_id}.bound.docx"
    filled_docx_target = REPORTS_DIR / f"{export_id}.filled.docx"
    template_resource = export_payload.get('template_resource', {}) or {}
    template_ready = bool(template_resource.get('template_found')) and template_resource.get('resource_status') == 'confirmed'
    report_export_enabled = _setting_enabled('export.enable_report_docx', True)
    raw_export_enabled = _setting_enabled('export.enable_raw_record', True)
    template_gate_enabled = _setting_enabled('template.enable_gate', True)
    template_gate_mode = _load_system_settings().get('template.gate_mode', {}).get('value', 'strict')
    final_payload = {
        'export_id': export_id,
        'saved_at': _x_now(),
        'schema_version': project.get('schema_version', '1.1'),
        'record_version': project.get('record_version', '1'),
        'trace_id': project.get('trace_id', ''),
        'normalized_at': project.get('normalized_at', ''),
        'export_payload': export_payload,
        'template_ready': template_ready,
    }

    try:
        with open(json_target, 'w', encoding='utf-8') as f:
            json.dump(final_payload, f, ensure_ascii=False, indent=2)
        build_canonical_excel_report(export_payload, str(xlsx_target)) if raw_export_enabled else None
        build_canonical_object_report(export_payload, str(docx_target)) if report_export_enabled else None
        build_template_bound_docx(export_payload, str(bound_docx_target)) if report_export_enabled else None
        filled_docx_path = build_mixed_report_docx(export_payload, str(filled_docx_target)) if (report_export_enabled and template_ready) else ''

        # 记录操作日志
        project_name = export_payload.get('project', {}).get('project_name', '')
        type_name = export_payload.get('room', {}).get('type_name', '')
        log_action(current_user.id, '导出报告', export_id, f'{project_name} - {type_name}')

    except Exception as e:
        log_error('export_report', str(e), f'export_id={export_id}')
        return jsonify({'success': False, 'error': str(e)}), 500

    # 检测报告模板命中闸门：模板未命中时，原始记录可生成，但正式检测报告不允许按成功件返回
    # 这里明确区分双链结果：xlsx 允许成功产出，docx 视为正式检测报告失败。
    if template_gate_enabled and template_gate_mode == 'strict' and report_export_enabled and not template_ready:
        return jsonify({
            'success': True,
            'report_success': False,
            'raw_record_success': bool(xlsx_target.exists()),
            'overall_status': 'partial_success' if xlsx_target.exists() else 'failed',
            'report_status': 'blocked_template_missing',
            'raw_record_status': 'success' if xlsx_target.exists() else 'failed',
            'error': '检测报告模板未命中，禁止生成正式检测报告；请先修正对象类型/等级/子类型口径或模板资源映射。',
            'export_id': export_id,
            'saved_at': final_payload['saved_at'],
            'json_path': str(json_target),
            'xlsx_path': str(xlsx_target) if xlsx_target.exists() else '',
            'template_ready': template_ready,
            'template_key': template_resource.get('template_key', ''),
            'template_name': template_resource.get('template_name', ''),
            'template_found': template_resource.get('template_found', False),
            'template_path': template_resource.get('template_path', ''),
            'export_stage': 'template-resource-missing',
            'export_payload': export_payload,
            'dual_chain': {
                'report': {'success': False, 'status': 'blocked_template_missing', 'blocked_by_template_gate': True},
                'raw_record': {'success': bool(xlsx_target.exists()), 'status': 'success' if xlsx_target.exists() else 'failed'}
            }
        }), 200

    # 飞书上传 + PDF 转换 + 正式目录落地：异步执行，不阻塞导出主流程
    def _async_post_export():
        """后台线程：飞书上传 + PDF 转换 + 正式目录落地"""
        try:
            feishu_report = {}
            feishu_export = {}
            feishu_enabled = _setting_enabled('feishu.enabled', True)
            detection_date = export_payload.get('project', {}).get('detection_date', '')
            year = int(detection_date[:4]) if detection_date and len(detection_date) >= 4 else datetime.now().year

            report_file = filled_docx_target if filled_docx_path else bound_docx_target
            if feishu_enabled and report_file.exists():
                reports_folder = resolve_feishu_upload_folder('reports', year)
                if reports_folder:
                    feishu_report = upload_file_to_feishu(str(report_file), reports_folder)
                    if feishu_report.get('success'):
                        print(f"✅ 检测报告已上传飞书: {feishu_report.get('feishu_url', '')}")

            if feishu_enabled and xlsx_target.exists():
                exports_folder = resolve_feishu_upload_folder('exports', year)
                if exports_folder:
                    feishu_export = upload_file_to_feishu(str(xlsx_target), exports_folder)
                    if feishu_export.get('success'):
                        print(f"✅ 原始记录已上传飞书: {feishu_export.get('feishu_url', '')}")

            # 正式目录双落地
            project_info = export_payload.get('project', {}) or {}
            cn = _safe_filename_part(project_info.get('client_name', ''), '未知委托单位')
            pn = _safe_filename_part(project_info.get('project_name', ''), '未命名项目')
            rn = _safe_filename_part(project_info.get('report_number', ''), export_id)
            # 文件名加时间戳后缀，避免同项目多次导出覆盖
            ts = datetime.now().strftime('%Y%m%d%H%M%S')
            formal_export_name = f"原始记录_{cn}_{pn}_{ts}.xlsx"
            report_source = Path(filled_docx_path) if filled_docx_path else (bound_docx_target if bound_docx_target.exists() else docx_target)
            formal_report_name = f"{rn}_{cn}_{ts}{report_source.suffix or '.docx'}"
            formal_export = _copy_to_formal_dir(xlsx_target, FORMAL_RECORDS_BASE, year, formal_export_name)
            formal_report = _copy_to_formal_dir(report_source, FORMAL_REPORTS_BASE, year, formal_report_name)

            # PDF 转换
            pdf_preview_path = ''
            try:
                from pdf_converter import convert_docx_to_pdf
                pdf_dir = BASE_DIR / 'preview_pdf'
                pdf_dir.mkdir(exist_ok=True)
                docx_for_pdf = Path(filled_docx_path) if filled_docx_path else (bound_docx_target if bound_docx_target.exists() else None)
                if docx_for_pdf and docx_for_pdf.exists():
                    pdf_out = pdf_dir / f"{export_id}.pdf"
                    pdf_preview_path = convert_docx_to_pdf(str(docx_for_pdf), str(pdf_out))
            except Exception as e:
                print(f"[async_post_export] PDF 转换跳过: {e}")

            # 回写完整结果到 JSON
            final_payload['feishu'] = {
                'report': feishu_report or {'success': False, 'error': '未执行或未获得上传结果'},
                'export': feishu_export or {'success': False, 'error': '未执行或未获得上传结果'}
            }
            final_payload['formal_local'] = {'report': formal_report, 'export': formal_export}
            final_payload['pdf_preview'] = pdf_preview_path
            with open(json_target, 'w', encoding='utf-8') as f:
                json.dump(final_payload, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[async_post_export] 后台任务异常: {e}")

    # 启动后台线程
    threading.Thread(target=_async_post_export, daemon=True).start()

    # 主流程立即返回（不等飞书/PDF）
    final_payload['feishu'] = {'report': {'success': False, 'error': '异步上传中'}, 'export': {'success': False, 'error': '异步上传中'}}
    final_payload['formal_local'] = {'report': '', 'export': ''}
    final_payload['pdf_preview'] = ''
    with open(json_target, 'w', encoding='utf-8') as f:
        json.dump(final_payload, f, ensure_ascii=False, indent=2)
    draft_deleted = _delete_draft_file_if_exists(source_draft_id)

    # 自动同步项目信息到后台项目管理
    _auto_sync_project_and_task(export_payload, export_id)

    # 自动流转：导出报告成功 → 检测完成 + 已出具
    _try_advance_on_export(export_payload)

    return jsonify({
        'success': True,
        'report_success': True,
        'raw_record_success': True,
        'overall_status': 'success',
        'report_status': 'success',
        'raw_record_status': 'success',
        'export_id': export_id,
        'saved_at': final_payload['saved_at'],
        'json_path': str(json_target),
        'xlsx_path': str(xlsx_target),
        'docx_path': str(docx_target),
        'bound_docx_path': str(bound_docx_target),
        'filled_docx_path': filled_docx_path,
        'template_ready': template_ready,
        'template_key': template_resource.get('template_key', ''),
        'template_name': template_resource.get('template_name', ''),
        'template_found': template_resource.get('template_found', False),
        'template_path': template_resource.get('template_path', ''),
        'export_stage': 'template-bound-ready' if template_ready else 'template-resource-missing',
        'export_payload': export_payload,
        'feishu': final_payload.get('feishu', {}),
        'formal_local': final_payload.get('formal_local', {}),
        'dual_chain': {
            'report': {'success': True, 'status': 'success', 'path': filled_docx_path or str(bound_docx_target)},
            'raw_record': {'success': True, 'status': 'success', 'path': str(xlsx_target)}
        },
        'source_draft_deleted': draft_deleted
    })


@export_bp.route('/api/x/list_exports')
@login_required
@require_permission('admin.records.view')
def api_x_list_exports():
    exports = []
    for fp in sorted(REPORTS_DIR.glob('*'), key=lambda p: p.stat().st_mtime, reverse=True):
        exports.append({
            'name': fp.name,
            'path': str(fp),
            'suffix': fp.suffix,
        })
    return jsonify({'success': True, 'exports': exports})
