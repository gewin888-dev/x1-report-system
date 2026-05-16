# -*- coding: utf-8 -*-
"""
Template-related utility functions extracted from app_x1.py.

Provides helpers for template scene state computation, validation,
inspection, and home/group statistics.
"""

import re
from pathlib import Path


def _verify_stage(value: str) -> int:
    v = str(value or '').strip().lower()
    if v in ('smoke_success',):
        return 3
    if v in ('success', 'passed', 'ok'):
        return 2
    if v in ('', 'unverified'):
        return 1
    return 0


def _flow_rank_from_scene_code(code: str) -> int:
    v = str(code or '').strip().lower()
    if v == 'registered':
        return 1
    if v == 'verified_basic':
        return 2
    if v == 'verified_export':
        return 3
    if v == 'enabled':
        return 4
    return 0


def _is_scene_error_code(code: str) -> bool:
    v = str(code or '').strip().lower()
    return v in (
        'pending_config',
        'missing_binding',
        'disabled',
        'missing_file',
        'file_invalid',
        'verify_failed',
        'unknown',
    )


def _compute_home_flow_state(scene_states) -> dict:
    rows = [s for s in (scene_states or []) if isinstance(s, dict)]
    if not rows:
        return {
            'code': 'error',
            'text': '异常',
            'level': 'danger',
            'reason': 'no_scene_state',
        }

    codes = [str((row or {}).get('code', '')).strip() for row in rows]
    if any(_is_scene_error_code(code) for code in codes):
        return {
            'code': 'error',
            'text': '异常',
            'level': 'danger',
            'reason': 'scene_error',
        }

    normalized = []
    for code in codes:
        raw = str(code or '').strip().lower()
        if raw in ('registered', 'verified_basic', 'verified_export', 'enabled'):
            normalized.append(raw)

    if not normalized:
        return {
            'code': 'error',
            'text': '异常',
            'level': 'danger',
            'reason': 'no_flow_state',
        }

    if len(set(normalized)) > 1:
        # 如果所有场景都在 registered / verified_basic / verified_export / enabled 中，
        # 且没有 pending 或 error，则按最低流程位判定状态，而不是笔笼统判 mixed
        flow_order = ['registered', 'verified_basic', 'verified_export', 'enabled']
        lowest = min(normalized, key=lambda c: flow_order.index(c) if c in flow_order else -1)
        if lowest == 'registered':
            return {
                'code': 'registered',
                'text': '已注册',
                'level': 'warning',
                'reason': 'min_flow_registered',
            }
        elif lowest == 'verified_basic':
            return {
                'code': 'verified_basic',
                'text': '基础验证通过',
                'level': 'info',
                'reason': 'min_flow_basic',
            }
        else:
            return {
                'code': 'verified_export',
                'text': '正常',
                'level': 'success',
                'reason': 'min_flow_export',
            }

    code = normalized[0]
    text_map = {
        'registered': '已注册',
        'verified_basic': '基础验证通过',
        'verified_export': '正常',
        'enabled': '正常',
    }
    level_map = {
        'registered': 'warning',
        'verified_basic': 'info',
        'verified_export': 'success',
        'enabled': 'success',
    }
    return {
        'code': code,
        'text': text_map.get(code, '异常'),
        'level': level_map.get(code, 'danger'),
        'reason': 'uniform_flow_stage',
    }


def _resolve_scene_state_for_home(mapping, overlay) -> dict:
    mapping = mapping or {}
    overlay = overlay or {}
    default_key = str(mapping.get('default_template_key', '')).strip()
    default_item = overlay.get(default_key) if default_key else None
    st = _compute_template_scene_state(mapping, default_item)
    if st.get('code') not in ('missing_binding', 'pending_config'):
        return st

    allowed_keys = list(mapping.get('allowed_template_keys', []) or [])
    for key in allowed_keys:
        item = overlay.get(key)
        if not isinstance(item, dict):
            continue
        fallback_mapping = dict(mapping)
        fallback_mapping['default_template_key'] = key
        fallback_state = _compute_template_scene_state(fallback_mapping, item)
        if fallback_state.get('code') in ('registered', 'verified_basic', 'verified_export', 'enabled'):
            return fallback_state
    return st


def _human_verify_result(value: str) -> str:
    v = str(value or '').strip().lower()
    if v in ('', 'unverified'):
        return '未做验证记录'
    if v in ('success', 'passed', 'ok'):
        return '基础验证通过'
    if v in ('smoke_success',):
        return '试导出验证通过'
    if v in ('failed', 'error'):
        return '基础验证失败'
    if v in ('smoke_failed',):
        return '试导出验证失败'
    return value or '未做验证记录'


def _validate_template_key(template_key: str) -> str:
    key = str(template_key or '').strip()
    if not key:
        return 'template key 不能为空'
    if re.search(r'\s', key):
        return 'template key 不能包含空格'
    if re.search(r'[A-Z]', key):
        return 'template key 必须使用小写'
    if re.search(r'[\u4e00-\u9fff]', key):
        return 'template key 不能包含中文'
    if not re.match(r'^[a-z0-9_\/-]+$', key):
        return 'template key 仅允许小写字母、数字、下划线、中划线和斜杠'
    if len(key) > 128:
        return 'template key 过长（最多 128 字符）'
    if key.count('/') > 6:
        return 'template key 层级过深（最多 6 层）'
    if '/' not in key:
        return 'template key 必须使用分层结构，不能只写临时短名'
    legacy_names = {'icu', 'hood', 'putong', 'pass-box', 'operating roon'}
    if key in legacy_names:
        return 'template key 含历史别名，请使用系统自动生成的规范 key'
    if 'electronic shop' in key or 'v2verify' in key or '/test/' in key or '/temp/' in key:
        return 'template key 含非规范命名痕迹，请使用系统自动生成的规范 key'
    return ''


def _inspect_template_docx(path_like) -> dict:
    path_obj = Path(str(path_like or '').strip()) if path_like else None
    exists = bool(path_obj and path_obj.exists())
    size = path_obj.stat().st_size if exists else 0
    valid = False
    parse_error = ''
    if exists and size >= 1024:
        try:
            from docx import Document
            Document(str(path_obj))
            valid = True
        except Exception as e:
            parse_error = str(e)
    elif exists and size > 0:
        parse_error = f'模板文件过小（{size} bytes），疑似无效 docx 或测试占位文件'
    elif exists and size == 0:
        parse_error = '模板文件为空（0 bytes）'
    elif not exists:
        parse_error = '模板文件不存在'
    return {
        'path': str(path_obj) if path_obj else '',
        'exists': exists,
        'size': size,
        'valid': valid,
        'parse_error': parse_error,
    }


def _compute_template_scene_state(mapping, item) -> dict:
    mapping = mapping or {}
    item = item or None
    default_key = str(mapping.get('default_template_key', '')).strip()
    if not default_key:
        return {
            'code': 'pending_config',
            'text': '待配置',
            'hint': '请选择一个模板作为当前模板',
            'level': 'warning',
        }
    if not item:
        return {
            'code': 'missing_binding',
            'text': '模板缺失',
            'hint': '默认模板未在候选项中命中，请切换模板或重新挂接',
            'level': 'error',
        }
    if item.get('enabled', True) is False:
        return {
            'code': 'disabled',
            'text': '模板已停用',
            'hint': '请切换模板，或先到下方模板池重新启用',
            'level': 'error',
        }

    template_path = str(item.get('template_path', '')).strip()
    path_obj = Path(template_path) if template_path else None
    exists = bool(path_obj and path_obj.exists())
    size = path_obj.stat().st_size if exists else 0
    verify_raw = str(item.get('last_verify_result', '') or '').strip().lower()

    if not exists:
        return {
            'code': 'missing_file',
            'text': '模板缺失',
            'hint': '当前默认模板文件不存在，请补齐文件或切换模板',
            'level': 'error',
        }
    if size > 0 and size < 1024:
        return {
            'code': 'file_invalid',
            'text': '模板异常',
            'hint': '当前默认模板文件体积异常，疑似不是有效 docx，请重新上传',
            'level': 'error',
        }
    if verify_raw in ('failed', 'error', 'smoke_failed'):
        return {
            'code': 'verify_failed',
            'text': '验证异常',
            'hint': '当前默认模板最近检查失败，请先修复或切换模板',
            'level': 'error',
        }
    if verify_raw in ('', 'unverified'):
        return {
            'code': 'registered',
            'text': '已注册',
            'hint': '当前模板已注册，下一步请先做基础验证',
            'level': 'warning',
        }
    if verify_raw in ('success', 'passed', 'ok'):
        return {
            'code': 'verified_basic',
            'text': '基础验证通过',
            'hint': '当前模板已通过基础验证，下一步请做试导出验证',
            'level': 'info',
        }
    if verify_raw == 'smoke_success':
        return {
            'code': 'verified_export',
            'text': '试导出验证通过',
            'hint': '当前模板已通过试导出验证，下一步可启用为当前模板',
            'level': 'success',
        }
    return {
        'code': 'unknown',
        'text': '状态未归类',
        'hint': f'当前模板存在未归类状态：{verify_raw or "unknown"}',
        'level': 'warning',
    }


def _summarize_template_detail_rows(files, group: str = '') -> dict:
    def _label_stage(label: str) -> int:
        text = str(label or '')
        if '试导出验证通过' in text or '导出验证通过' in text:
            return 3
        if '基础验证通过' in text or '验证通过' in text:
            return 2
        if text and '未做验证' not in text and '未验证' not in text:
            return 1
        return 1 if text else 0
    rows = files if isinstance(files, list) else []
    prefix = f'hospital/operating_room/{group}/' if group else ''
    summary = {
        'total': 0,
        'registered': 0,
        'basic': 0,
        'exportReady': 0,
        'current': 0,
        'enabled': 0,
        'missing': 0,
        'error': 0,
    }
    for row in rows:
        if not isinstance(row, dict):
            continue
        template_key = str(row.get('template_key', '')).strip()
        if not template_key:
            continue
        if prefix and not template_key.startswith(prefix):
            continue
        summary['total'] += 1
        verify_label = str(row.get('last_verify_result', '') or '')
        stage = _label_stage(verify_label)
        if stage >= 1:
            summary['registered'] += 1
        if stage >= 2:
            summary['basic'] += 1
        if stage >= 3:
            summary['exportReady'] += 1
        if row.get('is_default'):
            summary['current'] += 1
        if row.get('enabled', True) is not False:
            summary['enabled'] += 1
        if not row.get('exists'):
            summary['missing'] += 1
        if '失败' in verify_label:
            summary['error'] += 1
    return summary


def _compute_operating_room_group_stats(group: str, overlay: dict) -> dict:
    from template_resources import get_semantic_template_mapping
    group = str(group or '').strip()
    group_prefix = f'hospital/operating_room/{group}/'
    semantic_prefix = f'hospital.operating_room.{group}.'
    semantic_keys = [
        'hospital.operating_room.main.level1',
        'hospital.operating_room.main.level2',
        'hospital.operating_room.main.level3',
        'hospital.operating_room.main.level4',
        'hospital.operating_room.eye.level1',
        'hospital.operating_room.eye.level2',
        'hospital.operating_room.eye.level3',
        'hospital.operating_room.eye.level4',
        'hospital.operating_room.aux.level1',
        'hospital.operating_room.aux.level2',
        'hospital.operating_room.aux.level3',
        'hospital.operating_room.aux.level4',
    ]
    target_keys = [k for k in semantic_keys if k.startswith(semantic_prefix)]
    stats = {
        'total': len(target_keys),
        'registered_keys': 0,
        'enabled_count': 0,
        'missing_count': 0,
        'exists': True,
        'ready': 0,
        'readyBasic': 0,
        'pending': 0,
        'risk': 0,
        'activated': 0,
        'registeredOnly': 0,
        'display_enabled_count': None,
    }
    seen = set()
    for semantic_key in target_keys:
        mapping = get_semantic_template_mapping(semantic_key)
        default_key = str(mapping.get('default_template_key', '')).strip()
        item = overlay.get(default_key) if default_key else None
        st = _compute_template_scene_state(mapping, item)
        code = str(st.get('code', 'unknown'))
        if code == 'verified_export':
            stats['ready'] += 1
        elif code == 'verified_basic':
            stats['readyBasic'] += 1
        elif code == 'registered':
            stats['registeredOnly'] += 1
        elif code == 'pending_config':
            stats['pending'] += 1
        else:
            stats['risk'] += 1
        if item and item.get('enabled', True) is not False:
            stats['activated'] += 1
        allowed_keys = list(mapping.get('allowed_template_keys', []) or [])
        if default_key and default_key not in allowed_keys:
            allowed_keys.append(default_key)
        for tk in allowed_keys:
            tk = str(tk or '').strip()
            if not tk or not tk.startswith(group_prefix) or tk in seen:
                continue
            seen.add(tk)
            stats['registered_keys'] += 1
            reg_item = overlay.get(tk) or {}
            if reg_item.get('enabled', True) is not False:
                stats['enabled_count'] += 1
            tpath = str(reg_item.get('template_path', '')).strip()
            if not tpath or not Path(tpath).exists():
                stats['missing_count'] += 1
    return stats


def _compute_template_home_stats(type_id: str, overlay: dict) -> dict:
    from template_resources import get_type_template_mapping, get_semantic_template_mapping
    semantic_options = [
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.a', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.b', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.c', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.veterinary_gmp_workshop.grade.d', 'type_id': 'veterinary_gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.a', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.b', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.c', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'pharma.gmp_workshop.grade.d', 'type_id': 'gmp_workshop'},
        {'semantic_key': 'food.food_workshop.grade.1', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.2', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.3', 'type_id': 'food_workshop'},
        {'semantic_key': 'food.food_workshop.grade.4', 'type_id': 'food_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.5', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.6', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.7', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.8', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'electronics.electronics_workshop.iso.9', 'type_id': 'electronics_workshop'},
        {'semantic_key': 'hospital.clean_function_room.icu', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.cssd', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.dialysis', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.clean_function_room.general', 'type_id': 'clean_function_room'},
        {'semantic_key': 'hospital.operating_room.main.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.main.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.eye.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level1', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level2', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level3', 'type_id': 'operating_room'},
        {'semantic_key': 'hospital.operating_room.aux.level4', 'type_id': 'operating_room'},
        {'semantic_key': 'biosafety.animal_room.normal', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_main', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.isolation', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_storage', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.after_sterilization', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.clean_corridor', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.dirty_corridor', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.buffer', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_2', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.cleaning_disinfection', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.animal_room.barrier_aux.change_room_1', 'type_id': 'animal_room'},
        {'semantic_key': 'biosafety.bsl.p2', 'type_id': 'bsl'},
        {'semantic_key': 'biosafety.bsl.p3', 'type_id': 'bsl'},
    ]
    mapping = get_type_template_mapping(type_id)
    semantic_rows = [item for item in semantic_options if item.get('type_id') == type_id]
    scene_states = []
    stats = {
        'total': 1,
        'registered_keys': 0,
        'enabled_count': 0,
        'missing_count': 0,
        'ready': 0,
        'readyBasic': 0,
        'pending': 0,
        'risk': 0,
        'registeredOnly': 0,
        'display_enabled_count': 0,
    }
    if semantic_rows:
        stats['total'] = 0
        for opt in semantic_rows:
            semantic_mapping = get_semantic_template_mapping(opt.get('semantic_key', ''))
            st = _resolve_scene_state_for_home(semantic_mapping, overlay)
            scene_states.append(st)
            stats['total'] += 1
            code = str(st.get('code', 'unknown'))
            if code == 'verified_export':
                stats['ready'] += 1
            elif code == 'verified_basic':
                stats['readyBasic'] += 1
            elif code == 'registered':
                stats['registeredOnly'] += 1
            elif code == 'pending_config':
                stats['pending'] += 1
            else:
                stats['risk'] += 1
    else:
        st = _resolve_scene_state_for_home(mapping, overlay)
        scene_states.append(st)
        code = str(st.get('code', 'unknown'))
        if code == 'verified_export':
            stats['ready'] = 1
        elif code == 'verified_basic':
            stats['readyBasic'] = 1
        elif code == 'registered':
            stats['registeredOnly'] = 1
        elif code == 'pending_config':
            stats['pending'] = 1
        else:
            stats['risk'] = 1
    seen = set()
    for template_key, value in overlay.items():
        if not isinstance(value, dict) or value.get('type_id') != type_id:
            continue
        if template_key in seen:
            continue
        seen.add(template_key)
        stats['registered_keys'] += 1
        if value.get('enabled', True) is not False:
            stats['enabled_count'] += 1
        template_path = str(value.get('template_path', '')).strip()
        if not template_path or not Path(template_path).exists():
            stats['missing_count'] += 1
    stats['display_enabled_count'] = stats['enabled_count']
    home_state = _compute_home_flow_state(scene_states)
    return stats, home_state
