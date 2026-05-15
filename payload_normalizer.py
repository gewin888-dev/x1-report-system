from typing import Any, Dict, Optional
from datetime import datetime
import uuid

ALLOWED_DOMAINS = {'hospital', 'biosafety', 'food', 'pharma', 'electronics'}
ALLOWED_LEVEL_VALUES = {
    'gmp_workshop': {'A级', 'B级', 'C级', 'D级'},
    'veterinary_gmp_workshop': {'A级', 'B级', 'C级', 'D级'},
    'food_workshop': {'Ⅰ级', 'Ⅱ级', 'Ⅲ级', 'Ⅳ级', 'Ⅰ级（百级）', 'Ⅱ级（万级）', 'Ⅲ级（十万级）', 'Ⅳ级（三十万级）'},
    'electronics_workshop': {'ISO-5', 'ISO-6', 'ISO-7', 'ISO-8', 'ISO-9', 'ISO 5', 'ISO 6', 'ISO 7', 'ISO 8', 'ISO 9', 'ISO5', 'ISO6', 'ISO7', 'ISO8', 'ISO9'},
    'operating_room': {'Ⅰ级', 'Ⅱ级', 'Ⅲ级', 'Ⅳ级', '百级', '千级', '万级', '十万级', '三十万级', '辅房',
                       'Ⅰ级（百级）', 'Ⅱ级（千级）', 'Ⅲ级（万级）', 'Ⅳ级（十万级）'},
    'clean_function_room': {'Ⅰ级', 'Ⅱ级', 'Ⅲ级', 'Ⅳ级', 'Ⅰ级（百级）', 'Ⅱ级（千级）', 'Ⅲ级（万级）', 'Ⅳ级（十万级）', '十万级'},
    'animal_room': {'普通环境', '屏障环境', '隔离环境'},
    'bsl': {'BSL-2（P2）', 'BSL-3（P3）', 'P2', 'P3'},
}
ALLOWED_TYPE_IDS = {
    'operating_room',
    'clean_function_room',
    'negative_pressure',
    'bsl',
    'animal_room',
    'bsc',
    'clean_bench',
    'ivc',
    'food_workshop',
    'laminar_hood',
    'pass_box',
    'gmp_workshop',
    'veterinary_gmp_workshop',
    'electronics_workshop',
}
LEVEL_REQUIRED_TYPE_IDS = {
    'operating_room',
    'clean_function_room',
    'animal_room',
    'bsl',
    'food_workshop',
    'gmp_workshop',
    'veterinary_gmp_workshop',
    'electronics_workshop',
}


def _safe_float(value):
    if value is None or value == '':
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def normalize_weather(raw_payload: Dict[str, Any]) -> Dict[str, Optional[float]]:
    weather_obj = raw_payload.get('weather') if isinstance(raw_payload.get('weather'), dict) else {}
    return {
        'temperature': _safe_float(weather_obj.get('temperature', raw_payload.get('temperature'))),
        'humidity': _safe_float(weather_obj.get('humidity', raw_payload.get('humidity'))),
        'pressure': _safe_float(weather_obj.get('pressure', raw_payload.get('pressure'))),
    }


def normalize_legacy_subtype(type_id: str, subtype: Any, raw_room: Dict[str, Any], domain: str) -> Dict[str, Any]:
    context = dict(raw_room.get('context') or {})
    if not subtype:
        if type_id == 'food_workshop' and raw_room.get('food_grade') and not context.get('food_grade'):
            context['food_grade'] = raw_room.get('food_grade')
        if type_id in ('gmp_workshop', 'veterinary_gmp_workshop') and raw_room.get('gmp_grade') and not context.get('gmp_grade'):
            context['gmp_grade'] = raw_room.get('gmp_grade')
        if type_id == 'electronics_workshop' and raw_room.get('clean_class') and not context.get('iso_level'):
            context['iso_level'] = raw_room.get('clean_class')
        if type_id == 'animal_room':
            if raw_room.get('barrier_room_class') and not context.get('barrier_room_class'):
                context['barrier_room_class'] = raw_room.get('barrier_room_class')
            if raw_room.get('barrier_aux_room') and not context.get('barrier_aux_room'):
                context['barrier_aux_room'] = raw_room.get('barrier_aux_room')
            if raw_room.get('level_name') and raw_room.get('level_name') in ('普通环境', '屏障环境', '隔离环境') and not context.get('animal_environment'):
                context['animal_environment'] = raw_room.get('level_name')
        if type_id == 'operating_room':
            if raw_room.get('surgery_room_type') and not context.get('surgery_room_type'):
                context['surgery_room_type'] = raw_room.get('surgery_room_type')
            if raw_room.get('surgery_aux_room') and not context.get('surgery_aux_room'):
                context['surgery_aux_room'] = raw_room.get('surgery_aux_room')
            if raw_room.get('surgery_aux_clean_class') and not context.get('surgery_aux_clean_class'):
                context['surgery_aux_clean_class'] = raw_room.get('surgery_aux_clean_class')
        if type_id == 'clean_function_room' and raw_room.get('clean_function_subroom') and not context.get('clean_function_subroom'):
            context['clean_function_subroom'] = raw_room.get('clean_function_subroom')
        if type_id == 'bsl' and raw_room.get('bsl') and not context.get('bsl_level'):
            context['bsl_level'] = raw_room.get('bsl')
        return context

    subtype = str(subtype)
    if type_id == 'operating_room':
        if subtype in ('洁净辅房', '辅房'):
            context.setdefault('surgery_room_type', '辅房')
        elif subtype in ('手术室', '眼科手术室'):
            context.setdefault('surgery_room_type', subtype)
        else:
            context.setdefault('surgery_room_type', '辅房')
            context.setdefault('surgery_aux_room', subtype)
    elif type_id == 'clean_function_room':
        context.setdefault('clean_function_subroom', subtype)
    elif type_id == 'bsl':
        if subtype in ('BSL-2', 'P2', 'BSL-2（P2）', 'BSL-2实验室'):
            context.setdefault('bsl_level', 'BSL-2（P2）')
        elif subtype in ('BSL-3', 'P3', 'BSL-3（P3）'):
            context.setdefault('bsl_level', 'BSL-3（P3）')
    elif type_id == 'animal_room':
        if subtype == '普通环境':
            context.setdefault('animal_environment', '普通环境')
        elif subtype == '隔离环境':
            context.setdefault('animal_environment', '隔离环境')
        elif subtype == '屏障环境-主房间':
            context.setdefault('animal_environment', '屏障环境')
            context.setdefault('barrier_room_class', '主房间')
        elif subtype.startswith('屏障环境-'):
            context.setdefault('animal_environment', '屏障环境')
            context.setdefault('barrier_room_class', '洁净辅房')
            context.setdefault('barrier_aux_room', subtype.replace('屏障环境-', ''))
    elif type_id in ('gmp_workshop', 'veterinary_gmp_workshop'):
        context.setdefault('gmp_grade', subtype)
    elif type_id == 'food_workshop':
        context.setdefault('food_grade', subtype)
    elif type_id == 'electronics_workshop':
        context.setdefault('iso_level', subtype)
    return context


def normalize_room_payload(raw_room: Dict[str, Any], domain: str, index: int = 0) -> Dict[str, Any]:
    raw_room = dict(raw_room or {})
    type_id = raw_room.get('type_id') or raw_room.get('type') or ''
    room_name = raw_room.get('room_name') or raw_room.get('name') or ''
    subtype = raw_room.get('subtype')
    context = normalize_legacy_subtype(type_id, subtype, raw_room, domain)

    level_name = raw_room.get('level_name') or raw_room.get('clean_class') or ''
    clean_class = (
        raw_room.get('clean_class')
        or raw_room.get('level_name')
        or context.get('iso_level')
        or context.get('gmp_grade')
        or context.get('food_grade')
        or context.get('bsl_level')
        or context.get('animal_environment')
        or ''
    )

    if type_id == 'animal_room' and not level_name:
        level_name = context.get('animal_environment', '')
    if type_id == 'bsl' and not level_name:
        level_name = context.get('bsl_level', '')

    params = raw_room.get('params', [])
    if isinstance(params, dict):
        params = params

    return {
        'room_id': raw_room.get('room_id') or raw_room.get('id') or f'r{index + 1}',
        'id': raw_room.get('id') or raw_room.get('room_id') or f'r{index + 1}',
        'room_name': room_name,
        'name': room_name,
        'type_id': type_id,
        'type_name': raw_room.get('type_name') or subtype or '',
        'level_name': level_name,
        'clean_class': clean_class,
        'length': raw_room.get('length', ''),
        'width': raw_room.get('width', ''),
        'height': raw_room.get('height', ''),
        'basis': raw_room.get('basis', []),
        'basis_dataset': raw_room.get('basis_dataset', raw_room.get('basis', [])),
        'judgement': raw_room.get('judgement', []),
        'judgement_checked': raw_room.get('judgement_checked', raw_room.get('judgement', [])),
        'judgement_active': raw_room.get('judgement_active', raw_room.get('judgement', [])),
        'judgement_priority': raw_room.get('judgement_priority', raw_room.get('judgement', [])),
        'params': params,
        'summary': raw_room.get('summary', {}),
        'pass_box_result_state': raw_room.get('pass_box_result_state', ''),
        'hepa_leak_summary': raw_room.get('hepa_leak_summary', ''),
        'electronics_manual_range_keys': raw_room.get('electronics_manual_range_keys', []),
        'animal_environment': raw_room.get('animal_environment') or context.get('animal_environment', ''),
        'bsl': raw_room.get('bsl') or context.get('bsl_level', ''),
        'bsl_level': raw_room.get('bsl_level') or context.get('bsl_level', ''),
        'barrier_room_class': raw_room.get('barrier_room_class') or context.get('barrier_room_class', ''),
        'barrier_aux_room': raw_room.get('barrier_aux_room') or context.get('barrier_aux_room', ''),
        'surgery_room_type': raw_room.get('surgery_room_type') or context.get('surgery_room_type', ''),
        'surgery_aux_room': raw_room.get('surgery_aux_room') or context.get('surgery_aux_room', ''),
        'surgery_aux_clean_class': raw_room.get('surgery_aux_clean_class') or context.get('surgery_aux_clean_class', ''),
        'clean_function_subroom': raw_room.get('clean_function_subroom') or context.get('clean_function_subroom', ''),
        'context': context,
    }


def normalize_project_payload(raw_payload: Dict[str, Any], source: str = 'web') -> Dict[str, Any]:
    raw_payload = dict(raw_payload or {})
    rooms = raw_payload.get('rooms') or []
    normalized_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    normalized = {
        'schema_version': '1.1',
        'record_version': raw_payload.get('record_version') or '1',
        'trace_id': raw_payload.get('trace_id') or f"trace_{uuid.uuid4().hex[:12]}",
        'normalized_at': raw_payload.get('normalized_at') or normalized_at,
        'project_name': raw_payload.get('project_name', ''),
        'report_number': raw_payload.get('report_number', ''),
        'client_name': raw_payload.get('client_name') or raw_payload.get('client', ''),
        'contact_info': raw_payload.get('contact_info') or raw_payload.get('contact', ''),
        'project_address': raw_payload.get('project_address') or raw_payload.get('address', ''),
        'inspection_area': raw_payload.get('inspection_area') or raw_payload.get('area', ''),
        'detection_date': raw_payload.get('detection_date') or raw_payload.get('date', ''),
        'detection_state': raw_payload.get('detection_state') or raw_payload.get('state', ''),
        'domain': raw_payload.get('domain', ''),
        'domain_name': raw_payload.get('domain_name', ''),
        'weather': normalize_weather(raw_payload),
        'rooms': [],
        'inspector': raw_payload.get('inspector') or raw_payload.get('operator', ''),
        'source': source,
    }
    for idx, raw_room in enumerate(rooms):
        normalized['rooms'].append(normalize_room_payload(raw_room, normalized['domain'], idx))
    return normalized


def validate_normalized_project(project: Dict[str, Any]) -> Optional[str]:
    def _normalize_level_for_validation(type_id: str, room: Dict[str, Any]) -> str:
        context = room.get('context') or {}
        if type_id in ('gmp_workshop', 'veterinary_gmp_workshop'):
            return str(context.get('gmp_grade') or room.get('level_name') or room.get('clean_class') or '')
        if type_id == 'food_workshop':
            raw = str(context.get('food_grade') or room.get('level_name') or room.get('clean_class') or '')
            return raw  # 已在 ALLOWED_LEVEL_VALUES 中包含带括号格式
        if type_id == 'electronics_workshop':
            raw = str(context.get('iso_level') or room.get('level_name') or room.get('clean_class') or '')
            return raw.strip()  # 已在 ALLOWED_LEVEL_VALUES 中包含 ISO5/ISO 5/ISO-5 多种格式
        if type_id == 'animal_room':
            return str(context.get('animal_environment') or room.get('level_name') or room.get('clean_class') or '')
        if type_id == 'bsl':
            return str(context.get('bsl_level') or room.get('level_name') or room.get('clean_class') or '')
        raw = str(room.get('level_name') or room.get('clean_class') or '')
        # 处理前端 "Ⅰ级（百级）" / "Ⅰ级 (百级)" 等组合格式：提取括号前的核心等级
        import re
        m = re.match(r'^([^（(]+)[（(]', raw)
        if m:
            raw = m.group(1).strip()
        return raw

    if not project.get('project_name'):
        return 'project_name 不能为空'
    if not project.get('report_number'):
        return 'report_number 不能为空'
    if not project.get('client_name'):
        return 'client_name 不能为空'
    if not project.get('detection_date'):
        return 'detection_date 不能为空'
    if project.get('domain') not in ALLOWED_DOMAINS:
        return 'domain 不合法'

    rooms = project.get('rooms') or []
    if not rooms:
        return 'rooms 不能为空'

    room = rooms[0]
    if not room.get('room_id'):
        return 'room_id 不能为空'
    if not room.get('type_id'):
        return 'type_id 不能为空'
    if room.get('type_id') not in ALLOWED_TYPE_IDS:
        return f"未知 type_id: {room.get('type_id')}"
    if not room.get('room_name'):
        return 'room_name 不能为空'
    if room.get('type_id') in LEVEL_REQUIRED_TYPE_IDS and not (room.get('level_name') or room.get('clean_class')):
        return f"{room.get('type_id')} 缺少 level_name/clean_class"
    normalized_level = _normalize_level_for_validation(room.get('type_id'), room)
    allowed_levels = ALLOWED_LEVEL_VALUES.get(room.get('type_id'))
    if allowed_levels and normalized_level and normalized_level not in allowed_levels:
        return f"{room.get('type_id')} 的等级/子类型口径不合法: {normalized_level}；允许值: {', '.join(sorted(allowed_levels))}"
    return None
