from pathlib import Path
from typing import Dict, Any, List, Tuple
import json
import os
import re
from datetime import datetime
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape
from template_standard_profiles import get_template_standard_profile


def _para_xml(text: str) -> str:
    return (
        '<w:p>'
        '<w:pPr><w:jc w:val="center"/><w:textAlignment w:val="bottom"/></w:pPr>'
        '<w:r><w:t xml:space="preserve">'
        f'{escape(text)}'
        '</w:t></w:r>'
        '</w:p>'
    )


def _replace_negative_pressure_result_row(document_xml: str, row_label: str, result_text: str, debug_notes: List[Dict[str, Any]] = None) -> str:
    if result_text is None or str(result_text).strip() == '':
        return document_xml
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t[^>]*>(.*?)</w:t>', re.S)

    def _cell_plain(cell_xml: str) -> str:
        texts = text_pattern.findall(cell_xml)
        return ''.join(
            re.sub(r'<[^>]+>', '', t).replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()
            for t in texts
        ).strip()

    def _normalize_text(text: str) -> str:
        return (
            str(text or '')
            .replace('（', '(')
            .replace('）', ')')
            .replace('·', '')
            .replace(' ', '')
            .replace('\u00a0', '')
            .replace('\u3000', '')
            .strip()
        )

    normalized_label = _normalize_text(row_label)

    def _set_cell_text_keep_tcpr(cell_xml: str, value: str) -> str:
        m = re.match(r'(<w:tc\b[^>]*>)(.*?)(</w:tc>)', cell_xml, re.S)
        if not m:
            return cell_xml
        start_tag, inner, end_tag = m.groups()
        tcpr = re.search(r'(<w:tcPr\b.*?</w:tcPr>)', inner, re.S)
        tcpr_xml = tcpr.group(1) if tcpr else ''
        return start_tag + tcpr_xml + _para_xml(value) + end_tag

    tables = tbl_pattern.findall(document_xml)
    candidate_rows = []
    for ti, table_xml in enumerate(tables):
        rows = row_pattern.findall(table_xml)
        for ri, row_xml in enumerate(rows):
            cells = cell_pattern.findall(row_xml)
            if len(cells) != 5:
                continue
            cell_texts = [_cell_plain(c) for c in cells]
            row_joined = ''.join(cell_texts)
            row_joined_norm = _normalize_text(row_joined)
            if normalized_label not in row_joined_norm:
                continue
            candidate_rows.append({
                'table_index': ti,
                'row_index': ri,
                'cell_texts': cell_texts,
                'row_joined': row_joined,
            })
            before = _cell_plain(cells[3])
            new_cells = list(cells)
            new_cells[3] = _set_cell_text_keep_tcpr(cells[3], str(result_text))
            cell_iter = list(cell_pattern.finditer(row_xml))
            parts = []
            cursor = 0
            for i, cm in enumerate(cell_iter):
                parts.append(row_xml[cursor:cm.start()])
                parts.append(new_cells[i])
                cursor = cm.end()
            parts.append(row_xml[cursor:])
            new_row = ''.join(parts)
            changed = new_row != row_xml
            _append_debug_note(debug_notes, 'negative-pressure-hard-row-apply', {
                'row_label': row_label,
                'normalized_label': normalized_label,
                'table_index': ti,
                'row_index': ri,
                'before_text': before,
                'after_text': _cell_plain(new_cells[3]),
                'changed': changed,
                'matched_cell_texts': cell_texts,
            })
            if not changed:
                return document_xml
            new_table = table_xml.replace(row_xml, new_row, 1)
            return document_xml.replace(table_xml, new_table, 1)
    _append_debug_note(debug_notes, 'negative-pressure-hard-row-miss', {
        'row_label': row_label,
        'normalized_label': normalized_label,
        'result_text': str(result_text),
        'candidate_rows': candidate_rows[:8],
    })
    return document_xml





def _debug_enabled() -> bool:
    return os.environ.get('X1_TEMPLATE_DEBUG', '').strip().lower() in {'1', 'true', 'yes', 'on'}


def _append_debug_note(notes: List[Dict[str, Any]], stage: str, payload: Dict[str, Any]) -> None:
    if notes is None:
        return
    item = {'stage': stage}
    item.update(payload)
    notes.append(item)


def _read_docx_text_snippets(docx_path: str, limit: int = 12) -> List[str]:
    path = Path(docx_path)
    if not path.exists() or path.suffix.lower() != '.docx':
        return []
    snippets: List[str] = []
    try:
        with ZipFile(path, 'r') as zf:
            if 'word/document.xml' not in zf.namelist():
                return []
            xml_text = zf.read('word/document.xml').decode('utf-8', errors='ignore')
        raw_parts = xml_text.split('<w:t')
        for chunk in raw_parts[1:]:
            if '>' not in chunk or '</w:t>' not in chunk:
                continue
            text = chunk.split('>', 1)[1].split('</w:t>', 1)[0]
            text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()
            if text:
                snippets.append(text)
            if len(snippets) >= limit:
                break
    except Exception:
        return []
    return snippets


def _detect_template_placeholders(snippets: List[str]) -> Dict[str, Any]:
    joined = '\n'.join(snippets)
    markers = []
    for token in ['项目名称', '委托单位', '检测报告', '检测日期', '报告编号', '受检区域', '洁净', '实验室']:
        if token in joined:
            markers.append(token)
    return {
        'snippet_count': len(snippets),
        'markers': markers,
        'has_business_markers': bool(markers),
    }


def _build_common_fill_preview(report_context: Dict[str, Any]) -> Dict[str, Any]:
    project_context = report_context.get('project_context', {}) or {}
    room_context = report_context.get('room_context', {}) or {}
    return {
        'report_number': project_context.get('report_number', ''),
        'project_name': project_context.get('project_name', ''),
        'client_name': project_context.get('client_name', ''),
        'project_address': project_context.get('project_address', ''),
        'contact_info': project_context.get('contact_info', ''),
        'inspection_area': project_context.get('inspection_area', ''),
        'detection_date': project_context.get('detection_date', ''),
        'project_overview_text': project_context.get('project_overview_text', ''),
        'weather_text': project_context.get('weather_text', ''),
        'basis_text': room_context.get('basis_text', ''),
        'judgement_text': room_context.get('judgement_text', ''),
        'conclusion_text': room_context.get('conclusion_text', ''),
    }


def _build_object_context_preview(export_payload: Dict[str, Any]) -> Dict[str, Any]:
    room = export_payload.get('room', {}) or {}
    context = room.get('context', {}) or {}
    type_id = room.get('type_id', '')
    template_rule = export_payload.get('template_rule', {}) or {}
    template_key = str(template_rule.get('template_key', '') or '').strip()
    standard_profile = get_template_standard_profile(template_key)
    template_rule = export_payload.get('template_rule', {}) or {}
    template_key = str(template_rule.get('template_key', '') or '').strip()
    standard_profile = get_template_standard_profile(template_key)
    if type_id == 'gmp_workshop':
        return {
            'gmp_grade': context.get('gmp_grade', ''),
            'gmp_context_mode': context.get('gmp_context_mode', ''),
        }
    if type_id == 'clean_function_room':
        return {
            'clean_function_subroom': context.get('clean_function_subroom', ''),
        }
    if type_id == 'laminar_hood':
        param_map = build_param_map(room.get('params'))
        particle_meta = get_param_meta(param_map, 'particle')
        particle_values = get_param_values(param_map, 'particle')
        return {
            'room_name': room.get('room_name', ''),
            'avg_speed': get_param_value(param_map, 'avg_speed'),
            'speed_uniformity': get_param_value(param_map, 'speed_uniformity'),
            'airflow_pattern': get_param_result(param_map, 'airflow_pattern'),
            'hepa_leak_result': get_param_result(param_map, 'hepa_leak'),
            'particle_result': get_param_result(param_map, 'particle'),
            'particle_clean_class': particle_meta.get('clean_class', '') or room.get('clean_class', '') or room.get('level_name', ''),
            'particle_max_05': particle_values.get('max_0_5um', ''),
            'particle_max_5': particle_values.get('max_5um', ''),
            'particle_ucl_05': particle_values.get('ucl_0_5um', ''),
            'particle_ucl_5': particle_values.get('ucl_5um', ''),
        }
    if type_id == 'pass_box':
        param_map = build_param_map(room.get('params'))
        dimensions = get_param_dimensions(param_map, 'box_inner_size')
        return {
            'appearance_result': get_param_result(param_map, 'appearance'),
            'door_interlock_result': get_param_result(param_map, 'door_interlock'),
            'box_inner_length': dimensions.get('length', ''),
            'box_inner_width': dimensions.get('width', ''),
            'box_inner_height': dimensions.get('height', ''),
            'box_inner_volume': get_param_value(param_map, 'box_inner_size'),
            'airchange_b12': get_param_value(param_map, 'airchange_b12'),
            'airchange_b3': get_param_value(param_map, 'airchange_b3'),
            'noise': get_param_value(param_map, 'noise'),
            'hepa_leak_result': get_param_result(param_map, 'hepa_leak'),
            'particle_result': get_param_result(param_map, 'particle'),
            'pass_box_result_state': room.get('pass_box_result_state', '') or ((room.get('summary') or {}).get('result_state', '')),
        }
    if type_id == 'animal_room':
        return {
            'animal_environment': context.get('animal_environment', ''),
            'barrier_room_class': context.get('barrier_room_class', ''),
            'barrier_aux_room': context.get('barrier_aux_room', ''),
            'animal_context_mode': context.get('animal_context_mode', ''),
        }
    if type_id == 'operating_room':
        return {
            'surgery_room_type': context.get('surgery_room_type', ''),
            'surgery_aux_room': context.get('surgery_aux_room', ''),
            'surgery_aux_clean_class': context.get('surgery_aux_clean_class', ''),
            'clean_class': room.get('clean_class', '') or room.get('level_name', ''),
            'room_name': room.get('room_name', ''),
        }
    if type_id == 'negative_pressure':
        return {
            'negative_pressure_mode': context.get('negative_pressure_mode', ''),
            'airflow_direction_expected': context.get('airflow_direction_expected', ''),
        }
    return context


def _normalize_room_params(params: Any) -> Dict[str, Dict[str, Any]]:
    param_map: Dict[str, Dict[str, Any]] = {}

    def _register(alias: Any, item: Any) -> None:
        key = str(alias or '').strip()
        if not key or key in param_map or not isinstance(item, dict):
            return
        param_map[key] = item

    if isinstance(params, dict):
        for raw_key, item in params.items():
            if not isinstance(item, dict):
                continue
            canonical_key = str(raw_key or '').strip()
            _register(canonical_key, item)
            for alias in (item.get('key', ''), item.get('code', ''), item.get('label', ''), item.get('name', '')):
                _register(alias, item)
        return param_map

    if isinstance(params, list):
        for item in params:
            if not isinstance(item, dict):
                continue
            canonical_key = ''
            for candidate in (item.get('key', ''), item.get('code', ''), item.get('label', ''), item.get('name', '')):
                canonical_key = str(candidate or '').strip()
                if canonical_key:
                    break
            _register(canonical_key, item)
            for alias in (item.get('key', ''), item.get('code', ''), item.get('label', ''), item.get('name', '')):
                _register(alias, item)
        return param_map

    return param_map


def build_param_map(params: Any) -> Dict[str, Dict[str, Any]]:
    return _normalize_room_params(params)


def get_param_item(param_map: Dict[str, Dict[str, Any]], *aliases: str) -> Dict[str, Any]:
    for alias in aliases:
        key = str(alias or '').strip()
        if not key:
            continue
        item = param_map.get(key)
        if isinstance(item, dict):
            return item
    return {}


def get_param_values(param_map: Dict[str, Dict[str, Any]], *aliases: str) -> Dict[str, Any]:
    item = get_param_item(param_map, *aliases)
    values = item.get('values') if isinstance(item, dict) else {}
    return values if isinstance(values, dict) else {}


def get_param_meta(param_map: Dict[str, Dict[str, Any]], *aliases: str) -> Dict[str, Any]:
    item = get_param_item(param_map, *aliases)
    meta = item.get('meta') if isinstance(item, dict) else {}
    return meta if isinstance(meta, dict) else {}


def get_param_dimensions(param_map: Dict[str, Dict[str, Any]], *aliases: str) -> Dict[str, Any]:
    item = get_param_item(param_map, *aliases)
    dimensions = item.get('dimensions') if isinstance(item, dict) else {}
    if isinstance(dimensions, dict):
        return dimensions
    values = item.get('values') if isinstance(item, dict) else {}
    if isinstance(values, dict):
        fallback_dimensions = values.get('dimensions')
        if isinstance(fallback_dimensions, dict):
            return fallback_dimensions
    data = item.get('data') if isinstance(item, dict) else {}
    if isinstance(data, dict):
        fallback_dimensions = data.get('dimensions')
        if isinstance(fallback_dimensions, dict):
            return fallback_dimensions
    return {}


def get_param_result(param_map: Dict[str, Dict[str, Any]], *aliases: str) -> str:
    item = get_param_item(param_map, *aliases)
    if not item:
        return ''
    result = str(item.get('result', '') or '').strip()
    if result:
        return result
    value = str(item.get('value', '') or '').strip()
    if value in {'合格', '不合格'}:
        return value
    values = item.get('values') if isinstance(item, dict) else {}
    if isinstance(values, dict):
        for key in ('result', 'judge', 'judgement'):
            candidate = str(values.get(key, '') or '').strip()
            if candidate:
                return candidate
    data = item.get('data') if isinstance(item, dict) else {}
    if isinstance(data, dict):
        for key in ('result', 'judge', 'judgement'):
            candidate = str(data.get(key, '') or '').strip()
            if candidate:
                return candidate
    return ''


def get_param_value(param_map: Dict[str, Dict[str, Any]], *aliases: str) -> str:
    item = get_param_item(param_map, *aliases)
    if not item:
        return ''
    value = str(item.get('value', '') or '').strip()
    if value and value not in {'合格', '不合格'}:
        return _strip_emoji(value)
    values = item.get('values') if isinstance(item, dict) else {}
    if isinstance(values, dict):
        for key in ('value', 'avg', 'average', 'mean', 'text', 'display'):
            candidate = str(values.get(key, '') or '').strip()
            if candidate and candidate not in {'合格', '不合格'}:
                return _strip_emoji(candidate)
    elif isinstance(values, list) and values:
        # 真实 params 中 values 可能是数值列表如 ['0.23', '0.25']，取均值
        nums = []
        for v in values:
            try:
                nums.append(float(str(v).strip()))
            except (ValueError, TypeError):
                pass
        if nums:
            avg = sum(nums) / len(nums)
            # 如果均值是整数则不带小数点
            return str(int(avg)) if avg == int(avg) else str(round(avg, 2))
    data = item.get('data') if isinstance(item, dict) else {}
    if isinstance(data, dict):
        for key in ('value', 'avg', 'average', 'mean', 'text', 'display'):
            candidate = str(data.get(key, '') or '').strip()
            if candidate and candidate not in {'合格', '不合格'}:
                return _strip_emoji(candidate)
    result = str(item.get('result', '') or '').strip()
    if result and result not in {'合格', '不合格'}:
        return _strip_emoji(result)
    return ''


def _strip_emoji(text: str) -> str:
    """剥离值文本中的判定符号（✅❌⚠️✓✗☑☒）和尾部空格。"""
    if not text:
        return text
    import re as _re
    return _re.sub(r'[\s]*[\u2705\u274c\u26a0\ufe0f\u2713\u2717\u2611\u2612]+[\s]*', '', text).strip()



def _build_placeholder_fill_plan(export_payload: Dict[str, Any]) -> List[Tuple[str, str]]:
    report_context = export_payload.get('report_context', {}) or {}
    project_context = report_context.get('project_context', {}) or {}
    room_context = report_context.get('room_context', {}) or {}
    room = export_payload.get('room', {}) or {}
    context = room.get('context', {}) or {}
    type_id = room.get('type_id', '')
    template_rule = export_payload.get('template_rule', {}) or {}
    template_key = str(template_rule.get('template_key', '') or '').strip()
    standard_profile = get_template_standard_profile(template_key)

    _STANDARD_FULL_NAMES = {
        'GB 50333-2013': 'GB 50333-2013 医院洁净手术部建筑技术规范',
        'GB 50591-2010': 'GB 50591-2010 洁净室施工及验收规范',
    }

    def _expand_standard_text(value: str) -> str:
        lines = []
        seen = set()
        for raw in str(value or '').splitlines():
            raw = raw.strip()
            if not raw:
                continue
            full = _STANDARD_FULL_NAMES.get(raw, raw)
            if full not in seen:
                lines.append(full)
                seen.add(full)
        return '\n'.join(lines)

    _basis_text = _expand_standard_text(room_context.get('basis_text', ''))
    _judgement_text = _expand_standard_text(room_context.get('judgement_text', ''))

    detection_state_flags = project_context.get('detection_state_flags', {}) or {}
    if detection_state_flags.get('empty'):
        detection_state_text = '空态'
    elif detection_state_flags.get('static'):
        detection_state_text = '静态'
    elif detection_state_flags.get('dynamic'):
        detection_state_text = '动态'
    else:
        detection_state_text = ''

    plan: List[Tuple[str, str]] = [
        ('报告编号', project_context.get('report_number', '')),
        ('项目名称', project_context.get('project_name', '')),
        ('委托单位', project_context.get('client_name', '')),
        ('项目地址', project_context.get('project_address', '')),
        ('联系方式', project_context.get('contact_info', '')),
        ('检测类别', room_context.get('category_text', '') or room.get('type_name', '') or room.get('type_id', '')),
        ('检测区域', project_context.get('inspection_area', '')),
        ('受检区域', project_context.get('inspection_area', '')),
        ('检测日期', project_context.get('detection_date', '')),
        ('检测状态', detection_state_text),
        ('气象条件', project_context.get('weather_text', '')),
        ('项目概述', project_context.get('project_overview_text', '')),
        ('判定依据', _judgement_text),
            ('判定标准', _judgement_text),
        ('检测依据', _basis_text),
        ('检测结论', room_context.get('conclusion_text', '')),
    ]

    if type_id == 'animal_room':
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))

        def _animal_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        def _animal_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        animal_environment = context.get('animal_environment', '') or room.get('clean_class', '') or room.get('level_name', '')
        barrier_room_class = context.get('barrier_room_class', '')
        barrier_aux_room = context.get('barrier_aux_room', '')
        detection_environment = ' / '.join([v for v in [animal_environment, barrier_room_class, barrier_aux_room] if str(v).strip()])
        clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
        noise = _animal_value('noise', '噪声')
        if noise:
            import re as _re
            noise = _re.sub(r'\s*dB\(A\)\s*', '', noise).strip()

        particle = param_map.get('particle', {}) or {}
        particle_data = particle.get('data', {}) or particle.get('values', {}) or {}
        particle_meta = particle.get('meta', {}) or {}
        particle_clean_class = str(particle_meta.get('clean_class', '') or clean_class_text or '')
        particle_max_05 = str(
            particle_data.get('p05_max', '')
            or particle_data.get('max_0_5um', '')
            or _animal_value('cleanliness_05um', '≥0.5μm', '0.5um', '0.5μm')
            or ''
        )
        particle_max_5 = str(
            particle_data.get('p5_max', '')
            or particle_data.get('max_5um', '')
            or _animal_value('cleanliness_5um', '≥5μm', '5um', '5μm')
            or ''
        )
        particle_ucl_05 = str(
            particle_data.get('p05_ucl', '')
            or particle_data.get('ucl_0_5um', '')
            or _animal_value('0.5μmUCL', '0.5umUCL', 'ucl_0_5um')
            or ''
        )
        particle_ucl_5 = str(
            particle_data.get('p5_ucl', '')
            or particle_data.get('ucl_5um', '')
            or _animal_value('5μmUCL', '5umUCL', 'ucl_5um')
            or ''
        )

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('检测对象', room.get('type_name', '') or '动物房'),
            ('样品名称', room.get('type_name', '') or '动物房'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('动物房环境', animal_environment),
            ('房间类别', barrier_room_class),
            ('洁净辅房名称', barrier_aux_room),
            ('检测环境', detection_environment),
            ('洁净度设计级别', clean_class_text),
            ('洁净度级别', particle_clean_class or clean_class_text),
            ('洁净度', particle_clean_class or clean_class_text),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('换气次数', _animal_value('airchange_rate', 'airchange')),
            ('静压差', _animal_value('static_pressure_diff', 'pressure_diff', 'pressure')),
            ('温度', _animal_value('temperature')),
            ('最大日温差', _animal_value('temp_diff')),
            ('相对湿度', _animal_value('relative_humidity', 'humidity')),
            ('噪声', noise),
            ('平均照度', _animal_value('illumination', 'work_illumination')),
            ('最低照度', _animal_value('work_illumination', 'illumination')),
            ('动物照度', _animal_value('animal_illumination')),
            ('动物笼具处气流速度', _animal_value('cage_airspeed')),
            ('沉降菌', _animal_value('settling_bacteria', 'settle_bacteria', 'settling')),
            ('沉降菌（平均菌落数）', _animal_value('settling_bacteria', 'settle_bacteria', 'settling')),
            ('高效过滤器检漏', _animal_value('hepa_leak')),
            ('送风高效过滤器检漏', _animal_value('hepa_leak')),
        ])
    elif type_id == 'pass_box':
        param_map = build_param_map(room.get('params'))
        dimensions = get_param_dimensions(param_map, 'box_inner_size')
        appearance = get_param_result(param_map, 'appearance')
        door_interlock = get_param_result(param_map, 'door_interlock')
        
        # 优先从 dimensions 读取，fallback 到 room.context
        room_context = room.get('context', {})
        box_inner_length = dimensions.get('length', '') or room_context.get('inner_length', '')
        box_inner_width = dimensions.get('width', '') or room_context.get('inner_width', '')
        box_inner_height = dimensions.get('height', '') or room_context.get('inner_height', '')
        box_inner_volume = get_param_value(param_map, 'box_inner_size')
        if box_inner_length and box_inner_width and box_inner_height:
            product_inner_size_text = f"{box_inner_length}×{box_inner_width}×{box_inner_height} m"
        else:
            product_inner_size_text = ''
        airchange_b12 = get_param_value(param_map, 'airchange_b12')
        airchange_b3 = get_param_value(param_map, 'airchange_b3')
        airchange_combined = airchange_b12 if airchange_b12 else ''
        noise = get_param_value(param_map, 'noise', '噪声')
        illumination = get_param_value(param_map, 'illumination', '照度')
        pressure_val = get_param_value(param_map, 'pressure', 'static_pressure_diff', '静压差')
        hepa_leak_result = get_param_result(param_map, 'hepa_leak')
        particle_result = get_param_result(param_map, 'particle')
        pass_box_result_state = room.get('pass_box_result_state', '') or ((room.get('summary') or {}).get('result_state', ''))
        equipment_status = '可正常启动' if str(pass_box_result_state).strip() in {'合格', '全部符合要求', '符合要求'} else ''
        
        # 内尺寸字段（用于第二页表格）
        inner_size_text = product_inner_size_text  # 复用产品内尺寸的格式
        
        plan.extend([
            ('样品名称', room.get('type_name', '') or '传递窗'),
            ('检测对象', room.get('type_name', '') or '传递窗'),
            ('项目名称', project_context.get('project_name', '')),
            ('检测区域', room_context.get('detection_area', '') or project_context.get('inspection_area', '')),
            ('所在房间', room_context.get('detection_area', '') or room.get('room_name', '')),
            ('外观检验', appearance),
            ('门互锁功能', door_interlock),
            ('产品内尺寸', product_inner_size_text),
            ('内尺寸', inner_size_text),
            ('内长', box_inner_length),
            ('内宽', box_inner_width),
            ('内高', box_inner_height),
            ('换气次数', airchange_combined),
            ('噪声', noise),
            ('高效过滤器检漏', hepa_leak_result),
            ('洁净度', particle_result),
            ('设备状态', equipment_status),
            ('静压差', pressure_val),
            ('照度', illumination),
            ('平均照度', illumination),
        ])
    elif type_id == 'clean_function_room':
        clean_function_subroom = context.get('clean_function_subroom', '')
        clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))
        _cf_std_ranges = {}
        try:
            _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
            with open(_std_path, 'r', encoding='utf-8') as _sf:
                _all_std = json.load(_sf)
            _candidate_stds = []
            for _s in room.get('judgement', []) or []:
                if _s and _s not in _candidate_stds:
                    _candidate_stds.append(_s)
            for _s in room.get('basis', []) or []:
                if _s and _s not in _candidate_stds:
                    _candidate_stds.append(_s)
            for _std in _candidate_stds:
                _obj = ((_all_std.get(_std) or {}).get('clean_function_room') or {})
                _level = _obj.get(clean_class_text) or {}
                if isinstance(_level, dict) and _level:
                    _cf_std_ranges = _level
                    break
        except Exception:
            _cf_std_ranges = {}

        def _cf_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        def _cf_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        particle_meta = get_param_meta(param_map, 'particle')
        particle_values = get_param_values(param_map, 'particle')
        particle_item = get_param_item(param_map, 'particle')
        particle_data = particle_item.get('data', {}) if isinstance(particle_item, dict) else {}
        if not isinstance(particle_data, dict):
            particle_data = {}
        particle_clean_class = str(particle_meta.get('clean_class', '') or clean_class_text or '')
        particle_result = str(get_param_result(param_map, 'particle') or _cf_result('cleanliness_05um', '洁净度级别（悬浮粒子浓度）') or '')
        particle_max_05 = str(particle_values.get('max_0_5um', '') or particle_data.get('p05_max', '') or _cf_value('cleanliness_05um', '洁净度级别（悬浮粒子浓度）') or '')
        particle_max_5 = str(particle_values.get('max_5um', '') or particle_data.get('p5_max', '') or _cf_value('cleanliness_5um', '悬浮粒子数/m³') or '')
        particle_ucl_05 = str(particle_values.get('ucl_0_5um', '') or particle_data.get('p05_ucl', '') or '')
        particle_ucl_5 = str(particle_values.get('ucl_5um', '') or particle_data.get('p5_ucl', '') or '')
        bacteria = get_param_item(param_map, 'bacteria', 'settle_bacteria', 'settling_bacteria')
        bacteria_values = bacteria.get('values', {}) if isinstance(bacteria, dict) else {}
        if not isinstance(bacteria_values, dict):
            bacteria_values = {}
        bacteria_value = str(bacteria_values.get('value', '') or _cf_value('bacteria') or _cf_value('settle_bacteria') or _cf_value('settling_bacteria') or _cf_value('细菌浓度（沉降法）') or '')
        pressure_diff = _cf_value('static_pressure_diff') or _cf_value('pressure_diff') or _cf_value('pressure') or _cf_value('静压差')
        airchange_rate = _cf_value('airchange_rate') or _cf_value('air_change_rate') or _cf_value('airchange') or _cf_value('换气次数')
        temperature = _cf_value('temperature') or _cf_value('温度')
        humidity = _cf_value('humidity') or _cf_value('relative_humidity') or _cf_value('相对湿度')
        noise = _cf_value('noise') or _cf_value('噪声')
        illumination = _cf_value('illumination_min') or _cf_value('illumination') or _cf_value('照度') or _cf_value('平均照度')
        airflow_pattern = _cf_result('airflow_pattern')

        detection_environment_parts = []
        if clean_function_subroom:
            detection_environment_parts.append(clean_function_subroom)
        if clean_class_text:
            detection_environment_parts.append(clean_class_text)
        detection_environment = ' / '.join(detection_environment_parts)

        parameter_summary_parts = []
        if airchange_rate:
            parameter_summary_parts.append(f'换气次数：{airchange_rate}')
        if pressure_diff:
            parameter_summary_parts.append(f'静压差：{pressure_diff}')
        if particle_result:
            parameter_summary_parts.append(f'洁净度：{particle_result}')
        if bacteria_value:
            parameter_summary_parts.append(f'细菌浓度：{bacteria_value}')
        floating_bacteria = _cf_value('floating_bacteria') or _cf_value('浮游菌（平均浓度）') or _cf_value('浮游菌')
        parameter_summary_text = '；'.join(parameter_summary_parts)

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('房间类型', clean_function_subroom),
            ('功能用房类型', clean_function_subroom),
            ('洁净功能用房类型', clean_function_subroom),
            ('洁净级别', clean_class_text),
            ('洁净等级', clean_class_text),
            ('洁净度级别', particle_clean_class or clean_class_text),
            ('检测对象', room.get('type_name', '') or '洁净功能用房'),
            ('样品名称', room.get('type_name', '') or '洁净功能用房'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('检测环境', detection_environment),
            ('参数摘要', parameter_summary_text),
            ('换气次数', airchange_rate),
            ('静压差', pressure_diff),
            ('温度', temperature),
            ('相对湿度', humidity),
            ('噪声', noise),
            ('照度', illumination),
            ('气流流型', airflow_pattern),
            ('洁净度', particle_result),
            ('悬浮粒子数/m³', particle_max_05),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('细菌浓度', bacteria_value),
            ('沉降菌', bacteria_value),
            ('浮游菌（平均浓度）', floating_bacteria),
            ('浮游菌', floating_bacteria),
        ])
    elif type_id == 'bsl':
        clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))

        def _bsl_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        def _bsl_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        particle_meta = get_param_meta(param_map, 'particle')
        particle_values = get_param_values(param_map, 'particle')
        particle_item = get_param_item(param_map, 'particle')
        particle_data = particle_item.get('data', {}) if isinstance(particle_item, dict) else {}
        if not isinstance(particle_data, dict):
            particle_data = {}
        particle_clean_class = str(particle_meta.get('clean_class', '') or clean_class_text or '')
        particle_max_05 = str(particle_values.get('max_0_5um', '') or particle_data.get('p05_max', '') or _bsl_value('cleanliness_05um') or _bsl_value('洁净度级别（悬浮粒子浓度）') or '')
        particle_max_5 = str(particle_values.get('max_5um', '') or particle_data.get('p5_max', '') or _bsl_value('cleanliness_5um') or _bsl_value('悬浮粒子数/m³') or '')
        particle_ucl_05 = str(particle_values.get('ucl_0_5um', '') or particle_data.get('p05_ucl', '') or '')
        particle_ucl_5 = str(particle_values.get('ucl_5um', '') or particle_data.get('p5_ucl', '') or '')
        settling_bacteria = _bsl_value('settle_bacteria') or _bsl_value('settling_bacteria') or _bsl_value('settling') or _bsl_value('沉降菌（平均菌落数）') or _bsl_value('沉降菌')
        floating_bacteria = _bsl_value('floating_bacteria') or _bsl_value('floating') or _bsl_value('浮游菌（平均浓度）') or _bsl_value('浮游菌')
        temperature = _bsl_value('temperature') or _bsl_value('温度')
        humidity = _bsl_value('humidity') or _bsl_value('relative_humidity') or _bsl_value('相对湿度')
        illumination = _bsl_value('illumination') or _bsl_value('照度') or _bsl_value('平均照度')
        noise = _bsl_value('noise') or _bsl_value('噪声')
        pressure_diff = _bsl_value('static_pressure_diff') or _bsl_value('pressure_diff') or _bsl_value('pressure') or _bsl_value('静压差')
        airchange_rate = _bsl_value('airchange_rate') or _bsl_value('air_change_rate') or _bsl_value('airchange') or _bsl_value('换气次数')
        airflow_direction = _bsl_result('airflow_direction') or _bsl_result('气流流向') or '符合要求'

        detection_environment_parts = []
        if clean_class_text:
            detection_environment_parts.append(clean_class_text)
        detection_environment = ' / '.join(detection_environment_parts)

        parameter_summary_parts = []
        if airchange_rate:
            parameter_summary_parts.append(f'换气次数：{airchange_rate}')
        if pressure_diff:
            parameter_summary_parts.append(f'静压差：{pressure_diff}')
        if particle_clean_class:
            parameter_summary_parts.append(f'洁净度级别：{particle_clean_class}')
        if settling_bacteria:
            parameter_summary_parts.append(f'沉降菌：{settling_bacteria}')
        parameter_summary_text = '；'.join(parameter_summary_parts)

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('洁净级别', clean_class_text),
            ('洁净等级', clean_class_text),
            ('洁净度级别', particle_clean_class or clean_class_text),
            ('检测对象', room.get('type_name', '') or '生物安全实验室'),
            ('样品名称', room.get('type_name', '') or '生物安全实验室'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('检测环境', detection_environment),
            ('参数摘要', parameter_summary_text),
            ('换气次数', airchange_rate),
            ('静压差', pressure_diff),
            ('气流流向', airflow_direction),
            ('温度', temperature),
            ('相对湿度', humidity),
            ('噪声', noise),
            ('照度', illumination),
            ('悬浮粒子数/m³', particle_max_05),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('细菌浓度', settling_bacteria),
            ('沉降菌', settling_bacteria),
            ('浮游菌（平均浓度）', floating_bacteria),
            ('浮游菌', floating_bacteria),
        ])
    elif type_id == 'laminar_hood':
        param_map = build_param_map(room.get('params'))
        avg_speed = get_param_value(param_map, 'avg_speed', 'airflow_speed', 'wind_speed', '平均风速')
        speed_uniformity = get_param_value(param_map, 'speed_uniformity', 'wind_uniformity', '风速不均匀度')
        noise_val = get_param_value(param_map, 'noise', '噪声')
        illumination_val = get_param_value(param_map, 'illumination', '照度', '平均照度')
        settling_val = get_param_value(param_map, 'settling_bacteria', 'settling', 'settle_bacteria', '沉降菌')
        airflow_pattern = get_param_result(param_map, 'airflow_pattern')
        hepa_leak_result = get_param_result(param_map, 'hepa_leak')
        particle_meta = get_param_meta(param_map, 'particle')
        particle_values = get_param_values(param_map, 'particle')
        particle_result = get_param_result(param_map, 'particle')
        particle_clean_class = particle_meta.get('clean_class', '') or room.get('clean_class', '') or room.get('level_name', '')
        particle_max_05 = particle_values.get('max_0_5um', '')
        particle_max_5 = particle_values.get('max_5um', '')
        particle_ucl_05 = particle_values.get('ucl_0_5um', '')
        particle_ucl_5 = particle_values.get('ucl_5um', '')
        env_parts = []
        if avg_speed:
            env_parts.append(f'平均风速：{avg_speed} m/s')
        if speed_uniformity:
            env_parts.append(f'风速不均匀度：{speed_uniformity}')
        if particle_clean_class:
            env_parts.append(f'洁净度：{particle_clean_class}')
        detection_environment = '；'.join(env_parts)
        parameter_summary_parts = []
        if avg_speed:
            parameter_summary_parts.append(f'平均风速：{avg_speed} m/s')
        if speed_uniformity:
            parameter_summary_parts.append(f'风速不均匀度：{speed_uniformity}')
        if airflow_pattern:
            parameter_summary_parts.append(f'气流流型：{_normalize_conclusion_text(airflow_pattern)}')
        if hepa_leak_result:
            parameter_summary_parts.append(f'高效过滤器检漏：{_normalize_conclusion_text(hepa_leak_result)}')
        if particle_clean_class:
            parameter_summary_parts.append(f'洁净度：{particle_clean_class}')
        parameter_summary_text = '；'.join(parameter_summary_parts)
        plan.extend([
            ('样品名称', room.get('type_name', '') or '层流罩'),
            ('设备状态', '可正常启动' if str(((room.get('summary') or {}).get('result_state', ''))).strip() in {'合格', '全部符合要求', '符合要求'} else ''),
            ('检测类型', '现场检测'),
            ('项目名称', project_context.get('project_name', '')),
            ('所在房间', room_context.get('detection_area', '') or room.get('room_name', '')),
            ('检测环境', detection_environment),
            ('平均风速', avg_speed),
            ('风速不均匀度', speed_uniformity),
            ('垂直气流平均风速', avg_speed),
            ('气流流型', airflow_pattern),
            ('高效过滤器检漏', hepa_leak_result),
            ('送风高效过滤器检漏', hepa_leak_result),
            ('洁净度', particle_result),
            ('洁净度级别', particle_clean_class),
            ('悬浮粒子数/m³', particle_max_05),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('参数摘要', parameter_summary_text),
            ('噪声', noise_val),
            ('照度', illumination_val),
            ('平均照度', illumination_val),
            ('沉降菌（平均菌落数）', settling_val),
            ('沉降菌浓度', settling_val),
        ])
    elif type_id == 'operating_room':
        surgery_room_type = context.get('surgery_room_type', '')
        surgery_aux_room = context.get('surgery_aux_room', '')
        surgery_aux_clean_class = context.get('surgery_aux_clean_class', '')
        clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))

        def _op_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        # 医院洁净部照度映射规则（刘总 2026-05-07 明确）：
        # 前台虽然存在多个照度录入入口，但单次业务录入不会把所有照度都输入；
        # 模板侧只有一个照度落点是正确设计。
        # 因此系统规则不是“把所有照度同时写进模板”，而是“录哪个照度，就映射哪个照度到模板唯一照度位”。
        def _op_single_illumination_value(*keys: str) -> str:
            return _op_value(*keys)

        def _op_compact_value(*keys: str) -> str:
            raw = str(_op_value(*keys) or '').strip()
            if not raw:
                return ''
            import re as _re_op_val
            _m = _re_op_val.search(r'=\s*([\-]?[\d.]+)\s*(?:次/h|m/s|Pa|℃|%|lx|dB\(?A?\)?)?\s*$', raw)
            if _m:
                return _m.group(1)
            _m2 = _re_op_val.match(r'([\-]?[\d.]+)', raw)
            if _m2:
                return _m2.group(1)
            return raw

        def _op_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        particle_meta = get_param_meta(param_map, 'particle')
        particle_values = get_param_values(param_map, 'particle')
        particle_clean_class = particle_meta.get('clean_class', '') or clean_class_text
        particle_max_05 = str(particle_values.get('max_0_5um', '') or '')
        particle_result = get_param_result(param_map, 'particle')
        particle_max_5 = str(particle_values.get('max_5um', '') or '')
        particle_ucl_05 = str(particle_values.get('ucl_0_5um', '') or particle_values.get('op_05_ucl', '') or '')
        particle_ucl_5 = str(particle_values.get('ucl_5um', '') or particle_values.get('op_5_ucl', '') or '')
        particle_op_max_05 = str(particle_values.get('op_05_max', '') or particle_values.get('max_0_5um_op', '') or '')
        particle_op_ucl_05 = str(particle_values.get('op_05_ucl', '') or particle_values.get('ucl_0_5um_op', '') or '')
        particle_op_max_5 = str(particle_values.get('op_5_max', '') or particle_values.get('max_5um_op', '') or '')
        particle_op_ucl_5 = str(particle_values.get('op_5_ucl', '') or particle_values.get('ucl_5um_op', '') or '')
        particle_surr_max_05 = str(particle_values.get('surr_05_max', '') or particle_values.get('max_0_5um_surr', '') or '')
        particle_surr_ucl_05 = str(particle_values.get('surr_05_ucl', '') or particle_values.get('ucl_0_5um_surr', '') or '')
        particle_surr_max_5 = str(particle_values.get('surr_5_max', '') or particle_values.get('max_5um_surr', '') or '')
        particle_surr_ucl_5 = str(particle_values.get('surr_5_ucl', '') or particle_values.get('ucl_5um_surr', '') or '')

        bacteria_values = get_param_values(param_map, 'bacteria')
        bacteria_op_value = str(bacteria_values.get('op_value', '') or bacteria_values.get('surgical', '') or _op_value('settle_bacteria_surgical') or '')
        bacteria_surr_value = str(bacteria_values.get('surr_value', '') or bacteria_values.get('surrounding', '') or _op_value('settle_bacteria_surrounding') or '')

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('房间类型', surgery_room_type),
            ('辅助房间名称', surgery_aux_room),
            ('洁净级别', clean_class_text),
            ('洁净等级', clean_class_text),
            ('手术室级别', clean_class_text),
            ('辅房级别', surgery_aux_clean_class),
            ('检测对象', room.get('type_name', '') or '手术室'),
            ('样品名称', room.get('type_name', '') or '手术室'),
            ('换气次数', _op_compact_value('airchange_rate', 'airchange', '换气次数')),
            ('截面平均风速', _op_compact_value('wind_speed', 'air_velocity', 'sectional_air_velocity', '截面风速', '截面平均风速')),
            ('截面风速', _op_compact_value('wind_speed', 'air_velocity', 'sectional_air_velocity', '截面风速')),
            ('风速不均匀度', _op_compact_value('wind_uniformity', 'speed_uniformity', '风速不均匀度')),
            ('静压差', _op_value('static_pressure_diff', 'pressure_diff', 'pressure', '静压差')),
            ('严密性', _op_result('airtightness', '严密性') or '符合要求'),
            ('送风高效过滤器检漏', _op_result('hepa_leak', '高效过滤器检漏', '送风高效过滤器检漏')),
            ('温度', _op_value('temperature', '温度')),
            ('相对湿度', _op_value('relative_humidity', 'humidity', '相对湿度')),
            ('噪声', _op_value('noise', '噪声')),
            ('照度', _op_single_illumination_value('illumination', 'illumination_main_room', 'illumination_aux_room', 'illumination_min', 'illumination_main', 'illumination_aux', '照度', '最低照度')),
            ('最低照度', _op_single_illumination_value('illumination_min', 'illumination_main_room', 'illumination_aux_room', 'illumination_main', 'illumination_aux', 'illumination', '最低照度')),
            ('照度均匀度', _op_value('illumination_uniformity', '照度均匀度')),
            ('细菌浓度', _op_result('bacteria', 'settling_bacteria', '细菌浓度') or _op_value('bacteria', 'settling_bacteria', '细菌浓度')),
            ('洁净度级别', particle_clean_class),
            ('悬浮粒子数/m³', particle_max_05),
            ('洁净度结果', particle_result),
            ('细菌浓度（沉降法）手术区', bacteria_op_value),
            ('细菌浓度（沉降法）周边区', bacteria_surr_value),
            ('手术区≥0.5μm最大值', particle_op_max_05),
            ('手术区≥0.5μmUCL', particle_op_ucl_05),
            ('手术区≥5μm最大值', particle_op_max_5),
            ('手术区≥5μmUCL', particle_op_ucl_5),
            ('周边区≥0.5μm最大值', particle_surr_max_05),
            ('周边区≥0.5μmUCL', particle_surr_ucl_05),
            ('周边区≥5μm最大值', particle_surr_max_5),
            ('周边区≥5μmUCL', particle_surr_ucl_5),
            ('手术区细菌浓度', bacteria_op_value),
            ('周边区细菌浓度', bacteria_surr_value),
            # 单项结论来源：每个数值型参数的 param.result
            ('截面风速结果', _op_result('wind_speed', 'air_velocity', 'sectional_air_velocity', '截面风速', '截面平均风速')),
            ('截面平均风速结果', _op_result('wind_speed', 'air_velocity', 'sectional_air_velocity', '截面风速', '截面平均风速')),
            ('风速不均匀度结果', _op_result('wind_uniformity', 'speed_uniformity', '风速不均匀度')),
            ('静压差结果', _op_result('static_pressure_diff', 'pressure_diff', 'pressure', '静压差')),
            ('温度结果', _op_result('temperature', '温度')),
            ('相对湿度结果', _op_result('relative_humidity', 'humidity', '相对湿度')),
            ('湿度结果', _op_result('relative_humidity', 'humidity', '相对湿度')),
            ('噪声结果', _op_result('noise', '噪声')),
            ('照度结果', _op_result('illumination', 'illumination_main_room', 'illumination_aux_room', 'illumination_min', '照度')),
            ('平均照度结果', _op_result('illumination', 'illumination_main_room', 'illumination_aux_room', 'illumination_min', '照度')),
            ('照度均匀度结果', _op_result('illumination_uniformity', '照度均匀度')),
            ('严密性结果', _op_result('airtightness', '严密性')),
            ('高效过滤器检漏结果', _op_result('hepa_leak', '高效过滤器检漏', '送风高效过滤器检漏')),
            ('送风高效过滤器检漏结果', _op_result('hepa_leak', '高效过滤器检漏', '送风高效过滤器检漏')),
        ])
    elif type_id == 'negative_pressure':
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))
        
        def _np_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        def _np_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('检测对象', room.get('type_name', '') or '负压病房'),
            ('样品名称', room.get('type_name', '') or '负压病房'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('换气次数', _np_value('airchange', 'airchange_rate', 'air_change_rate')),
            ('污染区换气次数', _np_value('airchange', 'airchange_polluted')),
            ('清洁区换气次数', _np_value('airchange_clean')),
            ('排风口风速', _np_value('exhaust_speed', 'exhaust_velocity')),
            ('静压差', _np_value('pressure', 'static_pressure_diff')),
            ('气流流向', _np_value('airflow_direction')),
            ('温度', _np_value('temperature')),
            ('相对湿度', _np_value('relative_humidity', 'humidity')),
            ('噪声', _np_value('noise')),
            ('照度', _np_value('illumination')),
            ('细菌浓度', _np_value('settling_bacteria', 'bacteria', 'settle_bacteria')),
            ('物体表面微生物', _np_value('surface_bacteria')),
            ('送风高效过滤器检漏', _np_value('hepa_leak')),
        ])
    elif type_id == 'gmp_workshop':
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))

        def _gmp_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        def _gmp_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        gmp_grade = context.get('gmp_grade', '') or room.get('clean_class', '') or room.get('level_name', '')
        detection_environment = ' / '.join([v for v in [gmp_grade, room_display_name] if str(v).strip()])
        airchange_rate = _gmp_value('wind_speed', 'airchange_rate', 'air_change_rate', 'airchange', '换气次数', '截面风速') or _gmp_result('wind_speed', 'airchange_rate', 'air_change_rate', 'airchange', '换气次数', '截面风速')
        pressure_diff = _gmp_value('static_pressure_diff', 'pressure_diff', 'pressure', '静压差')
        temperature = _gmp_value('temperature', '温度')
        humidity = _gmp_value('relative_humidity', 'humidity', '相对湿度')
        illumination = _gmp_value('illumination', 'illumination_main_room', 'illumination_aux_room', '照度', '平均照度')
        noise = _gmp_value('noise', '噪声')
        # 清洗器器单位后缀
        if noise:
            import re as _re_noise
            noise = _re_noise.sub(r'\s*dB\(?A?\)?\s*$', '', noise, flags=_re_noise.IGNORECASE).strip()
        settling_bacteria = _gmp_value('settling_bacteria', 'settle_bacteria', 'settling', '沉降菌（平均菌落数）', '沉降菌')
        floating_bacteria = _gmp_value('floating_bacteria', 'floating', '浮游菌（平均浓度）', '浮游菌')
        self_clean = _gmp_value('self_clean', '自净时间')
        airflow_pattern = _gmp_value('airflow_pattern', '气流流型')
        hepa_leak = _gmp_value('hepa_leak', '送风高效过滤器检漏')
        particle_meta = get_param_meta(param_map, 'particle')
        particle_values = get_param_values(param_map, 'particle')
        particle_item = get_param_item(param_map, 'particle')
        particle_data = particle_item.get('data', {}) if isinstance(particle_item, dict) else {}
        if not isinstance(particle_data, dict):
            particle_data = {}
        particle_clean_class = str(particle_meta.get('clean_class', '') or gmp_grade or '')
        particle_max_05 = str(particle_values.get('max_0_5um', '') or particle_data.get('p05_max', '') or _gmp_value('cleanliness_05um', '洁净度级别（悬浮粒子浓度）') or '')
        particle_max_5 = str(particle_values.get('max_5um', '') or particle_data.get('p5_max', '') or _gmp_value('cleanliness_5um', '悬浮粒子数/m³') or '')
        particle_ucl_05 = str(particle_values.get('ucl_0_5um', '') or particle_data.get('p05_ucl', '') or '')
        particle_ucl_5 = str(particle_values.get('ucl_5um', '') or particle_data.get('p5_ucl', '') or '')
        particle_result = str(get_param_result(param_map, 'particle') or _gmp_result('cleanliness_05um', '洁净度级别（悬浮粒子浓度）') or '')

        parameter_summary_parts = []
        if airchange_rate:
            parameter_summary_parts.append(f'换气次数：{airchange_rate}')
        if pressure_diff:
            parameter_summary_parts.append(f'静压差：{pressure_diff}')
        if temperature:
            parameter_summary_parts.append(f'温度：{temperature}')
        if humidity:
            parameter_summary_parts.append(f'相对湿度：{humidity}')
        parameter_summary_text = '；'.join(parameter_summary_parts)

        gmp_particle_limits = {
            'A级': ('≥0.5㎛：≤3520', '≥5㎛：≤20'),
            'B级': ('≥0.5㎛：≤3520', '≥5㎛：≤29'),
            'C级': ('≥0.5㎛：≤352000', '≥5㎛：≤2900'),
            'D级': ('≥0.5㎛：≤3520000', '≥5㎛：≤29000'),
        }
        limit_05, limit_5 = gmp_particle_limits.get(str(gmp_grade).strip(), ('', ''))

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('检测对象', room.get('type_name', '') or 'GMP车间'),
            ('样品名称', room.get('type_name', '') or 'GMP车间'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('GMP等级', gmp_grade),
            ('洁净等级', gmp_grade),
            ('洁净级别', gmp_grade),
            ('洁净度设计级别', gmp_grade),
            ('洁净度级别', particle_clean_class or gmp_grade),
            ('洁净度', particle_clean_class or gmp_grade),
            ('悬浮粒子数/m³', particle_max_05),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('≥0.5μm标准', limit_05),
            ('≥5μm标准', limit_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('检测环境', detection_environment),
            ('参数摘要', parameter_summary_text),
            ('换气次数', airchange_rate),
            ('静压差', pressure_diff),
            ('温度', temperature),
            ('相对湿度', humidity),
            ('平均照度', illumination),
            ('照度', illumination),
            ('噪声', noise),
            ('沉降菌', settling_bacteria),
            ('沉降菌（平均菌落数）', settling_bacteria),
            ('浮游菌', floating_bacteria),
            ('浮游菌（平均浓度）', floating_bacteria),
            ('自净时间', self_clean),
            ('气流流型', airflow_pattern),
            ('送风高效过滤器检漏', hepa_leak),
            ('高效过滤器检漏', hepa_leak),
        ])
    elif type_id == 'veterinary_gmp_workshop':
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))

        def _vgmp_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        def _vgmp_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        gmp_grade = context.get('gmp_grade', '') or room.get('clean_class', '') or room.get('level_name', '')
        detection_environment = ' / '.join([v for v in [gmp_grade, room_display_name] if str(v).strip()])
        airflow_speed = _vgmp_value('sectional_air_velocity', 'air_velocity', 'wind_speed', 'airchange', '截面风速')
        speed_uniformity = _vgmp_value('speed_uniformity', 'wind_uniformity', '风速不均匀度')
        pressure_diff = _vgmp_value('static_pressure_diff', 'pressure_diff', 'pressure', '静压差')
        hepa_leak = _vgmp_value('hepa_leak', '送风高效过滤器检漏')
        temperature = _vgmp_value('temperature', '温度')
        humidity = _vgmp_value('relative_humidity', 'humidity', '相对湿度')
        illumination = _vgmp_value('illumination', 'illumination_main_room', 'illumination_aux_room', '照度', '平均照度')
        noise = _vgmp_value('noise', '噪声')
        if noise:
            import re as _re
            noise = _re.sub(r'\s*dB\(A\)\s*', '', noise).strip()
        settling_bacteria = _vgmp_value('settling_bacteria', 'settle_bacteria', 'settling', '沉降菌（平均菌落数）', '沉降菌')
        floating_bacteria = _vgmp_value('floating_bacteria', 'floating', '浮游菌（平均浓度）', '浮游菌')
        self_clean = _vgmp_value('self_clean', '自净时间')
        airflow_pattern = _vgmp_value('airflow_pattern', '气流流型')
        particle = param_map.get('particle', {}) or {}
        particle_meta = particle.get('meta', {}) or {}
        particle_values = particle.get('values', {}) or {}
        particle_clean_class = str(particle_meta.get('clean_class', '') or gmp_grade or '')
        particle_max_05 = str(
            particle_values.get('max_0_5um', '')
            or _vgmp_value('particle', 'cleanliness_05um', '≥0.5μm', '0.5um', '0.5μm')
            or ''
        )
        particle_max_5 = str(
            particle_values.get('max_5um', '')
            or _vgmp_value('cleanliness_5um', '≥5μm', '5um', '5μm', '悬浮粒子数/m³')
            or ''
        )
        particle_ucl_05 = str(
            particle_values.get('ucl_0_5um', '')
            or _vgmp_value('0.5μmUCL', '0.5umUCL', 'ucl_0_5um')
            or ''
        )
        particle_ucl_5 = str(
            particle_values.get('ucl_5um', '')
            or _vgmp_value('5μmUCL', '5umUCL', 'ucl_5um')
            or ''
        )
        particle_result = str(particle.get('result', '') or _vgmp_result('cleanliness_05um', '洁净度级别（悬浮粒子浓度）') or '')

        vet_particle_limits = {
            'A级': ('≥0.5㎛：≤3520', '≥5㎛：≤20'),
            'B级': ('≥0.5㎛：≤3520', '≥5㎛：≤29'),
            'C级': ('≥0.5㎛：≤352000', '≥5㎛：≤2900'),
            'D级': ('≥0.5㎛：≤3520000', '≥5㎛：≤29000'),
        }
        limit_05, limit_5 = vet_particle_limits.get(str(gmp_grade).strip(), ('', ''))

        parameter_summary_parts = []
        if airflow_speed:
            parameter_summary_parts.append(f'截面风速：{airflow_speed}')
        if pressure_diff:
            parameter_summary_parts.append(f'静压差：{pressure_diff}')
        if temperature:
            parameter_summary_parts.append(f'温度：{temperature}')
        if humidity:
            parameter_summary_parts.append(f'相对湿度：{humidity}')
        parameter_summary_text = '；'.join(parameter_summary_parts)

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('检测对象', room.get('type_name', '') or '兽药车间'),
            ('样品名称', room.get('type_name', '') or '兽药车间'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('GMP等级', gmp_grade),
            ('洁净等级', gmp_grade),
            ('洁净级别', gmp_grade),
            ('洁净度设计级别', gmp_grade),
            ('洁净度级别', particle_clean_class),
            ('洁净度', particle_result),
            ('悬浮粒子数/m³', particle_max_05),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('≥0.5μm标准', limit_05),
            ('≥5μm标准', limit_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('检测环境', detection_environment),
            ('参数摘要', parameter_summary_text),
            ('截面风速', airflow_speed),
            ('换气次数', airflow_speed),
            ('风速不均匀度', speed_uniformity),
            ('静压差', pressure_diff),
            ('送风高效过滤器检漏', hepa_leak),
            ('温度', temperature),
            ('相对湿度', humidity),
            ('平均照度', illumination),
            ('照度', illumination),
            ('噪声', noise),
            ('沉降菌', settling_bacteria),
            ('沉降菌（平均菌落数）', settling_bacteria),
            ('浮游菌', floating_bacteria),
            ('浮游菌（平均浓度）', floating_bacteria),
            ('自净时间', self_clean),
            ('气流流型', airflow_pattern),
        ])
    elif type_id == 'food_workshop':
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))

        def _food_value(*keys: str) -> str:
            return get_param_value(param_map, *keys)

        def _food_result(*keys: str) -> str:
            return get_param_result(param_map, *keys)

        food_grade = context.get('food_grade', '') or room.get('clean_class', '') or room.get('level_name', '')
        detection_environment = ' / '.join([v for v in [food_grade, room_display_name] if str(v).strip()])
        air_velocity = _food_value('wind_speed', 'air_velocity', 'sectional_air_velocity', '截面风速')
        airchange_rate = _food_value('airchange_rate', 'air_change_rate', 'airchange', '换气次数')
        pressure_diff = _food_value('static_pressure_diff', 'pressure_diff', 'pressure', '静压差')
        hepa_leak = _food_value('hepa_leak', '送风高效过滤器检漏')
        temperature = _food_value('temperature', '温度')
        humidity = _food_value('relative_humidity', 'humidity', '相对湿度', '湿度')
        illumination = _food_value('illumination', 'illumination_general_processing', 'illumination_mixed_processing', 'illumination_non_processing', '照度', '平均照度')
        noise = _food_value('noise', '噪声')
        # Strip dB(A) unit from noise value
        if noise:
            import re as _re
            noise = _re.sub(r'\s*dB\(A\)\s*', '', noise).strip()
        settling_bacteria = _food_value('settling_bacteria', 'settle_bacteria', 'settling', '沉降菌（平均菌落数）', '沉降菌')
        floating_bacteria = _food_value('floating_bacteria', 'floating', '浮游菌（平均浓度）', '浮游菌')
        particle = param_map.get('particle', {}) or {}
        particle_meta = particle.get('meta', {}) or {}
        particle_values = particle.get('values', {}) or {}
        particle_clean_class = str(particle_meta.get('clean_class', '') or food_grade or '')
        particle_max_05 = str(
            particle_values.get('max_0_5um', '')
            or _food_value('cleanliness_05um', '≥0.5μm', '0.5um', '0.5μm')
            or ''
        )
        particle_max_5 = str(
            particle_values.get('max_5um', '')
            or _food_value('cleanliness_5um', '≥5μm', '5um', '5μm', '悬浮粒子数/m³')
            or ''
        )
        particle_ucl_05 = str(
            particle_values.get('ucl_0_5um', '')
            or _food_value('0.5μmUCL', '0.5umUCL', 'ucl_0_5um')
            or ''
        )
        particle_ucl_5 = str(
            particle_values.get('ucl_5um', '')
            or _food_value('5μmUCL', '5umUCL', 'ucl_5um')
            or ''
        )
        particle_result = str(particle.get('result', '') or _food_result('cleanliness_05um', '洁净度级别（悬浮粒子浓度）') or '')

        food_particle_limits = {
            'Ⅰ级（百级）': ('≥0.5㎛：≤3520', '≥5㎛：≤29'),
            'Ⅱ级（万级）': ('≥0.5㎛：≤352000', '≥5㎛：≤2930'),
            'Ⅲ级（十万级）': ('≥0.5㎛：≤3520000', '≥5㎛：≤29300'),
            'Ⅳ级（三十万级）': ('≥0.5㎛：≤35200000', '≥5㎛：≤293000'),
        }
        limit_05, limit_5 = food_particle_limits.get(str(food_grade).strip(), ('', ''))

        parameter_summary_parts = []
        if airchange_rate:
            parameter_summary_parts.append(f'换气次数：{airchange_rate}')
        elif air_velocity:
            parameter_summary_parts.append(f'截面风速：{air_velocity}')
        if pressure_diff:
            parameter_summary_parts.append(f'静压差：{pressure_diff}')
        if temperature:
            parameter_summary_parts.append(f'温度：{temperature}')
        if humidity:
            parameter_summary_parts.append(f'相对湿度：{humidity}')
        parameter_summary_text = '；'.join(parameter_summary_parts)

        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('检测对象', room.get('type_name', '') or '食品车间'),
            ('样品名称', room.get('type_name', '') or '食品车间'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('食品等级', food_grade),
            ('洁净等级', food_grade),
            ('洁净级别', food_grade),
            ('洁净度设计级别', food_grade),
            ('洁净度级别', particle_clean_class or food_grade),
            ('洁净度', particle_result or food_grade),
            ('悬浮粒子数/m³', particle_max_05),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('≥0.5μm标准', limit_05),
            ('≥5μm标准', limit_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('检测环境', detection_environment),
            ('参数摘要', parameter_summary_text),
            ('截面风速', air_velocity),
            ('换气次数', airchange_rate or air_velocity),
            ('静压差', pressure_diff),
            ('送风高效过滤器检漏', hepa_leak),
            ('温度', temperature),
            ('相对湿度', humidity),
            ('湿度', humidity),
            ('平均照度', illumination),
            ('照度', illumination),
            ('噪声', noise),
            ('沉降菌', settling_bacteria),
            ('沉降菌（平均菌落数）', settling_bacteria),
            ('浮游菌', floating_bacteria),
            ('浮游菌（平均浓度）', floating_bacteria),
        ])
    elif type_id == 'electronics_workshop':
        room_display_name = room.get('room_name', '')
        param_map = build_param_map(room.get('params'))

        iso_level = context.get('iso_level', '') or room.get('level_name', '') or room.get('clean_class', '')
        # ISO 5 单向流用截面风速，ISO 6~9 乱流用换气次数
        wind_speed = get_param_value(param_map, 'wind_speed', 'air_velocity', 'sectional_air_velocity', '截面风速')
        airchange_rate = get_param_value(param_map, 'airchange_rate', 'air_change_rate', 'airchange', '换气次数')
        pressure_diff = get_param_value(param_map, 'static_pressure_diff', 'pressure_diff', 'pressure', '静压差')
        hepa_leak = get_param_value(param_map, 'hepa_leak', '送风高效过滤器检漏')
        temperature = get_param_value(param_map, 'temperature', '温度')
        humidity = get_param_value(param_map, 'relative_humidity', 'humidity', '相对湿度', '湿度')
        illumination = get_param_value(param_map, 'illumination', 'illumination_main', 'illumination_main_room', 'illumination_aux', '照度', '平均照度')
        noise = get_param_value(param_map, 'noise', '噪声')
        # Strip dB(A) unit from noise value
        if noise:
            import re as _re
            noise = _re.sub(r'\s*dB\(A\)\s*', '', noise).strip()
        airflow_pattern = get_param_result(param_map, 'airflow_pattern', '气流流型')
        particle = param_map.get('particle', {}) or {}
        _p_data = particle.get('data', {}) or particle.get('values', {}) or {}
        particle_max_05 = str(_p_data.get('p05_max', '') or _p_data.get('max_0_5um', '') or get_param_value(param_map, 'cleanliness_05um', '≥0.5μm', '0.5um', '0.5μm') or '')
        particle_max_5 = str(_p_data.get('p5_max', '') or _p_data.get('max_5um', '') or get_param_value(param_map, 'cleanliness_5um', '≥5μm', '5um', '5μm') or '')
        particle_ucl_05 = str(_p_data.get('p05_ucl', '') or _p_data.get('ucl_0_5um', '') or get_param_value(param_map, '0.5μmUCL', '0.5umUCL', 'ucl_0_5um') or '')
        particle_ucl_5 = str(_p_data.get('p5_ucl', '') or _p_data.get('ucl_5um', '') or get_param_value(param_map, '5μmUCL', '5umUCL', 'ucl_5um') or '')
        particle_result_val = str(particle.get('result', '') or get_param_result(param_map, 'cleanliness_05um', '洁净度级别（悬浮粒子浓度）') or '')
        # ISO 粒子标准限值（GB 50472-2008 / GB 50073-2013）
        iso_particle_limits = {
            'ISO 5': ('≥0.5㎛：≤3520', '≥5㎛：≤29'),
            'ISO 6': ('≥0.5㎛：≤35200', '≥5㎛：≤293'),
            'ISO 7': ('≥0.5㎛：≤352000', '≥5㎛：≤2930'),
            'ISO 8': ('≥0.5㎛：≤3520000', '≥5㎛：≤29300'),
            'ISO 9': ('≥0.5㎛：≤35200000', '≥5㎛：≤293000'),
        }
        limit_05, limit_5 = iso_particle_limits.get(str(iso_level).strip(), ('', ''))
        # ISO 5 优先填截面风速，ISO 6~9 优先填换气次数
        airflow_value = wind_speed if str(iso_level).strip() == 'ISO 5' else (airchange_rate or wind_speed)
        plan.extend([
            ('房间名称', room_display_name),
            ('受检区域名称', room_display_name),
            ('检测对象', room.get('type_name', '') or '电子车间'),
            ('样品名称', room.get('type_name', '') or '电子车间'),
            ('检测类型', '现场检测'),
            ('所在房间', room_display_name),
            ('ISO等级', iso_level),
            ('洁净度设计级别', iso_level),
            ('洁净等级', iso_level),
            ('洁净级别', iso_level),
            ('洁净度级别', particle_result_val or iso_level),
            ('洁净度', particle_result_val or iso_level),
            ('≥0.5μm', particle_max_05),
            ('≥5μm', particle_max_5),
            ('≥0.5μm标准', limit_05),
            ('≥5μm标准', limit_5),
            ('0.5μmUCL', particle_ucl_05),
            ('5μmUCL', particle_ucl_5),
            ('截面风速', wind_speed),
            ('换气次数', airchange_rate),
            ('风速或换气次数', airflow_value),
            ('静压差', pressure_diff),
            ('送风高效过滤器检漏', hepa_leak),
            ('温度', temperature),
            ('相对湿度', humidity),
            ('湿度', humidity),
            ('平均照度', illumination),
            ('照度', illumination),
            ('噪声', noise),
            ('气流流型', airflow_pattern),
        ])
    elif type_id == 'bsc':
        param_map = build_param_map(room.get('params'))
        bsc_model = get_param_value(param_map, 'bsc_model', 'model')
        bsc_type = get_param_value(param_map, 'bsc_type', 'type')
        appearance = get_param_result(param_map, 'appearance', '外观检验')
        alarm_interlock = get_param_result(param_map, 'alarm_interlock', '报警和连锁')
        downflow_velocity = get_param_value(param_map, 'downflow_velocity', 'downflow_speed')
        inflow_velocity = get_param_value(param_map, 'inflow_velocity', 'inflow_speed')
        speed_uniformity = get_param_value(param_map, 'speed_uniformity')
        airflow_pattern = get_param_result(param_map, 'airflow_pattern', '气流模式')
        hepa_integrity = get_param_result(param_map, 'hepa_integrity', 'hepa_leak', '高效过滤器检漏')
        hepa_leak_result = get_param_result(param_map, 'hepa_leak', 'hepa_integrity', '高效过滤器检漏')
        particle_result = get_param_result(param_map, 'particle', '洁净度')
        noise = get_param_value(param_map, 'noise', '噪声')
        illumination = get_param_value(param_map, 'illumination', '照度')
        illumination_min = get_param_value(param_map, 'illumination_min', '最低照度')
        uv_intensity = get_param_value(param_map, 'uv_intensity', '紫外灯辐照强度')
        vibration = get_param_value(param_map, 'vibration', '振动')
        bsc_result_state = room.get('bsc_result_state', '') or ((room.get('summary') or {}).get('result_state', ''))
        equipment_status = '可正常启动' if str(bsc_result_state).strip() in {'合格', '全部符合要求', '符合要求'} else ''
        plan.extend([
            ('样品名称', room.get('type_name', '') or '生物安全柜'),
            ('设备名称', room.get('room_name', '') or room.get('type_name', '') or '生物安全柜'),
            ('受检区域名称', room.get('room_name', '') or room.get('type_name', '') or '生物安全柜'),
            ('房间名称', room.get('room_name', '') or room.get('type_name', '') or '生物安全柜'),
            ('检测对象', room.get('type_name', '') or '生物安全柜'),
            ('项目名称', project_context.get('project_name', '')),
            ('检测日期', project_context.get('detection_date', '')),
            ('生物安全柜型号', bsc_model),
            ('生物安全柜类型', bsc_type),
            ('外观检验', appearance),
            ('报警和连锁系统', alarm_interlock),
            ('报警和连锁', alarm_interlock),
            ('下降气流平均风速', downflow_velocity),
            ('流入气流平均风速', inflow_velocity),
            ('风速不均匀度', speed_uniformity),
            ('气流模式', airflow_pattern),
            ('高效过滤器检漏', hepa_leak_result),
            ('高效过滤器完整性', hepa_integrity),
            ('洁净度', particle_result),
            ('噪声', noise),
            ('照度', illumination),
            ('最低照度', illumination_min),
            ('紫外灯辐照强度', uv_intensity),
            ('振动', vibration),
            ('设备状态', equipment_status),
        ])
    elif type_id == 'clean_bench':
        param_map = build_param_map(room.get('params'))
        bench_model = get_param_value(param_map, 'bench_model', 'model')
        appearance = get_param_result(param_map, 'appearance', '外观检验')
        function_result = get_param_result(param_map, 'function', '功能')
        air_velocity = get_param_value(param_map, 'air_velocity', 'wind_speed', 'avg_speed', 'vertical_airflow_speed', '垂直气流平均风速')
        speed_uniformity = get_param_value(param_map, 'speed_uniformity', 'wind_uniformity', '风速不均匀度')
        hepa_leak_result = get_param_result(param_map, 'hepa_leak', '高效过滤器检漏')
        particle_result = get_param_result(param_map, 'particle', '洁净度')
        airflow_pattern = get_param_result(param_map, 'airflow_pattern', 'airflow_state', '气流状态')
        settling_bacteria = get_param_value(param_map, 'settling_bacteria', 'settle_bacteria', 'settling', '沉降菌')
        noise = get_param_value(param_map, 'noise', '噪声')
        illumination = get_param_value(param_map, 'illumination', '照度')
        vibration = get_param_value(param_map, 'vibration', '振动')
        bench_result_state = room.get('bench_result_state', '') or ((room.get('summary') or {}).get('result_state', ''))
        equipment_status = '可正常启动' if str(bench_result_state).strip() in {'合格', '全部符合要求', '符合要求'} else ''
        plan.extend([
            ('样品名称', room.get('type_name', '') or '洁净工作台'),
            ('检测对象', room.get('type_name', '') or '洁净工作台'),
            ('项目名称', project_context.get('project_name', '')),
            ('工作台型号', bench_model),
            ('外观检验', appearance),
            ('功能', function_result),
            ('平均风速', air_velocity),
            ('垂直气流平均风速', air_velocity),
            ('风速不均匀度', speed_uniformity),
            ('高效过滤器检漏', hepa_leak_result),
            ('送风高效过滤器检漏', hepa_leak_result),
            ('洁净度', particle_result),
            ('工作区洁净度', particle_result),
            ('气流状态', airflow_pattern),
            ('沉降菌', settling_bacteria),
            ('沉降菌浓度', settling_bacteria),
            ('噪声', noise),
            ('照度', illumination),
            ('平均照度', illumination),
            ('振动', vibration),
            ('设备状态', equipment_status),
        ])
    elif type_id == 'ivc':
        param_map = build_param_map(room.get('params'))
        ivc_model = get_param_value(param_map, 'ivc_model', 'model')
        cage_count = get_param_value(param_map, 'cage_count', '笼具数量')
        appearance = get_param_result(param_map, 'appearance', '外观检验')
        air_velocity = get_param_value(param_map, 'air_velocity', 'airflow_speed', 'wind_speed', 'avg_speed', 'airchange')
        hepa_leak_result = get_param_result(param_map, 'hepa_leak', 'hepa_integrity', '高效过滤器检漏')
        particle_result = get_param_result(param_map, 'particle', '洁净度')
        noise = get_param_value(param_map, 'noise', '噪声')
        illumination = get_param_value(param_map, 'illumination', '照度')
        ammonia = get_param_value(param_map, 'ammonia', '氨浓度')
        pressure_diff = get_param_value(param_map, 'pressure', 'pressure_diff', 'static_pressure_diff', '静压差')
        airtightness = get_param_result(param_map, 'airtightness', '气密性', '笼盒气密性')
        airchange = get_param_value(param_map, 'airchange', 'airchange_rate', '换气次数')
        ivc_result_state = room.get('ivc_result_state', '') or ((room.get('summary') or {}).get('result_state', ''))
        equipment_status = '可正常启动' if str(ivc_result_state).strip() in {'合格', '全部符合要求', '符合要求'} else ''
        plan.extend([
            ('样品名称', room.get('type_name', '') or 'IVC笼具'),
            ('检测对象', room.get('type_name', '') or 'IVC笼具'),
            ('项目名称', project_context.get('project_name', '')),
            ('IVC型号', ivc_model),
            ('笼具数量', cage_count),
            ('外观检验', appearance),
            ('平均风速', air_velocity),
            ('气流流速', air_velocity),
            ('换气次数', airchange),
            ('静压差', pressure_diff),
            ('箱体静压差', pressure_diff),
            ('气密性', airtightness),
            ('笼盒气密性', airtightness),
            ('高效过滤器检漏', hepa_leak_result),
            ('高效过滤器完整性', hepa_leak_result),
            ('洁净度', particle_result),
            ('噪声', noise),
            ('照度', illumination),
            ('氨浓度', ammonia),
            ('设备状态', equipment_status),
        ])

    if standard_profile:
        fixed_requirements = standard_profile.get('fixed_requirements', {}) or {}
        design_requirement_fields = standard_profile.get('design_requirement_fields', {}) or {}
        result_field_aliases = standard_profile.get('result_field_aliases', {}) or {}
        param_map = build_param_map(room.get('params'))

        def _profile_result(aliases):
            aliases = aliases or []
            result = get_param_result(param_map, *aliases)
            if result:
                return result
            return get_param_value(param_map, *aliases)

        profile_rows = []
        for k, v in fixed_requirements.items():
            profile_rows.append((k, v))
        for k, v in design_requirement_fields.items():
            profile_rows.append((k, v))
        for k, aliases in result_field_aliases.items():
            profile_rows.append((k, _profile_result(aliases)))
        plan.extend(profile_rows)

    return [(k, v) for k, v in plan if str(v).strip()]


def _replace_first_plain_text(xml_text: str, label: str, value: str) -> str:
    if not value:
        return xml_text
    pattern = re.escape(label) + r'([^<]{0,120})'
    repl = lambda m: f"{label}{escape(value)}"
    return re.sub(pattern, repl, xml_text, count=1)


def _replace_all_plain_text(xml_text: str, label: str, value: str, max_count: int = 3) -> str:
    if not value:
        return xml_text
    pattern = re.escape(label) + r'([^<]{0,120})'
    repl = lambda m: f"{label}{escape(value)}"
    return re.sub(pattern, repl, xml_text, count=max_count)


def _replace_result_table_cell(xml_text: str, row_label: str, value: str, result_col: int = None) -> str:
    """在结论表中，根据行首列的 row_label 关键字定位行，将 value 写入“检测结果”列。
    只操作包含'标准要求'和'检测结果'表头的表格（结论表），不影响其他表格。
    若未显式提供 result_col，则自动定位表头中第一个“检测结果”列索引。
    """
    # 清洗前端 result 字段中的判定符号
    if value:
        import re as _re
        value = _re.sub(r'[\s]*[✅❌⚠️✓✗☑☒]+[\s]*$', '', value).strip()
    if not value:
        return xml_text
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
    replaced = False
    for tbl_m in tbl_pattern.finditer(xml_text):
        tbl = tbl_m.group(0)
        tbl_text = ''.join(text_pattern.findall(tbl))
        if ('标准要求' not in tbl_text and '标准（设计）要求' not in tbl_text) or '检测结果' not in tbl_text:
            continue
        rows = row_pattern.findall(tbl)
        target_col = result_col
        if target_col is None:
            header_row = None
            for row in rows:
                row_text = ''.join(text_pattern.findall(row))
                if '检测结果' in row_text and ('标准要求' in row_text or '标准（设计）要求' in row_text):
                    header_row = row
                    break
            if header_row is None:
                continue
            header_cells = cell_pattern.findall(header_row)
            for idx, cell in enumerate(header_cells):
                cell_text = ''.join(text_pattern.findall(cell)).strip()
                if '检测结果' in cell_text:
                    target_col = idx
                    break
        if target_col is None:
            continue
        for row in rows:
            cells = cell_pattern.findall(row)
            if len(cells) <= target_col:
                continue
            first_cell_text = ''.join(text_pattern.findall(cells[0])).strip()
            if row_label not in first_cell_text:
                continue
            target_cell = cells[target_col]
            t_matches = list(text_pattern.finditer(target_cell))
            if t_matches:
                last_t = t_matches[-1]
                new_cell = target_cell[:last_t.start(1)] + escape(value) + target_cell[last_t.end(1):]
            else:
                insert_pos = target_cell.rfind('</w:tc>')
                if insert_pos < 0:
                    continue
                run_xml = f'<w:r><w:t>{escape(value)}</w:t></w:r></w:p>'
                p_close = target_cell.rfind('</w:p>')
                if p_close >= 0:
                    new_cell = target_cell[:p_close] + run_xml
                    remaining = target_cell[p_close + 6:]
                    new_cell += remaining
                else:
                    new_cell = target_cell[:insert_pos] + f'<w:p>{run_xml}</w:p>' + target_cell[insert_pos:]
            new_row = row.replace(target_cell, new_row := row.replace(target_cell, new_cell, 1), 1) if False else row.replace(target_cell, new_cell, 1)
            new_tbl = tbl.replace(row, new_row, 1)
            xml_text = xml_text[:tbl_m.start()] + new_tbl + xml_text[tbl_m.end():]
            replaced = True
            break
        if replaced:
            break
    return xml_text


def _replace_result_table_cell_by_row_index(xml_text: str, table_match_text: str, row_index: int, value: str, result_col: int) -> str:
    """在指定结论表中，按真实 XML 行号 + cell 序号写“检测结果”。用于 operating_room 这类合并单元格复杂模板。"""
    if value:
        import re as _re
        value = _re.sub(r'[\s]*[✅❌⚠️✓✗☑☒]+[\s]*$', '', str(value)).strip()
    if not value:
        return xml_text
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
    for tbl_m in tbl_pattern.finditer(xml_text):
        tbl = tbl_m.group(0)
        tbl_text = ''.join(text_pattern.findall(tbl))
        if table_match_text not in tbl_text or '单项结论' not in tbl_text or '检测结果' not in tbl_text:
            continue
        rows = row_pattern.findall(tbl)
        if row_index >= len(rows):
            continue
        row = rows[row_index]
        cells = cell_pattern.findall(row)
        if result_col >= len(cells):
            continue
        target_cell = cells[result_col]
        t_matches = list(text_pattern.finditer(target_cell))
        if t_matches:
            last_t = t_matches[-1]
            new_cell = target_cell[:last_t.start(1)] + escape(value) + target_cell[last_t.end(1):]
        else:
            insert_pos = target_cell.rfind('</w:tc>')
            if insert_pos < 0:
                return xml_text
            run_xml = f'<w:r><w:t>{escape(value)}</w:t></w:r></w:p>'
            p_close = target_cell.rfind('</w:p>')
            if p_close >= 0:
                new_cell = target_cell[:p_close] + run_xml + target_cell[p_close + 6:]
            else:
                new_cell = target_cell[:insert_pos] + f'<w:p>{run_xml}</w:p>' + target_cell[insert_pos:]
        new_row = row.replace(target_cell, new_cell, 1)
        new_tbl = tbl.replace(row, new_row, 1)
        return xml_text[:tbl_m.start()] + new_tbl + xml_text[tbl_m.end():]
    return xml_text


def _normalize_conclusion_text(value: str) -> str:
    if value is None:
        return ''
    text = str(value).strip()
    if not text:
        return ''
    import re as _re
    # 先检测原始文本中是否包含 emoji 判定符号，用于后续推断
    has_pass_emoji = bool(_re.search(r'[✅✓☑]', text))
    has_fail_emoji = bool(_re.search(r'[❌✗☒]', text))
    # 剥离 emoji
    text = _re.sub(r'[\s]*[✅❌⚠️✓✗☑☒]+[\s]*', '', text).strip()
    mapping = {
        '符合要求': '合格',
        '满足要求': '合格',
        '通过': '合格',
        'pass': '合格',
        'ok': '合格',
        '合格': '合格',
        '不符合要求': '不合格',
        '不满足要求': '不合格',
        '未通过': '不合格',
        'fail': '不合格',
        'ng': '不合格',
        '不合格': '不合格',
    }
    lowered = text.lower()
    if lowered in mapping:
        return mapping[lowered]
    if text in mapping:
        return mapping[text]
    # 如果文本中包含“全部符合”“均符合”“合格”等关键词
    if any(kw in text for kw in ['全部符合', '均符合', '合格', '符合要求', '满足要求', '通过']):
        return '合格'
    if any(kw in text for kw in ['不符合', '不合格', '不满足', '未通过', '超标']):
        return '不合格'
    # 如果原始文本含有 emoji 判定符号，则根据 emoji 推断
    if has_fail_emoji:
        return '不合格'
    if has_pass_emoji:
        return '合格'
    return ''


def _replace_conclusion_table_cell(xml_text: str, row_label: str, value: str, conclusion_col=None) -> str:
    """在结论表中，根据行首列的 row_label 关键字定位行，将规范化后的结论写入“单项结论”列。"""
    value = _normalize_conclusion_text(value)
    if not value:
        return xml_text
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
    replaced = False
    for tbl_m in tbl_pattern.finditer(xml_text):
        tbl = tbl_m.group(0)
        tbl_text = ''.join(text_pattern.findall(tbl))
        if ('标准要求' not in tbl_text and '标准（设计）要求' not in tbl_text) or '检测结果' not in tbl_text or '单项结论' not in tbl_text:
            continue
        rows = row_pattern.findall(tbl)
        target_col = conclusion_col
        if target_col is None:
            header_row = None
            for row in rows:
                row_text = ''.join(text_pattern.findall(row))
                if '单项结论' in row_text and '检测结果' in row_text:
                    header_row = row
                    break
            if header_row is None:
                continue
            header_cells = cell_pattern.findall(header_row)
            for idx, cell in enumerate(header_cells):
                cell_text = ''.join(text_pattern.findall(cell)).strip()
                if '单项结论' in cell_text:
                    target_col = idx
                    break
        if target_col is None:
            continue
        for row in rows:
            cells = cell_pattern.findall(row)
            if len(cells) <= target_col:
                continue
            first_cell_text = ''.join(text_pattern.findall(cells[0])).strip()
            if row_label not in first_cell_text:
                continue
            target_cell = cells[target_col]
            t_matches = list(text_pattern.finditer(target_cell))
            if t_matches:
                last_t = t_matches[-1]
                new_cell = target_cell[:last_t.start(1)] + escape(value) + target_cell[last_t.end(1):]
            else:
                insert_pos = target_cell.rfind('</w:tc>')
                if insert_pos < 0:
                    continue
                run_xml = f'<w:r><w:t>{escape(value)}</w:t></w:r></w:p>'
                p_close = target_cell.rfind('</w:p>')
                if p_close >= 0:
                    new_cell = target_cell[:p_close] + run_xml + target_cell[p_close + 6:]
                else:
                    new_cell = target_cell[:insert_pos] + f'<w:p>{run_xml}</w:p>' + target_cell[insert_pos:]
            new_row = row.replace(target_cell, new_cell, 1)
            new_tbl = tbl.replace(row, new_row, 1)
            xml_text = xml_text[:tbl_m.start()] + new_tbl + xml_text[tbl_m.end():]
            replaced = True
            break
        if replaced:
            break
    return xml_text


def _replace_conclusion_table_cell_by_row_index(xml_text: str, table_match_text: str, row_index: int, value: str, conclusion_col: int) -> str:
    """在指定结论表中，按真实 XML 行号 + cell 序号写“单项结论”。"""
    value = _normalize_conclusion_text(value)
    if not value:
        return xml_text
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
    for tbl_m in tbl_pattern.finditer(xml_text):
        tbl = tbl_m.group(0)
        tbl_text = ''.join(text_pattern.findall(tbl))
        if table_match_text not in tbl_text or '单项结论' not in tbl_text or '检测结果' not in tbl_text:
            continue
        rows = row_pattern.findall(tbl)
        if row_index >= len(rows):
            continue
        row = rows[row_index]
        cells = cell_pattern.findall(row)
        if conclusion_col >= len(cells):
            continue
        target_cell = cells[conclusion_col]
        t_matches = list(text_pattern.finditer(target_cell))
        if t_matches:
            last_t = t_matches[-1]
            new_cell = target_cell[:last_t.start(1)] + escape(value) + target_cell[last_t.end(1):]
        else:
            insert_pos = target_cell.rfind('</w:tc>')
            if insert_pos < 0:
                return xml_text
            run_xml = f'<w:r><w:t>{escape(value)}</w:t></w:r></w:p>'
            p_close = target_cell.rfind('</w:p>')
            if p_close >= 0:
                new_cell = target_cell[:p_close] + run_xml + target_cell[p_close + 6:]
            else:
                new_cell = target_cell[:insert_pos] + f'<w:p>{run_xml}</w:p>' + target_cell[insert_pos:]
        new_row = row.replace(target_cell, new_cell, 1)
        new_tbl = tbl.replace(row, new_row, 1)
        return xml_text[:tbl_m.start()] + new_tbl + xml_text[tbl_m.end():]
    return xml_text


def _replace_cover_label_value(xml_text: str, label: str, value: str, cover_window: int = 20000) -> str:
    if not value:
        return xml_text
    head = xml_text[:cover_window]
    tail = xml_text[cover_window:]
    pattern = re.compile(
        rf'({re.escape(label)}</w:t></w:r><w:r><w:rPr>.*?<w:u w:val="single".*?</w:rPr><w:t(?: xml:space="preserve")?>)(.*?)(</w:t>)',
        re.S
    )
    head = pattern.sub(lambda m: m.group(1) + escape(value) + m.group(3), head, count=1)
    return head + tail


def _replace_cover_split_label_value(xml_text: str, split_label_chars: list, value: str, cover_window: int = 20000) -> str:
    if not value or not split_label_chars:
        return xml_text
    head = xml_text[:cover_window]
    tail = xml_text[cover_window:]
    label_pattern = ''.join([rf'<w:r[^>]*>.*?<w:t>{re.escape(ch)}</w:t>.*?</w:r>' for ch in split_label_chars])
    pattern = re.compile(rf'({label_pattern}<w:r[^>]*>.*?<w:t>：</w:t>.*?</w:r><w:r[^>]*>.*?<w:u w:val="single".*?</w:rPr><w:t(?: xml:space="preserve")?>)(.*?)(</w:t>)', re.S)
    head = pattern.sub(lambda m: m.group(1) + escape(value) + m.group(3), head, count=1)
    return head + tail



def _replace_cover_paragraph_after_label(xml_text: str, label_chars: list, value: str, cover_window: int = 20000) -> str:
    if not value or not label_chars:
        return xml_text
    head = xml_text[:cover_window]
    tail = xml_text[cover_window:]
    label_pattern = ''.join([rf'<w:r[^>]*>.*?<w:t>{re.escape(ch)}</w:t>.*?</w:r>' for ch in label_chars])
    # 标签后可能直接跟冒号 run，再跟 1~3 个占位 run；保留版式，仅替换第一个占位 w:t 文本
    pattern = re.compile(rf'({label_pattern}(?:<w:r[^>]*>.*?<w:t>[:：]</w:t>.*?</w:r>)?)(.*?)(<w:t(?: xml:space="preserve")?>)(.*?)(</w:t>)(.*?</w:p>)', re.S)
    def repl(m):
        prefix, middle, t_open, _old, t_close, suffix = m.groups()
        if 'w:u w:val="single"' not in middle + suffix and 'w:color w:val="FFFFFF"' not in middle + suffix:
            return m.group(0)
        return prefix + middle + t_open + escape(value) + t_close + suffix
    head = pattern.sub(repl, head, count=1)
    return head + tail


def _extract_cover_text_tokens(xml_head: str) -> list:
    """提取封面区域的文本 token 列表，排除 XML 碎片误匹配"""
    tokens = []
    pattern = re.compile(r'(<w:t)((?:\s+xml:space="preserve")?)>(.*?)</w:t>', re.S)
    for m in pattern.finditer(xml_head):
        content = m.group(3)
        if content.startswith('<'):
            continue
        tokens.append({
            'content': content,
            'start': m.start(),
            'end': m.end(),
            'attrs': m.group(2) or '',
            'full_match': m.group(0),
        })
    return tokens


def _replace_cover_field(xml_text: str, label_text: str, value: str, cover_window: int = 25000) -> str:
    """通用封面字段替换：自动处理 run 分裂、冒号分离、值占位缺失等各种模板结构"""
    if not value or not label_text:
        return xml_text
    head = xml_text[:cover_window]
    tail = xml_text[cover_window:]
    tokens = _extract_cover_text_tokens(head)
    # 在 token 序列中搜索 label
    found_label_end = None
    for ti in range(len(tokens)):
        remaining = label_text
        tj = ti
        while remaining and tj < len(tokens):
            content = tokens[tj]['content']
            if remaining.startswith(content):
                remaining = remaining[len(content):]
                tj += 1
            elif content.startswith(remaining):
                remaining = ''
                found_label_end = tj
                break
            else:
                break
        if not remaining:
            if found_label_end is None:
                found_label_end = tj - 1
            break
    if found_label_end is None:
        return xml_text
    # 从 label 结束位置往后找冒号
    colon_idx = None
    for ti in range(found_label_end, min(found_label_end + 4, len(tokens))):
        content = tokens[ti]['content']
        if '：' in content or ':' in content:
            colon_idx = ti
            break
    if colon_idx is None:
        return xml_text
    # 冒号后找第一个可替换的值 token（同段落内）
    for ti in range(colon_idx + 1, min(colon_idx + 6, len(tokens))):
        content = tokens[ti]['content']
        between = head[tokens[colon_idx]['end']:tokens[ti]['start']]
        if '</w:p>' in between:
            break
        if not content.strip() or all(c in '。，.、 \u3000' for c in content.strip()):
            old = tokens[ti]['full_match']
            new = f'<w:t{tokens[ti]["attrs"]}>{escape(value)}</w:t>'
            head = head[:tokens[ti]['start']] + new + head[tokens[ti]['end']:]
            return head + tail
    # 冒号后面没有值 token，在冒号 run 结束后插入新 run
    colon_run_end = head.find('</w:r>', tokens[colon_idx]['end'])
    if colon_run_end > 0:
        colon_run_end += 6
        new_run = ('<w:r><w:rPr><w:rFonts w:ascii="Arial" w:hAnsi="Arial" w:eastAsia="宋体" w:cs="Arial"/>'
                   '<w:b/><w:bCs/><w:sz w:val="28"/><w:szCs w:val="28"/>'
                   '<w:u w:val="single"/></w:rPr><w:t>' + escape(value) + '</w:t></w:r>')
        head = head[:colon_run_end] + new_run + head[colon_run_end:]
        return head + tail
    return xml_text




def _is_device_cover_template(type_id: str) -> bool:
    return str(type_id or '').strip() in {'clean_bench', 'bsc', 'ivc'}


def _cleanup_placeholder_noise(xml_text: str) -> str:
    replacements = [
        ('项目名称： 。', '项目名称：'),
        ('项目名称：。', '项目名称：'),
        ('检测对象： 。', '检测对象：'),
        ('检测对象： 。，。', '检测对象：'),
        ('检测对象：。，。', '检测对象：'),
        ('检测类别： .', '检测类别：'),
        ('检测类别：.', '检测类别：'),
        ('委托单位：。，', '委托单位：'),
        ('委托单位：，', '委托单位：'),
        ('委托单位：。', '委托单位：'),
    ]
    for old, new in replacements:
        xml_text = xml_text.replace(old, new)
    xml_text = re.sub(r'(<w:t[^>]*>项目名称：</w:t>)(?:<w:t[^>]*>\s*[。.]\s*</w:t>)+', r'\1', xml_text)
    xml_text = re.sub(r'(<w:t[^>]*>检测类别：</w:t>)(?:<w:t[^>]*>\s*[。.,，]\s*</w:t>)+', r'\1', xml_text)
    xml_text = re.sub(r'(<w:t[^>]*>委托单位：</w:t>)(?:<w:t[^>]*>\s*[。.,，]\s*</w:t>)+', r'\1', xml_text)
    return xml_text


def _replace_table_value_by_left_label(xml_text: str, label: str, value: str, value_cell_offset: int = 1, max_hits=None, table_must_contain: str = None) -> str:
    if not value:
        return xml_text
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t[^>]*>(.*?)</w:t>', re.S)

    def _cell_plain(cell_xml: str) -> str:
        texts = text_pattern.findall(cell_xml)
        plain = ''.join(
            t.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()
            for t in texts
        )
        return plain.strip()

    def _cell_contains_label(cell_xml: str, expected_label: str) -> bool:
        cell_text = _cell_plain(cell_xml).replace(' ', '').replace('\n', '').replace('\t', '')
        label_text = expected_label.replace(' ', '').replace('\n', '').replace('\t', '')
        return label_text in cell_text

    def _replace_cell_content(cell_xml: str, new_text: str) -> str:
        paragraphs = list(re.finditer(r'<w:p\b.*?</w:p>', cell_xml, re.S))
        if not paragraphs:
            return cell_xml
        first = paragraphs[0]
        last = paragraphs[-1]
        return cell_xml[:first.start()] + _para_xml(new_text) + cell_xml[last.end():]

    changed = False
    hit_count = 0
    # 如果指定 table_must_contain，则只在包含该文本的表格中搜索
    if table_must_contain:
        for tbl_m in tbl_pattern.finditer(xml_text):
            tbl = tbl_m.group(0)
            tbl_text = ''.join(text_pattern.findall(tbl))
            if table_must_contain not in tbl_text:
                continue
            rows = row_pattern.findall(tbl)
            new_tbl = tbl
            for row_xml in rows:
                cells = cell_pattern.findall(row_xml)
                if not cells:
                    continue
                target_index = None
                for idx, cell in enumerate(cells):
                    if _cell_contains_label(cell, label):
                        target_index = idx + value_cell_offset
                        break
                if target_index is None or target_index >= len(cells):
                    continue
                old_cell = cells[target_index]
                new_cell = _replace_cell_content(old_cell, value)
                if new_cell == old_cell:
                    continue
                new_row = row_xml.replace(old_cell, new_cell, 1)
                new_tbl = new_tbl.replace(row_xml, new_row, 1)
                changed = True
                hit_count += 1
                if max_hits is not None and hit_count >= max_hits:
                    break
            if changed:
                xml_text = xml_text[:tbl_m.start()] + new_tbl + xml_text[tbl_m.end():]
            break
        return xml_text
    rows = row_pattern.findall(xml_text)
    for row_xml in rows:
        cells = cell_pattern.findall(row_xml)
        if not cells:
            continue
        target_index = None
        for idx, cell in enumerate(cells):
            if _cell_contains_label(cell, label):
                target_index = idx + value_cell_offset
                break
        if target_index is None or target_index >= len(cells):
            continue
        old_cell = cells[target_index]
        new_cell = _replace_cell_content(old_cell, value)
        if new_cell == old_cell:
            continue
        new_row = row_xml.replace(old_cell, new_cell, 1)
        xml_text = xml_text.replace(row_xml, new_row, 1)
        changed = True
        hit_count += 1
        if max_hits is not None and hit_count >= max_hits:
            break
    return xml_text


def _replace_table_row_cells_by_anchor(xml_text: str, anchor_text: str, replacements_by_index: Dict[int, str]) -> str:
    if not replacements_by_index:
        return xml_text
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t[^>]*>(.*?)</w:t>', re.S)

    def _cell_plain(cell_xml: str) -> str:
        texts = text_pattern.findall(cell_xml)
        return ''.join(
            t.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()
            for t in texts
        ).strip()

    def _replace_cell_content(cell_xml: str, new_text: str) -> str:
        paragraphs = list(re.finditer(r'<w:p\b.*?</w:p>', cell_xml, re.S))
        if not paragraphs:
            return cell_xml
        first = paragraphs[0]
        last = paragraphs[-1]
        return cell_xml[:first.start()] + _para_xml(new_text) + cell_xml[last.end():]

    for row_xml in row_pattern.findall(xml_text):
        cells = cell_pattern.findall(row_xml)
        if not cells:
            continue
        joined = ' '.join(_cell_plain(c) for c in cells)
        if anchor_text not in joined:
            continue
        new_row = row_xml
        current_cells = cell_pattern.findall(new_row)
        for idx, value in replacements_by_index.items():
            if value is None or str(value).strip() == '':
                continue
            if idx < 0 or idx >= len(current_cells):
                continue
            old_cell = current_cells[idx]
            new_cell = _replace_cell_content(old_cell, str(value))
            new_row = new_row.replace(old_cell, new_cell, 1)
            current_cells = cell_pattern.findall(new_row)
        return xml_text.replace(row_xml, new_row, 1)
    return xml_text


def _replace_table_row_cells_by_anchor_index(xml_text: str, anchor_text: str, row_match_index: int, replacements_by_index: Dict[int, str], debug_notes: List[Dict[str, Any]] = None, table_match_index: int = None) -> str:
    if not replacements_by_index:
        return xml_text
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t[^>]*>(.*?)</w:t>', re.S)

    def _cell_plain(cell_xml: str) -> str:
        texts = text_pattern.findall(cell_xml)
        return ''.join(
            t.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()
            for t in texts
        ).strip()

    def _force_set_cell_content(cell_xml: str, new_text: str) -> str:
        tcpr = re.search(r'(<w:tcPr\b.*?</w:tcPr>)', cell_xml, re.S)
        if tcpr:
            return cell_xml[:tcpr.end()] + _para_xml(new_text) + cell_xml[tcpr.end():]
        inner = re.match(r'(<w:tc\b[^>]*>)(.*?)(</w:tc>)', cell_xml, re.S)
        if inner:
            return inner.group(1) + _para_xml(new_text) + inner.group(3)
        return cell_xml

    matched_tables = []
    for table_abs_index, table_xml in enumerate(tbl_pattern.findall(xml_text)):
        table_rows = []
        table_meta = []
        for row_abs_index, row_xml in enumerate(row_pattern.findall(table_xml)):
            cells = cell_pattern.findall(row_xml)
            if not cells:
                continue
            cell_texts = [_cell_plain(c) for c in cells]
            joined = ' '.join(cell_texts)
            if anchor_text in joined:
                table_rows.append(row_xml)
                table_meta.append({
                    'table_absolute_index': table_abs_index,
                    'row_absolute_index_in_table': row_abs_index,
                    'joined': joined[:300],
                    'cell_count': len(cells),
                    'cell_texts': cell_texts,
                })
        if table_rows:
            matched_tables.append((table_xml, table_rows, table_meta))

    if not matched_tables:
        _append_debug_note(debug_notes, 'anchor-index-miss', {
            'anchor_text': anchor_text,
            'row_match_index': row_match_index,
            'table_match_index': table_match_index,
            'matched_table_count': 0,
            'replacements_by_index': replacements_by_index,
        })
        return xml_text

    selected_table_index = 0 if table_match_index is None else table_match_index
    if selected_table_index < 0 or selected_table_index >= len(matched_tables):
        _append_debug_note(debug_notes, 'anchor-index-miss', {
            'anchor_text': anchor_text,
            'row_match_index': row_match_index,
            'table_match_index': table_match_index,
            'matched_table_count': len(matched_tables),
            'error': 'table_match_index out of range',
            'replacements_by_index': replacements_by_index,
        })
        return xml_text

    table_xml, matched_rows, matched_meta = matched_tables[selected_table_index]
    if row_match_index < 0 or row_match_index >= len(matched_rows):
        _append_debug_note(debug_notes, 'anchor-index-miss', {
            'anchor_text': anchor_text,
            'row_match_index': row_match_index,
            'table_match_index': table_match_index,
            'matched_count': len(matched_rows),
            'matched_rows': matched_meta[:8],
            'replacements_by_index': replacements_by_index,
        })
        return xml_text
    row_xml = matched_rows[row_match_index]
    row_meta = matched_meta[row_match_index]
    current_cells = cell_pattern.findall(row_xml)
    replacement_results = []
    rebuilt_cells = list(current_cells)
    row_changed = False
    for idx, value in replacements_by_index.items():
        if value is None or str(value).strip() == '':
            replacement_results.append({'cell_index': idx, 'skipped': 'empty-value'})
            continue
        if idx < 0 or idx >= len(rebuilt_cells):
            replacement_results.append({'cell_index': idx, 'skipped': 'out-of-range', 'cell_count': len(rebuilt_cells)})
            continue
        old_cell = rebuilt_cells[idx]
        before_text = _cell_plain(old_cell)
        new_cell = _force_set_cell_content(old_cell, str(value))
        after_text = _cell_plain(new_cell)
        replaced = new_cell != old_cell
        if replaced:
            rebuilt_cells[idx] = new_cell
            row_changed = True
        replacement_results.append({
            'cell_index': idx,
            'value': str(value),
            'before_text': before_text,
            'after_text': after_text,
            'replaced': replaced,
        })
    new_row = row_xml
    if row_changed:
        cell_iter = list(cell_pattern.finditer(row_xml))
        if len(cell_iter) == len(rebuilt_cells):
            parts = []
            cursor = 0
            for i, m in enumerate(cell_iter):
                parts.append(row_xml[cursor:m.start()])
                parts.append(rebuilt_cells[i])
                cursor = m.end()
            parts.append(row_xml[cursor:])
            new_row = ''.join(parts)
    changed = new_row != row_xml
    _append_debug_note(debug_notes, 'anchor-index-apply', {
        'anchor_text': anchor_text,
        'row_match_index': row_match_index,
        'table_match_index': table_match_index,
        'matched_count': len(matched_rows),
        'selected_row': row_meta,
        'replacement_results': replacement_results,
        'changed': changed,
    })
    if not changed:
        return xml_text
    new_table = table_xml.replace(row_xml, new_row, 1)
    return xml_text.replace(table_xml, new_table, 1)


def _replace_table_cell_by_table_and_row(xml_text: str, table_index: int, row_index: int, replacements_by_index: Dict[int, str], debug_notes: List[Dict[str, Any]] = None, allow_blank: bool = False) -> str:
    if not replacements_by_index:
        return xml_text
    tbl_pattern = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pattern = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pattern = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    text_pattern = re.compile(r'<w:t[^>]*>(.*?)</w:t>', re.S)

    def _cell_plain(cell_xml: str) -> str:
        texts = text_pattern.findall(cell_xml)
        return ''.join(
            t.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&').strip()
            for t in texts
        ).strip()

    def _force_set_cell_content(cell_xml: str, new_text: str) -> str:
        tcpr = re.search(r'(<w:tcPr\b.*?</w:tcPr>)', cell_xml, re.S)
        if tcpr:
            inner = cell_xml[tcpr.end():]
            return cell_xml[:tcpr.end()] + _para_xml(new_text) + re.sub(r'<w:p\b.*?</w:p>', '', inner, flags=re.S)
        inner = re.match(r'(<w:tc\b[^>]*>)(.*?)(</w:tc>)', cell_xml, re.S)
        if inner:
            return inner.group(1) + _para_xml(new_text) + inner.group(3)
        return cell_xml

    tables = tbl_pattern.findall(xml_text)
    if table_index < 0 or table_index >= len(tables):
        _append_debug_note(debug_notes, 'table-row-direct-miss', {
            'table_index': table_index,
            'row_index': row_index,
            'error': 'table_index out of range',
        })
        return xml_text
    table_xml = tables[table_index]
    rows = row_pattern.findall(table_xml)
    if row_index < 0 or row_index >= len(rows):
        _append_debug_note(debug_notes, 'table-row-direct-miss', {
            'table_index': table_index,
            'row_index': row_index,
            'error': 'row_index out of range',
        })
        return xml_text
    row_xml = rows[row_index]
    cells = cell_pattern.findall(row_xml)
    rebuilt_cells = list(cells)
    row_changed = False
    replacement_results = []
    for idx, value in replacements_by_index.items():
        if value is None or (not allow_blank and str(value).strip() == ''):
            replacement_results.append({'cell_index': idx, 'skipped': 'empty-value'})
            continue
        if idx < 0 or idx >= len(rebuilt_cells):
            replacement_results.append({'cell_index': idx, 'skipped': 'out-of-range', 'cell_count': len(rebuilt_cells)})
            continue
        old_cell = rebuilt_cells[idx]
        before_text = _cell_plain(old_cell)
        new_cell = _force_set_cell_content(old_cell, str(value))
        after_text = _cell_plain(new_cell)
        replaced = new_cell != old_cell
        if replaced:
            rebuilt_cells[idx] = new_cell
            row_changed = True
        replacement_results.append({
            'cell_index': idx,
            'value': str(value),
            'before_text': before_text,
            'after_text': after_text,
            'replaced': replaced,
        })
    new_row = row_xml
    if row_changed:
        cell_iter = list(cell_pattern.finditer(row_xml))
        if len(cell_iter) == len(rebuilt_cells):
            parts = []
            cursor = 0
            for i, m in enumerate(cell_iter):
                parts.append(row_xml[cursor:m.start()])
                parts.append(rebuilt_cells[i])
                cursor = m.end()
            parts.append(row_xml[cursor:])
            new_row = ''.join(parts)
    changed = new_row != row_xml
    _append_debug_note(debug_notes, 'table-row-direct-apply', {
        'table_index': table_index,
        'row_index': row_index,
        'replacement_results': replacement_results,
        'changed': changed,
    })
    if not changed:
        return xml_text
    new_table = table_xml.replace(row_xml, new_row, 1)
    return xml_text.replace(table_xml, new_table, 1)


def build_template_filled_docx(export_payload: Dict[str, Any], output_path: str) -> str:
    template_resource = export_payload.get('template_resource', {}) or {}
    template_path = template_resource.get('template_path', '') or ''
    if not template_path or not Path(template_path).exists():
        return ''

    fill_plan = _build_placeholder_fill_plan(export_payload)
    replacements = {k: v for k, v in fill_plan}
    # emoji 清洗已在 get_param_value / _strip_emoji 中处理，
    # _normalize_conclusion_text 需要保留 emoji 来推断合格/不合格，不再做全局清洗。
    # 清洗常见单位后缀（仅对数值型参数，不动文本型如"符合要求"）
    import re as _re_clean
    _unit_pat = _re_clean.compile(r'^([\-]?[\d.]+)\s*(?:次/h|Pa|Pa\b|℃|dB\(?A?\)?|lx|%|m/s|cfu)[\s]*$')
    for _ck, _cv in replacements.items():
        if isinstance(_cv, str):
            _um = _unit_pat.match(_cv)
            if _um:
                replacements[_ck] = _um.group(1)
    room = export_payload.get('room', {}) or {}
    type_id = str(room.get('type_id', '') or '')
    debug_notes: List[Dict[str, Any]] = [] if _debug_enabled() else None
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    with ZipFile(template_path, 'r') as src:
        members = src.namelist()
        document_xml = src.read('word/document.xml').decode('utf-8', errors='ignore')
        single_replace_labels = []
        multi_replace_labels = [] if type_id in {'operating_room', 'bsl', 'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop', 'negative_pressure', 'animal_room'} else ['检测区域', '受检区域']
        table_cell_replace_map = {
            '委托单位': 1,
            '项目地址': 1,
            '联系方式': 1,
            '检测日期': 1,
            '检测状态': 1,
            '气象条件': 1,
            '判定依据': 1,
            '判定标准': 1,
            '检测依据': 1,
            '检测结论': 1,
            '项目名称': 1,
            '样品名称': 1,
            '生产厂家': 1,
            '产品类型': 1,
            '产品外尺寸': 1,
            '设备状态': 1,
            '产品内尺寸': 1,
            '内尺寸': 1,
            '检测类型': 1,
            '所在房间': 1,
            '检测环境': 1,
            '垂直气流平均风速': 1,
            '气流流型': 1,
            '送风高效过滤器检漏': 1,
            '名称：': 1,
            '设备名称': 1,
            '受检区域名称': 1,
            '区域': 1,
            '洁净度级别': 1,
            '级别': 1,
        }
        if replacements.get('设备状态') and replacements.get('产品内尺寸'):
            document_xml = _replace_table_value_by_left_label(document_xml, '设备状态', replacements.get('设备状态', ''), value_cell_offset=1)
            document_xml = _replace_table_value_by_left_label(document_xml, '产品内尺寸', replacements.get('产品内尺寸', ''), value_cell_offset=1)
        
        for label in single_replace_labels:
            document_xml = _replace_first_plain_text(document_xml, label, replacements.get(label, ''))
        for label in multi_replace_labels:
            document_xml = _replace_all_plain_text(document_xml, label, replacements.get(label, ''))
        for label, offset in table_cell_replace_map.items():
            if label in {'设备状态', '产品内尺寸'}:
                continue
            if type_id in ('gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop') and label in {'洁净度级别', '级别', '洁净度'}:
                continue
            document_xml = _replace_table_value_by_left_label(document_xml, label, replacements.get(label, ''), value_cell_offset=offset, table_must_contain='委托单位')
        document_xml = _replace_table_value_by_left_label(document_xml, '设备状态', replacements.get('设备状态', ''), value_cell_offset=1)
        document_xml = _replace_table_value_by_left_label(document_xml, '产品内尺寸', replacements.get('产品内尺寸', ''), value_cell_offset=1)
        if replacements.get('名称：') or replacements.get('样品名称') or replacements.get('项目名称'):
            name_value = replacements.get('受检区域名称', '') or replacements.get('房间名称', '') or replacements.get('样品名称', '')
            if _is_device_cover_template(type_id):
                name_value = replacements.get('项目名称', '') or name_value
            document_xml = _replace_table_value_by_left_label(document_xml, '名称：', name_value, value_cell_offset=1)
        if (replacements.get('设备名称') or replacements.get('样品名称')) and _is_device_cover_template(type_id):
            document_xml = _replace_table_value_by_left_label(document_xml, '设备名称', replacements.get('样品名称', ''), value_cell_offset=1, table_must_contain='委托单位')
        if _is_device_cover_template(type_id) and replacements.get('委托单位'):
            document_xml = _replace_table_value_by_left_label(document_xml, '委托单位', replacements.get('委托单位', ''), value_cell_offset=1, max_hits=1)
        if replacements.get('受检区域名称') or replacements.get('房间名称'):
            room_name_value = replacements.get('受检区域名称', '') or replacements.get('房间名称', '')
            if room_name_value:
                document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '受检区域名称', 1, {
                    1: room_name_value,
                }, debug_notes=debug_notes)
                document_xml = _replace_table_value_by_left_label(document_xml, '受检区域', room_name_value, value_cell_offset=1)
                document_xml = _replace_first_plain_text(document_xml, '受检区域名称', room_name_value)
                document_xml = _replace_first_plain_text(document_xml, '受检区域', room_name_value)
                document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '本次委托检验项目为', 1, {
                    0: f'本次委托检验项目为{replacements.get("项目名称","")}，项目地点位于{replacements.get("项目地址","")}。本次检测区域{replacements.get("检测区域","")}。'
                }, debug_notes=debug_notes)
        if replacements.get('项目概述'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '项目概述', 0, {
                1: replacements.get('项目概述', ''),
            }, debug_notes=debug_notes, table_match_index=0)
        # 气象条件已通过 table_cell_replace_map 统一填写，不再重复
        # if replacements.get('气象条件'):
        #     document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '气象条件', 0, {
        #         1: replacements.get('气象条件', ''),
        #     }, debug_notes=debug_notes, table_match_index=0)
        if type_id == 'bsl' and (replacements.get('洁净级别') or replacements.get('洁净等级')):
            level_value = replacements.get('洁净级别', '') or replacements.get('洁净等级', '')
            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, {
                5: level_value,
            }, debug_notes=debug_notes)
        if type_id == 'clean_function_room':
            _cf_std_ranges = {}
            try:
                _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _all_std = json.load(_sf)
                _candidate_stds = []
                for _s in room.get('judgement', []) or []:
                    if _s and _s not in _candidate_stds:
                        _candidate_stds.append(_s)
                for _s in room.get('basis', []) or []:
                    if _s and _s not in _candidate_stds:
                        _candidate_stds.append(_s)
                _clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
                for _std in _candidate_stds:
                    _obj = ((_all_std.get(_std) or {}).get('clean_function_room') or {})
                    _level = _obj.get(_clean_class_text) or {}
                    if isinstance(_level, dict) and _level:
                        _cf_std_ranges = dict(_level)
                        # 补缺：若主判定标准缺 floating 等字段，则从 basis 中后续标准回补
                        for _std2 in _candidate_stds:
                            _obj2 = ((_all_std.get(_std2) or {}).get('clean_function_room') or {})
                            _level2 = _obj2.get(_clean_class_text) or {}
                            if isinstance(_level2, dict):
                                for _k, _v in _level2.items():
                                    if _k not in _cf_std_ranges and _v:
                                        _cf_std_ranges[_k] = _v
                        break
            except Exception:
                _cf_std_ranges = {}
            # table 3 / row 0-1 fixed header info
            if replacements.get('检测日期') or replacements.get('洁净级别'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, {
                    3: replacements.get('检测日期', ''),
                    5: replacements.get('洁净级别', '') or replacements.get('洁净等级', ''),
                }, debug_notes=debug_notes, allow_blank=True)
            # 房间参数 S/V
            _room_length = str(room.get('length', '') or '').strip()
            _room_width = str(room.get('width', '') or '').strip()
            _room_height = str(room.get('height', '') or '').strip()
            try:
                _rl = float(_room_length) if _room_length else 0
                _rw = float(_room_width) if _room_width else 0
                _rh = float(_room_height) if _room_height else 0
            except (ValueError, TypeError):
                _rl = _rw = _rh = 0
            _area_str = str(round(_rl * _rw, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0) else ''
            _vol_str = str(round(_rl * _rw * _rh, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0 and _rh > 0) else ''
            if _area_str or _vol_str:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {
                    1: f'面积S（m²）={_area_str}          体积V（m³）={_vol_str}'
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('换气次数'):
                document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '换气次数', 0, {
                    2: str(((_cf_std_ranges.get('airchange') or {}).get('range', '') or '')),
                    3: replacements.get('换气次数', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'airchange', 'airchange_rate', '换气次数')),
                }, debug_notes=debug_notes, table_match_index=1)
            if replacements.get('静压差'):
                document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '静压差', 0, {
                    2: str(((_cf_std_ranges.get('pressure') or {}).get('range', '') or '')),
                    3: replacements.get('静压差', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'pressure', 'static_pressure_diff', '静压差')),
                }, debug_notes=debug_notes, table_match_index=1)
            if replacements.get('温度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, {
                    2: str(((_cf_std_ranges.get('temperature') or {}).get('range', '') or '')),
                    3: replacements.get('温度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'temperature', '温度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('相对湿度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, {
                    2: str(((_cf_std_ranges.get('humidity') or {}).get('range', '') or '')),
                    3: replacements.get('相对湿度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'humidity', 'relative_humidity', '相对湿度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('照度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, {
                    2: str(((_cf_std_ranges.get('illumination') or {}).get('range', '') or '')),
                    3: replacements.get('照度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'illumination_min', 'illumination', '照度', '平均照度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('噪声'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, {
                    2: str(((_cf_std_ranges.get('noise') or {}).get('range', '') or '')),
                    3: replacements.get('噪声', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'noise', '噪声')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('细菌浓度'):
                _settling_std = (_cf_std_ranges.get('settling') or {}).get('range', '') or ((_cf_std_ranges.get('bacteria') or {}).get('range', '') or '')
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 15, {
                    2: str(_settling_std),
                    3: replacements.get('细菌浓度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'bacteria', 'settle_bacteria', '细菌浓度（沉降法）')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('浮游菌（平均浓度）'):
                _floating_std = (_cf_std_ranges.get('floating') or {}).get('range', '') or ((_cf_std_ranges.get('settling') or {}).get('range', '') if not replacements.get('浮游菌（平均浓度）', '') else '') or ''
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 16, {
                    2: str(_floating_std),
                    3: replacements.get('浮游菌（平均浓度）', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'floating_bacteria', '浮游菌（平均浓度）', '浮游菌')),
                }, debug_notes=debug_notes, allow_blank=True)
            # 洁净度 4 行
            if replacements.get('洁净度级别') or replacements.get('悬浮粒子数/m³') or replacements.get('洁净度'):
                _pt_conclusion = _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'particle', '洁净度级别（悬浮粒子浓度）'))
                _particle_std = _cf_std_ranges.get('particle') or {}
                _range_all = str(_particle_std.get('range_05', '') or _particle_std.get('range', '') or '')
                _range_05 = _range_all
                _range_5 = str(_particle_std.get('range_5', '') or '')
                if _range_all and ',' in _range_all:
                    _parts = [x.strip() for x in _range_all.split(',') if x.strip()]
                    if len(_parts) >= 1:
                        _range_05 = _parts[0]
                    if len(_parts) >= 2 and not _range_5:
                        _range_5 = _parts[1]
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, {
                    1: replacements.get('洁净级别', '') or replacements.get('洁净度级别', ''),
                    2: _range_05,
                    3: replacements.get('洁净度级别', ''),
                    5: replacements.get('悬浮粒子数/m³', ''),
                    6: _pt_conclusion,
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('0.5μmUCL'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {
                    5: replacements.get('0.5μmUCL', ''),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('≥5μm'):
                _particle_std = _cf_std_ranges.get('particle') or {}
                _range_5 = str(_particle_std.get('range_5', '') or '')
                if not _range_5:
                    _range_all = str(_particle_std.get('range', '') or '')
                    if ',' in _range_all:
                        _parts = [x.strip() for x in _range_all.split(',') if x.strip()]
                        if len(_parts) >= 2:
                            _range_5 = _parts[1]
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, {
                    2: _range_5,
                    5: replacements.get('≥5μm', ''),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('5μmUCL'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {
                    5: replacements.get('5μmUCL', ''),
                }, debug_notes=debug_notes, allow_blank=True)
            # 检漏值/结论
            _hepa_result = get_param_result(build_param_map(room.get('params')), 'hepa_leak', '送风高效过滤器检漏')
            _hepa_item = get_param_item(build_param_map(room.get('params')), 'hepa_leak', '送风高效过滤器检漏')
            _hepa_objects = _hepa_item.get('objects', []) if isinstance(_hepa_item, dict) else []
            _hepa_value = str((_hepa_objects[0] or {}).get('value', '') if _hepa_objects else '')
            if _hepa_value:
                _hepa_conclusion = _normalize_conclusion_text(_hepa_result) or ('合格' if float(_hepa_value) <= 0.01 else '不合格')
                _hepa_std = str(((_cf_std_ranges.get('hepa_leak') or {}).get('range', '') or '≤0.01'))
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, {
                    2: _hepa_std,
                    3: _hepa_value,
                    4: _hepa_conclusion,
                }, debug_notes=debug_notes, allow_blank=True)
        elif type_id == 'negative_pressure':
            # --- Dynamic standards ---
            _np_std_ranges = {}
            try:
                _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _all_std = json.load(_sf)
                for _s in (room.get('judgement', []) or []) + (room.get('basis', []) or []):
                    _obj = ((_all_std.get(_s) or {}).get('negative_pressure') or {})
                    _level = _obj.get('_default') or {}
                    if isinstance(_level, dict) and _level:
                        for _pk, _pv in _level.items():
                            if _pk not in _np_std_ranges:
                                _np_std_ranges[_pk] = _pv
            except Exception:
                pass
            def _np_std(key):
                r = _np_std_ranges.get(key, {})
                return str(r.get('range', '') if isinstance(r, dict) else r or '')
            _np_pm = build_param_map(room.get('params'))
            def _np_concl(*keys):
                return _normalize_conclusion_text(get_param_result(_np_pm, *keys))

            # ROW 0: room name + date
            _r0 = {}
            _room_name = replacements.get('受检区域名称', '') or replacements.get('房间名称', '')
            if _room_name: _r0[1] = _room_name
            _det_date = replacements.get('检测日期', '')
            if _det_date: _r0[3] = _det_date
            if _r0: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, _r0, debug_notes=debug_notes)

            # ROW 1: S/V
            _length = str(room.get('length', '') or '')
            _width = str(room.get('width', '') or '')
            _height = str(room.get('height', '') or '')
            if _length and _width and _height:
                try:
                    _s = round(float(_length) * float(_width), 1)
                    _v = round(float(_length) * float(_width) * float(_height), 0)
                    _sv_text = f'S（m²）={_s}                 V（m³）={int(_v)}'
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {1: _sv_text}, debug_notes=debug_notes)
                except (ValueError, TypeError):
                    pass

            # ROW 3-12: all params with standard + value + conclusion
            _np_rows = [
                (3, '换气次数', '污染区换气次数', 'airchange', ('airchange', 'airchange_rate', 'air_change_rate')),
                (4, '排风口风速', '排风口风速', 'exhaust_speed', ('exhaust_speed', 'exhaust_velocity')),
                (5, '静压差', '静压差', 'pressure', ('static_pressure_diff', 'pressure_diff', 'pressure')),
                (7, '气流流向', '气流流向', 'airflow_direction', ('airflow_direction', 'airflow_pattern')),
                (8, '温度', '温度', 'temperature', ('temperature',)),
                (9, '相对湿度', '相对湿度', 'humidity', ('relative_humidity', 'humidity')),
                (10, '平均照度', '照度', 'illumination', ('illumination',)),
                (11, '噪声', '噪声', 'noise', ('noise',)),
                (12, '细菌浓度', '细菌浓度', 'bacteria', ('bacteria', 'settling_bacteria', 'settle_bacteria', 'settling')),
            ]
            for _ri, _label, _repl_key, _std_key, _concl_keys in _np_rows:
                _val = replacements.get(_repl_key, '') or replacements.get(_label, '')
                _std = _np_std(_std_key) or ''
                _concl = _np_concl(*_concl_keys)
                _row = {}
                if _std: _row[2] = _std
                if _val: _row[3] = _val
                if _concl: _row[4] = _concl
                if _row: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, _ri, _row, debug_notes=debug_notes)

            # ROW 6: 检漏
            _hl_val = replacements.get('送风高效过滤器检漏', '') or replacements.get('检漏', '')
            _hl_concl = _np_concl('hepa_leak')
            _r6 = {}
            if _hl_val: _r6[3] = _hl_val
            if _hl_concl: _r6[4] = _hl_concl
            if _r6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _r6, debug_notes=debug_notes)
        elif type_id == 'bsl':
            _bsl_std_ranges = {}
            try:
                _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _all_std = json.load(_sf)
                _candidate_stds = []
                for _s in room.get('judgement', []) or []:
                    if _s and _s not in _candidate_stds:
                        _candidate_stds.append(_s)
                for _s in room.get('basis', []) or []:
                    if _s and _s not in _candidate_stds:
                        _candidate_stds.append(_s)
                _clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
                for _std in _candidate_stds:
                    _obj = ((_all_std.get(_std) or {}).get('bsl') or {})
                    _level = _obj.get(_clean_class_text) or _obj.get(_clean_class_text.replace('ISO ', 'ISO-')) or {}
                    if isinstance(_level, dict) and _level:
                        _bsl_std_ranges = dict(_level)
                        for _std2 in _candidate_stds:
                            _obj2 = ((_all_std.get(_std2) or {}).get('bsl') or {})
                            _level2 = _obj2.get(_clean_class_text) or _obj2.get(_clean_class_text.replace('ISO ', 'ISO-')) or {}
                            if isinstance(_level2, dict):
                                for _k, _v in _level2.items():
                                    if _k not in _bsl_std_ranges and _v:
                                        _bsl_std_ranges[_k] = _v
                        break
            except Exception:
                _bsl_std_ranges = {}
            if replacements.get('检测日期') or replacements.get('洁净级别') or replacements.get('洁净等级'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, {
                    3: replacements.get('检测日期', ''),
                    5: replacements.get('洁净级别', '') or replacements.get('洁净等级', ''),
                }, debug_notes=debug_notes, allow_blank=True)
            _room_length = str(room.get('length', '') or '').strip()
            _room_width = str(room.get('width', '') or '').strip()
            _room_height = str(room.get('height', '') or '').strip()
            try:
                _rl = float(_room_length) if _room_length else 0
                _rw = float(_room_width) if _room_width else 0
                _rh = float(_room_height) if _room_height else 0
            except (ValueError, TypeError):
                _rl = _rw = _rh = 0
            _area_str = str(round(_rl * _rw, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0) else ''
            _vol_str = str(round(_rl * _rw * _rh, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0 and _rh > 0) else ''
            if _area_str or _vol_str:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {
                    1: f'面积S（m2）={_area_str}         体积V（m3）={_vol_str}'
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('换气次数'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, {
                    2: str(((_bsl_std_ranges.get('airchange') or {}).get('range', '') or '')),
                    3: replacements.get('换气次数', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'airchange', 'airchange_rate', '换气次数')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('静压差'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, {
                    2: str(((_bsl_std_ranges.get('pressure') or {}).get('range', '') or '')),
                    3: replacements.get('静压差', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'pressure', 'static_pressure_diff', '静压差')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('气流流向'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, {
                    3: replacements.get('气流流向', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'airflow_direction', '气流流向')) or '合格',
                }, debug_notes=debug_notes, allow_blank=True)
            _hepa_result = get_param_result(build_param_map(room.get('params')), 'hepa_leak', '送风高效过滤器检漏')
            _hepa_item = get_param_item(build_param_map(room.get('params')), 'hepa_leak', '送风高效过滤器检漏')
            _hepa_objects = _hepa_item.get('objects', []) if isinstance(_hepa_item, dict) else []
            _hepa_value = str((_hepa_objects[0] or {}).get('value', '') if _hepa_objects else '')
            if _hepa_value:
                _hepa_conclusion = _normalize_conclusion_text(_hepa_result) or ('合格' if float(_hepa_value) <= 0.01 else '不合格')
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, {
                    3: _hepa_value,
                    4: _hepa_conclusion,
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('洁净度级别') or replacements.get('悬浮粒子数/m³'):
                _particle_std = _bsl_std_ranges.get('particle') or {}
                _range_all = str(_particle_std.get('range_05', '') or _particle_std.get('range', '') or '')
                _range_05 = _range_all
                _range_5 = str(_particle_std.get('range_5', '') or '')
                if _range_all and ',' in _range_all:
                    _parts = [x.strip() for x in _range_all.split(',') if x.strip()]
                    if len(_parts) >= 1: _range_05 = _parts[0]
                    if len(_parts) >= 2 and not _range_5: _range_5 = _parts[1]
                _particle_conclusion = _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'particle', '洁净度级别（悬浮粒子浓度）')) or '合格'
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, {
                    3: replacements.get('洁净度级别', ''),
                    5: replacements.get('洁净度级别', ''),
                    6: _particle_conclusion,
                }, debug_notes=debug_notes, allow_blank=True)
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {
                    4: replacements.get('≥0.5μm', ''),
                    2: _range_05,
                }, debug_notes=debug_notes, allow_blank=True)
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, {
                    5: replacements.get('0.5μmUCL', ''),
                }, debug_notes=debug_notes, allow_blank=True)
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {
                    2: _range_5,
                    4: replacements.get('≥5μm', ''),
                }, debug_notes=debug_notes, allow_blank=True)
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, {
                    5: replacements.get('5μmUCL', ''),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('温度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, {
                    2: str(((_bsl_std_ranges.get('temperature') or {}).get('range', '') or '')),
                    3: replacements.get('温度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'temperature', '温度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('相对湿度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, {
                    2: str(((_bsl_std_ranges.get('humidity') or {}).get('range', '') or '')),
                    3: replacements.get('相对湿度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'humidity', 'relative_humidity', '相对湿度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('照度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, {
                    2: str(((_bsl_std_ranges.get('illumination') or {}).get('range', '') or '')),
                    3: replacements.get('照度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'illumination', '照度', '平均照度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('噪声'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 15, {
                    2: str(((_bsl_std_ranges.get('noise') or {}).get('range', '') or '')),
                    3: replacements.get('噪声', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'noise', '噪声')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('沉降菌'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 16, {
                    2: str(((_bsl_std_ranges.get('settling') or {}).get('range', '') or '')),
                    3: replacements.get('沉降菌', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'settle_bacteria', 'settling_bacteria', 'settling', '沉降菌')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('浮游菌（平均浓度）'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 17, {
                    2: str(((_bsl_std_ranges.get('floating') or {}).get('range', '') or '')),
                    3: replacements.get('浮游菌（平均浓度）', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'floating_bacteria', 'floating', '浮游菌')),
                }, debug_notes=debug_notes, allow_blank=True)
        elif type_id == 'gmp_workshop':
            _gmp_std_ranges = {}
            try:
                _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _all_std = json.load(_sf)
                _candidate_stds = []
                for _s in room.get('judgement', []) or []:
                    if _s and _s not in _candidate_stds:
                        _candidate_stds.append(_s)
                for _s in room.get('basis', []) or []:
                    if _s and _s not in _candidate_stds:
                        _candidate_stds.append(_s)
                _clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
                for _std in _candidate_stds:
                    _obj = ((_all_std.get(_std) or {}).get('gmp_workshop') or {})
                    _level = _obj.get(_clean_class_text) or {}
                    if isinstance(_level, dict) and _level:
                        _gmp_std_ranges = dict(_level)
                        break
            except Exception:
                _gmp_std_ranges = {}
            gmp_grade = str(replacements.get('洁净度', '') or replacements.get('洁净度级别', '') or room.get('clean_class', '') or room.get('level_name', '') or '')
            _grade_display = gmp_grade.replace('GMP静态', '') if gmp_grade.startswith('GMP静态') else gmp_grade
            _particle_std = _gmp_std_ranges.get('particle') or {}
            _particle_all = str(_particle_std.get('range', '') or '')
            _particle_limit_05 = str(replacements.get('≥0.5μm标准', '') or replacements.get('≥0.5μm限值', '') or replacements.get('≥0.5μm标准位', '') or '')
            _particle_limit_5 = str(replacements.get('≥5μm标准', '') or replacements.get('≥5μm限值', '') or replacements.get('≥5μm标准位', '') or '')
            if _particle_all and ',' in _particle_all:
                _parts = [x.strip() for x in _particle_all.split(',') if x.strip()]
                if len(_parts) >= 1 and not _particle_limit_05:
                    _particle_limit_05 = _parts[0].replace('μm', '㎛').replace('≤', '：≤') if '：' not in _parts[0] else _parts[0]
                if len(_parts) >= 2 and not _particle_limit_5:
                    _particle_limit_5 = _parts[1].replace('μm', '㎛').replace('≤', '：≤') if '：' not in _parts[1] else _parts[1]
            if replacements.get('检测日期') or gmp_grade:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, {
                    3: replacements.get('检测日期', ''),
                    5: _grade_display,
                }, debug_notes=debug_notes, allow_blank=True)
            _room_length = str(room.get('length', '') or '').strip()
            _room_width = str(room.get('width', '') or '').strip()
            _room_height = str(room.get('height', '') or '').strip()
            try:
                _rl = float(_room_length) if _room_length else 0
                _rw = float(_room_width) if _room_width else 0
                _rh = float(_room_height) if _room_height else 0
            except (ValueError, TypeError):
                _rl = _rw = _rh = 0
            _area_str = str(round(_rl * _rw, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0) else ''
            _vol_str = str(round(_rl * _rw * _rh, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0 and _rh > 0) else ''
            if _area_str or _vol_str:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {
                    1: f'面积S（m2）={_area_str}              体积V（m3）={_vol_str}'
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('换气次数'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, {
                    2: str(((_gmp_std_ranges.get('wind_speed') or {}).get('range', '') or ((_gmp_std_ranges.get('airchange') or {}).get('range', '') or ''))),
                    3: replacements.get('换气次数', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'wind_speed', 'airchange', '换气次数')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('静压差'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, {
                    2: str(((_gmp_std_ranges.get('pressure') or {}).get('range', '') or '')),
                    3: replacements.get('静压差', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'pressure', '静压差')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('洁净度') or replacements.get('洁净度级别'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, {
                    3: _grade_display,
                    5: _grade_display,
                    6: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'particle', '洁净度级别（悬浮粒子浓度）')) or '合格',
                }, debug_notes=debug_notes, allow_blank=True)
            # GMP 粒子区块结构：row7/9 tc[5]=最大值, row8/10 tc[5]=UCL
            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, {
                3: _grade_display,
                5: replacements.get('≥0.5μm', ''),
            }, debug_notes=debug_notes, allow_blank=True)
            if _particle_limit_05:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, {2: _particle_limit_05}, debug_notes=debug_notes, allow_blank=True)
            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {
                5: replacements.get('0.5μmUCL', ''),
            }, debug_notes=debug_notes, allow_blank=True)
            if _particle_limit_05:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {2: _particle_limit_05}, debug_notes=debug_notes, allow_blank=True)
            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, {
                3: _grade_display if replacements.get('≥5μm', '') else '',
                5: replacements.get('≥5μm', ''),
            }, debug_notes=debug_notes, allow_blank=True)
            if _particle_limit_5:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, {2: _particle_limit_5}, debug_notes=debug_notes, allow_blank=True)
            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {
                5: replacements.get('5μmUCL', ''),
            }, debug_notes=debug_notes, allow_blank=True)
            if _particle_limit_5:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {2: _particle_limit_5}, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('温度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, {
                    2: str(((_gmp_std_ranges.get('temperature') or {}).get('range', '') or '20～24')),
                    3: replacements.get('温度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'temperature', '温度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('相对湿度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, {
                    2: str(((_gmp_std_ranges.get('humidity') or {}).get('range', '') or '45～60')),
                    3: replacements.get('相对湿度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'humidity', '相对湿度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('平均照度') or replacements.get('照度'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, {
                    2: str(((_gmp_std_ranges.get('illumination_main_room') or {}).get('range', '') or '≥300')),
                    3: replacements.get('平均照度', '') or replacements.get('照度', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'illumination', '照度', '平均照度')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('噪声'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, {
                    2: str(((_gmp_std_ranges.get('noise') or {}).get('range', '') or '')),
                    3: replacements.get('噪声', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'noise', '噪声')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('沉降菌') or replacements.get('沉降菌（平均菌落数）'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 15, {
                    2: str(((_gmp_std_ranges.get('settling') or {}).get('range', '') or '≤1')),
                    3: replacements.get('沉降菌', '') or replacements.get('沉降菌（平均菌落数）', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'settle_bacteria', 'settling', '沉降菌')),
                }, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('浮游菌（平均浓度）') or replacements.get('浮游菌'):
                _floating_std_val = str(((_gmp_std_ranges.get('floating') or {}).get('range', '') or ''))
                _floating_fill = {
                    3: replacements.get('浮游菌（平均浓度）', '') or replacements.get('浮游菌', ''),
                    4: _normalize_conclusion_text(get_param_result(build_param_map(room.get('params')), 'floating_bacteria', '浮游菌')),
                }
                if _floating_std_val:
                    _floating_fill[2] = _floating_std_val
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 16, _floating_fill, debug_notes=debug_notes, allow_blank=True)
            if replacements.get('送风高效过滤器检漏') or replacements.get('高效过滤器检漏'):
                _hepa_item = get_param_item(build_param_map(room.get('params')), 'hepa_leak', '送风高效过滤器检漏')
                _hepa_objects = _hepa_item.get('objects', []) if isinstance(_hepa_item, dict) else []
                _hepa_value = str((_hepa_objects[0] or {}).get('value', '') if _hepa_objects else '') or (replacements.get('送风高效过滤器检漏', '') or replacements.get('高效过滤器检漏', ''))
                _hepa_result = get_param_result(build_param_map(room.get('params')), 'hepa_leak', '送风高效过滤器检漏')
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, {
                    3: _hepa_value,
                    4: _normalize_conclusion_text(_hepa_result) or ('合格' if _hepa_value and float(_hepa_value) <= 0.01 else ''),
                }, debug_notes=debug_notes, allow_blank=True)
        elif type_id == 'veterinary_gmp_workshop':
            # --- Dynamic standards from standards_ranges.json ---
            _vgmp_std_ranges = {}
            try:
                _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _all_std = json.load(_sf)
                _clean_class_text = room.get('clean_class', '') or room.get('level_name', '')
                for _s in (room.get('judgement', []) or []) + (room.get('basis', []) or []):
                    _obj = ((_all_std.get(_s) or {}).get('veterinary_gmp_workshop') or {})
                    _level = _obj.get(_clean_class_text) or {}
                    if isinstance(_level, dict) and _level:
                        for _pk, _pv in _level.items():
                            if _pk not in _vgmp_std_ranges:
                                _vgmp_std_ranges[_pk] = _pv
            except Exception:
                pass
            def _vgmp_std(key):
                r = _vgmp_std_ranges.get(key, {})
                return str(r.get('range', '') if isinstance(r, dict) else r or '')

            gmp_grade = str(replacements.get('GMP等级', '') or replacements.get('洁净等级', '') or replacements.get('洁净级别', '') or replacements.get('洁净度设计级别', '') or replacements.get('洁净度', '') or replacements.get('洁净度级别', '') or '')
            _grade_display = gmp_grade.replace('GMP静态', '') if gmp_grade.startswith('GMP静态') else gmp_grade
            _p_map = build_param_map(room.get('params'))
            _vgmp_result_fn = lambda *k: get_param_result(_p_map, *k)
            def _vgmp_concl(*keys):
                return _normalize_conclusion_text(_vgmp_result_fn(*keys))

            # Particle data
            _p_data = (_p_map.get('particle', {}) or {}).get('data', {}) or {}
            _p05_max = str(_p_data.get('p05_max', '') or replacements.get('≥0.5μm', '') or '')
            _p05_ucl = str(_p_data.get('p05_ucl', '') or replacements.get('0.5μmUCL', '') or '')
            _p5_max = str(_p_data.get('p5_max', '') or replacements.get('≥5μm', '') or '')
            _p5_ucl = str(_p_data.get('p5_ucl', '') or replacements.get('5μmUCL', '') or '')

            # Particle limits
            _particle_std = _vgmp_std_ranges.get('particle', {})
            _particle_range = str(_particle_std.get('range', '') if isinstance(_particle_std, dict) else '')
            _range_05 = str(replacements.get('≥0.5μm标准', '') or '')
            _range_5 = str(replacements.get('≥5μm标准', '') or '')
            if not _range_05 and _particle_range:
                parts = [p.strip() for p in _particle_range.split(',')]
                for p in parts:
                    if '0.5' in p and not _range_05:
                        _range_05 = p
                    elif '5' in p and '0.5' not in p and not _range_5:
                        _range_5 = p

            # --- ROW 0: room name + date + grade ---
            _row0 = {}
            detection_date = replacements.get('检测日期', '')
            if detection_date: _row0[3] = detection_date
            if gmp_grade: _row0[5] = _grade_display
            _room_name = replacements.get('受检区域名称', '') or replacements.get('房间名称', '')
            if _room_name: _row0[1] = _room_name
            if _row0:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, _row0, debug_notes=debug_notes)

            # --- ROW 1: S/V ---
            _length = str(room.get('length', '') or '')
            _width = str(room.get('width', '') or '')
            _height = str(room.get('height', '') or '')
            if _length and _width and _height:
                try:
                    _s = round(float(_length) * float(_width), 1)
                    _v = round(float(_length) * float(_width) * float(_height), 0)
                    _sv_text = f'面积S（m²）={_s}              体积V（m³）={int(_v)}'
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {1: _sv_text}, debug_notes=debug_notes)
                except (ValueError, TypeError):
                    pass

            # --- ROW 3: 截面风速 ---
            _ws_val = replacements.get('截面风速', '') or replacements.get('换气次数', '')
            _ws_std = _vgmp_std('wind_speed') or _vgmp_std('airchange') or ''
            _ws_concl = _vgmp_concl('sectional_air_velocity', 'air_velocity', 'wind_speed', 'airchange')
            _r3 = {}
            if _ws_std: _r3[2] = _ws_std
            if _ws_val: _r3[3] = _ws_val
            if _ws_concl: _r3[4] = _ws_concl
            if _r3: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, _r3, debug_notes=debug_notes)

            # --- ROW 4: 风速不均匀度 ---
            _su_val = replacements.get('风速不均匀度', '')
            _su_std = _vgmp_std('wind_uniformity') or ''
            _su_concl = _vgmp_concl('speed_uniformity', 'wind_uniformity')
            _r4 = {}
            if _su_std: _r4[2] = _su_std
            if _su_val: _r4[3] = _su_val
            if _su_concl: _r4[4] = _su_concl
            if _r4: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, _r4, debug_notes=debug_notes)

            # --- ROW 5: 静压差 ---
            _pr_val = replacements.get('静压差', '')
            _pr_std = _vgmp_std('pressure') or ''
            _pr_concl = _vgmp_concl('static_pressure_diff', 'pressure_diff', 'pressure')
            _r5 = {}
            if _pr_std: _r5[2] = _pr_std
            if _pr_val: _r5[3] = _pr_val
            if _pr_concl: _r5[4] = _pr_concl
            if _r5: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, _r5, debug_notes=debug_notes)

            # --- ROW 6: 检漏 ---
            _hl_val = replacements.get('送风高效过滤器检漏', '')
            _hl_concl = _vgmp_concl('hepa_leak')
            _r6 = {}
            if _hl_val: _r6[3] = _hl_val
            if _hl_concl: _r6[4] = _hl_concl
            if _r6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _r6, debug_notes=debug_notes)

            # --- ROW 7: 气流流型 ---
            _af_val = replacements.get('气流流型', '')
            _af_concl = _vgmp_concl('airflow_pattern')
            _r7 = {}
            if _af_val: _r7[3] = _af_val
            if _af_concl: _r7[4] = _af_concl
            if _r7: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, _r7, debug_notes=debug_notes)

            # --- ROW 8: 洁净度级别 header ---
            _pc = _vgmp_concl('particle')
            if _grade_display or _pc:
                _r8 = {}
                if _grade_display: _r8[3] = _grade_display; _r8[5] = _grade_display
                if _pc: _r8[6] = _pc
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, _r8, debug_notes=debug_notes)

            # --- ROW 9-12: Particle block ---
            _r9 = {}
            if _range_05: _r9[2] = _range_05
            if _grade_display: _r9[3] = 'GMP静态' + _grade_display if 'GMP' not in _grade_display else _grade_display
            if _p05_max: _r9[5] = _p05_max
            if _r9: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, _r9, debug_notes=debug_notes)
            if _p05_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {5: _p05_ucl}, debug_notes=debug_notes)
            _r11 = {}
            if _range_5: _r11[2] = _range_5
            if _p5_max: _r11[5] = _p5_max
            if _r11: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, _r11, debug_notes=debug_notes)
            if _p5_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, {5: _p5_ucl}, debug_notes=debug_notes)

            # --- ROW 13-18: simple params ---
            _simple_rows = [
                (13, '温度', 'temperature', ('temperature',)),
                (14, '相对湿度', 'humidity', ('relative_humidity', 'humidity')),
                (15, '平均照度', 'illumination_main_room', ('illumination', 'illumination_main_room', 'illumination_aux_room')),
                (16, '噪声', 'noise', ('noise',)),
                (17, '沉降菌', 'settling', ('settling_bacteria', 'settle_bacteria', 'settling')),
                (18, '浮游菌', 'floating', ('floating_bacteria', 'floating')),
            ]
            for _ri, _label, _std_key, _concl_keys in _simple_rows:
                _val = replacements.get(_label, '') or replacements.get(_label + '（平均菌落数）', '') or replacements.get(_label + '（平均浓度）', '')
                _std = _vgmp_std(_std_key) or ''
                _concl = _vgmp_concl(*_concl_keys)
                _row = {}
                if _std: _row[2] = _std
                if _val: _row[3] = _val
                if _concl: _row[4] = _concl
                if _row: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, _ri, _row, debug_notes=debug_notes)

            # --- ROW 19: 自净时间 ---
            _sc_val = replacements.get('自净时间', '')
            _sc_concl = _vgmp_concl('self_clean')
            _r19 = {}
            if _sc_val: _r19[3] = _sc_val
            if _sc_concl: _r19[4] = _sc_concl
            if _r19: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 19, _r19, debug_notes=debug_notes)
        elif type_id == 'food_workshop':
            food_grade = str(replacements.get('食品等级', '') or replacements.get('洁净等级', '') or replacements.get('洁净级别', '') or replacements.get('洁净度设计级别', '') or replacements.get('洁净度', '') or replacements.get('洁净度级别', '') or '')
            food_grade_short = food_grade
            if '（' in food_grade_short:
                food_grade_short = food_grade_short.split('（', 1)[0]
            # --- Dynamic standards from standards_ranges.json ---
            _food_std_ranges = {}
            try:
                import json as _json
                _sr_path = Path(__file__).parent.parent / 'static' / 'standards_ranges.json'
                with open(_sr_path, encoding='utf-8') as _sf:
                    _sr_all = _json.load(_sf)
                _food_grade_norm = str(food_grade).strip()
                _report_ctx = export_payload.get('report_context', {}) or {}
                _room_ctx = _report_ctx.get('room_context', {}) or {}
                _food_judgement = _room_ctx.get('judgement') or room.get('judgement') or []
                _food_basis = _room_ctx.get('basis') or room.get('basis') or []
                # Try judgement standards first, then basis
                for _std_name in (_food_judgement + _food_basis):
                    _std_data = _sr_all.get(_std_name, {})
                    _type_data = _std_data.get('food_workshop', {})
                    for _lev, _params in _type_data.items():
                        if _lev == _food_grade_norm or _food_grade_norm in _lev or _lev in _food_grade_norm:
                            for _pk, _pv in (_params if isinstance(_params, dict) else {}).items():
                                if _pk not in _food_std_ranges:
                                    _food_std_ranges[_pk] = _pv
            except Exception:
                pass

            def _food_std(key):
                r = _food_std_ranges.get(key, {})
                return str(r.get('range', '') if isinstance(r, dict) else r or '')

            # --- Conclusions ---
            def _food_conclusion(*keys):
                return _normalize_conclusion_text(_food_result(*keys))

            _food_result_fn = lambda *k: get_param_result(build_param_map(room.get('params')), *k)
            def _food_conclusion_from(*keys):
                return _normalize_conclusion_text(_food_result_fn(*keys))

            # --- ROW 0: date + grade ---
            _food_row0 = {}
            detection_date = replacements.get('检测日期', '')
            if detection_date:
                _food_row0[3] = detection_date
            if food_grade:
                _food_row0[5] = food_grade
            if _food_row0:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, _food_row0, debug_notes=debug_notes)
            # Room name in ROW 0
            _room_name = replacements.get('受检区域名称', '') or replacements.get('房间名称', '')
            if _room_name:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, {1: _room_name}, debug_notes=debug_notes)

            # --- ROW 1: S/V ---
            _length = str(room.get('length', '') or '')
            _width = str(room.get('width', '') or '')
            _height = str(room.get('height', '') or '')
            if _length and _width and _height:
                try:
                    _s = round(float(_length) * float(_width), 1)
                    _v = round(float(_length) * float(_width) * float(_height), 0)
                    _sv_text = f'面积S（m²）={_s}              体积V（m³）={int(_v)}'
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {1: _sv_text}, debug_notes=debug_notes)
                except (ValueError, TypeError):
                    pass

            # --- ROW 3: 截面风速 / 换气次数 ---
            _airflow_val = replacements.get('换气次数', '') or replacements.get('截面风速', '')
            _airflow_std = _food_std('wind_speed') or _food_std('airchange') or ''
            _airflow_concl = _food_conclusion_from('wind_speed', 'air_velocity', 'sectional_air_velocity', 'airchange_rate', 'air_change_rate', 'airchange')
            _row3 = {}
            if _airflow_std:
                _row3[2] = _airflow_std
            if _airflow_val:
                _row3[3] = _airflow_val
            if _airflow_concl:
                _row3[4] = _airflow_concl
            if _row3:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, _row3, debug_notes=debug_notes)

            # --- ROW 4: 静压差 ---
            _pressure_val = replacements.get('静压差', '')
            _pressure_std = _food_std('pressure') or ''
            _pressure_concl = _food_conclusion_from('static_pressure_diff', 'pressure_diff', 'pressure')
            _row4 = {}
            if _pressure_std:
                _row4[2] = _pressure_std
            if _pressure_val:
                _row4[3] = _pressure_val
            if _pressure_concl:
                _row4[4] = _pressure_concl
            if _row4:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, _row4, debug_notes=debug_notes)

            # --- ROW 5: 送风高效过滤器检漏 ---
            _hepa_val = replacements.get('送风高效过滤器检漏', '')
            _hepa_concl = _food_conclusion_from('hepa_leak')
            _row5 = {}
            if _hepa_val:
                _row5[3] = _hepa_val
            if _hepa_concl:
                _row5[4] = _hepa_concl
            if _row5:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, _row5, debug_notes=debug_notes)

            # --- ROW 6: 洁净度级别 header ---
            _particle_concl = _food_conclusion_from('particle')
            if food_grade or _particle_concl:
                _row6 = {}
                if food_grade:
                    _row6[3] = food_grade
                    _row6[5] = food_grade
                if _particle_concl:
                    _row6[6] = _particle_concl
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _row6, debug_notes=debug_notes)

            # --- ROW 7-10: Particle block ---
            # Get particle data from params
            _p_map = build_param_map(room.get('params'))
            _p_data = (_p_map.get('particle', {}) or {}).get('data', {}) or {}
            _p05_max = str(_p_data.get('p05_max', '') or replacements.get('≥0.5μm', '') or '')
            _p05_ucl = str(_p_data.get('p05_ucl', '') or replacements.get('0.5μmUCL', '') or '')
            _p5_max = str(_p_data.get('p5_max', '') or replacements.get('≥5μm', '') or '')
            _p5_ucl = str(_p_data.get('p5_ucl', '') or replacements.get('5μmUCL', '') or '')

            # Particle limits from standards or fill plan
            _particle_std = _food_std_ranges.get('particle', {})
            _particle_range = str(_particle_std.get('range', '') if isinstance(_particle_std, dict) else '')
            _range_05 = str(replacements.get('≥0.5μm标准', '') or '')
            _range_5 = str(replacements.get('≥5μm标准', '') or '')
            if not _range_05 and _particle_range:
                parts = [p.strip() for p in _particle_range.split(',')]
                for p in parts:
                    if '0.5' in p:
                        _range_05 = p
                    elif '5' in p and '0.5' not in p:
                        _range_5 = p

            # ROW 7: 0.5μm max
            _row7 = {}
            if _range_05:
                _row7[2] = _range_05
            if food_grade_short:
                _row7[3] = food_grade_short
            if _p05_max:
                _row7[5] = _p05_max
            if _row7:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, _row7, debug_notes=debug_notes)
            # ROW 8: 0.5μm UCL
            if _p05_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {5: _p05_ucl}, debug_notes=debug_notes)
            # ROW 9: 5μm max
            _row9 = {}
            if _range_5:
                _row9[2] = _range_5
            if _p5_max:
                _row9[5] = _p5_max
            if _row9:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, _row9, debug_notes=debug_notes)
            # ROW 10: 5μm UCL
            if _p5_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {5: _p5_ucl}, debug_notes=debug_notes)

            # --- ROW 11: 温度 ---
            _temp_val = replacements.get('温度', '')
            _temp_std = _food_std('temperature') or ''
            _temp_concl = _food_conclusion_from('temperature')
            _row11 = {}
            if _temp_std:
                _row11[2] = _temp_std
            if _temp_val:
                _row11[3] = _temp_val
            if _temp_concl:
                _row11[4] = _temp_concl
            if _row11:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, _row11, debug_notes=debug_notes)

            # --- ROW 12: 湿度 ---
            _hum_val = replacements.get('相对湿度', '') or replacements.get('湿度', '')
            _hum_std = _food_std('humidity') or ''
            _hum_concl = _food_conclusion_from('relative_humidity', 'humidity')
            _row12 = {}
            if _hum_std:
                _row12[2] = _hum_std
            if _hum_val:
                _row12[3] = _hum_val
            if _hum_concl:
                _row12[4] = _hum_concl
            if _row12:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, _row12, debug_notes=debug_notes)

            # --- ROW 13: 照度 ---
            _illu_val = replacements.get('平均照度', '') or replacements.get('照度', '')
            _illu_std = _food_std('illumination_general_processing') or _food_std('illumination_mixed_processing') or _food_std('illumination_non_processing') or ''
            _illu_concl = _food_conclusion_from('illumination', 'illumination_general_processing', 'illumination_mixed_processing', 'illumination_non_processing')
            _row13 = {}
            if _illu_std:
                _row13[2] = _illu_std
            if _illu_val:
                _row13[3] = _illu_val
            if _illu_concl:
                _row13[4] = _illu_concl
            if _row13:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, _row13, debug_notes=debug_notes)

            # --- ROW 14: 噪声 ---
            _noise_val = replacements.get('噪声', '')
            _noise_std = _food_std('noise') or ''
            _noise_concl = _food_conclusion_from('noise')
            _row14 = {}
            if _noise_std:
                _row14[2] = _noise_std
            if _noise_val:
                _row14[3] = _noise_val
            if _noise_concl:
                _row14[4] = _noise_concl
            if _row14:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, _row14, debug_notes=debug_notes)

            # --- ROW 15: 沉降菌 ---
            _settle_val = replacements.get('沉降菌', '') or replacements.get('沉降菌（平均菌落数）', '')
            _settle_std = _food_std('settling') or ''
            _settle_concl = _food_conclusion_from('settling_bacteria', 'settle_bacteria', 'settling')
            _row15 = {}
            if _settle_std:
                _row15[2] = _settle_std
            if _settle_val:
                _row15[3] = _settle_val
            if _settle_concl:
                _row15[4] = _settle_concl
            if _row15:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 15, _row15, debug_notes=debug_notes)

            # --- ROW 16: 浮游菌 ---
            _float_val = replacements.get('浮游菌（平均浓度）', '') or replacements.get('浮游菌', '')
            _float_std = _food_std('floating') or ''
            _float_concl = _food_conclusion_from('floating_bacteria', 'floating')
            _row16 = {}
            if _float_std:
                _row16[2] = _float_std
            if _float_val:
                _row16[3] = _float_val
            if _float_concl:
                _row16[4] = _float_concl
            if _row16:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 16, _row16, debug_notes=debug_notes)
        elif type_id == 'electronics_workshop':
            # --- Dynamic standards from standards_ranges.json ---
            _elec_std_ranges = {}
            try:
                _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _all_std = json.load(_sf)
                _elec_iso = str(
                    replacements.get('ISO等级', '')
                    or replacements.get('洁净度设计级别', '')
                    or replacements.get('洁净等级', '')
                    or replacements.get('洁净级别', '')
                    or ''
                ).strip()
                _report_ctx = export_payload.get('report_context', {}) or {}
                _room_ctx = _report_ctx.get('room_context', {}) or {}
                _elec_judgement = _room_ctx.get('judgement') or room.get('judgement') or []
                _elec_basis = _room_ctx.get('basis') or room.get('basis') or []
                for _std_name in (_elec_judgement + _elec_basis):
                    _std_data = _all_std.get(_std_name, {})
                    _type_data = _std_data.get('electronics_workshop', {})
                    for _lev, _params in _type_data.items():
                        if _lev == _elec_iso or _elec_iso in _lev or _lev in _elec_iso:
                            for _pk, _pv in (_params if isinstance(_params, dict) else {}).items():
                                if _pk not in _elec_std_ranges:
                                    _elec_std_ranges[_pk] = _pv
            except Exception:
                pass

            def _elec_std(key):
                r = _elec_std_ranges.get(key, {})
                return str(r.get('range', '') if isinstance(r, dict) else r or '')

            iso_level = str(
                replacements.get('ISO等级', '')
                or replacements.get('洁净度设计级别', '')
                or replacements.get('洁净等级', '')
                or replacements.get('洁净级别', '')
                or ''
            )
            _p_map = build_param_map(room.get('params'))
            def _elec_concl(*keys):
                return _normalize_conclusion_text(get_param_result(_p_map, *keys))

            # --- ROW 0: room name + date + grade ---
            _elec_row0 = {}
            _room_name = replacements.get('受检区域名称', '') or replacements.get('房间名称', '')
            if _room_name:
                _elec_row0[1] = _room_name
            detection_date = replacements.get('检测日期', '')
            if detection_date:
                _elec_row0[3] = detection_date
            if iso_level:
                _elec_row0[5] = iso_level
            if _elec_row0:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, _elec_row0, debug_notes=debug_notes)

            # --- ROW 1: S/V ---
            _room_length = str(room.get('length', '') or '').strip()
            _room_width = str(room.get('width', '') or '').strip()
            _room_height = str(room.get('height', '') or '').strip()
            try:
                _rl = float(_room_length) if _room_length else 0
                _rw = float(_room_width) if _room_width else 0
                _rh = float(_room_height) if _room_height else 0
            except (ValueError, TypeError):
                _rl = _rw = _rh = 0
            if _rl > 0 and _rw > 0:
                _area_str = str(round(_rl * _rw, 2)).rstrip('0').rstrip('.')
                _vol_str = str(round(_rl * _rw * _rh, 2)).rstrip('0').rstrip('.') if _rh > 0 else ''
                _sv_text = f'面积S（m2）={_area_str}              体积V（m3）={_vol_str}'
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {1: _sv_text}, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 3: 截面风速 (ISO5) / 换气次数 (ISO6~9) ---
            _airflow_val = replacements.get('风速或换气次数', '') or replacements.get('换气次数', '') or replacements.get('截面风速', '')
            _airflow_std = _elec_std('wind_speed') or _elec_std('airchange') or ''
            _airflow_concl = _elec_concl('wind_speed', 'air_velocity', 'sectional_air_velocity', 'airchange_rate', 'air_change_rate', 'airchange')
            _row3 = {}
            if _airflow_std:
                _row3[2] = _airflow_std
            if _airflow_val:
                _row3[3] = _airflow_val
            if _airflow_concl:
                _row3[4] = _airflow_concl
            if _row3:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, _row3, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 4: 静压差 ---
            _pressure_val = replacements.get('静压差', '')
            _pressure_std = _elec_std('pressure') or ''
            _pressure_concl = _elec_concl('static_pressure_diff', 'pressure_diff', 'pressure', '静压差')
            _row4 = {}
            if _pressure_std:
                _row4[2] = _pressure_std
            if _pressure_val:
                _row4[3] = _pressure_val
            if _pressure_concl:
                _row4[4] = _pressure_concl
            if _row4:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, _row4, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 5: 送风高效过滤器检漏 ---
            _hepa_item = get_param_item(_p_map, 'hepa_leak', '送风高效过滤器检漏')
            _hepa_objects = _hepa_item.get('objects', []) if isinstance(_hepa_item, dict) else []
            _hepa_value = str((_hepa_objects[0] or {}).get('value', '') if _hepa_objects else '') or (replacements.get('送风高效过滤器检漏', ''))
            _hepa_result = get_param_result(_p_map, 'hepa_leak', '送风高效过滤器检漏')
            _row5 = {}
            if _hepa_value:
                _row5[3] = _hepa_value
            _hepa_concl = _normalize_conclusion_text(_hepa_result)
            if not _hepa_concl and _hepa_value:
                try:
                    _hepa_concl = '合格' if float(_hepa_value) <= 0.01 else ''
                except (ValueError, TypeError):
                    pass
            if _hepa_concl:
                _row5[4] = _hepa_concl
            if _row5:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, _row5, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 6: 洁净度级别（悬浮粒子浓度）header ---
            _particle_concl = _elec_concl('particle', '洁净度级别（悬浮粒子浓度）')
            if iso_level or _particle_concl:
                _row6 = {}
                if iso_level:
                    _row6[3] = iso_level
                    _row6[5] = iso_level
                if _particle_concl:
                    _row6[6] = _particle_concl
                elif iso_level:
                    _row6[6] = '合格'
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _row6, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 7-10: Particle block ---
            _p_data = (_p_map.get('particle', {}) or {}).get('data', {}) or {}
            _p05_max = str(_p_data.get('p05_max', '') or replacements.get('≥0.5μm', '') or '')
            _p05_ucl = str(_p_data.get('p05_ucl', '') or replacements.get('0.5μmUCL', '') or '')
            _p5_max = str(_p_data.get('p5_max', '') or replacements.get('≥5μm', '') or '')
            _p5_ucl = str(_p_data.get('p5_ucl', '') or replacements.get('5μmUCL', '') or '')

            # Particle limits from standards or fill plan
            particle_limit_05 = str(replacements.get('≥0.5μm标准', '') or '')
            particle_limit_5 = str(replacements.get('≥5μm标准', '') or '')
            _particle_std = _elec_std_ranges.get('particle', {})
            _particle_range = str(_particle_std.get('range', '') if isinstance(_particle_std, dict) else '')
            if not particle_limit_05 and _particle_range:
                parts = [p.strip() for p in _particle_range.split(',')]
                for p in parts:
                    if '0.5' in p and not particle_limit_05:
                        particle_limit_05 = p
                    elif '5' in p and '0.5' not in p and not particle_limit_5:
                        particle_limit_5 = p

            # ROW 7: 0.5μm max
            _row7 = {}
            if particle_limit_05:
                _row7[2] = particle_limit_05
            if iso_level:
                _row7[3] = iso_level
            if _p05_max:
                _row7[5] = _p05_max
            if _row7:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, _row7, debug_notes=debug_notes, allow_blank=True)
            # ROW 8: 0.5μm UCL
            if _p05_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {5: _p05_ucl}, debug_notes=debug_notes, allow_blank=True)
            # ROW 9: 5μm max
            _row9 = {}
            if particle_limit_5:
                _row9[2] = particle_limit_5
            if _p5_max:
                _row9[5] = _p5_max
            if _row9:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, _row9, debug_notes=debug_notes, allow_blank=True)
            # ROW 10: 5μm UCL
            if _p5_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {5: _p5_ucl}, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 11: 温度 ---
            _temp_val = replacements.get('温度', '')
            _temp_std = _elec_std('temperature') or ''
            _temp_concl = _elec_concl('temperature', '温度')
            _row11 = {}
            if _temp_std:
                _row11[2] = _temp_std
            if _temp_val:
                _row11[3] = _temp_val
            if _temp_concl:
                _row11[4] = _temp_concl
            if _row11:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, _row11, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 12: 湿度 ---
            _hum_val = replacements.get('相对湿度', '') or replacements.get('湿度', '')
            _hum_std = _elec_std('humidity') or ''
            _hum_concl = _elec_concl('relative_humidity', 'humidity', '相对湿度', '湿度')
            _row12 = {}
            if _hum_std:
                _row12[2] = _hum_std
            if _hum_val:
                _row12[3] = _hum_val
            if _hum_concl:
                _row12[4] = _hum_concl
            if _row12:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, _row12, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 13: 照度 ---
            _illu_val = replacements.get('平均照度', '') or replacements.get('照度', '')
            _illu_std = _elec_std('illumination_main') or _elec_std('illumination_aux') or ''
            _illu_concl = _elec_concl('illumination', 'illumination_main', 'illumination_main_room', 'illumination_aux', '照度', '平均照度')
            _row13 = {}
            if _illu_std:
                _row13[2] = _illu_std
            if _illu_val:
                _row13[3] = _illu_val
            if _illu_concl:
                _row13[4] = _illu_concl
            if _row13:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, _row13, debug_notes=debug_notes, allow_blank=True)

            # --- ROW 14: 噪声 ---
            _noise_val = replacements.get('噪声', '')
            _noise_std = _elec_std('noise') or ''
            _noise_concl = _elec_concl('noise', '噪声')
            _row14 = {}
            if _noise_std:
                _row14[2] = _noise_std
            if _noise_val:
                _row14[3] = _noise_val
            if _noise_concl:
                _row14[4] = _noise_concl
            if _row14:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, _row14, debug_notes=debug_notes, allow_blank=True)
        elif type_id == 'animal_room':
            room_context = room.get('context', {}) or {}
            animal_environment = str(room_context.get('animal_environment', '') or room.get('clean_class', '') or room.get('level_name', '') or '')
            barrier_room_class = str(room_context.get('barrier_room_class', '') or '')
            barrier_aux_room = str(room_context.get('barrier_aux_room', '') or '')

            _animal_std_ranges = {}
            try:
                _std_path = os.path.join(os.path.dirname(__file__), '..', 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _all_std = json.load(_sf)
                for _s in (room.get('judgement', []) or []) + (room.get('basis', []) or []):
                    _obj = ((_all_std.get(_s) or {}).get('animal_room') or {})
                    if animal_environment == '屏障环境' and barrier_room_class == '洁净辅房':
                        _level = (((_obj.get('屏障环境洁净辅房') or {}) if isinstance(_obj, dict) else {}) .get(barrier_aux_room) or {})
                    else:
                        _level = (_obj.get(animal_environment) if isinstance(_obj, dict) else {}) or (_obj.get('_default') if isinstance(_obj, dict) else {}) or {}
                    if isinstance(_level, dict) and _level:
                        for _pk, _pv in _level.items():
                            if _pk not in _animal_std_ranges:
                                _animal_std_ranges[_pk] = _pv
            except Exception:
                pass

            def _animal_std(key):
                r = _animal_std_ranges.get(key, {})
                return str(r.get('range', '') if isinstance(r, dict) else r or '')

            _p_map = build_param_map(room.get('params'))
            def _animal_concl(*keys):
                return _normalize_conclusion_text(get_param_result(_p_map, *keys))

            # ROW 0 / 1 common
            _row0 = {}
            _room_name = replacements.get('受检区域名称', '') or replacements.get('房间名称', '')
            if _room_name: _row0[1] = _room_name
            _det_date = replacements.get('检测日期', '')
            if _det_date: _row0[3] = _det_date
            _clean_class = replacements.get('洁净度设计级别', '') or room.get('clean_class', '') or room.get('level_name', '') or ''
            _particle_class_display = _clean_class
            if animal_environment == '屏障环境' and barrier_room_class != '洁净辅房':
                _particle_class_display = 'ISO-7'
            elif animal_environment == '隔离环境':
                _particle_class_display = 'ISO-7'
            if _clean_class: _row0[5] = _clean_class
            if _row0:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, _row0, debug_notes=debug_notes)
            _length = str(room.get('length', '') or '')
            _width = str(room.get('width', '') or '')
            _height = str(room.get('height', '') or '')
            if _length and _width and _height:
                try:
                    _s = str(round(float(_length) * float(_width), 2)).rstrip('0').rstrip('.')
                    _v = str(round(float(_length) * float(_width) * float(_height), 2)).rstrip('0').rstrip('.')
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {1: f'面积S（m2）={_s}                体积V（m3）={_v}'}, debug_notes=debug_notes, allow_blank=True)
                except (ValueError, TypeError):
                    pass

            # 屏障环境主房间 / 隔离环境：18行模板，完整三层
            if animal_environment in {'屏障环境', '隔离环境'} and barrier_room_class != '洁净辅房':
                _particle_item = get_param_item(_p_map, 'particle_negative', 'particle')
                _particle_data = (_particle_item.get('data', {}) if isinstance(_particle_item, dict) else {}) or (_particle_item.get('values', {}) if isinstance(_particle_item, dict) else {}) or {}
                _p05_max = str(_particle_data.get('p05_max', '') or _particle_data.get('max_0_5um', '') or replacements.get('≥0.5μm', '') or '')
                _p05_ucl = str(_particle_data.get('p05_ucl', '') or _particle_data.get('ucl_0_5um', '') or replacements.get('0.5μmUCL', '') or '')
                _p5_max = str(_particle_data.get('p5_max', '') or _particle_data.get('max_5um', '') or replacements.get('≥5μm', '') or '')
                _p5_ucl = str(_particle_data.get('p5_ucl', '') or _particle_data.get('ucl_5um', '') or replacements.get('5μmUCL', '') or '')
                _particle_range = _animal_std('particle_negative' if animal_environment == '隔离环境' else 'particle') or ''
                _range_05 = _range_5 = ''
                if _particle_range:
                    import re as _re
                    m05 = _re.search(r'([^，,]*0\.5μm[^，,]*)', _particle_range)
                    m5 = _re.search(r'([^，,]*5μm[^，,]*)', _particle_range)
                    if m05: _range_05 = m05.group(1).strip()
                    if m5:
                        _cand = m5.group(1).strip()
                        if '0.5μm' not in _cand:
                            _range_5 = _cand
                    if not _range_05 or not _range_5:
                        for p in [x.strip() for x in re.split(r'[，,]', _particle_range) if x.strip()]:
                            if '0.5μm' in p and not _range_05:
                                _range_05 = p
                            elif '5μm' in p and '0.5μm' not in p and not _range_5:
                                _range_5 = p
                _rows = [
                    (3, '换气次数', '换气次数', 'airchange', ('airchange_rate', 'airchange')),
                    (4, '动物笼具处气流速度', '动物笼具处气流速度', 'cage_airspeed', ('cage_airspeed',)),
                    (5, '静压差', '静压差', 'pressure', ('static_pressure_diff', 'pressure_diff', 'pressure')),
                    (11, '温度', '温度', 'temperature', ('temperature',)),
                    (12, '相对湿度', '相对湿度', 'humidity', ('relative_humidity', 'humidity')),
                    (13, '最大日温差', '最大日温差', 'temp_diff', ('temp_diff',)),
                    (16, '噪声', '噪声', 'noise', ('noise',)),
                    (17, '沉降菌（平均菌落数）', '沉降菌', 'settling', ('settling_bacteria', 'settle_bacteria', 'settling')),
                ]
                for _ri, _label, _key, _std_key, _ckeys in _rows:
                    _val = replacements.get(_key, '') or replacements.get(_label, '')
                    _std = _animal_std(_std_key) or ''
                    _concl = _animal_concl(*_ckeys)
                    _row = {}
                    if _std: _row[2] = _std
                    if _val: _row[3] = _val
                    if _concl: _row[4] = _concl
                    if _row:
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, _ri, _row, debug_notes=debug_notes, allow_blank=True)
                # particle header + blocks
                _pc = _animal_concl('particle', 'particle_negative')
                _row6 = {}
                if _clean_class: _row6[3] = _particle_class_display; _row6[5] = _particle_class_display
                if _pc: _row6[6] = _pc
                if _row6:
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _row6, debug_notes=debug_notes, allow_blank=True)
                if _range_05 or _p05_max or _clean_class:
                    _r7 = {}
                    if _range_05: _r7[2] = _range_05
                    if _clean_class: _r7[3] = _particle_class_display
                    if _p05_max: _r7[5] = _p05_max
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, _r7, debug_notes=debug_notes, allow_blank=True)
                if _p05_ucl:
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {5: _p05_ucl}, debug_notes=debug_notes, allow_blank=True)
                if _range_5 or _p5_max:
                    _r9 = {}
                    if _range_5: _r9[2] = _range_5
                    if _p5_max: _r9[5] = _p5_max
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, _r9, debug_notes=debug_notes, allow_blank=True)
                if _p5_ucl:
                    document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {5: _p5_ucl}, debug_notes=debug_notes, allow_blank=True)
                # illumination rows 14/15
                _work_std = _animal_std('work_illumination') or ''
                _animal_illu_std = _animal_std('animal_illumination') or ''
                _work_val = replacements.get('最低照度', '') or replacements.get('平均照度', '')
                _animal_illu_val = replacements.get('动物照度', '')
                _row14 = {}
                if _work_std: _row14[3] = _work_std
                if _work_val: _row14[4] = _work_val
                if _animal_concl('work_illumination', 'illumination'): _row14[5] = _animal_concl('work_illumination', 'illumination')
                if _row14: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, _row14, debug_notes=debug_notes, allow_blank=True)
                _row15 = {}
                if _animal_illu_std: _row15[3] = _animal_illu_std
                if _animal_illu_val: _row15[4] = _animal_illu_val
                if _animal_concl('animal_illumination'): _row15[5] = _animal_concl('animal_illumination')
                if _row15: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 15, _row15, debug_notes=debug_notes, allow_blank=True)

            # 普通环境：11行模板，三层填充
            elif animal_environment == '普通环境':
                _rows = [
                    (3, '换气次数', '换气次数', 'airchange', ('airchange_rate', 'airchange')),
                    (4, '动物笼具处气流速度', '动物笼具处气流速度', 'cage_airspeed', ('cage_airspeed',)),
                    (5, '温度', '温度', 'temperature', ('temperature',)),
                    (6, '相对湿度', '相对湿度', 'humidity', ('relative_humidity', 'humidity')),
                    (7, '最大日温差', '最大日温差', 'temp_diff', ('temp_diff',)),
                    (10, '噪声', '噪声', 'noise', ('noise',)),
                ]
                for _ri, _label, _key, _std_key, _ckeys in _rows:
                    _val = replacements.get(_key, '') or replacements.get(_label, '')
                    _std = _animal_std(_std_key) or ''
                    _concl = _animal_concl(*_ckeys)
                    _row = {}
                    if _std: _row[2] = _std
                    if _val: _row[3] = _val
                    if _concl: _row[4] = _concl
                    if _row:
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, _ri, _row, debug_notes=debug_notes, allow_blank=True)
                _work_std = _animal_std('work_illumination') or ''
                _animal_illu_std = _animal_std('animal_illumination') or ''
                _work_val = replacements.get('最低照度', '') or replacements.get('平均照度', '')
                _animal_illu_val = replacements.get('动物照度', '')
                _row8 = {}
                if _work_std: _row8[3] = _work_std
                if _work_val: _row8[4] = _work_val
                if _animal_concl('work_illumination', 'illumination'): _row8[5] = _animal_concl('work_illumination', 'illumination')
                if _row8: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, _row8, debug_notes=debug_notes, allow_blank=True)
                _row9 = {}
                if _animal_illu_std: _row9[3] = _animal_illu_std
                if _animal_illu_val: _row9[4] = _animal_illu_val
                if _animal_concl('animal_illumination'): _row9[5] = _animal_concl('animal_illumination')
                if _row9: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, _row9, debug_notes=debug_notes, allow_blank=True)

            # 其余分支暂保留旧逻辑，后续继续收口
            else:
                if animal_environment == '屏障环境' and barrier_room_class == '洁净辅房':
                    def _write_simple_row(_ri, _std_key, _value_key, *_ckeys):
                        _val = replacements.get(_value_key, '')
                        _std = _animal_std(_std_key) or ''
                        _concl = _animal_concl(*_ckeys)
                        _row = {}
                        if _std: _row[2] = _std
                        if _val: _row[3] = _val
                        if _concl: _row[4] = _concl
                        if _row:
                            return _replace_table_cell_by_table_and_row(document_xml, 3, _ri, _row, debug_notes=debug_notes, allow_blank=True)
                        return document_xml

                    if barrier_aux_room in {'污物走廊', '缓冲间'}:
                        document_xml = _write_simple_row(3, 'airchange', '换气次数', 'airchange_rate', 'airchange')
                        document_xml = _write_simple_row(4, 'pressure', '静压差', 'static_pressure_diff', 'pressure_diff', 'pressure')
                        document_xml = _write_simple_row(10, 'temperature_aux', '温度', 'temperature')
                        document_xml = _write_simple_row(11, 'humidity_aux', '相对湿度', 'relative_humidity', 'humidity')
                        document_xml = _write_simple_row(12, 'illumination_min', '最低照度', 'work_illumination', 'illumination')
                        document_xml = _write_simple_row(13, 'noise', '噪声', 'noise')
                    elif barrier_aux_room == '清洗消毒室':
                        document_xml = _write_simple_row(3, 'airchange', '换气次数', 'airchange_rate', 'airchange')
                        document_xml = _write_simple_row(10, 'temperature_aux', '温度', 'temperature')
                        document_xml = _write_simple_row(11, 'humidity_aux', '相对湿度', 'relative_humidity', 'humidity')
                        document_xml = _write_simple_row(12, 'illumination_min', '最低照度', 'work_illumination', 'illumination')
                        document_xml = _write_simple_row(13, 'noise', '噪声', 'noise')
                    elif barrier_aux_room == '一更':
                        document_xml = _write_simple_row(10, 'temperature_aux', '温度', 'temperature')
                        document_xml = _write_simple_row(11, 'humidity_aux', '相对湿度', 'relative_humidity', 'humidity')
                        document_xml = _write_simple_row(12, 'illumination_min', '最低照度', 'work_illumination', 'illumination')
                        document_xml = _write_simple_row(13, 'noise', '噪声', 'noise')
                    elif barrier_aux_room in {'洁物储存室', '灭菌后室/区', '洁净走廊', '二更'}:
                        _particle_item = get_param_item(_p_map, 'particle')
                        _particle_data = (_particle_item.get('data', {}) if isinstance(_particle_item, dict) else {}) or (_particle_item.get('values', {}) if isinstance(_particle_item, dict) else {}) or {}
                        _p05_max = str(_particle_data.get('p05_max', '') or _particle_data.get('max_0_5um', '') or replacements.get('≥0.5μm', '') or '')
                        _p05_ucl = str(_particle_data.get('p05_ucl', '') or _particle_data.get('ucl_0_5um', '') or replacements.get('0.5μmUCL', '') or '')
                        _p5_max = str(_particle_data.get('p5_max', '') or _particle_data.get('max_5um', '') or replacements.get('≥5μm', '') or '')
                        _p5_ucl = str(_particle_data.get('p5_ucl', '') or _particle_data.get('ucl_5um', '') or replacements.get('5μmUCL', '') or '')
                        _clean_aux_class = 'ISO-7'
                        _particle_range = _animal_std('particle') or ''
                        _range_05 = _range_5 = ''
                        if _particle_range:
                            import re as _re
                            for p in [x.strip() for x in _re.split(r'[，,]', _particle_range) if x.strip()]:
                                if '0.5μm' in p and not _range_05: _range_05 = p
                                elif '5μm' in p and '0.5μm' not in p and not _range_5: _range_5 = p
                        document_xml = _write_simple_row(3, 'airchange', '换气次数', 'airchange_rate', 'airchange')
                        document_xml = _write_simple_row(4, 'pressure', '静压差', 'static_pressure_diff', 'pressure_diff', 'pressure')
                        _row5 = {}
                        if _clean_aux_class: _row5[3] = _clean_aux_class; _row5[5] = _clean_aux_class
                        if _animal_concl('particle'): _row5[6] = _animal_concl('particle')
                        if _row5: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, _row5, debug_notes=debug_notes, allow_blank=True)
                        if _range_05 or _p05_max:
                            _r6 = {}
                            if _range_05: _r6[2] = _range_05
                            if _clean_aux_class: _r6[3] = _clean_aux_class
                            if _p05_max: _r6[5] = _p05_max
                            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _r6, debug_notes=debug_notes, allow_blank=True)
                        if _p05_ucl:
                            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, {5: _p05_ucl}, debug_notes=debug_notes, allow_blank=True)
                        if _range_5 or _p5_max:
                            _r8 = {}
                            if _range_5: _r8[2] = _range_5
                            if _p5_max: _r8[5] = _p5_max
                            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, _r8, debug_notes=debug_notes, allow_blank=True)
                        if _p5_ucl:
                            document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, {5: _p5_ucl}, debug_notes=debug_notes, allow_blank=True)
                        document_xml = _write_simple_row(10, 'temperature_aux', '温度', 'temperature')
                        document_xml = _write_simple_row(11, 'humidity_aux', '相对湿度', 'relative_humidity', 'humidity')
                        document_xml = _write_simple_row(12, 'illumination_min', '最低照度', 'work_illumination', 'illumination')
                        document_xml = _write_simple_row(13, 'noise', '噪声', 'noise')
                else:
                    if replacements.get('换气次数'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, {3: replacements.get('换气次数', '')}, debug_notes=debug_notes)
                    if replacements.get('静压差'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, {3: replacements.get('静压差', '')}, debug_notes=debug_notes)
                    if replacements.get('洁净度级别'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {5: replacements.get('洁净度级别', '')}, debug_notes=debug_notes)
                    if replacements.get('温度'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, {3: replacements.get('温度', '')}, debug_notes=debug_notes)
                    if replacements.get('相对湿度'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, {3: replacements.get('相对湿度', '')}, debug_notes=debug_notes)
                    if replacements.get('平均照度'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 16, {3: replacements.get('平均照度', '')}, debug_notes=debug_notes)
                    if replacements.get('噪声'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 17, {3: replacements.get('噪声', '')}, debug_notes=debug_notes)
                    if replacements.get('沉降菌'):
                        document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 18, {3: replacements.get('沉降菌', '')}, debug_notes=debug_notes)
        # 检测日期已通过 table_cell_replace_map 处理，不再重复 plain text 替换
        if replacements.get('洁净级别') or replacements.get('洁净等级') or replacements.get('手术室级别'):
            level_value = replacements.get('洁净级别', '') or replacements.get('洁净等级', '') or replacements.get('手术室级别', '')
            document_xml = _replace_first_plain_text(document_xml, '洁净度设计级别', level_value)
        if replacements.get('区域'):
            document_xml = _replace_table_value_by_left_label(document_xml, '区域', replacements.get('检测区域', ''), value_cell_offset=1)
        if replacements.get('洁净级别') and type_id not in {'bsl'}:
            document_xml = _replace_table_value_by_left_label(document_xml, '洁净度级别', replacements.get('洁净级别', ''), value_cell_offset=1, table_must_contain='委托单位')
            document_xml = _replace_table_value_by_left_label(document_xml, '级别', replacements.get('洁净级别', ''), value_cell_offset=1, table_must_contain='委托单位')
        if type_id not in {'clean_function_room', 'bsl', 'operating_room', 'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop', 'negative_pressure', 'animal_room'} and (replacements.get('洁净度级别') or replacements.get('悬浮粒子数/m³')):
            document_xml = _replace_table_row_cells_by_anchor(document_xml, '洁净度级别', {
                4: replacements.get('洁净度级别', ''),
                5: replacements.get('悬浮粒子数/m³', ''),
                6: replacements.get('洁净度', ''),
            })
        if type_id not in {'clean_function_room', 'bsl', 'operating_room', 'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop', 'negative_pressure', 'animal_room'} and (replacements.get('≥0.5μm') or replacements.get('0.5μmUCL')):
            document_xml = _replace_table_row_cells_by_anchor(document_xml, '≥0.5㎛：≤3520', {
                3: replacements.get('洁净度级别', ''),
                5: replacements.get('≥0.5μm', ''),
                6: replacements.get('0.5μmUCL', ''),
            })
        if type_id not in {'clean_function_room', 'bsl', 'operating_room', 'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop', 'negative_pressure', 'animal_room'} and (replacements.get('≥5μm') or replacements.get('5μmUCL')):
            document_xml = _replace_table_row_cells_by_anchor(document_xml, '≥5㎛：≤20', {
                3: replacements.get('洁净度级别', ''),
                5: replacements.get('≥5μm', ''),
                6: replacements.get('5μmUCL', ''),
            })
        if type_id not in {'clean_function_room', 'bsl', 'operating_room', 'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop', 'negative_pressure', 'animal_room'} and replacements.get('换气次数'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '换气次数', 1, {
                3: replacements.get('换气次数', ''),
            }, debug_notes=debug_notes)
        if type_id not in {'clean_function_room', 'bsl', 'operating_room', 'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop', 'negative_pressure', 'animal_room'} and replacements.get('静压差'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '静压差', 1, {
                3: replacements.get('静压差', ''),
            }, debug_notes=debug_notes)
        if replacements.get('洁净度结果'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '洁净度级别', 1, {
                6: replacements.get('洁净度结果', ''),
            }, debug_notes=debug_notes)
        if replacements.get('细菌浓度（沉降法）手术区'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '手术区', 2, {
                4: replacements.get('细菌浓度（沉降法）手术区', ''),
            }, debug_notes=debug_notes)
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '手术区', 1, {
                4: replacements.get('细菌浓度（沉降法）手术区', ''),
            }, debug_notes=debug_notes)
        if replacements.get('细菌浓度（沉降法）周边区'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '周边区', 2, {
                4: replacements.get('细菌浓度（沉降法）周边区', ''),
            }, debug_notes=debug_notes)
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '周边区', 1, {
                4: replacements.get('细菌浓度（沉降法）周边区', ''),
            }, debug_notes=debug_notes)
        if replacements.get('手术区≥0.5μm最大值') or replacements.get('手术区≥0.5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '手术区', 0, {
                7: replacements.get('手术区≥0.5μm最大值', ''),
            }, debug_notes=debug_notes)
        if replacements.get('手术区≥0.5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '95%置信度', 0, {
                6: replacements.get('手术区≥0.5μmUCL', ''),
            }, debug_notes=debug_notes)
        if replacements.get('手术区≥5μm最大值') or replacements.get('手术区≥5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '≥5㎛：≤2930', 0, {
                6: replacements.get('手术区≥5μm最大值', ''),
            }, debug_notes=debug_notes)
        if replacements.get('手术区≥5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '95%置信度', 1, {
                6: replacements.get('手术区≥5μmUCL', ''),
            }, debug_notes=debug_notes)
        if replacements.get('周边区≥0.5μm最大值') or replacements.get('周边区≥0.5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '周边区', 0, {
                7: replacements.get('周边区≥0.5μm最大值', ''),
            }, debug_notes=debug_notes)
        if replacements.get('周边区≥0.5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '95%置信度', 2, {
                6: replacements.get('周边区≥0.5μmUCL', ''),
            }, debug_notes=debug_notes)
        if replacements.get('周边区≥5μm最大值') or replacements.get('周边区≥5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '≥5㎛：≤29300', 0, {
                6: replacements.get('周边区≥5μm最大值', ''),
            }, debug_notes=debug_notes)
        if replacements.get('周边区≥5μmUCL'):
            document_xml = _replace_table_row_cells_by_anchor_index(document_xml, '95%置信度', 3, {
                6: replacements.get('周边区≥5μmUCL', ''),
            }, debug_notes=debug_notes)
        # bsc / clean_bench / ivc：设备类 Word 填充（逐字段替换）
        elif type_id == 'bsc':
            # 结论表中的数值参数 → 写入“检测结果”列
            if replacements.get('下降气流平均风速'):
                document_xml = _replace_result_table_cell(document_xml, '下降气流', replacements.get('下降气流平均风速', ''))
            if replacements.get('流入气流平均风速'):
                document_xml = _replace_result_table_cell(document_xml, '流入气流', replacements.get('流入气流平均风速', ''))
            if replacements.get('气流模式'):
                document_xml = _replace_result_table_cell(document_xml, '气流模式', replacements.get('气流模式', ''))
            if replacements.get('高效过滤器完整性') or replacements.get('高效过滤器检漏'):
                val = replacements.get('高效过滤器完整性') or replacements.get('高效过滤器检漏', '')
                document_xml = _replace_result_table_cell(document_xml, '高效过滤器', val)
            if replacements.get('噪声'):
                document_xml = _replace_result_table_cell(document_xml, '噪声', replacements.get('噪声', ''))
            if replacements.get('照度') or replacements.get('平均照度'):
                val = replacements.get('照度') or replacements.get('平均照度', '')
                document_xml = _replace_result_table_cell(document_xml, '照度', val)
            if replacements.get('紫外灯辐照强度'):
                document_xml = _replace_result_table_cell(document_xml, '紫外灯', replacements.get('紫外灯辐照强度', ''))
            # 信息页表格中的型号/类型 → 用 table_cell
            if replacements.get('生物安全柜型号'):
                document_xml = _replace_table_value_by_left_label(document_xml, '型号', replacements.get('生物安全柜型号', ''), value_cell_offset=1)
            if replacements.get('生物安全柜类型'):
                document_xml = _replace_table_value_by_left_label(document_xml, '类型', replacements.get('生物安全柜类型', ''), value_cell_offset=1)
        elif type_id == 'clean_bench':
            # 结论表中的数值参数 → 写入“检测结果”列（第3列）
            if replacements.get('平均风速') or replacements.get('垂直气流平均风速'):
                val = replacements.get('平均风速') or replacements.get('垂直气流平均风速', '')
                document_xml = _replace_result_table_cell(document_xml, '垂直气流平均风速', val)
            if replacements.get('风速不均匀度'):
                document_xml = _replace_result_table_cell(document_xml, '风速不均匀度', replacements.get('风速不均匀度', ''))
            if replacements.get('沉降菌浓度') or replacements.get('沉降菌'):
                val = replacements.get('沉降菌浓度') or replacements.get('沉降菌', '')
                document_xml = _replace_result_table_cell(document_xml, '沉降菌', val)
            if replacements.get('噪声'):
                document_xml = _replace_result_table_cell(document_xml, '噪声', replacements.get('噪声', ''))
            if replacements.get('照度') or replacements.get('平均照度'):
                val = replacements.get('照度') or replacements.get('平均照度', '')
                document_xml = _replace_result_table_cell(document_xml, '平均照度', val)
            if replacements.get('高效过滤器检漏') or replacements.get('送风高效过滤器检漏'):
                val = replacements.get('高效过滤器检漏') or replacements.get('送风高效过滤器检漏', '')
                document_xml = _replace_result_table_cell(document_xml, '扫描检漏', val)
            # 信息页表格中的型号 → 仍用 table_cell
            if replacements.get('工作台型号'):
                document_xml = _replace_table_value_by_left_label(document_xml, '型号', replacements.get('工作台型号', ''), value_cell_offset=1)
        elif type_id == 'ivc':
            # 结论表中的数值参数 → 写入“检测结果”列
            if replacements.get('气流流速') or replacements.get('平均风速'):
                val = replacements.get('气流流速') or replacements.get('平均风速', '')
                document_xml = _replace_result_table_cell(document_xml, '气流流速', val)
            if replacements.get('换气次数'):
                document_xml = _replace_result_table_cell(document_xml, '换气次数', replacements.get('换气次数', ''))
            if replacements.get('静压差') or replacements.get('箱体静压差'):
                val = replacements.get('静压差') or replacements.get('箱体静压差', '')
                document_xml = _replace_result_table_cell(document_xml, '静压差', val)
            if replacements.get('笼盒气密性'):
                document_xml = _replace_result_table_cell(document_xml, '气密性', replacements.get('笼盒气密性', ''))
            if replacements.get('高效过滤器完整性') or replacements.get('高效过滤器检漏'):
                val = replacements.get('高效过滤器完整性') or replacements.get('高效过滤器检漏', '')
                document_xml = _replace_result_table_cell(document_xml, '高效过滤器', val)
            # 信息页表格中的型号/笼具数量 → 用 table_cell
            if replacements.get('IVC型号'):
                document_xml = _replace_table_value_by_left_label(document_xml, '型号', replacements.get('IVC型号', ''), value_cell_offset=1)
            if replacements.get('笼具数量'):
                document_xml = _replace_table_value_by_left_label(document_xml, '笼具数量', replacements.get('笼具数量', ''), value_cell_offset=1)
        # ---------- BSC / clean_bench / IVC 专项单项结论 + 粒子填充 ----------
        if type_id == 'bsc':
            _bsc_pm = build_param_map(room.get('params'))
            # TABLE 3 qualitative
            _bsc_appear_item = get_param_item(_bsc_pm, 'appearance', '外观')
            if isinstance(_bsc_appear_item, dict):
                _av = _bsc_appear_item.get('values', [])
                _val = str(_av[0]) if isinstance(_av, list) and _av else ''
                _concl = _normalize_conclusion_text(str(_bsc_appear_item.get('result', '') or ''))
                _r = {};
                if _val: _r[3] = _val
                if _concl: _r[4] = _concl
                if _r: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, _r, debug_notes=debug_notes, allow_blank=True)
            _bsc_alarm_item = get_param_item(_bsc_pm, 'alarm_interlock', '报警和联锁系统')
            if isinstance(_bsc_alarm_item, dict):
                _av = _bsc_alarm_item.get('values', [])
                _val = str(_av[0]) if isinstance(_av, list) and _av else ''
                _concl = _normalize_conclusion_text(str(_bsc_alarm_item.get('result', '') or ''))
                _r = {};
                if _val: _r[3] = _val
                if _concl: _r[4] = _concl
                if _r: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, _r, debug_notes=debug_notes, allow_blank=True)
            # TABLE 3 ROW 5: 下降气流结论
            _c5 = _normalize_conclusion_text(get_param_result(_bsc_pm, 'downflow_speed', '下降气流流速'))
            if _c5: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, {4: _c5}, debug_notes=debug_notes, allow_blank=True)
            # TABLE 3 ROW 6: 流入气流结论
            _c6 = _normalize_conclusion_text(get_param_result(_bsc_pm, 'inflow_speed', '流入气流流速'))
            if _c6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, {4: _c6}, debug_notes=debug_notes, allow_blank=True)
            # TABLE 3 ROW 7: 气流烟雾模式
            _bsc_af_item = get_param_item(_bsc_pm, 'airflow_pattern', '气流烟雾模式')
            if isinstance(_bsc_af_item, dict):
                _av = _bsc_af_item.get('values', [])
                _val = str(_av[0]) if isinstance(_av, list) and _av else ''
                _concl = _normalize_conclusion_text(str(_bsc_af_item.get('result', '') or ''))
                _r = {};
                if _val: _r[3] = _val
                if _concl: _r[4] = _concl
                if _r: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, _r, debug_notes=debug_notes, allow_blank=True)
            # TABLE 3 ROW 11: 高效检漏结论
            _c11 = _normalize_conclusion_text(get_param_result(_bsc_pm, 'hepa_leak', '高效过滤器检漏'))
            if _c11: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, {4: _c11}, debug_notes=debug_notes, allow_blank=True)
            # TABLE 4: 粒子 + 噪声 + 照度 + 紫外结论
            _bsc_pi = get_param_item(_bsc_pm, 'particle')
            _bsc_pd = (_bsc_pi.get('data', {}) if isinstance(_bsc_pi, dict) else {}) or {}
            _bp05m = str(_bsc_pd.get('p05_max', '') or ''); _bp05u = str(_bsc_pd.get('p05_ucl', '') or '')
            _bp5m = str(_bsc_pd.get('p5_max', '') or ''); _bp5u = str(_bsc_pd.get('p5_ucl', '') or '')
            _bpc = _normalize_conclusion_text(get_param_result(_bsc_pm, 'particle'))
            if _bpc: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 1, {6: _bpc}, debug_notes=debug_notes, allow_blank=True)
            if _bp05m: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 2, {5: _bp05m}, debug_notes=debug_notes, allow_blank=True)
            if _bp05u: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 3, {5: _bp05u}, debug_notes=debug_notes, allow_blank=True)
            if _bp5m: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 4, {5: _bp5m}, debug_notes=debug_notes, allow_blank=True)
            if _bp5u: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 5, {5: _bp5u}, debug_notes=debug_notes, allow_blank=True)
            _cn6 = _normalize_conclusion_text(get_param_result(_bsc_pm, 'noise', '噪声'))
            if _cn6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 6, {4: _cn6}, debug_notes=debug_notes, allow_blank=True)
            _ci7 = _normalize_conclusion_text(get_param_result(_bsc_pm, 'illumination', '照度'))
            if _ci7: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 7, {4: _ci7}, debug_notes=debug_notes, allow_blank=True)
            _cuv = _normalize_conclusion_text(get_param_result(_bsc_pm, 'uv_intensity', '紫外灯辐照强度'))
            if _cuv: document_xml = _replace_table_cell_by_table_and_row(document_xml, 4, 12, {4: _cuv}, debug_notes=debug_notes, allow_blank=True)
        elif type_id == 'clean_bench':
            _cb_pm = build_param_map(room.get('params'))
            # TABLE 3 qualitative
            _cb_appear = get_param_item(_cb_pm, 'appearance', '外观')
            if isinstance(_cb_appear, dict):
                _av = _cb_appear.get('values', [])
                _val = str(_av[0]) if isinstance(_av, list) and _av else ''
                _concl = _normalize_conclusion_text(str(_cb_appear.get('result', '') or ''))
                _r = {};
                if _val: _r[3] = _val
                if _concl: _r[4] = _concl
                if _r: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, _r, debug_notes=debug_notes, allow_blank=True)
            _cb_func = get_param_item(_cb_pm, 'function', '功能')
            if isinstance(_cb_func, dict):
                _av = _cb_func.get('values', [])
                _val = str(_av[0]) if isinstance(_av, list) and _av else ''
                _concl = _normalize_conclusion_text(str(_cb_func.get('result', '') or ''))
                _r = {};
                if _val: _r[3] = _val
                if _concl: _r[4] = _concl
                if _r: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, _r, debug_notes=debug_notes, allow_blank=True)
            # ROW 6 检漏结论, ROW 7 风速结论, ROW 8 不均匀度结论
            _cc6 = _normalize_conclusion_text(get_param_result(_cb_pm, 'hepa_leak', '高效过滤器检漏'))
            if _cc6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, {4: _cc6}, debug_notes=debug_notes, allow_blank=True)
            _cc7 = _normalize_conclusion_text(get_param_result(_cb_pm, 'avg_speed', '垂直气流平均风速'))
            if _cc7: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, {4: _cc7}, debug_notes=debug_notes, allow_blank=True)
            _cc8 = _normalize_conclusion_text(get_param_result(_cb_pm, 'speed_uniformity', '风速不均匀度'))
            if _cc8: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {4: _cc8}, debug_notes=debug_notes, allow_blank=True)
            # ROW 9: 洁净度结论
            _cb_pc = _normalize_conclusion_text(get_param_result(_cb_pm, 'particle'))
            if _cb_pc: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, {6: _cb_pc}, debug_notes=debug_notes, allow_blank=True)
            # ROW 10-13: 粒子值
            _cb_pi = get_param_item(_cb_pm, 'particle')
            _cb_pd = (_cb_pi.get('data', {}) if isinstance(_cb_pi, dict) else {}) or {}
            _cp05m = str(_cb_pd.get('p05_max', '') or ''); _cp05u = str(_cb_pd.get('p05_ucl', '') or '')
            _cp5m = str(_cb_pd.get('p5_max', '') or ''); _cp5u = str(_cb_pd.get('p5_ucl', '') or '')
            if _cp05m: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {5: _cp05m}, debug_notes=debug_notes, allow_blank=True)
            if _cp05u: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, {5: _cp05u}, debug_notes=debug_notes, allow_blank=True)
            if _cp5m: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, {5: _cp5m}, debug_notes=debug_notes, allow_blank=True)
            if _cp5u: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, {5: _cp5u}, debug_notes=debug_notes, allow_blank=True)
            # ROW 14-17 结论
            _cc14 = _normalize_conclusion_text(get_param_result(_cb_pm, 'settling', '沉降菌'))
            if _cc14: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, {4: _cc14}, debug_notes=debug_notes, allow_blank=True)
            _cb_af = get_param_item(_cb_pm, 'airflow_pattern', '气流状态')
            if isinstance(_cb_af, dict):
                _av = _cb_af.get('values', [])
                _val = str(_av[0]) if isinstance(_av, list) and _av else ''
                _concl = _normalize_conclusion_text(str(_cb_af.get('result', '') or ''))
                _r = {};
                if _val: _r[3] = _val
                if _concl: _r[4] = _concl
                if _r: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 15, _r, debug_notes=debug_notes, allow_blank=True)
            _cc16 = _normalize_conclusion_text(get_param_result(_cb_pm, 'illumination', '照度', '平均照度'))
            if _cc16: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 16, {4: _cc16}, debug_notes=debug_notes, allow_blank=True)
            _cc17 = _normalize_conclusion_text(get_param_result(_cb_pm, 'noise', '噪声'))
            if _cc17: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 17, {4: _cc17}, debug_notes=debug_notes, allow_blank=True)
        elif type_id == 'ivc':
            _ivc_pm = build_param_map(room.get('params'))
            # ROW 1-4 结论
            _ic1 = _normalize_conclusion_text(get_param_result(_ivc_pm, 'airflow_speed', '气流流速'))
            if _ic1: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, {4: _ic1}, debug_notes=debug_notes, allow_blank=True)
            _ic2 = _normalize_conclusion_text(get_param_result(_ivc_pm, 'airchange', '换气次数'))
            if _ic2: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 2, {4: _ic2}, debug_notes=debug_notes, allow_blank=True)
            _ic3 = _normalize_conclusion_text(get_param_result(_ivc_pm, 'pressure', '箱体静压差', '静压差'))
            if _ic3: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, {4: _ic3}, debug_notes=debug_notes, allow_blank=True)
            # ROW 4: 笼盒气密性 值+结论
            _ivc_seal_val = get_param_value(_ivc_pm, 'cage_airtightness', '笼盒气密性') or ''
            _ivc_seal_concl = _normalize_conclusion_text(get_param_result(_ivc_pm, 'cage_airtightness', '笼盒气密性'))
            _r4 = {}
            if _ivc_seal_val: _r4[3] = _ivc_seal_val
            if _ivc_seal_concl: _r4[4] = _ivc_seal_concl
            if _r4: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, _r4, debug_notes=debug_notes, allow_blank=True)
            # ROW 5-6: HEPA supply/exhaust 值+结论
            _ivc_hs_item = get_param_item(_ivc_pm, 'hepa_leak_supply', '送风高效检漏')
            _ivc_hs_val = ''
            if isinstance(_ivc_hs_item, dict):
                _hv = _ivc_hs_item.get('values', [])
                if isinstance(_hv, list) and _hv: _ivc_hs_val = str(_hv[0]).strip()
            _ivc_hs_concl = _normalize_conclusion_text(get_param_result(_ivc_pm, 'hepa_leak_supply', '送风高效检漏'))
            _r5 = {}
            if _ivc_hs_val: _r5[4] = _ivc_hs_val
            if _ivc_hs_concl: _r5[5] = _ivc_hs_concl
            if _r5: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, _r5, debug_notes=debug_notes, allow_blank=True)
            _ivc_he_item = get_param_item(_ivc_pm, 'hepa_leak_exhaust', '排风高效检漏')
            _ivc_he_val = ''
            if isinstance(_ivc_he_item, dict):
                _hv = _ivc_he_item.get('values', [])
                if isinstance(_hv, list) and _hv: _ivc_he_val = str(_hv[0]).strip()
            _ivc_he_concl = _normalize_conclusion_text(get_param_result(_ivc_pm, 'hepa_leak_exhaust', '排风高效检漏'))
            _r6 = {}
            if _ivc_he_val: _r6[4] = _ivc_he_val
            if _ivc_he_concl: _r6[5] = _ivc_he_concl
            if _r6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _r6, debug_notes=debug_notes, allow_blank=True)
        # 层流罩专项：项目名称 run 分裂，用 label='名称：' 的方式填入
        if type_id == 'laminar_hood' and replacements.get('项目名称'):
            document_xml = _replace_first_plain_text(document_xml, '名称：', replacements.get('项目名称', ''))
        # ---------- 层流罩 TABLE 3 专项填充 ----------
        if type_id == 'laminar_hood':
            _lh_param_map = build_param_map(room.get('params'))
            _lh_avg_speed = get_param_value(_lh_param_map, 'avg_speed', 'airflow_speed', 'wind_speed', '平均风速') or ''
            _lh_speed_unif = get_param_value(_lh_param_map, 'speed_uniformity', 'wind_uniformity', '风速不均匀度') or ''
            _lh_airflow_item = get_param_item(_lh_param_map, 'airflow_pattern', '气流流型')
            _lh_airflow = ''
            if isinstance(_lh_airflow_item, dict):
                _af_vals = _lh_airflow_item.get('values', [])
                if _af_vals and isinstance(_af_vals, list) and len(_af_vals) > 0:
                    _lh_airflow = str(_af_vals[0])
                if not _lh_airflow:
                    _lh_airflow = _normalize_conclusion_text(str(_lh_airflow_item.get('result', '') or ''))
            _lh_airflow_concl = _normalize_conclusion_text(get_param_result(_lh_param_map, 'airflow_pattern', '气流流型'))
            _lh_hepa_item = get_param_item(_lh_param_map, 'hepa_leak', '高效过滤器检漏', '送风高效过滤器检漏')
            _lh_hepa = ''
            if isinstance(_lh_hepa_item, dict):
                _hv = _lh_hepa_item.get('values', [])
                if isinstance(_hv, list) and _hv:
                    _lh_hepa = str(_hv[0]).strip()
                if not _lh_hepa:
                    _lh_hepa = _strip_emoji(str(_lh_hepa_item.get('result', '') or '')).strip()
            _lh_hepa_concl = _normalize_conclusion_text(get_param_result(_lh_param_map, 'hepa_leak', '高效过滤器检漏', '送风高效过滤器检漏'))
            _lh_speed_concl = _normalize_conclusion_text(get_param_result(_lh_param_map, 'avg_speed', 'airflow_speed', 'wind_speed', '平均风速'))
            _lh_unif_concl = _normalize_conclusion_text(get_param_result(_lh_param_map, 'speed_uniformity', 'wind_uniformity', '风速不均匀度'))
            _lh_particle_item = get_param_item(_lh_param_map, 'particle')
            _lh_particle_data = (_lh_particle_item.get('data', {}) if isinstance(_lh_particle_item, dict) else {}) or {}
            _lh_p05_max = str(_lh_particle_data.get('p05_max', '') or _lh_particle_data.get('max_0_5um', '') or '')
            _lh_p05_ucl = str(_lh_particle_data.get('p05_ucl', '') or _lh_particle_data.get('ucl_0_5um', '') or '')
            _lh_p5_max = str(_lh_particle_data.get('p5_max', '') or _lh_particle_data.get('max_5um', '') or '')
            _lh_p5_ucl = str(_lh_particle_data.get('p5_ucl', '') or _lh_particle_data.get('ucl_5um', '') or '')
            _lh_particle_concl = _normalize_conclusion_text(get_param_result(_lh_param_map, 'particle'))
            _lh_clean_class = replacements.get('洁净度级别', '') or room.get('clean_class', '') or room.get('level_name', '')
            _lh_report_ctx = export_payload.get('report_context', {})
            _lh_project_ctx = _lh_report_ctx.get('project_context', {})
            _lh_room_ctx = _lh_report_ctx.get('room_context', {})
            _lh_room_name = _lh_room_ctx.get('detection_area', '') or room.get('room_name', '')
            _lh_detection_date = _lh_project_ctx.get('detection_date', '')
            _lh_device_name = room.get('type_name', '') or '层流罩'
            # ROW 0: 受检设备名称 + 检测日期
            _r0 = {}
            if _lh_device_name: _r0[1] = _lh_device_name
            if _lh_detection_date: _r0[3] = _lh_detection_date
            if _r0: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, _r0, debug_notes=debug_notes, allow_blank=True)
            # ROW 1: 受控编号 + 所在房间
            _r1 = {}
            if _lh_room_name: _r1[3] = _lh_room_name
            if _r1: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 1, _r1, debug_notes=debug_notes, allow_blank=True)
            # ROW 3: 垂直气流平均风速
            _r3 = {}
            if _lh_avg_speed: _r3[3] = _lh_avg_speed
            if _lh_speed_concl: _r3[4] = _lh_speed_concl
            if _r3: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, _r3, debug_notes=debug_notes, allow_blank=True)
            # ROW 4: 风速不均匀度
            _r4 = {}
            if _lh_speed_unif: _r4[3] = _lh_speed_unif
            if _lh_unif_concl: _r4[4] = _lh_unif_concl
            if _r4: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 4, _r4, debug_notes=debug_notes, allow_blank=True)
            # ROW 5: 气流流型
            _r5 = {}
            if _lh_airflow: _r5[3] = _lh_airflow
            if _lh_airflow_concl: _r5[4] = _lh_airflow_concl
            if _r5: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 5, _r5, debug_notes=debug_notes, allow_blank=True)
            # ROW 6: 送风高效过滤器检漏
            _r6 = {}
            if _lh_hepa: _r6[3] = _lh_hepa
            if _lh_hepa_concl: _r6[4] = _lh_hepa_concl
            if _r6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _r6, debug_notes=debug_notes, allow_blank=True)
            # ROW 7: 洁净度级别头行
            _r7 = {}
            if _lh_clean_class: _r7[3] = _lh_clean_class
            if _lh_particle_concl: _r7[6] = _lh_particle_concl
            if _r7: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 7, _r7, debug_notes=debug_notes, allow_blank=True)
            # ROW 8: 0.5μm max
            if _lh_p05_max:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, {5: _lh_p05_max}, debug_notes=debug_notes, allow_blank=True)
            # ROW 9: 0.5μm UCL
            if _lh_p05_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, {5: _lh_p05_ucl}, debug_notes=debug_notes, allow_blank=True)
            # ROW 10: 5μm max
            if _lh_p5_max:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {5: _lh_p5_max}, debug_notes=debug_notes, allow_blank=True)
            # ROW 11: 5μm UCL
            if _lh_p5_ucl:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, {5: _lh_p5_ucl}, debug_notes=debug_notes, allow_blank=True)
        # 传递窗专项：所在房间 直接按表格/行/列索引填入（表3行0 tc[5] 是合并占位格，无文字内容，需用 _force_set_cell_content）
        if type_id == 'pass_box':
            if replacements.get('所在房间'):
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, {5: replacements.get('所在房间', '')})
            if replacements.get('项目名称'):
                document_xml = _replace_first_plain_text(document_xml, '名称：', replacements.get('项目名称', ''))
        # ---------- 传递窗 TABLE 3 专项填充 ----------
        if type_id == 'pass_box':
            _pb_param_map = build_param_map(room.get('params'))
            _pb_report_ctx = export_payload.get('report_context', {})
            _pb_project_ctx = _pb_report_ctx.get('project_context', {})
            _pb_room_ctx = _pb_report_ctx.get('room_context', {})
            _pb_room_name = room.get('context', {}).get('detection_area', '') or room.get('room_name', '')
            _pb_device_name = room.get('type_name', '') or '传递窗'
            # ROW 0: 样品名称 + 所在房间
            _r0 = {}
            if _pb_device_name: _r0[1] = _pb_device_name
            if _pb_room_name: _r0[3] = _pb_room_name
            if _r0: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 0, _r0, debug_notes=debug_notes, allow_blank=True)
            # ROW 3: 外观检验 结果+结论
            _pb_appear_item = get_param_item(_pb_param_map, 'appearance', '外观检验')
            if isinstance(_pb_appear_item, dict):
                _av = _pb_appear_item.get('values', [])
                _pb_appear_val = str(_av[0]) if isinstance(_av, list) and _av else ''
                _pb_appear_concl = _normalize_conclusion_text(str(_pb_appear_item.get('result', '') or ''))
                _r3 = {}
                if _pb_appear_val: _r3[3] = _pb_appear_val
                if _pb_appear_concl: _r3[4] = _pb_appear_concl
                if _r3: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 3, _r3, debug_notes=debug_notes, allow_blank=True)
            # ROW 6: 门互锁功能 结果+结论
            _pb_door_item = get_param_item(_pb_param_map, 'door_interlock', '门互锁功能')
            if isinstance(_pb_door_item, dict):
                _dv = _pb_door_item.get('values', [])
                _pb_door_val = str(_dv[0]) if isinstance(_dv, list) and _dv else ''
                _pb_door_concl = _normalize_conclusion_text(str(_pb_door_item.get('result', '') or ''))
                _r6 = {}
                if _pb_door_val: _r6[3] = _pb_door_val
                if _pb_door_concl: _r6[4] = _pb_door_concl
                if _r6: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 6, _r6, debug_notes=debug_notes, allow_blank=True)
            # ROW 8: 换气次数 值+结论
            _pb_air_val = get_param_value(_pb_param_map, 'airchange_b12', 'airchange', '换气次数') or ''
            _pb_air_concl = _normalize_conclusion_text(get_param_result(_pb_param_map, 'airchange_b12', 'airchange', '换气次数'))
            _r8 = {}
            if _pb_air_val: _r8[3] = _pb_air_val
            if _pb_air_concl: _r8[4] = _pb_air_concl
            if _r8:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 8, _r8, debug_notes=debug_notes, allow_blank=True)
            # ROW 9: 洁净度级别头行
            _pb_particle_concl = _normalize_conclusion_text(get_param_result(_pb_param_map, 'particle'))
            _r9 = {}
            if _pb_particle_concl: _r9[6] = _pb_particle_concl
            if _r9: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 9, _r9, debug_notes=debug_notes, allow_blank=True)
            # ROW 10-13: 粒子值
            _pb_particle_item = get_param_item(_pb_param_map, 'particle')
            _pb_pd = (_pb_particle_item.get('data', {}) if isinstance(_pb_particle_item, dict) else {}) or {}
            _pb_p05_max = str(_pb_pd.get('p05_max', '') or _pb_pd.get('max_0_5um', '') or '')
            _pb_p05_ucl = str(_pb_pd.get('p05_ucl', '') or _pb_pd.get('ucl_0_5um', '') or '')
            _pb_p5_max = str(_pb_pd.get('p5_max', '') or _pb_pd.get('max_5um', '') or '')
            _pb_p5_ucl = str(_pb_pd.get('p5_ucl', '') or _pb_pd.get('ucl_5um', '') or '')
            if _pb_p05_max: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 10, {5: _pb_p05_max}, debug_notes=debug_notes, allow_blank=True)
            if _pb_p05_ucl: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 11, {5: _pb_p05_ucl}, debug_notes=debug_notes, allow_blank=True)
            if _pb_p5_max: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 12, {5: _pb_p5_max}, debug_notes=debug_notes, allow_blank=True)
            if _pb_p5_ucl: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 13, {5: _pb_p5_ucl}, debug_notes=debug_notes, allow_blank=True)
            # ROW 14: 噪声 值+结论
            _pb_noise_val = get_param_value(_pb_param_map, 'noise', '噪声') or ''
            if _pb_noise_val:
                import re as _re_pb
                _pb_noise_val = _re_pb.sub(r'\s*dB\(A\).*', '', _pb_noise_val).strip()
            _pb_noise_concl = _normalize_conclusion_text(get_param_result(_pb_param_map, 'noise', '噪声'))
            _r14 = {}
            if _pb_noise_val: _r14[3] = _pb_noise_val
            if _pb_noise_concl: _r14[4] = _pb_noise_concl
            if _r14:
                document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 14, _r14, debug_notes=debug_notes, allow_blank=True)
            # ROW 15: 高效过滤器检漏 值+结论
            _pb_hepa_item = get_param_item(_pb_param_map, 'hepa_leak', '高效过滤器检漏')
            _pb_hepa_val = ''
            if isinstance(_pb_hepa_item, dict):
                _hv = _pb_hepa_item.get('values', [])
                if isinstance(_hv, list) and _hv: _pb_hepa_val = str(_hv[0]).strip()
                if not _pb_hepa_val: _pb_hepa_val = _strip_emoji(str(_pb_hepa_item.get('result','') or '')).strip()
            _pb_hepa_concl = _normalize_conclusion_text(get_param_result(_pb_param_map, 'hepa_leak', '高效过滤器检漏'))
            _r15 = {}
            if _pb_hepa_val: _r15[3] = _pb_hepa_val
            if _pb_hepa_concl: _r15[4] = _pb_hepa_concl
            if _r15: document_xml = _replace_table_cell_by_table_and_row(document_xml, 3, 15, _r15, debug_notes=debug_notes, allow_blank=True)
        # ===== 通用结论表参数填充 =====
        # 将 fill plan 中的参数值写入结论表的“检测结果”列（第3列）
        # 设备类对象已在上方专项代码块中处理，此处补全房间类对象
        _RESULT_TABLE_LABELS = [
            # 换气/风速类
            '换气次数', '静压差', '截面风速',
            '污染区换气次数', '清洁区换气次数',
            '排风口风速', '动物笼具处气流速度',
            '风速不均匀度',
            # 压差类
            '静压差',
            # 温湿度类
            '温度', '相对湿度', '湿度', '最大日温差',
            # 噪声/照度类
            '噪声', '平均照度', '照度', '最低照度',
            '照度均匀度', '动物照度',
            # 菌类
            '沉降菌（平均菌落数）', '沉降菌浓度', '细菌浓度(沉降法)',
            '浮游菌（平均浓度）', '物体表面微生物',
            # 其他
            '气流流向', '严密性', '自净时间', '气流流型',
            '送风高效过滤器检漏',
        ]
        _CONCLUSION_TABLE_LABELS = [
            '换气次数', '静压差', '截面风速', '风速不均匀度',
            '静压差', '温度', '相对湿度', '湿度', '噪声',
            '平均照度', '照度', '最低照度', '照度均匀度',
            '沉降菌（平均菌落数）', '沉降菌浓度', '细菌浓度(沉降法)',
            '浮游菌（平均浓度）', '物体表面微生物',
            '气流流向', '严密性', '自净时间', '气流流型',
            '送风高效过滤器检漏',
        ]
        _CONCLUSION_ALIAS_MAP = {
            '换气次数': '换气次数结果',
            '静压差': '截面风速结果',
            '截面风速': '截面风速结果',
            '静压差': '静压差结果',
            '温度': '温度结果',
            '相对湿度': '相对湿度结果',
            '湿度': '相对湿度结果',
            '噪声': '噪声结果',
            '平均照度': '照度结果',
            '照度': '照度结果',
            '送风高效过滤器检漏': '高效过滤器检漏结果',
            '气流流型': '气流流型结果',
            '洁净度': '洁净度结果',
        }
        _TYPES_WITH_SPECIFIC_RESULT_HANDLERS = (
            'bsc', 'clean_bench', 'ivc', 'operating_room', 'gmp_workshop', 'veterinary_gmp_workshop', 'food_workshop', 'electronics_workshop', 'negative_pressure', 'animal_room', 'laminar_hood', 'pass_box',
        )
        if type_id not in _TYPES_WITH_SPECIFIC_RESULT_HANDLERS:
            # Exclude labels already handled by table_cell_replace_map to avoid double-write
            _skip = set(table_cell_replace_map.keys())
            for lbl in _RESULT_TABLE_LABELS:
                if lbl in _skip:
                    continue
                val = replacements.get(lbl, '')
                if val:
                    document_xml = _replace_result_table_cell(document_xml, lbl, val)
            for lbl in _CONCLUSION_TABLE_LABELS:
                conclusion_val = ''
                for key in [
                    _CONCLUSION_ALIAS_MAP.get(lbl, ''),
                    f'{lbl}结果',
                    lbl,
                ]:
                    if not key:
                        continue
                    conclusion_val = _normalize_conclusion_text(replacements.get(key, ''))
                    if conclusion_val:
                        break
                if conclusion_val:
                    document_xml = _replace_conclusion_table_cell(document_xml, lbl, conclusion_val)
        if type_id == 'operating_room':
            # operating_room 在模板层必须拆成三套结构：主手术室 / 眼科手术室 / 洁净辅房。
            # 眼科与主手术室主体结构一致，辅房结构独立，不能再共用同一套 row map。

            _or_context = room.get('context', {}) if isinstance(room.get('context', {}), dict) else {}
            _branch_mode = ((room.get('business_context') or {}).get('branch_mode') or '').strip() or (
                'auxiliary-room' if _or_context.get('surgery_aux_room') or _or_context.get('surgery_aux_clean_class') else 'main-operating-room'
            )
            _is_aux_room = _branch_mode == 'auxiliary-room'

            # --- 检测模板变体：统计 TABLE 3 实际行数 ---
            _tbl3_row_count = 0
            try:
                import re as _re_op
                _op_tbl_pat = _re_op.compile(r'<w:tbl\b.*?</w:tbl>', _re_op.S)
                _op_row_pat = _re_op.compile(r'<w:tr\b.*?</w:tr>', _re_op.S)
                _op_tbls = list(_op_tbl_pat.finditer(document_xml))
                if len(_op_tbls) > 3:
                    _tbl3_row_count = len(_op_row_pat.findall(_op_tbls[3].group(0)))
            except Exception:
                pass

            if _is_aux_room:
                if _tbl3_row_count >= 22:
                    _op_variant = 'aux_level1'
                elif _tbl3_row_count >= 17:
                    _op_variant = 'aux_level234'
                else:
                    _op_variant = 'aux_level234'
            else:
                if _tbl3_row_count >= 29:
                    _op_variant = 'level1'
                elif _tbl3_row_count >= 24:
                    _op_variant = 'level23'
                else:
                    _op_variant = 'level4'

            _op_clean_class = room.get('clean_class', '') or room.get('level_name', '')
            _op_std_ranges = {}
            _surgery_room_type_for_std = (_or_context or {}).get('surgery_room_type', '')
            try:
                import os as _os
                _std_path = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), 'static', 'standards_ranges.json')
                with open(_std_path, 'r', encoding='utf-8') as _sf:
                    _std_db = json.load(_sf)
                if _is_aux_room:
                    _std_obj_key = 'operating_room_aux'
                else:
                    _std_obj_key = 'eye_operating_room' if '眼科' in _surgery_room_type_for_std else 'operating_room'
                _or_std = _std_db.get('GB 50333-2013', {}).get(_std_obj_key, {})
                _level_std = _or_std.get(_op_clean_class, {})
                for _sk, _sv in _level_std.items():
                    if isinstance(_sv, dict) and 'range' in _sv:
                        _op_std_ranges[_sk] = _sv['range']
            except Exception:
                _level_std = {}

            def _op_conclusion_for(*keys: str):
                for key in keys:
                    if not key:
                        continue
                    v = _normalize_conclusion_text(replacements.get(key, ''))
                    if v:
                        return v
                return ''

            _raw_params = room.get('params', {})
            _param_map = _raw_params if isinstance(_raw_params, dict) else {}

            if _is_aux_room:
                if _op_variant == 'aux_level1':
                    _R = {'wind': 3, 'pressure': 4, 'hepa': 6,
                          'particle_hdr': 7, 'temp': 16, 'humid': 17, 'illum': 18,
                          'noise': 19, 'bact_local': 20, 'bact_surr': 21,
                          'pt_local_start': 8, 'pt_surr_start': 12,
                          'pt_cols': 9, 'has_bact_split': True}
                else:
                    _R = {'wind': 3, 'pressure': 4, 'hepa': 6,
                          'particle_hdr': 7, 'temp': 12, 'humid': 13, 'illum': 14,
                          'noise': 15, 'bact_local': 16, 'bact_surr': None,
                          'pt_local_start': 8, 'pt_surr_start': None,
                          'pt_cols': 8, 'has_bact_split': False}

                _aux_rows = [
                    (_R['wind'], _op_std_ranges.get('wind_speed', '') or _op_std_ranges.get('airchange', ''),
                     replacements.get('截面风速', '') or replacements.get('截面平均风速', '') or replacements.get('换气次数', ''),
                     _op_conclusion_for('截面风速结果', '截面平均风速结果', '换气次数结果', '换气次数'), 2, 3, 4),
                    (_R['pressure'], _op_std_ranges.get('pressure', ''),
                     replacements.get('静压差', ''),
                     _op_conclusion_for('静压差结果', '静压差'), 2, 3, 4),
                    (_R['hepa'], _op_std_ranges.get('hepa_leak', ''),
                     replacements.get('高效过滤器检漏', '') or replacements.get('送风高效过滤器检漏', ''),
                     _op_conclusion_for('高效过滤器检漏结果', '送风高效过滤器检漏结果', '送风高效过滤器检漏'), 2, 3, 4),
                    (_R['temp'], _op_std_ranges.get('temperature', ''), replacements.get('温度', ''),
                     _op_conclusion_for('温度结果', '温度'), 2, 3, 4),
                    (_R['humid'], _op_std_ranges.get('humidity', ''),
                     replacements.get('相对湿度', '') or replacements.get('湿度', ''),
                     _op_conclusion_for('相对湿度结果', '湿度结果', '相对湿度', '湿度'), 2, 3, 4),
                    (_R['illum'], _op_std_ranges.get('illumination_min', '') or _op_std_ranges.get('illumination', ''),
                     replacements.get('照度', '') or replacements.get('平均照度', ''),
                     _op_conclusion_for('照度结果', '平均照度结果', '照度', '平均照度'), 3, 4, 5),
                    (_R['noise'], _op_std_ranges.get('noise', ''), replacements.get('噪声', ''),
                     _op_conclusion_for('噪声结果', '噪声'), 2, 3, 4),
                ]
                for row_idx, standard_val, result_val, conclusion_val, std_col, result_col, conclusion_col in _aux_rows:
                    if standard_val and std_col is not None:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', row_idx, standard_val, std_col)
                    if result_val:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', row_idx, result_val, result_col)
                    if conclusion_val:
                        document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', row_idx, conclusion_val, conclusion_col)

                _pt = _param_map.get('particle', {})
                _pt_data = _pt.get('data', {}) if isinstance(_pt, dict) else {}
                _pt_result = str(_pt.get('result', '') or '') if isinstance(_pt, dict) else ''
                _pt_conclusion = '合格' if '✅' in _pt_result and '❌' not in _pt_result else ('不合格' if '❌' in _pt_result else '')
                if isinstance(_pt_data, dict):
                    _pt_local_std = _op_std_ranges.get('particle', '')
                    _pt_local_std_05 = ''
                    _pt_local_std_5 = ''
                    if _pt_local_std:
                        for _seg in _pt_local_std.split(','):
                            _seg = _seg.strip()
                            if '0.5' in _seg:
                                _pt_local_std_05 = _seg
                            elif '5' in _seg:
                                _pt_local_std_5 = _seg
                    _pt_surr_std = ''
                    try:
                        _pt_std_entry = _level_std.get('particle', {})
                        _pt_surr_std = _pt_std_entry.get('range_surr', '') if isinstance(_pt_std_entry, dict) else ''
                    except Exception:
                        pass
                    _pt_surr_std_05 = ''
                    _pt_surr_std_5 = ''
                    if _pt_surr_std:
                        for _seg in _pt_surr_std.split(','):
                            _seg = _seg.strip()
                            if '0.5' in _seg:
                                _pt_surr_std_05 = _seg
                            elif '5' in _seg:
                                _pt_surr_std_5 = _seg
                    _pt_val_col = 6 if _R['pt_cols'] == 9 else 5
                    _pt_iso_col = 7 if _R['pt_cols'] == 9 else 6
                    _pt_concl_col = 8 if _R['pt_cols'] == 9 else 7
                    _pts = _R['pt_local_start']
                    if _pt_local_std_05:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts, _pt_local_std_05, 3)
                    if _pt_local_std_5:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts+2, _pt_local_std_5, 3)
                    for _off, _dk in [(0,'op_05_max'),(1,'op_05_ucl'),(2,'op_5_max'),(3,'op_5_ucl')]:
                        _rv = _pt_data.get(_dk, '')
                        if _rv:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts+_off, str(_rv), _pt_val_col)
                    if _pt_conclusion:
                        document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _R['particle_hdr'], _pt_conclusion, 6)
                        document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _pts, _pt_conclusion, _pt_concl_col)
                    _local_iso = 'ISO-5' if '3520' in str(_pt_local_std_05) and '35200' not in str(_pt_local_std_05) else ('ISO-7' if '352000' in str(_pt_local_std_05) else 'ISO-8')
                    if _pt_conclusion == '合格' and _pt_local_std_05:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts, _local_iso, _pt_iso_col)
                    elif _pt_conclusion == '不合格':
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts, '超标', _pt_iso_col)

                    if _R['pt_surr_start'] is not None:
                        _ptss = _R['pt_surr_start']
                        if _pt_surr_std_05:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss, _pt_surr_std_05, 3)
                        if _pt_surr_std_5:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss+2, _pt_surr_std_5, 3)
                        for _off, _dk in [(0,'surr_05_max'),(1,'surr_05_ucl'),(2,'surr_5_max'),(3,'surr_5_ucl')]:
                            _rv = _pt_data.get(_dk, '')
                            if _rv:
                                document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss+_off, str(_rv), _pt_val_col)
                        _surr_iso = 'ISO-6'
                        if '352000' in str(_pt_surr_std_05) and '3520000' not in str(_pt_surr_std_05):
                            _surr_iso = 'ISO-7'
                        elif '3520000' in str(_pt_surr_std_05):
                            _surr_iso = 'ISO-8'
                        if _pt_conclusion == '合格' and _pt_surr_std_05:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss, _surr_iso, _pt_iso_col)
                        elif _pt_conclusion == '不合格':
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss, '超标', _pt_iso_col)

                _bact = _param_map.get('bacteria', {})
                _bact_data = _bact.get('data', {}) if isinstance(_bact, dict) else {}
                _bact_result = str(_bact.get('result', '') or '') if isinstance(_bact, dict) else ''
                _bact_conclusion = '合格' if '✅' in _bact_result and '❌' not in _bact_result else ('不合格' if '❌' in _bact_result else '')
                if isinstance(_bact_data, dict):
                    def _avg_list(vals):
                        if not vals or not isinstance(vals, list): return ''
                        try:
                            nums = [float(v) for v in vals if v]
                            if nums: return str(round(sum(nums)/len(nums), 1))
                        except (ValueError, TypeError):
                            pass
                        return ''
                    _local_avg = _avg_list(_bact_data.get('op_values', []) or _bact_data.get('local_values', []))
                    _surr_avg = _avg_list(_bact_data.get('surr_values', []))
                    if _local_avg:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _R['bact_local'], _local_avg, 4)
                        if _bact_conclusion:
                            document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _R['bact_local'], _bact_conclusion, 5)
                    if _R['bact_surr'] is not None and _surr_avg:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _R['bact_surr'], _surr_avg, 4)
                        if _bact_conclusion:
                            document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _R['bact_surr'], _bact_conclusion, 5)

                _hepa = _param_map.get('hepa_leak', {})
                if isinstance(_hepa, dict):
                    _hepa_objs = _hepa.get('objects', [])
                    if isinstance(_hepa_objs, list) and _hepa_objs:
                        _parts = []; _all_pass = True
                        for _ho in _hepa_objs:
                            _hv = str(_ho.get('value', '') or '')
                            if _hv and _hv != '-':
                                _hn = str(_ho.get('name', '') or '')
                                _parts.append(f'{_hn}:{_hv}%' if len(_hepa_objs) > 1 else _hv)
                                try:
                                    if float(_hv) > 0.01: _all_pass = False
                                except ValueError:
                                    pass
                        if _parts:
                            _hepa_text = ' / '.join(_parts) if len(_parts) > 1 else _parts[0]
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _R['hepa'], _hepa_text, 3)
                            document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _R['hepa'], '合格' if _all_pass else '不合格', 4)
            else:
                # 主手术室 / 眼科手术室共用同一结构，标准范围不同
                if _op_variant == 'level1':
                    _R = {'wind': 3, 'unif': 4, 'pressure': 5, 'hepa': 11, 'seal': 12,
                          'particle_hdr': 13, 'temp': 22, 'humid': 23, 'illum': 24, 'illum_unif': 25,
                          'noise': 26, 'bact_op': 27, 'bact_surr': 28,
                          'pd_start': 7, 'pt_op_start': 14, 'pt_surr_start': 18,
                          'has_particle_door': True, 'has_uniformity': True, 'has_bact_split': True,
                          'pt_op_cols': 9, 'pt_surr_cols': 9}
                elif _op_variant == 'level23':
                    _R = {'wind': 3, 'unif': None, 'pressure': 4, 'hepa': 6, 'seal': 7,
                          'particle_hdr': 8, 'temp': 17, 'humid': 18, 'illum': 19, 'illum_unif': 20,
                          'noise': 21, 'bact_op': 22, 'bact_surr': 23,
                          'pd_start': None, 'pt_op_start': 9, 'pt_surr_start': 13,
                          'has_particle_door': False, 'has_uniformity': False, 'has_bact_split': True,
                          'pt_op_cols': 9, 'pt_surr_cols': 9}
                else:
                    _R = {'wind': 3, 'unif': None, 'pressure': 4, 'hepa': 6, 'seal': 7,
                          'particle_hdr': 8, 'temp': 13, 'humid': 14, 'illum': 15, 'illum_unif': 16,
                          'noise': 17, 'bact_op': 18, 'bact_surr': None,
                          'pd_start': None, 'pt_op_start': 9, 'pt_surr_start': None,
                          'has_particle_door': False, 'has_uniformity': False, 'has_bact_split': False,
                          'pt_op_cols': 8, 'pt_surr_cols': 0}

                _op_xml_rows = [
                    (_R['wind'], _op_std_ranges.get('wind_speed', '') or _op_std_ranges.get('airchange', ''),
                     replacements.get('截面风速', '') or replacements.get('截面平均风速', '') or replacements.get('换气次数', ''),
                     _op_conclusion_for('截面风速结果', '截面平均风速结果', '截面平均风速', '换气次数结果', '换气次数'),
                     2, 3, 4),
                ]
                if _R['unif'] is not None:
                    _op_xml_rows.append(
                        (_R['unif'], _op_std_ranges.get('wind_uniformity', ''),
                         replacements.get('风速不均匀度', ''),
                         _op_conclusion_for('风速不均匀度结果', '风速不均匀度'),
                         2, 3, 4))
                _op_xml_rows.extend([
                    (_R['pressure'], _op_std_ranges.get('pressure', ''),
                     replacements.get('静压差', ''),
                     _op_conclusion_for('静压差结果', '静压差'), 2, 3, 4),
                    (_R['hepa'], _op_std_ranges.get('hepa_leak', ''),
                     replacements.get('高效过滤器检漏', '') or replacements.get('送风高效过滤器检漏', ''),
                     _op_conclusion_for('高效过滤器检漏结果', '送风高效过滤器检漏结果', '送风高效过滤器检漏'), 2, 3, 4),
                    (_R['seal'], _op_std_ranges.get('airtightness', ''),
                     replacements.get('严密性', ''),
                     _op_conclusion_for('严密性结果', '严密性'), 2, 3, 4),
                    (_R['temp'], _op_std_ranges.get('temperature', ''), replacements.get('温度', ''),
                     _op_conclusion_for('温度结果', '温度'), 2, 3, 4),
                    (_R['humid'], _op_std_ranges.get('humidity', ''),
                     replacements.get('相对湿度', '') or replacements.get('湿度', ''),
                     _op_conclusion_for('相对湿度结果', '湿度结果', '相对湿度', '湿度'), 2, 3, 4),
                    (_R['illum'], _op_std_ranges.get('illumination_min', '') or _op_std_ranges.get('illumination', ''), replacements.get('照度', '') or replacements.get('平均照度', ''),
                     _op_conclusion_for('照度结果', '平均照度结果', '照度', '平均照度'), 3, 4, 5),
                    (_R['illum_unif'], _op_std_ranges.get('illumination_uniformity', ''), replacements.get('照度均匀度', ''),
                     _op_conclusion_for('照度均匀度结果', '照度均匀度'), 3, 4, 5),
                    (_R['noise'], _op_std_ranges.get('noise', ''), replacements.get('噪声', ''),
                     _op_conclusion_for('噪声结果', '噪声'), 2, 3, 4),
                ])
                for row_idx, standard_val, result_val, conclusion_val, std_col, result_col, conclusion_col in _op_xml_rows:
                    if standard_val and std_col is not None:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', row_idx, standard_val, std_col)
                    if result_val:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', row_idx, result_val, result_col)
                    if conclusion_val:
                        document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', row_idx, conclusion_val, conclusion_col)

                # --- 主手术室/眼科复杂多行参数填充 ---
                if _R['has_particle_door']:
                    _pd = _param_map.get('particle_door', {})
                    _pd_data = _pd.get('data', {}) if isinstance(_pd, dict) else {}
                    _pd_result = str(_pd.get('result', '') or '') if isinstance(_pd, dict) else ''
                    _pd_conclusion = '合格' if '✅' in _pd_result and '❌' not in _pd_result else ('不合格' if '❌' in _pd_result else '')
                    _pd_std = _op_std_ranges.get('particle_door', '')
                    _pd_std_05 = ''; _pd_std_5 = ''
                    if _pd_std:
                        for _seg in _pd_std.split(','):
                            _seg = _seg.strip()
                            if '0.5' in _seg: _pd_std_05 = _seg
                            elif '5' in _seg: _pd_std_5 = _seg
                    _pds = _R['pd_start']
                    if isinstance(_pd_data, dict):
                        if _pd_std_05:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pds, _pd_std_05, 2)
                        if _pd_std_5:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pds+2, _pd_std_5, 2)
                        _pd_iso = ''
                        if _pd_std_05:
                            if '3520' in _pd_std_05 and '35200' not in _pd_std_05: _pd_iso = 'ISO-5'
                            elif '35200' in _pd_std_05 and '352000' not in _pd_std_05: _pd_iso = 'ISO-6'
                            elif '352000' in _pd_std_05: _pd_iso = 'ISO-7'
                        if _pd_iso:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pds, _pd_iso, 3)
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pds+2, _pd_iso, 3)
                        for _off, _dk in [(0,'p05_max'),(1,'p05_ucl'),(2,'p5_max'),(3,'p5_ucl')]:
                            _rv = _pd_data.get(_dk, '')
                            if _rv:
                                document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pds+_off, str(_rv), 5)
                                if _pd_conclusion:
                                    document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _pds+_off, _pd_conclusion, 6)

                _pt = _param_map.get('particle', {})
                _pt_data = _pt.get('data', {}) if isinstance(_pt, dict) else {}
                _pt_result = str(_pt.get('result', '') or '') if isinstance(_pt, dict) else ''
                _pt_conclusion = '合格' if '✅' in _pt_result and '❌' not in _pt_result else ('不合格' if '❌' in _pt_result else '')
                if isinstance(_pt_data, dict):
                    _pts = _R['pt_op_start']
                    _pt_hdr = _R['particle_hdr']
                    _pt_val_col = 6 if _R['pt_op_cols'] == 9 else 5
                    _pt_concl_col = 8 if _R['pt_op_cols'] == 9 else 7
                    _pt_iso_col = 7 if _R['pt_op_cols'] == 9 else 6
                    _pt_surr_std = ''
                    try:
                        _pt_std_entry = _level_std.get('particle', {})
                        _pt_surr_std = _pt_std_entry.get('range_surr', '') if isinstance(_pt_std_entry, dict) else ''
                    except Exception:
                        pass
                    _pt_surr_std_05 = ''; _pt_surr_std_5 = ''
                    if _pt_surr_std:
                        for _seg in _pt_surr_std.split(','):
                            _seg = _seg.strip()
                            if '0.5' in _seg: _pt_surr_std_05 = _seg
                            elif '5' in _seg: _pt_surr_std_5 = _seg
                    for _off, _dk in [(0,'op_05_max'),(1,'op_05_ucl'),(2,'op_5_max'),(3,'op_5_ucl')]:
                        _rv = _pt_data.get(_dk, '')
                        if _rv:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts+_off, str(_rv), _pt_val_col)
                    if _R['pt_surr_start'] is not None:
                        _ptss = _R['pt_surr_start']
                        if _pt_surr_std_05:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss, _pt_surr_std_05, 3)
                        if _pt_surr_std_5:
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss+2, _pt_surr_std_5, 3)
                        for _off, _dk in [(0,'surr_05_max'),(1,'surr_05_ucl'),(2,'surr_5_max'),(3,'surr_5_ucl')]:
                            _rv = _pt_data.get(_dk, '')
                            if _rv:
                                document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss+_off, str(_rv), _pt_val_col)
                        _surr_iso = 'ISO-6'
                        if _op_std_ranges.get('particle', ''):
                            _psr = _op_std_ranges.get('particle', '')
                            if '352000' in str(_psr) and '3520000' not in str(_psr): _surr_iso = 'ISO-7'
                            elif '35200' in str(_psr) and '352000' not in str(_psr): _surr_iso = 'ISO-6'
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss, _surr_iso, 4)
                        if _pt_conclusion == '合格':
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss, _surr_iso, _pt_iso_col)
                        elif _pt_conclusion == '不合格':
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _ptss, '超标', _pt_iso_col)
                    if _pt_conclusion:
                        _hdr_concl_col = 6
                        document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _pt_hdr, _pt_conclusion, _hdr_concl_col)
                        document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _pts, _pt_conclusion, _pt_concl_col)
                        _op_iso = 'ISO-5'
                        if _op_std_ranges.get('particle', ''):
                            _posr = str(_op_std_ranges.get('particle', ''))
                            if '3520' in _posr and '35200' not in _posr: _op_iso = 'ISO-5'
                            elif '35200' in _posr and '352000' not in _posr: _op_iso = 'ISO-6'
                            elif '352000' in _posr and '3520000' not in _posr: _op_iso = 'ISO-7'
                            elif '3520000' in _posr: _op_iso = 'ISO-8'
                        if _pt_conclusion == '合格':
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts, _op_iso, _pt_iso_col)
                        elif _pt_conclusion == '不合格':
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _pts, '超标', _pt_iso_col)

                _bact = _param_map.get('bacteria', {})
                _bact_data = _bact.get('data', {}) if isinstance(_bact, dict) else {}
                _bact_result = str(_bact.get('result', '') or '') if isinstance(_bact, dict) else ''
                _bact_conclusion = '合格' if '✅' in _bact_result and '❌' not in _bact_result else ('不合格' if '❌' in _bact_result else '')
                if isinstance(_bact_data, dict):
                    def _avg_list(vals):
                        if not vals or not isinstance(vals, list): return ''
                        try:
                            nums = [float(v) for v in vals if v]
                            if nums: return str(round(sum(nums)/len(nums), 1))
                        except (ValueError, TypeError): pass
                        return ''
                    _op_avg = _avg_list(_bact_data.get('op_values', []))
                    _surr_avg = _avg_list(_bact_data.get('surr_values', []))
                    _bact_row_op = _R['bact_op']
                    _bact_row_surr = _R['bact_surr']
                    if _op_avg:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _bact_row_op, _op_avg, 4)
                        if _bact_conclusion:
                            document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _bact_row_op, _bact_conclusion, 5)
                    if _bact_row_surr is not None and _surr_avg:
                        document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _bact_row_surr, _surr_avg, 4)
                        if _bact_conclusion:
                            document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _bact_row_surr, _bact_conclusion, 5)

                _hepa = _param_map.get('hepa_leak', {})
                if isinstance(_hepa, dict):
                    _hepa_objs = _hepa.get('objects', [])
                    if isinstance(_hepa_objs, list) and _hepa_objs:
                        _parts = []; _all_pass = True
                        for _ho in _hepa_objs:
                            _hv = str(_ho.get('value', '') or '')
                            if _hv and _hv != '-':
                                _hn = str(_ho.get('name', '') or '')
                                _parts.append(f'{_hn}:{_hv}%' if len(_hepa_objs) > 1 else _hv)
                                try:
                                    if float(_hv) > 0.01: _all_pass = False
                                except ValueError: pass
                        if _parts:
                            _hepa_text = ' / '.join(_parts) if len(_hepa_objs) > 1 else _parts[0]
                            document_xml = _replace_result_table_cell_by_row_index(document_xml, '静压差', _R['hepa'], _hepa_text, 3)
                            document_xml = _replace_conclusion_table_cell_by_row_index(document_xml, '静压差', _R['hepa'], '合格' if _all_pass else '不合格', 4)
        # --- 房间参数 S（m2）= V（m3）= 填充 (ROW 1 tc[1]) ---
        _room_length = str(room.get('length', '') or '').strip()
        _room_width = str(room.get('width', '') or '').strip()
        _room_height = str(room.get('height', '') or '').strip()
        try:
            _rl = float(_room_length) if _room_length else 0
            _rw = float(_room_width) if _room_width else 0
            _rh = float(_room_height) if _room_height else 0
        except (ValueError, TypeError):
            _rl = _rw = _rh = 0
        if _rl > 0 and _rw > 0:
            _area = round(_rl * _rw, 2)
            _area_str = str(int(_area)) if _area == int(_area) else str(_area)
        else:
            _area_str = ''
        if _rl > 0 and _rw > 0 and _rh > 0:
            _vol = round(_rl * _rw * _rh, 2)
            _vol_str = str(int(_vol)) if _vol == int(_vol) else str(_vol)
        else:
            _vol_str = ''
        if _area_str or _vol_str:
            # ROW 1 tc[1] 包含 "S（m2）=...V（m3）=..."，XML 中 run 分裂成 5 个 w:t
            # 需要清空所有 w:t 内容，然后在第一个 w:t 中写入完整文本
            _sv_text = f'S\uff08m\u00b2\uff09={_area_str}                 V\uff08m\u00b3\uff09={_vol_str}'
            _tbl_pat = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
            _row_pat = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
            _cell_pat = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
            _t_pat = re.compile(r'(<w:t(?:\s[^>]*)?>)([^<]*)(</w:t>)', re.S)
            for _tm in _tbl_pat.finditer(document_xml):
                _tbl = _tm.group(0)
                if '\u622a\u9762\u5e73\u5747\u98ce\u901f' not in ''.join(re.findall(r'<w:t[^>]*>([^<]*)</w:t>', _tbl)):
                    continue
                _rows = _row_pat.findall(_tbl)
                if len(_rows) < 2:
                    continue
                _row1 = _rows[1]
                _cells = _cell_pat.findall(_row1)
                if len(_cells) < 2:
                    continue
                _tc1 = _cells[1]
                # 找到所有 w:t，第一个写入完整文本，其余清空
                _t_matches = list(_t_pat.finditer(_tc1))
                if _t_matches:
                    _new_tc1 = _tc1
                    for _i, _tm2 in enumerate(reversed(_t_matches)):
                        if _i == len(_t_matches) - 1:  # first match (processing reversed)
                            _new_tc1 = _new_tc1[:_tm2.start(2)] + escape(_sv_text) + _new_tc1[_tm2.end(2):]
                        else:
                            _new_tc1 = _new_tc1[:_tm2.start(2)] + _new_tc1[_tm2.end(2):]
                    _new_row1 = _row1.replace(_tc1, _new_tc1, 1)
                    _new_tbl = _tbl.replace(_row1, _new_row1, 1)
                    document_xml = document_xml[:_tm.start()] + _new_tbl + document_xml[_tm.end():]
                break

        document_xml = _replace_cover_field(document_xml, '报告编号', replacements.get('报告编号', ''))
        document_xml = _replace_cover_field(document_xml, '检测对象', replacements.get('检测对象', '') or replacements.get('样品名称', ''))
        document_xml = _replace_cover_field(document_xml, '检测类别', replacements.get('检测类型', '') or replacements.get('检测类别', ''))
        document_xml = _replace_cover_field(document_xml, '项目名称', replacements.get('项目名称', ''))
        document_xml = _replace_cover_field(document_xml, '委托单位', replacements.get('委托单位', ''))
        document_xml = _replace_cover_field(document_xml, '检测区域', replacements.get('检测区域', ''))
        document_xml = _replace_cover_field(document_xml, '受检区域', replacements.get('检测区域', ''))
        # 正文中多处“报告编号：”也需要填充，但封面重复编号只保留前面的正式字段，避免重复写入造成双编号
        if replacements.get('报告编号') and type_id != 'operating_room':
            document_xml = _replace_all_plain_text(document_xml, '报告编号：', replacements.get('报告编号', ''), max_count=10)
        document_xml = _cleanup_placeholder_noise(document_xml)

        if type_id == 'operating_room':
            # 单房间 operating_room 在公共信息表后、仪器表前常残留一组空标题块（检 测 报 告 / 报告编号：），
            # mixed report 复用完整文档时会把这组空块带入第一房间页前。这里在单房间输出阶段直接清理。
            # 性能优化：原正则在大文档上有灾难性回溯（14秒），改用字符串定位
            # 目标：删除"检测报告标题+报告编号+信息表+编制人"重复块
            _gap_start = -1
            _gap_end = -1
            # 找第一个"检 测 报 告"标题（在仪器表之前）
            _first_title = document_xml.find('检 测 报 告')
            if _first_title < 0:
                _first_title = document_xml.find('检测报告')
            if _first_title > 0:
                # 找这个标题所在段落的开始
                _p_start = document_xml.rfind('<w:p', 0, _first_title)
                if _p_start > 0:
                    # 找"序号"和"检测项目"（仪器表的标志）
                    _instr_tbl = document_xml.find('序号', _first_title)
                    if _instr_tbl > 0 and '检测项目' in document_xml[_instr_tbl:_instr_tbl+500]:
                        # 找仪器表前的"检 测 报 告"标题段落开始
                        _second_title = document_xml.rfind('<w:p', _first_title + 10, _instr_tbl)
                        # 检查这个位置附近是否有"检测报告"文本
                        _check_area = document_xml[max(0, _second_title):_instr_tbl]
                        if '报告编号' in _check_area:
                            # 删除从第一个标题段落开始到第二个标题段落开始之间的内容
                            # 但要保留第二个标题（仪器表前的那个）
                            _gap_start = _p_start
                            _gap_end = _second_title
            if _gap_start > 0 and _gap_end > _gap_start and (_gap_end - _gap_start) < 200000:
                document_xml = document_xml[:_gap_start] + document_xml[_gap_end:]
        with ZipFile(output, 'w', ZIP_DEFLATED) as dst:
            for name in members:
                # 跳过目录项，避免重写 zip 时生成损坏条目
                if name.endswith('/'):
                    continue
                if name == 'word/document.xml':
                    dst.writestr(name, document_xml)
                else:
                    dst.writestr(name, src.read(name))
    if debug_notes is not None:
        debug_path = output.with_suffix(output.suffix + '.debug.json')
        debug_payload = {
            'output_path': str(output),
            'type_id': type_id,
            'export_room_name': room.get('room_name', ''),
            'interesting_values_present_after_write': {
                '手术区≥0.5μm最大值': replacements.get('手术区≥0.5μm最大值', '') in document_xml if replacements.get('手术区≥0.5μm最大值') else False,
                '手术区≥0.5μmUCL': replacements.get('手术区≥0.5μmUCL', '') in document_xml if replacements.get('手术区≥0.5μmUCL') else False,
                '手术区≥5μm最大值': replacements.get('手术区≥5μm最大值', '') in document_xml if replacements.get('手术区≥5μm最大值') else False,
                '手术区≥5μmUCL': replacements.get('手术区≥5μmUCL', '') in document_xml if replacements.get('手术区≥5μmUCL') else False,
                '周边区≥0.5μm最大值': replacements.get('周边区≥0.5μm最大值', '') in document_xml if replacements.get('周边区≥0.5μm最大值') else False,
                '周边区≥0.5μmUCL': replacements.get('周边区≥0.5μmUCL', '') in document_xml if replacements.get('周边区≥0.5μmUCL') else False,
                '周边区≥5μm最大值': replacements.get('周边区≥5μm最大值', '') in document_xml if replacements.get('周边区≥5μm最大值') else False,
                '周边区≥5μmUCL': replacements.get('周边区≥5μmUCL', '') in document_xml if replacements.get('周边区≥5μmUCL') else False,
                '细菌浓度（沉降法）手术区': replacements.get('细菌浓度（沉降法）手术区', '') in document_xml if replacements.get('细菌浓度（沉降法）手术区') else False,
                '细菌浓度（沉降法）周边区': replacements.get('细菌浓度（沉降法）周边区', '') in document_xml if replacements.get('细菌浓度（沉降法）周边区') else False,
                'negative_pressure_细菌浓度': replacements.get('细菌浓度', '') in document_xml if replacements.get('细菌浓度') else False,
                'negative_pressure_物体表面微生物': replacements.get('物体表面微生物', '') in document_xml if replacements.get('物体表面微生物') else False,
            },
            'notes': debug_notes,
        }
        debug_path.write_text(json.dumps(debug_payload, ensure_ascii=False, indent=2), encoding='utf-8')
    return str(output)


def build_template_bound_docx(export_payload: Dict[str, Any], output_path: str) -> str:
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)

    project = export_payload.get('project', {}) or {}
    room = export_payload.get('room', {}) or {}
    template_rule = export_payload.get('template_rule', {}) or {}
    template_resource = export_payload.get('template_resource', {}) or {}
    semantics = export_payload.get('clean_class_semantics', {}) or {}
    report_context = export_payload.get('report_context', {}) or {}

    template_path = template_resource.get('template_path', '') or ''
    template_snippets = _read_docx_text_snippets(template_path, limit=12)
    template_probe = _detect_template_placeholders(template_snippets)
    common_fill_preview = _build_common_fill_preview(report_context)
    object_context_preview = _build_object_context_preview(export_payload)
    placeholder_fill_plan = _build_placeholder_fill_plan(export_payload)

    report_title = f"X1 模板绑定报告 - {room.get('type_name', '') or room.get('type_id', '')}"
    paragraphs = [
        f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        f"项目名称：{project.get('project_name', '')}",
        f"对象名称：{room.get('room_name', '')}",
        f"对象类型：{room.get('type_name', '')}",
        f"模板键：{template_rule.get('template_key', '')}",
        f"模板名：{template_resource.get('template_name', '') or template_rule.get('template_name', '')}",
        f"模板路径：{template_path}",
        f"模板命中：{template_resource.get('template_found', False)}",
        f"资源状态：{template_resource.get('resource_status', '')}",
        f"资源说明：{template_resource.get('resource_note', '')}",
        f"等级语义键：{semantics.get('level_semantic_key', '')}",
        f"语义说明：{semantics.get('semantic_note', '')}",
        '',
        '【模板结构探针】',
        f"片段数量：{template_probe.get('snippet_count', 0)}",
        f"业务标记：{', '.join(template_probe.get('markers', []))}",
        f"是否检测到业务标记：{template_probe.get('has_business_markers', False)}",
        '',
        '【模板正文前12段文本探针】',
    ]
    if template_snippets:
        paragraphs.extend([f"- {line}" for line in template_snippets])
    else:
        paragraphs.append('- 未读取到模板正文片段（可能为空模板、结构特殊，或后续需要更深解析）。')

    paragraphs.extend([
        '',
        '【公共字段消费预览】',
        json.dumps(common_fill_preview, ensure_ascii=False, indent=2),
        '',
        '【对象特有上下文预览】',
        json.dumps(object_context_preview, ensure_ascii=False, indent=2),
        '',
        '【第一版占位符填充计划】',
    ])
    if placeholder_fill_plan:
        paragraphs.extend([f"- {k} => {v}" for k, v in placeholder_fill_plan])
    else:
        paragraphs.append('- 当前未生成可用占位符填充计划。')

    paragraphs.extend([
        '',
        '【报告上下文快照】',
        json.dumps(report_context, ensure_ascii=False, indent=2),
        '',
        '【说明】',
        '当前阶段这是 X1 自己的模板绑定输出入口，已开始读取真实模板资源并做正文结构探针。',
        '本轮已新增“公共字段消费预览”“对象特有上下文预览”“第一版占位符填充计划”，用于把 report_context 真正推进到模板填充前一层。',
        '它仍不是正式字段回填，但已经从“只知道模板路径”推进到“开始输出可落位字段清单”。',
    ])

    body = ''.join(_para_xml(p) for p in paragraphs)
    document_xml = f'''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas"
 xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006"
 xmlns:o="urn:schemas-microsoft-com:office:office"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"
 xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math"
 xmlns:v="urn:schemas-microsoft-com:vml"
 xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing"
 xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
 xmlns:w10="urn:schemas-microsoft-com:office:word"
 xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"
 xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"
 xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup"
 xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk"
 xmlns:wne="http://schemas.microsoft.com/office/2006/wordml"
 xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape"
 mc:Ignorable="w14 wp14">
 <w:body>
 {_para_xml(report_title)}
 {body}
 <w:sectPr>
   <w:pgSz w:w="11906" w:h="16838"/>
   <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440" w:header="708" w:footer="708" w:gutter="0"/>
 </w:sectPr>
 </w:body>
</w:document>'''

    content_types = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
    <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
    <Default Extension="xml" ContentType="application/xml"/>
    <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>'''

    rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>'''

    doc_rels = '''<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"></Relationships>'''

    with ZipFile(output, 'w', ZIP_DEFLATED) as zf:
        zf.writestr('[Content_Types].xml', content_types)
        zf.writestr('_rels/.rels', rels)
        zf.writestr('word/document.xml', document_xml)
        zf.writestr('word/_rels/document.xml.rels', doc_rels)

    return str(output)


# ---------------------------------------------------------------------------
# 混合报告导出（同检测类型多房间）
# ---------------------------------------------------------------------------

def _extract_last_table_xml(template_path: str) -> str:
    """从模板 docx 中提取最后一个 <w:tbl>...</w:tbl>（数据表）的原始 XML。"""
    with ZipFile(template_path, 'r') as z:
        xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
    matches = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', xml, re.S))
    if not matches:
        return ''
    return matches[-1].group()


def _page_break_para_xml() -> str:
    """生成一个分页符段落的 XML。"""
    return (
        '<w:p><w:r><w:br w:type="page"/></w:r></w:p>'
    )


def _fill_data_table_xml(table_xml: str, room_export: dict, export_payload: dict) -> str:
    """对单个房间的数据表 XML 进行填充。
    
    构建一个虚拟的 export_payload（替换 room/template_rule/report_context），
    调用 _build_placeholder_fill_plan 获取填充键值对，
    然后对数据表 XML 做定点替换。
    """
    # 构建虚拟 payload
    virtual_payload = dict(export_payload)
    virtual_payload['room'] = room_export['room']
    virtual_payload['template_rule'] = room_export['template_rule']
    virtual_payload['template_resource'] = room_export['template_resource']
    virtual_payload['report_context'] = room_export['report_context']
    virtual_payload['clean_class_semantics'] = room_export['clean_class_semantics']
    virtual_payload['judgement_result'] = room_export['judgement_result']

    fill_plan = _build_placeholder_fill_plan(virtual_payload)
    replacements = {k: v for k, v in fill_plan}

    # 清洗单位后缀
    import re as _re_clean
    _unit_pat = _re_clean.compile(r'^([\-]?[\d.]+)\s*(?:次/h|Pa|Pa\b|℃|dB\(?A?\)?|lx|%|m/s|cfu)[\s]*$')
    for _ck, _cv in replacements.items():
        if isinstance(_cv, str):
            _um = _unit_pat.match(_cv)
            if _um:
                replacements[_ck] = _um.group(1)

    room = room_export['room']
    type_id = str(room.get('type_id', '') or '')

    # 填充 Row0: 房间名称/受检区域(cell1) / 检测日期(cell3) / 洁净度级别(cell5)
    room_name = room.get('room_name', '') or replacements.get('受检区域名称', '') or replacements.get('房间名称', '')
    detection_date = replacements.get('检测日期', '')
    level_value = replacements.get('洁净级别', '') or replacements.get('洁净等级', '') or replacements.get('洁净度级别', '')
    # cell[0] 标签标准化：受检区域名称 / 受检区域名称及编号 → 房间名称（防止通用替换拼入值导致重复）
    for _old_label in ['受检区域名称及编号', '受检区域名称']:
        table_xml = table_xml.replace(_old_label, '房间名称')
    table_xml = _replace_table_cell_by_table_and_row(table_xml, 0, 0, {
        1: room_name,
        3: detection_date,
        5: level_value,
    }, allow_blank=True)

    # 填充 Row1: 房间参数 S/V (cell1, span=8)
    _room_length = str(room.get('length', '') or '').strip()
    _room_width = str(room.get('width', '') or '').strip()
    _room_height = str(room.get('height', '') or '').strip()
    try:
        _rl = float(_room_length) if _room_length else 0
        _rw = float(_room_width) if _room_width else 0
        _rh = float(_room_height) if _room_height else 0
    except (ValueError, TypeError):
        _rl = _rw = _rh = 0
    _area_str = str(round(_rl * _rw, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0) else ''
    _vol_str = str(round(_rl * _rw * _rh, 2)).rstrip('0').rstrip('.') if (_rl > 0 and _rw > 0 and _rh > 0) else ''
    if _area_str or _vol_str:
        table_xml = _replace_table_cell_by_table_and_row(table_xml, 0, 1, {
            1: f'面积S（m²）={_area_str}          体积V（m³）={_vol_str}'
        }, allow_blank=True)

    # === 构建判定结果索引（key → {range, passed}）===
    _judgement = room_export.get('judgement_result') or {}
    _item_results = _judgement.get('item_results', []) if isinstance(_judgement, dict) else []
    # key → {range, passed}  映射
    _jr_map = {}
    for _ir in _item_results:
        _ir_key = str(_ir.get('key', ''))
        if _ir_key and _ir_key not in _jr_map:  # 保留第一个（避免重复 key）
            _jr_map[_ir_key] = {'range': str(_ir.get('range', '')), 'passed': _ir.get('passed')}

    # judgement key → 行首列锚点 映射
    _JR_KEY_TO_ANCHOR = {
        'airchange': '换气次数',
        'wind_speed': '截面风速',
        'pressure': '静压差',
        'hepa_leak': '送风高效',
        'temperature': '温度',
        'humidity': '相对湿度',
        'noise': '噪声',
        'illumination': '平均照度',
        'illumination_main': '平均照度',
        'illumination_min': '平均照度',
        'settling': '沉降菌',
        'floating': '浮游菌',
        'floating_bacteria': '浮游菌',
        'self_purification_time': '自净时间',
        'downflow_speed': '截面风速',
        'avg_speed': '截面风速',
        'wind_uniformity': '风速不均匀度',
        'speed_uniformity': '风速不均匀度',
        'cage_airspeed': '笼内风速',
        'exhaust_speed': '排风口风速',
        'airchange_clean': '洁净区换气次数',
        'uv_intensity': '紫外线',
        'work_illumination': '工作照度',
        'illumination_uniformity': '照度均匀度',
        'temp_diff': '温差',
    }
    # 按锚点构建：锚点 → {range, conclusion}
    _anchor_judgement = {}
    for _jk, _jv in _jr_map.items():
        _anc = _JR_KEY_TO_ANCHOR.get(_jk, '')
        if _anc and _anc not in _anchor_judgement:
            _conclusion = '合格' if _jv.get('passed') else '不合格'
            _anchor_judgement[_anc] = {'range': _jv['range'], 'conclusion': _conclusion}

    # === 参数检测结果映射 ===
    param_fill_map = {
        '截面风速': replacements.get('截面风速', ''),
        '换气次数': replacements.get('换气次数', ''),
        '静压差': replacements.get('静压差', ''),
        '送风高效': replacements.get('送风高效过滤器检漏', '') or replacements.get('高效过滤器检漏', ''),
        '温度': replacements.get('温度', ''),
        '相对湿度': replacements.get('相对湿度', ''),
        '平均照度': replacements.get('照度', '') or replacements.get('平均照度', ''),
        '噪声': replacements.get('噪声', ''),
        '沉降菌': replacements.get('沉降菌', ''),
        '浮游菌': replacements.get('浮游菌', ''),
        '自净时间': replacements.get('自净时间', ''),
        '风速不均匀度': replacements.get('风速不均匀度', ''),
        '笼内风速': replacements.get('笼内风速', ''),
        '排风口风速': replacements.get('排风口风速', ''),
        '工作照度': replacements.get('工作照度', ''),
        '照度均匀度': replacements.get('照度均匀度', ''),
        '温差': replacements.get('温差', ''),
        '紫外线': replacements.get('紫外线', ''),
    }

    # === 辅助函数：向指定 tc 写入文本值 ===
    # 注意：_text_pat 必须精确匹配 <w:t> 和 <w:t ...>，不能匹配 <w:tc>/<w:tbl> 等
    _wt_pat = re.compile(r'<w:t(?:\s[^>]*)?>([\s\S]*?)</w:t>', re.S)
    def _write_tc_value(tc_xml, value):
        """向一个 <w:tc> 的第一个 <w:t> 写入 value，清空其余 <w:t>。"""
        _t_matches = list(_wt_pat.finditer(tc_xml))
        if _t_matches:
            new_tc = tc_xml
            _all_t = list(_wt_pat.finditer(new_tc))
            for _ti in range(len(_all_t) - 1, -1, -1):
                _tm = _all_t[_ti]
                if _ti == 0:
                    new_tc = new_tc[:_tm.start(1)] + escape(str(value)) + new_tc[_tm.end(1):]
                else:
                    new_tc = new_tc[:_tm.start(1)] + new_tc[_tm.end(1):]
            return new_tc
        else:
            _insert_pos = tc_xml.rfind('</w:p>')
            if _insert_pos > 0:
                _run_xml = f'<w:r><w:t xml:space="preserve">{escape(str(value))}</w:t></w:r>'
                return tc_xml[:_insert_pos] + _run_xml + tc_xml[_insert_pos:]
            return tc_xml

    # === 按行遍历填充：cell2(标准范围) + cell3(检测结果) + cell4(单项结论) ===
    _row_pat = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    _tc_pat = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    for _rm in _row_pat.finditer(table_xml):
        _row_xml = _rm.group()
        _tcs = list(_tc_pat.finditer(_row_xml))
        if len(_tcs) < 4:
            continue
        # 提取第一个 cell 的文本作为行标签
        _tc0 = _tcs[0].group()
        _tc0_texts = _wt_pat.findall(_tc0)
        _tc0_plain = ''.join(_tc0_texts).strip().replace(' ', '').replace('\u3000', '').replace('\n', '')
        for _anchor, _value in param_fill_map.items():
            if not _value:
                continue
            if _anchor not in _tc0_plain:
                continue

            _new_row = _row_xml

            # --- cell2: 标准范围（以标准数据库为准：相同作罢，不同替换）---
            _aj = _anchor_judgement.get(_anchor)
            if _aj and _aj.get('range') and len(_tcs) > 2:
                _old_tc2 = _tcs[2].group()
                _tc2_texts = _wt_pat.findall(_old_tc2)
                _tc2_plain = ''.join(_tc2_texts).strip()
                _db_range = _aj['range']
                # 标准化比较（去空格、全角半角统一）
                _tc2_norm = _tc2_plain.replace(' ', '').replace('\u3000', '')
                _db_norm = _db_range.replace(' ', '').replace('\u3000', '')
                if _tc2_norm != _db_norm:  # 不同则替换（包括空值情况）
                    _new_tc2 = _write_tc_value(_old_tc2, _db_range)
                    _new_row = _new_row.replace(_old_tc2, _new_tc2, 1)

            # --- cell3: 检测结果 ---
            _old_tc3 = _tcs[3].group()
            _new_tc3 = _write_tc_value(_old_tc3, _value)
            _new_row = _new_row.replace(_old_tc3, _new_tc3, 1)

            # --- cell4: 单项结论 ---
            if _aj and _aj.get('conclusion') and len(_tcs) > 4:
                _old_tc4 = _tcs[4].group()
                _new_tc4 = _write_tc_value(_old_tc4, _aj['conclusion'])
                _new_row = _new_row.replace(_old_tc4, _new_tc4, 1)

            table_xml = table_xml.replace(_row_xml, _new_row, 1)
            break  # 每个 anchor 只匹配一次

    # 填充洁净度检测结果（多行）
    for key in ['≥ 0.5μm', '≥0.5μm', '≥5μm', '≥ 5μm',
                '≥0.5µm静态', '≥0.5µm动态',
                '≥5µm静态', '≥5µm动态']:
        val = replacements.get(key, '')
        if val and key in table_xml:
            table_xml = _replace_table_row_cells_by_anchor_index(
                table_xml, key, 0, {3: val})

    return table_xml


def _extract_operating_room_page_fragment(room_doc_xml: str, report_number: str = '') -> str:
    """从单房间 operating_room 完整文档中提取干净的房间参数页 fragment。

    原则：
    - 丢弃封面/声明/公共信息/仪器页等骨架内容
    - 仅保留最后一个房间参数表所在页的标题+编号+数据表
    - 清掉“本页以下无正文”等模板尾迹
    - 房间页编号按传入 report_number 统一填充
    """
    _m = re.search(r'<w:body[^>]*>([\s\S]*?)</w:body>', room_doc_xml)
    if not _m:
        return ''
    _inner = _m.group(1)
    _sect_idx = _inner.rfind('<w:sectPr')
    if _sect_idx >= 0:
        _inner = _inner[:_sect_idx]

    _tbl_matches = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', _inner, re.S))
    if not _tbl_matches:
        return ''
    _last_tbl = _tbl_matches[-1]

    _paras = list(re.finditer(r'<w:p\b[\s\S]*?</w:p>', _inner, re.S))
    _titles = [pm for pm in _paras if re.search(r'<w:t[^>]*>检\s*测\s*报\s*告</w:t>', pm.group(0), re.S)]
    _reports = [pm for pm in _paras if '报告编号：' in pm.group(0)]

    _page_start = _last_tbl.start()
    _report_before_tbl = [pm for pm in _reports if pm.end() <= _last_tbl.start()]
    if _report_before_tbl:
        _last_report = _report_before_tbl[-1]
        _title_before_report = [pm for pm in _titles if pm.end() <= _last_report.start()]
        if _title_before_report:
            _page_start = _title_before_report[-1].start()
        else:
            _page_start = _last_report.start()
    elif _titles:
        _titles_before_tbl = [pm for pm in _titles if pm.start() < _last_tbl.start()]
        if _titles_before_tbl:
            _page_start = _titles_before_tbl[-1].start()

    _fragment = _inner[_page_start:_last_tbl.end()]

    # 若仍混入多组标题/编号，只保留最后一组（最接近数据表的那组）
    _header_pair_matches = list(re.finditer(
        r'(<w:p[\s\S]*?<w:t[^>]*>检\s*测\s*报\s*告</w:t>[\s\S]*?</w:p>\s*<w:p[\s\S]*?报告编号：[\s\S]*?</w:p>)',
        _fragment, re.S
    ))
    if len(_header_pair_matches) > 1:
        _fragment = _fragment[_header_pair_matches[-1].start():]

    # 清掉“本页以下无正文”之类尾迹段落
    _tail_markers = ['本页以下无正文']
    for _marker in _tail_markers:
        _tail_idx = _fragment.find(_marker)
        if _tail_idx >= 0:
            _tail_para_start = _fragment.rfind('<w:p', 0, _tail_idx)
            if _tail_para_start >= 0:
                _fragment = _fragment[:_tail_para_start]

    if report_number:
        _fragment = _replace_all_plain_text(_fragment, '报告编号：', report_number, max_count=3)

    return _fragment


def build_mixed_report_docx(export_payload: Dict[str, Any], output_path: str) -> str:
    """混合报告导出：骨架（前4页）+ 多房间数据页。
    
    如果只有 1 个房间，直接调用 build_template_filled_docx。
    多个房间时：
    1. 用第一个房间的模板生成完整报告（骨架+房间1数据页）
    2. 对房间2~N，从各自等级模板提取数据表，填充后追加
    """
    rooms_export = export_payload.get('rooms_export') or []
    if len(rooms_export) <= 1:
        # 单房间，走现有逻辑，但仍需标准范围校验
        base_path = build_template_filled_docx(export_payload, output_path)
        if not base_path or not Path(base_path).exists() or not rooms_export:
            return base_path
        # 对数据表做标准范围校验 + 结论填充
        with ZipFile(base_path, 'r') as z:
            _s_members = z.namelist()
            _s_doc_xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
            _s_others = {n: z.read(n) for n in _s_members if n != 'word/document.xml' and not n.endswith('/')}
        _s_tbl_matches = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', _s_doc_xml, re.S))
        if _s_tbl_matches:
            _s_last = _s_tbl_matches[-1]
            _s_orig = _s_last.group()
            _s_filled = _fill_data_table_xml(_s_orig, rooms_export[0], export_payload)
            if _s_filled != _s_orig:
                _s_doc_xml = _s_doc_xml[:_s_last.start()] + _s_filled + _s_doc_xml[_s_last.end():]
                # 同时设置 updateFields
                _s_settings = _s_others.get('word/settings.xml', b'')
                if isinstance(_s_settings, bytes):
                    _s_settings = _s_settings.decode('utf-8', errors='ignore')
                if '<w:updateFields' not in _s_settings:
                    _s_settings = _s_settings.replace('</w:settings>', '<w:updateFields w:val="true"/></w:settings>')
                with ZipFile(base_path, 'w', ZIP_DEFLATED) as dst:
                    for n in _s_members:
                        if n.endswith('/'):
                            continue
                        if n == 'word/document.xml':
                            dst.writestr(n, _s_doc_xml)
                        elif n == 'word/settings.xml':
                            dst.writestr(n, _s_settings)
                        else:
                            dst.writestr(n, _s_others.get(n, b''))
        return base_path

    # 步骤1：用第一个房间生成基础文档
    base_path = build_template_filled_docx(export_payload, output_path)
    if not base_path or not Path(base_path).exists():
        return base_path

    # 步骤2：读取基础文档的 document.xml
    with ZipFile(base_path, 'r') as z:
        members = z.namelist()
        document_xml = z.read('word/document.xml').decode('utf-8', errors='ignore')
        other_files = {}
        for name in members:
            if name != 'word/document.xml' and not name.endswith('/'):
                other_files[name] = z.read(name)

    # 步骤2.5：对骨架页（房间1）的数据表做标准范围校验 + 结论填充
    if rooms_export:
        # 先清理通用替换对标签的污染：“受检区域+房间名”→“房间名称”
        _r1_name = (rooms_export[0].get('room', {}).get('room_name') or '').strip()
        if _r1_name:
            document_xml = document_xml.replace(f'受检区域{_r1_name}', '房间名称')
        _tbl_matches = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', document_xml, re.S))
        if _tbl_matches:
            _last_tbl = _tbl_matches[-1]
            _orig_tbl_xml = _last_tbl.group()
            _filled_tbl_xml = _fill_data_table_xml(_orig_tbl_xml, rooms_export[0], export_payload)
            if _filled_tbl_xml != _orig_tbl_xml:
                document_xml = document_xml[:_last_tbl.start()] + _filled_tbl_xml + document_xml[_last_tbl.end():]

    # operating_room mixed report：前四页骨架只保留一次，后续仅追加干净的房间页 fragment。
    if rooms_export and all(str((re.get('room') or {}).get('type_id', '') or '') == 'operating_room' for re in rooms_export):
        _tbl_matches = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', document_xml, re.S))
        if _tbl_matches:
            _last_tbl = _tbl_matches[-1]
            _base_before_tbl = document_xml[:_last_tbl.start()]
            _base_after_tbl = document_xml[_last_tbl.end():]

            _base_report_number = str((((export_payload.get('report_context') or {}).get('project_context') or {}).get('report_number', '')) or '')
            if _base_report_number:
                _first_room_header_pat = re.compile(
                    r'(<w:p[^>]*>[\s\S]*?<w:t[^>]*>检\s*测\s*报\s*告</w:t>[\s\S]*?</w:p>\s*'
                    r'<w:p[^>]*>[\s\S]*?报告编号：</w:t>[\s\S]*?</w:p>\s*)'
                    r'(<w:tbl\b[\s\S]*?房间名称[\s\S]*?</w:tbl>)',
                    re.S
                )
                _hm = _first_room_header_pat.search(document_xml)
                if _hm:
                    _header_block = _hm.group(1)
                    _filled_header_block = _replace_all_plain_text(_header_block, '报告编号：', _base_report_number, max_count=1)
                    if _filled_header_block != _header_block:
                        document_xml = document_xml[:_hm.start(1)] + _filled_header_block + document_xml[_hm.end(1):]
                        _tbl_matches = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', document_xml, re.S))
                        if _tbl_matches:
                            _last_tbl = _tbl_matches[-1]
                            _base_before_tbl = document_xml[:_last_tbl.start()]
                            _base_after_tbl = document_xml[_last_tbl.end():]
            _first_fragment = _extract_operating_room_page_fragment(document_xml, _base_report_number)
            _base_tail_markers = list(re.finditer(
                r'<w:p[\s\S]*?<w:t[^>]*>检\s*测\s*报\s*告</w:t>[\s\S]*?</w:p>\s*<w:p[\s\S]*?报告编号：[\s\S]*?</w:p>',
                _base_before_tbl, re.S
            ))
            if _base_tail_markers:
                _last_base_header_start = _base_tail_markers[-1].start()
                _base_tail_text = re.sub(r'<[^>]+>', '', _base_before_tbl[_last_base_header_start:])
                _base_tail_text = re.sub(r'\s+', ' ', _base_tail_text)
                if '房间名称' not in _base_tail_text:
                    # 确保不截断到仪器表之前：在 _base_before_tbl 中找所有表格，截断点不能早于倒数第一个表格的结束位
                    _pre_tbls = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', _base_before_tbl, re.S))
                    _min_cut = _pre_tbls[-1].end() if _pre_tbls else 0
                    if _last_base_header_start >= _min_cut:
                        _base_before_tbl = _base_before_tbl[:_last_base_header_start]

            _room_pages_xml = _first_fragment or _last_tbl.group(0)
            for _idx, room_export in enumerate(rooms_export[1:], start=2):
                _virtual_payload = dict(export_payload)
                _virtual_payload['room'] = room_export['room']
                _virtual_payload['template_rule'] = room_export['template_rule']
                _virtual_payload['template_resource'] = room_export['template_resource']
                _virtual_payload['report_context'] = room_export['report_context']
                _virtual_payload['clean_class_semantics'] = room_export['clean_class_semantics']
                _virtual_payload['judgement_result'] = room_export['judgement_result']
                _virtual_payload['rooms_export'] = [room_export]
                _tmp_path = str(Path(output_path).with_name(f".{Path(output_path).stem}.room{_idx}.docx"))
                _built_path = build_template_filled_docx(_virtual_payload, _tmp_path)
                if not _built_path or not Path(_built_path).exists():
                    continue
                with ZipFile(_built_path, 'r') as _rz:
                    _room_doc_xml = _rz.read('word/document.xml').decode('utf-8', errors='ignore')
                # 对房间2~N的数据表做表头填充（房间名称/检测日期/洁净度/S/V）
                _room_tbl_matches = list(re.finditer(r'<w:tbl\b.*?</w:tbl>', _room_doc_xml, re.S))
                if _room_tbl_matches:
                    _room_last_tbl = _room_tbl_matches[-1]
                    _room_orig_tbl = _room_last_tbl.group()
                    _room_filled_tbl = _fill_data_table_xml(_room_orig_tbl, room_export, export_payload)
                    if _room_filled_tbl != _room_orig_tbl:
                        _room_doc_xml = _room_doc_xml[:_room_last_tbl.start()] + _room_filled_tbl + _room_doc_xml[_room_last_tbl.end():]
                # 辅房模板标签清理：通用替换可能把“受检区域名称”改成了“受检区域+房间名”，还原为“房间名称”
                _rn = (room_export.get('room', {}).get('room_name') or '').strip()
                if _rn:
                    _room_doc_xml = _room_doc_xml.replace(f'受检区域{_rn}', '房间名称')
                _room_report_number = str((((room_export.get('report_context') or {}).get('project_context') or {}).get('report_number', '')) or _base_report_number)
                _room_fragment = _extract_operating_room_page_fragment(_room_doc_xml, _room_report_number)
                if not _room_fragment:
                    continue
                _room_pages_xml += _page_break_para_xml() + _room_fragment

            if _room_pages_xml:
                document_xml = _base_before_tbl + _room_pages_xml + _base_after_tbl

        output = Path(output_path)
        with ZipFile(str(output), 'w', ZIP_DEFLATED) as dst:
            for name in members:
                if name.endswith('/'):
                    continue
                if name == 'word/document.xml':
                    dst.writestr(name, document_xml)
                elif name == 'word/settings.xml':
                    settings_xml = other_files.get(name, b'').decode('utf-8', errors='ignore') if isinstance(other_files.get(name, b''), bytes) else other_files.get(name, '')
                    if '<w:updateFields' not in settings_xml:
                        settings_xml = settings_xml.replace('</w:settings>', '<w:updateFields w:val="true"/></w:settings>')
                    dst.writestr(name, settings_xml)
                else:
                    dst.writestr(name, other_files.get(name, b''))
        return str(output)

    # 步骤3：对房间2~N，提取数据表并追加
    insert_before = '</w:body>'
    insert_pos = document_xml.rfind(insert_before)
    if insert_pos < 0:
        return base_path  # 异常情况，不追加

    additional_xml = ''
    for room_export in rooms_export[1:]:
        tpl_resource = room_export.get('template_resource', {}) or {}
        tpl_path = tpl_resource.get('template_path', '')
        if not tpl_path or not Path(tpl_path).exists():
            continue

        # 从该房间等级的模板提取数据表
        data_table_xml = _extract_last_table_xml(tpl_path)
        if not data_table_xml:
            continue

        # 填充数据
        filled_table = _fill_data_table_xml(data_table_xml, room_export, export_payload)

        # 追加分页符 + 标题段落 + 数据表
        # 注意：房间页片段/模板自身已带原生报告编号位，这里不要再手工补 report_num_xml，避免第二房间起重复编号
        header_xml = (
            '<w:p><w:pPr><w:jc w:val="center"/></w:pPr>'
            '<w:r><w:rPr><w:rFonts w:ascii="\u5b8b\u4f53" w:hAnsi="\u5b8b\u4f53" w:eastAsia="\u5b8b\u4f53"/>'
            '<w:b/><w:sz w:val="28"/></w:rPr>'
            f'<w:t xml:space="preserve">\u68c0 \u6d4b \u62a5 \u544a</w:t></w:r></w:p>'
        )

        additional_xml += _page_break_para_xml() + header_xml + filled_table

    if additional_xml:
        document_xml = document_xml[:insert_pos] + additional_xml + document_xml[insert_pos:]

    # 步骤4：写出最终文档
    output = Path(output_path)
    with ZipFile(str(output), 'w', ZIP_DEFLATED) as dst:
        for name in members:
            if name.endswith('/'):
                continue
            if name == 'word/document.xml':
                dst.writestr(name, document_xml)
            elif name == 'word/settings.xml':
                # 设置 updateFields=true 让 WPS/Word 打开时自动更新页码域
                settings_xml = other_files.get(name, b'').decode('utf-8', errors='ignore') if isinstance(other_files.get(name, b''), bytes) else other_files.get(name, '')
                if '<w:updateFields' not in settings_xml:
                    settings_xml = settings_xml.replace('</w:settings>', '<w:updateFields w:val="true"/></w:settings>')
                dst.writestr(name, settings_xml)
            else:
                dst.writestr(name, other_files.get(name, b''))

    return str(output)
