import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BASE_DIR = Path(__file__).parent
STANDARDS_FILE = BASE_DIR / 'static' / 'standards_ranges.json'

with open(STANDARDS_FILE, 'r', encoding='utf-8') as f:
    STANDARDS = json.load(f)

OPERATING_ROOM_STANDARD = STANDARDS.get('GB 50333-2013', {}).get('operating_room', {})
AUXILIARY_ROOM_STANDARD = STANDARDS.get('GB 50333-2013', {}).get('auxiliary_room', {})
NEGATIVE_PRESSURE_STANDARD = STANDARDS.get('GB/T 35428-2017', {}).get('negative_pressure', {}).get('_default', {})
CLEAN_FUNCTION_STANDARD = (
    STANDARDS.get('WS 310.1-2016', {}).get('clean_function_room', {})
    or {}
)
CLEAN_FUNCTION_FALLBACK_STANDARD = (
    STANDARDS.get('国家卫生健康委办公厅', {}).get('clean_function_room', {})
    or STANDARDS.get('WS/T 368-2012', {}).get('clean_function_room', {})
    or STANDARDS.get('GB 15982-2012', {}).get('clean_function_room', {})
    or {}
)
GMP_STANDARD = STANDARDS.get('GB 50457-2019', {}).get('gmp_workshop', {})
VETERINARY_GMP_STANDARD = STANDARDS.get('GB 50457-2019', {}).get('veterinary_gmp_workshop', {})
ELECTRONICS_STANDARD = STANDARDS.get('GB 50472-2008', {}).get('electronics_workshop', {})
FOOD_STANDARD = STANDARDS.get('GB 50687-2011', {}).get('food_workshop', {})
ANIMAL_ROOM_STANDARD = STANDARDS.get('GB 14925-2023', {}).get('animal_room', {})
ANIMAL_ROOM_FALLBACK_DEFAULT = STANDARDS.get('实验动物环境及设施', {}).get('animal_room', {}).get('_default', {}) or STANDARDS.get('GB 14925-2023', {}).get('animal_room', {}).get('屏障环境', {})
BSC_STANDARD = STANDARDS.get('GB 41918-2022', {}).get('bsc', {}).get('_default', {})
CLEAN_BENCH_STANDARD = STANDARDS.get('JG/T 292-2010', {}).get('clean_bench', {}).get('_default', {})
IVC_STANDARD = STANDARDS.get('DB32/T972-2006', {}).get('ivc', {}).get('_default', {})
PASS_BOX_STANDARD = STANDARDS.get('JG/T 382-2012', {}).get('pass_box', {})
BSL_STANDARD = STANDARDS.get('GB 50346-2011', {}).get('bsl', {})
LAMINAR_HOOD_STANDARD = STANDARDS.get('GB 50591-2010', {}).get('laminar_hood', {}) or {
    '_default': {
        'avg_speed': {'range': '0.36～0.54', 'unit': 'm/s'},
        'speed_uniformity': {'range': '≤0.20', 'unit': ''},
        'hepa_leak': {'range': '≤0.01', 'unit': '%'},
        'airflow_pattern': {'range': '气流垂直向下、无旋涡', 'unit': ''},
    }
}

OPERATING_ROOM_LEVEL_MAP = {
    'Ⅰ级': 'Ⅰ级（百级）',
    'Ⅱ级': 'Ⅱ级（千级）',
    'Ⅲ级': 'Ⅲ级（万级）',
    'Ⅳ级': 'Ⅳ级（十万级）',
    'Ⅰ级（百级）': 'Ⅰ级（百级）',
    'Ⅱ级（千级）': 'Ⅱ级（千级）',
    'Ⅲ级（万级）': 'Ⅲ级（万级）',
    'Ⅳ级（十万级）': 'Ⅳ级（十万级）',
    'Ⅰ级辅房': '体外循环室',
    'Ⅱ级辅房': '刷手间',
    'Ⅲ级辅房': '术前准备室',
    'Ⅳ级辅房': '恢复室',
    '体外循环室': '体外循环室',
    '刷手间': '刷手间',
    '术前准备室': '术前准备室',
    '恢复室': '恢复室',
}

PARAM_KEY_MAP = {
    'temperature': 'temperature',
    'humidity': 'humidity',
    'pressure': 'pressure',
    'wind_speed': 'wind_speed',
    'wind_uniformity': 'wind_uniformity',
    'airchange': 'airchange',
    'air_changes': 'airchange',
    'airchange_b12': 'airchange_b12',
    'airchange_b3': 'airchange_b3',
    'airchange_clean': 'airchange_clean',
    'airflow_speed': 'airflow_speed',
    'noise': 'noise',
    'illumination': 'illumination',
    'illumination_min': 'illumination_min',
    'illumination_uniformity': 'illumination_uniformity',
    'illumination_main': 'illumination_main',
    'illumination_aux': 'illumination_aux',
    'work_illumination': 'work_illumination',
    'animal_illumination': 'animal_illumination',
    'bacteria': 'bacteria',
    'floating': 'floating',
    'exhaust_speed': 'exhaust_speed',
    'surface_bacteria': 'surface_bacteria',
    'illumination_main_room': 'illumination_main_room',
    'illumination_aux_room': 'illumination_aux_room',
    'illumination_general_processing': 'illumination_general_processing',
    'illumination_mixed_processing': 'illumination_mixed_processing',
    'illumination_non_processing': 'illumination_non_processing',
    'cage_airspeed': 'cage_airspeed',
    'temperature_aux': 'temperature_aux',
    'humidity_aux': 'humidity_aux',
    'temp_diff': 'temp_diff',
    'wind_speed_down': 'downflow_speed',
    'downflow_speed': 'downflow_speed',
    'avg_speed': 'avg_speed',
    'speed_uniformity': 'speed_uniformity',
    'hepa_integrity': 'hepa_integrity',
    'hepa_leak': 'hepa_leak',
    'uv_intensity': 'uv_intensity',
    'airtightness': 'airtightness',
    'door_interlock': 'door_interlock',
    'alarm_interlock': 'alarm_interlock',
    'appearance': 'appearance',
    'function': 'function',
    'airflow_pattern': 'airflow_pattern',
    'airflow_state': 'airflow_state',
    'particle': 'particle',
    'particle_door': 'particle_door',
    'particle_negative': 'particle_negative',
    'settling': 'settling',
    'self_clean': 'self_purification_time',
    'self_purification_time': 'self_purification_time',
}


def _extract_param_payload(param: Dict[str, Any]) -> Dict[str, Any]:
    raw = param.get('raw') if isinstance(param.get('raw'), dict) else {}
    return raw if isinstance(raw, dict) else {}


def _extract_particle_measurements(param: Dict[str, Any]) -> Dict[str, Optional[float]]:
    raw = _extract_param_payload(param)
    data = raw.get('data') if isinstance(raw.get('data'), dict) else {}
    result = {
        'p05_max': None, 'p05_ucl': None, 'p5_max': None, 'p5_ucl': None,
        'op_05_max': None, 'op_05_ucl': None, 'op_5_max': None, 'op_5_ucl': None,
        'surr_05_max': None, 'surr_05_ucl': None, 'surr_5_max': None, 'surr_5_ucl': None,
    }
    for k in result.keys():
        result[k] = _to_number(data.get(k))
    return result


def _extract_bacteria_measurements(param: Dict[str, Any]) -> Dict[str, Optional[float]]:
    raw = _extract_param_payload(param)
    data = raw.get('data') if isinstance(raw.get('data'), dict) else {}
    op_values = data.get('op_values') if isinstance(data.get('op_values'), list) else []
    surr_values = data.get('surr_values') if isinstance(data.get('surr_values'), list) else []
    return {
        'op': max([_to_number(v) for v in op_values if _to_number(v) is not None], default=None),
        'surr': max([_to_number(v) for v in surr_values if _to_number(v) is not None], default=None),
        'value': _to_number(param.get('value')),
    }


def _normalize_range_text(rule: str) -> str:
    return str(rule or '').strip().replace(' ', '').replace('平均', '').replace('~', '～')



def _iter_params(room: Dict[str, Any]):
    params = room.get('params', []) or []
    if isinstance(params, dict):
        for key, item in params.items():
            values = []
            if isinstance(item, dict):
                raw_values = item.get('values')
                if isinstance(raw_values, list):
                    values = raw_values
                elif raw_values is not None:
                    values = [raw_values]
                elif item.get('value') is not None:
                    values = [item.get('value')]
                else:
                    values = [item.get('result')]
            else:
                values = [item]
            for v in values:
                yield {'key': key, 'value': v, 'raw': item}
        return
    for item in params:
        if isinstance(item, dict):
            yield item


def _to_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return None
    m = re.search(r'-?\d+(?:\.\d+)?', s)
    return float(m.group(0)) if m else None


def _parse_range(rule: str) -> Optional[Tuple[Optional[float], Optional[float], bool, bool]]:
    s = _normalize_range_text(rule)
    if not s or s in {'—', '-'}:
        return None
    if '≤' in s and '≥' in s and 'μm' in s:
        return None
    if '～' in s:
        a, b = s.split('～', 1)
        if a[:1] in {'≥', '>', '≤', '<'}:
            a = a[1:]
        if b[:1] in {'≥', '>', '≤', '<'}:
            b = b[1:]
        low = _to_number(a)
        high = _to_number(b)
        if low is not None and high is not None and low > high:
            low, high = high, low
        return low, high, True, True
    m_between = re.match(r'^(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)$', s)
    if m_between:
        low = float(m_between.group(1))
        high = float(m_between.group(2))
        if low > high:
            low, high = high, low
        return low, high, True, True
    if s.startswith('≥'):
        return _to_number(s[1:]), None, True, True
    if s.startswith('>'):
        return _to_number(s[1:]), None, False, True
    if s.startswith('≤'):
        return None, _to_number(s[1:]), True, True
    if s.startswith('<'):
        return None, _to_number(s[1:]), True, False
    return None


def _within(value: float, parsed: Tuple[Optional[float], Optional[float], bool, bool]) -> bool:
    low, high, low_inclusive, high_inclusive = parsed
    if low is not None:
        if low_inclusive and value < low:
            return False
        if not low_inclusive and value <= low:
            return False
    if high is not None:
        if high_inclusive and value > high:
            return False
        if not high_inclusive and value >= high:
            return False
    return True


def _particle_rule_upper_limit(rule_text: str) -> Optional[float]:
    s = _normalize_range_text(rule_text)
    m = re.search(r'≤(-?\d+(?:\.\d+)?)', s)
    if m:
        return float(m.group(1))
    m = re.search(r'<(-?\d+(?:\.\d+)?)', s)
    if m:
        return float(m.group(1))
    return None


def _judge_particle_param(src_key: str, rule: Dict[str, Any], param: Dict[str, Any]) -> List[Dict[str, Any]]:
    m = _extract_particle_measurements(param)
    checks = []

    if rule.get('range'):
        range_text = _normalize_range_text(rule.get('range'))
        parts = [p.strip() for p in range_text.split(',') if p.strip()]
        if len(parts) >= 1 and m.get('p05_max') is not None:
            checks.append((f'{src_key}.p05_max', m['p05_max'], parts[0]))
        if len(parts) >= 2 and m.get('p5_max') is not None:
            checks.append((f'{src_key}.p5_max', m['p5_max'], parts[1]))
        if not checks and param.get('value') is not None:
            return []

    if rule.get('range_op') or rule.get('range_surr'):
        op_parts = [p.strip() for p in _normalize_range_text(rule.get('range_op')).split(',') if p.strip()] if rule.get('range_op') else []
        surr_parts = [p.strip() for p in _normalize_range_text(rule.get('range_surr')).split(',') if p.strip()] if rule.get('range_surr') else []
        if len(op_parts) >= 1 and m.get('op_05_max') is not None:
            checks.append((f'{src_key}.op_05_max', m['op_05_max'], op_parts[0]))
        if len(op_parts) >= 2 and m.get('op_5_max') is not None:
            checks.append((f'{src_key}.op_5_max', m['op_5_max'], op_parts[1]))
        if len(surr_parts) >= 1 and m.get('surr_05_max') is not None:
            checks.append((f'{src_key}.surr_05_max', m['surr_05_max'], surr_parts[0]))
        if len(surr_parts) >= 2 and m.get('surr_5_max') is not None:
            checks.append((f'{src_key}.surr_5_max', m['surr_5_max'], surr_parts[1]))

    results = []
    for key, value, range_text in checks:
        upper = _particle_rule_upper_limit(range_text)
        if upper is None:
            continue
        results.append({
            'key': key,
            'standard_key': rule.get('_std_key', 'particle'),
            'value': value,
            'range': range_text,
            'passed': value <= upper,
            'unit': rule.get('unit', ''),
        })
    return results


def _judge_bacteria_param(src_key: str, rule: Dict[str, Any], param: Dict[str, Any]) -> List[Dict[str, Any]]:
    m = _extract_bacteria_measurements(param)
    checks = []
    if rule.get('range_op') and m.get('op') is not None:
        checks.append((f'{src_key}.op', m['op'], rule.get('range_op')))
    if rule.get('range_surr') and m.get('surr') is not None:
        checks.append((f'{src_key}.surr', m['surr'], rule.get('range_surr')))
    if rule.get('range') and m.get('value') is not None:
        checks.append((src_key, m['value'], rule.get('range')))

    results = []
    for key, value, range_text in checks:
        parsed = _parse_range(range_text)
        if not parsed:
            continue
        results.append({
            'key': key,
            'standard_key': rule.get('_std_key', 'bacteria'),
            'value': value,
            'range': range_text,
            'passed': _within(value, parsed),
            'unit': rule.get('unit', ''),
        })
    return results


def _normalize_operating_room_level(room: Dict[str, Any]) -> Tuple[str, bool]:
    ctx = room.get('context') or {}
    branch = ctx.get('surgery_room_type') or ctx.get('room_type') or ''
    level_name = room.get('level_name') or room.get('clean_class') or ''
    room_name = room.get('room_name') or ''
    is_aux = branch in ('洁净辅房', '辅房', 'auxiliary-room') or '辅房' in str(level_name)
    raw = room_name if is_aux else level_name
    return OPERATING_ROOM_LEVEL_MAP.get(raw, raw), is_aux


def judge_operating_room(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    level_key, is_aux = _normalize_operating_room_level(room)
    ctx = room.get('context') or {}
    is_eye = (ctx.get('surgery_room_type') or '') == '眼科手术室' and not is_aux
    eye_standard = STANDARDS.get('GB 50333-2013', {}).get('eye_operating_room', {})
    standard_group = AUXILIARY_ROOM_STANDARD if is_aux else (eye_standard if is_eye else OPERATING_ROOM_STANDARD)
    rules = standard_group.get(level_key)
    if not rules:
        return None

    item_results: List[Dict[str, Any]] = []
    abnormal_items: List[Dict[str, Any]] = []
    for param in _iter_params(room):
        src_key = param.get('key')
        std_key = PARAM_KEY_MAP.get(src_key)
        if not std_key:
            continue
        rule = dict(rules.get(std_key) or {})
        if not rule:
            continue
        rule['_std_key'] = std_key

        if std_key in {'particle', 'particle_door'}:
            items = _judge_particle_param(src_key, rule, param)
        elif std_key == 'bacteria':
            items = _judge_bacteria_param(src_key, rule, param)
        else:
            range_text = rule.get('range')
            if not range_text:
                continue
            value = _to_number(param.get('value'))
            if value is None:
                continue
            parsed = _parse_range(range_text)
            if not parsed:
                continue
            items = [{
                'key': src_key,
                'standard_key': std_key,
                'value': value,
                'range': range_text,
                'passed': _within(value, parsed),
                'unit': rule.get('unit', ''),
            }]

        item_results.extend(items)
        abnormal_items.extend([x for x in items if not x.get('passed')])

    if not item_results:
        return None
    return {
        'engine': 'operating_room_v2',
        'matched_standard': 'GB 50333-2013',
        'matched_level': level_key,
        'room_branch': 'auxiliary-room' if is_aux else ('eye-operating-room' if is_eye else 'main-room'),
        'item_results': item_results,
        'abnormal_items': abnormal_items,
        'result_state': '不合格' if abnormal_items else '合格',
        'reason': '存在超出标准范围的检测项' if abnormal_items else '已检测项目均落入标准范围',
    }




def _normalize_clean_function_level(room: Dict[str, Any]) -> str:
    ctx = room.get('context') or {}
    subroom = ctx.get('clean_function_subroom') or room.get('clean_function_subroom') or ''
    explicit = room.get('level_name') or room.get('clean_class') or ''
    if explicit in CLEAN_FUNCTION_STANDARD:
        return explicit
    default_map = {
        'ICU病房': 'Ⅲ级（万级）',
        '消毒供应中心': 'Ⅲ级（万级）',
        '透析室': 'Ⅲ级（万级）',
        '通用洁净功能用房': 'Ⅲ级（万级）',
    }
    return default_map.get(subroom, 'Ⅲ级（万级）')


def _judge_by_rules(room: Dict[str, Any], rules: Dict[str, Any], engine: str, standard: str, matched_level: str, room_branch: str) -> Optional[Dict[str, Any]]:
    if not rules:
        return None
    item_results: List[Dict[str, Any]] = []
    abnormal_items: List[Dict[str, Any]] = []
    for param in _iter_params(room):
        src_key = param.get('key')
        std_key = PARAM_KEY_MAP.get(src_key)
        if not std_key:
            continue
        rule = dict(rules.get(std_key) or {})
        if not rule:
            continue
        rule['_std_key'] = std_key

        if std_key in {'particle', 'particle_door', 'particle_negative'}:
            items = _judge_particle_param(src_key, rule, param)
        elif std_key in {'bacteria', 'settling', 'floating'}:
            items = _judge_bacteria_param(src_key, rule, param)
        else:
            range_text = rule.get('range')
            if not range_text or '→' in str(range_text):
                continue
            value = _to_number(param.get('value'))
            if value is None:
                continue
            parsed = _parse_range(range_text)
            if not parsed:
                continue
            items = [{
                'key': src_key,
                'standard_key': std_key,
                'value': value,
                'range': range_text,
                'passed': _within(value, parsed),
                'unit': rule.get('unit', ''),
            }]
        item_results.extend(items)
        abnormal_items.extend([x for x in items if not x.get('passed')])
    if not item_results:
        return None
    return {
        'engine': engine,
        'matched_standard': standard,
        'matched_level': matched_level,
        'room_branch': room_branch,
        'item_results': item_results,
        'abnormal_items': abnormal_items,
        'result_state': '不合格' if abnormal_items else '合格',
        'reason': '存在超出标准范围的检测项' if abnormal_items else '已检测项目均落入标准范围',
    }


def judge_negative_pressure(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _judge_by_rules(room, NEGATIVE_PRESSURE_STANDARD, 'negative_pressure_v1', 'GB/T 35428-2017', '_default', 'negative-pressure-room')


def judge_clean_function_room(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    level = _normalize_clean_function_level(room)
    rules = dict(CLEAN_FUNCTION_FALLBACK_STANDARD.get(level) or {})
    rules.update(CLEAN_FUNCTION_STANDARD.get(level) or {})
    return _judge_by_rules(room, rules, 'clean_function_room_v1', 'WS 310.1-2016 + 国家卫生健康委办公厅', level, 'clean-function-room')


def judge_gmp_workshop(room: Dict[str, Any], veterinary: bool = False) -> Optional[Dict[str, Any]]:
    level = room.get('level_name') or room.get('clean_class') or 'C级'
    rules_group = VETERINARY_GMP_STANDARD if veterinary else GMP_STANDARD
    rules = rules_group.get(level) or {}
    engine = 'veterinary_gmp_workshop_v1' if veterinary else 'gmp_workshop_v1'
    branch = 'veterinary-gmp-workshop' if veterinary else 'gmp-workshop'
    standard = 'GB 50457-2019'
    return _judge_by_rules(room, rules, engine, standard, level, branch)


def judge_electronics_workshop(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ctx = room.get('context') or {}
    level = ctx.get('iso_level') or room.get('level_name') or room.get('clean_class') or 'ISO 7'
    # 统一归一化：ISO-7 → ISO 7，ISO7级 → ISO 7，ISO7 → ISO 7
    level = level.replace('-', ' ').strip()
    level = level.replace('ISO5级', 'ISO 5').replace('ISO6级', 'ISO 6').replace('ISO7级', 'ISO 7').replace('ISO8级', 'ISO 8').replace('ISO9级', 'ISO 9')
    # 补全无空格形式：ISO7 → ISO 7
    import re as _re
    level = _re.sub(r'^ISO(\d)$', r'ISO \1', level)
    rules = ELECTRONICS_STANDARD.get(level) or {}
    return _judge_by_rules(room, rules, 'electronics_workshop_v1', 'GB 50472-2008', level, 'electronics-workshop')


def judge_food_workshop(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    level = room.get('level_name') or room.get('clean_class') or 'Ⅲ级'
    level = {
        'Ⅰ级': 'Ⅰ级（百级）',
        'Ⅱ级': 'Ⅱ级（万级）',
        'Ⅲ级': 'Ⅲ级（十万级）',
        'Ⅳ级': 'Ⅳ级（三十万级）',
    }.get(level, level)
    rules = FOOD_STANDARD.get(level) or {}
    return _judge_by_rules(room, rules, 'food_workshop_v1', 'GB 50687-2011', level, 'food-workshop')


def judge_bsc(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _judge_by_rules(room, BSC_STANDARD, 'bsc_v1', 'GB 41918-2022', '_default', 'biosafety-cabinet')


def judge_clean_bench(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _judge_by_rules(room, CLEAN_BENCH_STANDARD, 'clean_bench_v1', 'JG/T 292-2010', '_default', 'clean-bench')


def judge_ivc(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return _judge_by_rules(room, IVC_STANDARD, 'ivc_v1', 'DB32/T972-2006', '_default', 'ivc')


def judge_pass_box(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ctx = room.get('context') or {}
    level = ctx.get('pass_box_mode') or room.get('level_name') or room.get('clean_class') or '_default'
    if level in ('默认', 'default', '_default', ''):
        level = '_default'
    rules = PASS_BOX_STANDARD.get(level) or PASS_BOX_STANDARD.get('_default') or {}
    return _judge_by_rules(room, rules, 'pass_box_v1', 'JG/T 382-2012', level, 'pass-box')


def judge_laminar_hood(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    rules = LAMINAR_HOOD_STANDARD.get('_default') or {}
    if not rules:
        return None

    item_results: List[Dict[str, Any]] = []
    abnormal_items: List[Dict[str, Any]] = []
    for param in _iter_params(room):
        src_key = param.get('key')
        if src_key == 'airflow_pattern':
            raw = str(param.get('value') or '').strip()
            if not raw:
                continue
            normalized = raw.replace('，', ',').replace('、', ',').replace('。', '').replace('；', ',').replace(' ', '')
            has_vertical_down = any(token in normalized for token in ['垂直向下', '垂直下降', '向下'])
            has_no_vortex = any(token in normalized for token in ['无旋涡', '无涡流', '无回流'])
            has_bad_flow = any(token in normalized for token in ['紊流', '旋涡', '涡流', '回流']) and not has_no_vortex
            passed = has_vertical_down and has_no_vortex and not has_bad_flow
            item = {
                'key': src_key,
                'standard_key': src_key,
                'value': raw,
                'range': '气流垂直向下、无旋涡',
                'passed': passed,
                'unit': '',
            }
            item_results.append(item)
            if not passed:
                abnormal_items.append(item)
            continue

        std_key = PARAM_KEY_MAP.get(src_key)
        if not std_key:
            continue
        rule = rules.get(std_key) or {}
        range_text = rule.get('range')
        if not range_text:
            continue
        value = _to_number(param.get('value'))
        if value is None:
            continue
        parsed = _parse_range(range_text)
        if not parsed:
            continue
        passed = _within(value, parsed)
        item = {
            'key': src_key,
            'standard_key': std_key,
            'value': value,
            'range': range_text,
            'passed': passed,
            'unit': rule.get('unit', ''),
        }
        item_results.append(item)
        if not passed:
            abnormal_items.append(item)

    if not item_results:
        return None
    return {
        'engine': 'laminar_hood_v1',
        'matched_standard': 'GB 50591-2010 + 项目内控规则',
        'matched_level': '_default',
        'room_branch': 'laminar-hood',
        'item_results': item_results,
        'abnormal_items': abnormal_items,
        'result_state': '不合格' if abnormal_items else '合格',
        'reason': '存在超出标准范围的检测项' if abnormal_items else '已检测项目均落入标准范围',
    }


def judge_animal_room(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ctx = room.get('context') or {}
    env = ctx.get('animal_environment') or room.get('level_name') or room.get('clean_class') or '普通环境'
    barrier_class = ctx.get('barrier_room_class') or room.get('barrier_room_class') or ''
    aux_room = ctx.get('barrier_aux_room') or room.get('barrier_aux_room') or ''
    if env == '屏障环境' and barrier_class == '洁净辅房' and aux_room:
        group = ANIMAL_ROOM_STANDARD.get('屏障环境洁净辅房', {})
        rules = group.get(aux_room) or {}
        matched_level = f'屏障环境洁净辅房/{aux_room}'
    elif env == '隔离环境':
        rules = ANIMAL_ROOM_FALLBACK_DEFAULT
        matched_level = '隔离环境'
    else:
        rules = ANIMAL_ROOM_STANDARD.get(env) or {}
        matched_level = env
    return _judge_by_rules(room, rules, 'animal_room_v1', 'GB 14925-2023', matched_level, 'animal-room')


def judge_bsl(room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    ctx = room.get('context') or {}
    level = ctx.get('bsl_level') or room.get('level_name') or room.get('clean_class') or 'BSL-2（P2）'
    if '2' in level:
        iso = 'ISO-7'
    elif '3' in level:
        iso = 'ISO-5'
    else:
        iso = 'ISO-7'
    rules = BSL_STANDARD.get(iso) or {}
    return _judge_by_rules(room, rules, 'bsl_v1', 'GB 50346-2011', iso, 'biosafety-lab')


def judge_room(project: Dict[str, Any], room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    type_id = (room.get('type_id') or '')
    if type_id == 'operating_room':
        return judge_operating_room(room)
    if type_id == 'negative_pressure':
        return judge_negative_pressure(room)
    if type_id == 'clean_function_room':
        return judge_clean_function_room(room)
    if type_id == 'gmp_workshop':
        return judge_gmp_workshop(room, veterinary=False)
    if type_id == 'veterinary_gmp_workshop':
        return judge_gmp_workshop(room, veterinary=True)
    if type_id == 'electronics_workshop':
        return judge_electronics_workshop(room)
    if type_id == 'food_workshop':
        return judge_food_workshop(room)
    if type_id == 'animal_room':
        return judge_animal_room(room)
    if type_id == 'bsc':
        return judge_bsc(room)
    if type_id == 'clean_bench':
        return judge_clean_bench(room)
    if type_id == 'ivc':
        return judge_ivc(room)
    if type_id == 'pass_box':
        return judge_pass_box(room)
    if type_id == 'laminar_hood':
        return judge_laminar_hood(room)
    if type_id == 'bsl':
        return judge_bsl(room)
    return None
