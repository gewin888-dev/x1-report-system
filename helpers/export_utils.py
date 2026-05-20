"""
导出相关辅助函数 - 从 app_x1.py 提取。

提供：
- _x_export_path()
- _x_select_template()
- _build_single_room_export()
- _build_export_payload()
- _try_advance_on_export()
"""

from pathlib import Path
from datetime import datetime

from config_loader import load_x1_config
from template_rules import resolve_template_rule
from template_resources import (
    resolve_template_resource,
    apply_type_default_template,
    apply_semantic_default_template,
)
from report_context_builder import build_report_context
from clean_class_semantics import build_clean_class_semantics, _normalize_operating_room_context
from judgement_engine import judge_room
from payload_normalizer import normalize_project_payload
from helpers.db import get_x1_data_conn
from helpers.project_utils import _auto_advance_project_stage

# ---------------------------------------------------------------------------
# 模块级配置（与 app_x1.py 保持一致）
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent
CFG = load_x1_config(BASE_DIR)
APP_VERSION = CFG.get('version', 'UNKNOWN_VERSION')

# 模板基础路径
_template_base_config = CFG.get('template_base', '~/公司资料/检测部/检测报告模板')
if _template_base_config.startswith('~'):
    TEMPLATE_BASE = Path.home() / _template_base_config[2:]
else:
    TEMPLATE_BASE = Path(_template_base_config)
TEMPLATE_BASE = TEMPLATE_BASE.expanduser().resolve()

TEMPLATE_MAP_X1 = [
    ('hospital', 'operating_room', 'Ⅰ级', '医院洁净部/洁净手术部-百级手术室检测报告模板.docx'),
    ('hospital', 'operating_room', 'Ⅱ级', '医院洁净部/洁净手术部-千级手术室检测报告模板.docx'),
    ('hospital', 'operating_room', 'Ⅲ级', '医院洁净部/洁净手术部-万级手术室检测报告模板.docx'),
    ('hospital', 'operating_room', 'Ⅳ级', '医院洁净部/洁净手术部-十万级手术室检测报告模板.docx'),
]

PATHS = CFG.get('paths', {})
REPORTS_DIR = BASE_DIR / PATHS.get('reports', 'reports_x1')


# ---------------------------------------------------------------------------
# 辅助
# ---------------------------------------------------------------------------
def _x_now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')


# ---------------------------------------------------------------------------
# 导出函数
# ---------------------------------------------------------------------------

def _x_export_path(export_id: str) -> Path:
    return REPORTS_DIR / f"{export_id}.json"


def _x_select_template(domain: str, level_name: str = '', type_id: str = ''):
    if type_id:
        for d, t, kw, tpl in TEMPLATE_MAP_X1:
            if d == domain and t == type_id and kw and kw in level_name:
                path = TEMPLATE_BASE / tpl
                if path.exists():
                    return path
        for d, t, kw, tpl in TEMPLATE_MAP_X1:
            if d == domain and t == type_id and not kw:
                path = TEMPLATE_BASE / tpl
                if path.exists():
                    return path
    return None


def _build_single_room_export(project: dict, room: dict, room_index: int = 0) -> dict:
    """对单个房间做判定 + 模板匹配，返回该房间的导出数据。"""
    room_context = room.get('context', {}) or {}
    room_summary = dict(room.get('summary', {}) or {})

    # 确保 params 中每个项有 value 字段（判定引擎需要）
    _params = room.get('params', []) or []
    if isinstance(_params, list):
        for _p in _params:
            if isinstance(_p, dict) and 'value' not in _p:
                _data = _p.get('data', {}) or {}
                if isinstance(_data, dict) and _data.get('total') is not None:
                    _p['value'] = _data['total']
                elif _p.get('result'):
                    _p['value'] = _p['result']

    room_judgement = judge_room(project, room)
    if room_judgement:
        room_summary['input_result_state'] = room_summary.get('result_state', '')
        room_summary['result_state'] = room_judgement.get('result_state', room_summary.get('result_state', ''))
        room_summary['judgement_engine'] = room_judgement.get('engine', '')
        room_summary['judgement_reason'] = room_judgement.get('reason', '')
        room_summary['judgement_overridden'] = room_summary.get('input_result_state', '') != room_summary.get('result_state', '')
    else:
        room_summary['input_result_state'] = room_summary.get('result_state', '')
        room_summary['judgement_engine'] = room_summary.get('judgement_engine', '') or 'unmatched_or_insufficient_params'
        room_summary['judgement_reason'] = room_summary.get('judgement_reason', '') or '判定引擎未命中：对象缺少可判定参数、等级/上下文字段不足，或当前样本仅满足导出不满足自动判定。'
        room_summary['judgement_overridden'] = False
    room = dict(room)
    room['summary'] = room_summary

    # 构建以该房间为 rooms[0] 的虚拟 project，供 resolve_template_rule 使用
    room_project = dict(project)
    room_project['rooms'] = [room]
    clean_class_semantics = build_clean_class_semantics(room_project)
    template_rule = resolve_template_rule(room_project)
    template_rule = apply_semantic_default_template(room_project, template_rule)
    template_rule = apply_type_default_template(template_rule)
    template_resource = resolve_template_resource(template_rule)
    report_context = build_report_context(room_project, template_rule)

    room_type = room.get('type_id', '')
    export_room = {
        'room_id': room.get('room_id', ''),
        'room_name': room.get('room_name', ''),
        'type_id': room.get('type_id', ''),
        'type_name': room.get('type_name', ''),
        'level_name': room.get('level_name', ''),
        'clean_class': room.get('clean_class', ''),
        'basis': room.get('basis', []),
        'judgement': room.get('judgement', []),
        'summary': room_summary,
        'params': room.get('params', []),
        'context': room_context,
        'length': room.get('length', ''),
        'width': room.get('width', ''),
        'height': room.get('height', ''),
    }
    if room_type == 'operating_room':
        normalized_or = _normalize_operating_room_context(room)
        room_context['surgery_room_type'] = room_context.get('surgery_room_type') or normalized_or.get('surgery_room_type', '')
        room_context['surgery_aux_clean_class'] = room_context.get('surgery_aux_clean_class') or normalized_or.get('surgery_aux_clean_class', '')
        aux_clean_class = room_context.get('surgery_aux_clean_class', '')
        branch = room_context.get('surgery_room_type', '')
        export_room['business_context'] = {
            'room_branch': branch,
            'aux_room_name': room_context.get('surgery_aux_room', ''),
            'aux_clean_class': aux_clean_class,
            'context_mode': 'operating-room-minimal',
        }
        if branch:
            export_room['business_context']['branch_mode'] = (
                'auxiliary-room'
                if branch in ('洁净辅房', '辅房')
                else 'main-operating-room'
            )
        if aux_clean_class:
            export_room['business_context']['aux_clean_rule'] = {
                'source': 't-business-logic-extracted',
                'clean_override_key': aux_clean_class,
            }
        if branch in ('洁净辅房', '辅房'):
            export_room['business_context']['parameter_strategy'] = 'aux-clean-override'
        else:
            export_room['business_context']['parameter_strategy'] = 'main-clean-class'
    return {
        'room': export_room,
        'clean_class_semantics': clean_class_semantics,
        'template_rule': template_rule,
        'template_resource': template_resource,
        'report_context': report_context,
        'judgement_result': room_judgement,
        'room_index': room_index,
    }


def _build_export_payload(project: dict) -> dict:
    project = normalize_project_payload(project, source=project.get('source', 'runtime'))
    rooms = project.get('rooms') or []
    if not rooms:
        rooms = [{}]

    # 对每个房间独立做判定 + 模板匹配
    rooms_export = []
    for i, room in enumerate(rooms):
        rooms_export.append(_build_single_room_export(project, room, room_index=i))

    # 主房间（第一个）的数据作为顶层兼容字段
    primary = rooms_export[0]
    room = primary['room']
    room_type = room.get('type_id', '')
    clean_class_semantics = primary['clean_class_semantics']
    template_rule = primary['template_rule']
    template_resource = primary['template_resource']
    report_context = primary['report_context']
    return {
        'export_version': APP_VERSION,
        'export_type': room_type,
        'generated_at': _x_now(),
        'project': {
            'project_name': project.get('project_name', ''),
            'report_number': project.get('report_number', ''),
            'client_name': project.get('client_name', ''),
            'contact_info': project.get('contact_info', ''),
            'project_address': project.get('project_address', ''),
            'inspection_area': project.get('inspection_area', ''),
            'detection_date': project.get('detection_date', ''),
            'domain': project.get('domain', ''),
            'domain_name': project.get('domain_name', ''),
            'detection_state': project.get('detection_state', ''),
            'weather': project.get('weather', {}),
            'rooms': project.get('rooms', []),
            'inspector': project.get('inspector', '') or project.get('operator', ''),
        },
        'room': room,
        'rooms_export': rooms_export,
        'clean_class_semantics': clean_class_semantics,
        'template_rule': template_rule,
        'template_resource': template_resource,
        'report_context': report_context,
        'judgement_result': primary['judgement_result'],
        'source': 'x1-canonical-model'
    }


def _try_advance_on_export(export_payload):
    """导出报告成功后，尝试推进已存在项目的状态到 检测完成 + 报告编制中。
    注意：导出后还需人工审核，审核通过后才上传审核稿推进到“待客户确认”。
    同时将该项目的活跃任务收口为 completed，避免项目已检测完成但任务仍显示执行中。
    """
    try:
        project_info = export_payload.get('project', {}) or {}
        project_name = (project_info.get('project_name') or '').strip()
        client_name = (project_info.get('client_name') or '').strip()
        if not project_name:
            return
        conn = get_x1_data_conn()
        try:
            row = conn.execute(
                "SELECT id FROM business_projects WHERE project_name=? AND client_name=?",
                (project_name, client_name)
            ).fetchone()
            if not row:
                return
            project_id = row['id']
        finally:
            conn.close()
        _auto_advance_project_stage(
            project_id,
            target_inspection='检测完成',
            target_report='报告编制中'
        )
        conn = get_x1_data_conn()
        try:
            now = datetime.now().isoformat(timespec='seconds')
            conn.execute(
                """
                UPDATE project_tasks
                SET task_status='completed',
                    completed_at=COALESCE(NULLIF(completed_at, ''), ?),
                    updated_at=?
                WHERE project_id=?
                  AND task_status IN ('pending_assign', 'assigned', 'accepted', 'in_progress')
                """,
                (now, now, project_id)
            )
            conn.commit()
        finally:
            conn.close()
    except Exception:
        pass
