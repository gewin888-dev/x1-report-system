from typing import Any, Dict, List


_STANDARD_FULL_NAMES = {
    'GB 50333-2013': 'GB 50333-2013 医院洁净手术部建筑技术规范',
    'GB 50591-2010': 'GB 50591-2010 洁净室施工及验收规范',
}


def _expand_standard_lines(values: List[str]) -> List[str]:
    lines: List[str] = []
    seen = set()
    for v in values or []:
        raw = str(v).strip()
        if not raw:
            continue
        full = _STANDARD_FULL_NAMES.get(raw, raw)
        if full not in seen:
            lines.append(full)
            seen.add(full)
    return lines


def _join_lines(values: List[str]) -> str:
    return '\n'.join([str(v).strip() for v in values if str(v).strip()])


def _build_project_overview_text(project: Dict[str, Any]) -> str:
    project_name = project.get('project_name', '')
    project_address = project.get('project_address', '')
    inspection_area = project.get('inspection_area', '')
    return f"本次委托检测项目为{project_name}，项目地点位于{project_address}，本次检测区域为{inspection_area}。"


def _build_detection_state_flags(project: Dict[str, Any]) -> Dict[str, bool]:
    state = project.get('detection_state', '')
    return {
        'empty': state == '空态',
        'static': state == '静态',
        'dynamic': state == '动态',
    }


def _build_weather_text(project: Dict[str, Any]) -> str:
    weather = project.get('weather') or {}
    return f"温度：{weather.get('temperature', '')}℃  湿度：{weather.get('humidity', '')}%RH  大气压力：{weather.get('pressure', '')}hPa"


def _build_conclusion_text(room: Dict[str, Any]) -> str:
    result_state = ((room.get('summary') or {}).get('result_state') or '').strip()
    if result_state in {'合格', '全部符合要求', '符合要求'}:
        return '本次检测的所测参数，均符合判定依据中的相应规定。'
    if result_state in {'不合格', '不符合要求'}:
        return '本次检测的部分参数不符合判定依据中的相应规定。'
    return '本次检测结果详见报告正文及对应检测项目判定结果。'


def build_report_context(project: Dict[str, Any], rule: Dict[str, Any]) -> Dict[str, Any]:
    rooms = project.get('rooms') or []
    room = rooms[0] if rooms else {}
    context = room.get('context') or {}
    semantics = rule.get('clean_class_semantics') or {}
    type_id = room.get('type_id', '')

    business_context = {
        'surgery_room_type': context.get('surgery_room_type', ''),
        'surgery_aux_room': context.get('surgery_aux_room', ''),
        'surgery_aux_clean_class': context.get('surgery_aux_clean_class', ''),
    }

    if type_id == 'clean_function_room':
        business_context.update({
            'clean_function_subroom': context.get('clean_function_subroom', ''),
            'clean_function_context_mode': 'subroom-driven',
        })
    elif type_id == 'bsl':
        business_context.update({
            'bsl_level': context.get('bsl_level') or context.get('bsl') or '',
            'biosafety_context_mode': 'bsl-plus-clean-class',
        })
    elif type_id == 'gmp_workshop':
        business_context.update({
            'gmp_grade': context.get('gmp_grade', ''),
            'gmp_context_mode': context.get('gmp_context_mode', 'grade-driven'),
        })
    elif type_id == 'veterinary_gmp_workshop':
        business_context.update({
            'gmp_grade': context.get('gmp_grade', ''),
            'gmp_context_mode': context.get('gmp_context_mode', 'grade-driven'),
            'pharma_context_variant': context.get('pharma_context_variant', 'veterinary-gmp'),
        })
    elif type_id == 'food_workshop':
        business_context.update({
            'food_grade': context.get('food_grade', ''),
            'food_context_mode': context.get('food_context_mode', 'grade-driven'),
        })
    elif type_id == 'negative_pressure':
        business_context.update({
            'negative_pressure_mode': context.get('negative_pressure_mode', 'ward-pressure-driven'),
            'airflow_direction_expected': context.get('airflow_direction_expected', '由清洁区→半污染区→污染区'),
            'pressure_context_mode': 'negative-pressure-control',
        })
    elif type_id == 'animal_room':
        business_context.update({
            'animal_environment': context.get('animal_environment', ''),
            'barrier_room_class': context.get('barrier_room_class', ''),
            'barrier_aux_room': context.get('barrier_aux_room', ''),
            'animal_context_mode': context.get('animal_context_mode', 'environment-driven'),
        })
    elif type_id == 'electronics_workshop':
        business_context.update({
            'iso_level': context.get('iso_level', ''),
            'electronics_context_mode': context.get('electronics_context_mode', 'iso-driven'),
        })

    return {
        'project_context': {
            'project_name': project.get('project_name', ''),
            'report_number': project.get('report_number', ''),
            'client_name': project.get('client_name', ''),
            'contact_info': project.get('contact_info', ''),
            'project_address': project.get('project_address', ''),
            'inspection_area': project.get('inspection_area', ''),
            'detection_date': project.get('detection_date', ''),
            'domain': project.get('domain', ''),
            'domain_name': project.get('domain_name', ''),
            'project_overview_text': _build_project_overview_text(project),
            'detection_state_flags': _build_detection_state_flags(project),
            'weather_text': _build_weather_text(project),
        },
        'room_context': {
            'room_id': room.get('room_id', ''),
            'room_name': room.get('room_name', ''),
            'type_id': room.get('type_id', ''),
            'type_name': room.get('type_name', ''),
            'clean_class': room.get('clean_class', ''),
            'level_name': room.get('level_name', ''),
            'basis': room.get('basis', []),
            'judgement': room.get('judgement', []),
            'basis_text': _join_lines(_expand_standard_lines(room.get('basis', []))),
            'judgement_text': _join_lines(_expand_standard_lines(room.get('judgement', []))),
            'summary': room.get('summary', {}),
            'conclusion_text': _build_conclusion_text(room),
            'business_context': business_context,
        },
        'template_context': rule,
        'clean_class_semantics': semantics,
        'report_sections': {
            'cover': True,
            'object_summary': True,
            'business_context': True,
            'result_summary': True,
        }
    }
