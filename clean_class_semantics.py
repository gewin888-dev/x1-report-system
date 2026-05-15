from typing import Any, Dict


OPERATING_ROOM_AUX_LEVEL_MAP = {
    'Ⅰ级（局部5级其他6级）': 'Ⅰ级（局部5级其他6级）',
    'Ⅱ级（7级）': 'Ⅱ级（7级）',
    'Ⅲ级（8级）': 'Ⅲ级（8级）',
    'Ⅳ级（8.5级）': 'Ⅳ级（8.5级）',
    'Ⅰ级辅房': 'Ⅰ级（局部5级其他6级）',
    'Ⅱ级辅房': 'Ⅱ级（7级）',
    'Ⅲ级辅房': 'Ⅲ级（8级）',
    'Ⅳ级辅房': 'Ⅳ级（8.5级）',
}

OPERATING_ROOM_MAIN_LEVEL_KEY_MAP = {
    'Ⅰ级': 'level1',
    'Ⅰ级（百级）': 'level1',
    'Ⅱ级': 'level2',
    'Ⅱ级（千级）': 'level2',
    'Ⅲ级': 'level3',
    'Ⅲ级（万级）': 'level3',
    'Ⅳ级': 'level4',
    'Ⅳ级（十万级）': 'level4',
}

OPERATING_ROOM_AUX_LEVEL_KEY_MAP = {
    'Ⅰ级（局部5级其他6级）': 'level1',
    'Ⅱ级（7级）': 'level2',
    'Ⅲ级（8级）': 'level3',
    'Ⅳ级（8.5级）': 'level4',
}


def _normalize_operating_room_level_key(level_name: str, aux: bool = False) -> str:
    normalized = str(level_name or '').strip()
    if aux:
        return OPERATING_ROOM_AUX_LEVEL_KEY_MAP.get(normalized, 'unknown')
    return OPERATING_ROOM_MAIN_LEVEL_KEY_MAP.get(normalized, 'unknown')


def _normalize_operating_room_context(room: Dict[str, Any]) -> Dict[str, str]:
    context = room.get('context') or {}
    level_name = room.get('level_name') or room.get('clean_class') or ''

    branch_raw = (
        context.get('surgery_room_type')
        or context.get('room_type')
        or ''
    )
    aux_raw = context.get('surgery_aux_clean_class') or ''

    if branch_raw in ('auxiliary-room', '洁净辅房', '辅房') or '局部5级其他6级' in level_name or '（7级）' in level_name or '（8级）' in level_name or '（8.5级）' in level_name:
        branch = '辅房'
        aux_clean = OPERATING_ROOM_AUX_LEVEL_MAP.get(aux_raw or level_name, aux_raw or level_name)
    else:
        branch = branch_raw or '手术室'
        if branch in ('main-room', ''):
            branch = '手术室'
        aux_clean = OPERATING_ROOM_AUX_LEVEL_MAP.get(aux_raw, aux_raw)

    return {
        'surgery_room_type': branch,
        'surgery_aux_clean_class': aux_clean,
    }


def build_clean_class_semantics(project: Dict[str, Any]) -> Dict[str, Any]:
    rooms = project.get('rooms') or []
    room = rooms[0] if rooms else {}
    context = room.get('context') or {}

    domain = project.get('domain', '')
    type_id = room.get('type_id', '')
    level_name = room.get('level_name') or room.get('clean_class') or ''
    surgery_room_type = context.get('surgery_room_type', '')
    surgery_aux_clean_class = context.get('surgery_aux_clean_class', '')
    if domain == 'hospital' and type_id == 'operating_room':
        normalized = _normalize_operating_room_context(room)
        surgery_room_type = normalized.get('surgery_room_type', surgery_room_type)
        surgery_aux_clean_class = normalized.get('surgery_aux_clean_class', surgery_aux_clean_class)
    clean_function_subroom = context.get('clean_function_subroom', '') or context.get('room_usage', '')

    semantics = {
        'domain': domain,
        'standard_code': '',
        'object_type': type_id,
        'object_branch': surgery_room_type or clean_function_subroom,
        'level_raw': level_name,
        'level_semantic_key': '',
        'semantic_note': '',
        'impacts': [],
    }

    if domain == 'hospital' and type_id == 'operating_room':
        semantics['standard_code'] = 'GB 50333-2013'
        if surgery_room_type in ('洁净辅房', '辅房'):
            semantics['level_raw'] = surgery_aux_clean_class or level_name
            aux_level_key = _normalize_operating_room_level_key(surgery_aux_clean_class or level_name, aux=True)
            semantics['level_semantic_key'] = f"hospital.operating_room.aux.{aux_level_key}"
            semantics['semantic_note'] = '医院洁净手术部洁净辅房等级表达，属于辅房链，不等于主手术室等级。'
            semantics['impacts'] = ['template_rule', 'parameter_override', 'report_context']
        elif surgery_room_type == '眼科手术室':
            main_level_key = _normalize_operating_room_level_key(level_name, aux=False)
            semantics['level_semantic_key'] = f"hospital.operating_room.eye.{main_level_key}"
            semantics['semantic_note'] = '医院洁净手术部眼科手术室等级表达，当前模板可与主手术室复用，但业务语义应单独归到 eye 链。'
            semantics['impacts'] = ['template_rule', 'report_context']
        else:
            main_level_key = _normalize_operating_room_level_key(level_name, aux=False)
            semantics['level_semantic_key'] = f"hospital.operating_room.main.{main_level_key}"
            semantics['semantic_note'] = '医院洁净手术部主手术室等级表达。'
            semantics['impacts'] = ['template_rule', 'report_context']

    elif domain == 'hospital' and type_id == 'clean_function_room':
        semantics['standard_code'] = 'GB 50333-2013'
        semantics['object_branch'] = clean_function_subroom
        subroom_map = {
            'ICU': 'icu',
            'ICU病房': 'icu',
            '消毒供应中心': 'cssd',
            '透析室': 'dialysis',
        }
        subroom_key = subroom_map.get(clean_function_subroom, 'general' if clean_function_subroom else 'general')
        semantics['level_semantic_key'] = f"hospital.clean_function_room.{subroom_key}"
        semantics['semantic_note'] = '医院洁净功能用房等级表达需要结合子房间语义理解，不能脱离子房间独立看待。'
        semantics['impacts'] = ['template_rule', 'report_context']

    elif domain == 'pharma' and type_id == 'pass_box':
        semantics['standard_code'] = 'GB 50457-2019'
        semantics['object_branch'] = 'default'
        semantics['level_raw'] = level_name or '无等级要求'
        semantics['level_semantic_key'] = 'pharma.pass_box.default'
        semantics['semantic_note'] = '传递窗当前按单模板维护态对象治理。'
        semantics['impacts'] = ['template_rule', 'report_context']

    elif domain == 'pharma' and type_id == 'laminar_hood':
        semantics['standard_code'] = 'GB 50457-2019'
        semantics['object_branch'] = 'default'
        semantics['level_raw'] = level_name or 'A级'
        semantics['level_semantic_key'] = 'pharma.laminar_hood.default'
        semantics['semantic_note'] = '层流罩当前按单模板维护态对象治理。'
        semantics['impacts'] = ['template_rule', 'report_context']

    elif domain == 'biosafety' and type_id == 'bsc':
        semantics['standard_code'] = 'NSF/ANSI 49'
        semantics['object_branch'] = 'default'
        semantics['level_raw'] = level_name or context.get('bsc_class', '') or 'default'
        semantics['level_semantic_key'] = 'biosafety.bsc.default'
        semantics['semantic_note'] = '生物安全柜当前按单模板维护态对象治理。'
        semantics['impacts'] = ['template_rule', 'report_context']

    elif domain == 'biosafety' and type_id == 'clean_bench':
        semantics['standard_code'] = 'JG/T 292-2010'
        semantics['object_branch'] = 'default'
        semantics['level_raw'] = level_name or 'default'
        semantics['level_semantic_key'] = 'biosafety.clean_bench.default'
        semantics['semantic_note'] = '洁净工作台当前按单模板维护态对象治理。'
        semantics['impacts'] = ['template_rule', 'report_context']

    elif domain == 'biosafety' and type_id == 'ivc':
        semantics['standard_code'] = 'GB 14925-2023'
        semantics['object_branch'] = 'default'
        semantics['level_raw'] = level_name or 'default'
        semantics['level_semantic_key'] = 'biosafety.ivc.default'
        semantics['semantic_note'] = 'IVC 笼具当前按单模板维护态对象治理。'
        semantics['impacts'] = ['template_rule', 'report_context']

    elif domain == 'biosafety' and type_id == 'bsl':
        semantics['standard_code'] = 'GB 50346-2011 + GB 19489-2008'
        bsl_level = context.get('bsl_level') or context.get('bsl') or ''
        level_norm = str(bsl_level or level_name or '').strip().upper()
        semantics['object_branch'] = bsl_level or level_name
        semantics['level_raw'] = bsl_level or level_name
        semantics['level_semantic_key'] = f"biosafety.bsl.{level_norm.lower()}" if level_norm in ('P2', 'P3') else f"biosafety.bsl.clean_class.{level_name or 'unknown'}"
        semantics['semantic_note'] = '生物安全对象中，BSL等级与洁净等级不是同一概念，洁净等级通常还需与ISO表达联合理解。'
        semantics['impacts'] = ['template_rule', 'report_context', 'compliance_check']

    elif domain == 'pharma' and type_id == 'gmp_workshop':
        gmp_grade = context.get('gmp_grade', '') or level_name
        grade_norm = str(gmp_grade or 'unknown').strip().replace('（', '(').replace('）', ')')
        grade_norm = grade_norm.replace('A级', 'a').replace('B级', 'b').replace('C级', 'c').replace('D级', 'd')
        grade_norm = grade_norm.replace('a级', 'a').replace('b级', 'b').replace('c级', 'c').replace('d级', 'd')
        semantics['standard_code'] = 'GB 50457-2019 + GMP 2010'
        semantics['object_branch'] = gmp_grade
        semantics['level_raw'] = gmp_grade
        semantics['level_semantic_key'] = f"pharma.gmp_workshop.grade.{grade_norm or 'unknown'}"
        semantics['semantic_note'] = 'GMP车间等级表达属于制药工业洁净环境体系，应独立于医院等级和ISO等级理解。'
        semantics['impacts'] = ['template_rule', 'report_context', 'parameter_profile']

    elif domain == 'pharma' and type_id == 'veterinary_gmp_workshop':
        gmp_grade = context.get('gmp_grade', '') or level_name
        grade_norm = str(gmp_grade or 'unknown').strip().replace('（', '(').replace('）', ')')
        grade_norm = grade_norm.replace('A级', 'a').replace('B级', 'b').replace('C级', 'c').replace('D级', 'd')
        grade_norm = grade_norm.replace('a级', 'a').replace('b级', 'b').replace('c级', 'c').replace('d级', 'd')
        semantics['standard_code'] = '农业农村部令2020年第3号 + 农业农村部公告第389号 + 农业农村部公告第292号'
        semantics['object_branch'] = gmp_grade
        semantics['level_raw'] = gmp_grade
        semantics['level_semantic_key'] = f"pharma.veterinary_gmp_workshop.grade.{grade_norm or 'unknown'}"
        semantics['semantic_note'] = '兽药车间等级表达属于兽药 GMP 独立标准链，不能直接按普通 GMP 车间语义替代。'
        semantics['impacts'] = ['template_rule', 'report_context', 'parameter_profile', 'compliance_check']

    elif domain == 'food' and type_id == 'food_workshop':
        food_grade = context.get('food_grade', '') or level_name
        grade_norm = str(food_grade or 'unknown').strip().replace('Ⅰ级', '1').replace('Ⅱ级', '2').replace('Ⅲ级', '3').replace('Ⅳ级', '4')
        semantics['standard_code'] = 'GB 50687-2011 + GB 50591-2010'
        semantics['object_branch'] = food_grade
        semantics['level_raw'] = food_grade
        semantics['level_semantic_key'] = f"food.food_workshop.grade.{grade_norm or 'unknown'}"
        semantics['semantic_note'] = '食品车间等级表达属于食品工业洁净环境体系，采用Ⅰ/Ⅱ/Ⅲ/Ⅳ级链，不能直接按 GMP 或电子 ISO 等级替代。'
        semantics['impacts'] = ['template_rule', 'report_context', 'parameter_profile']

    elif domain == 'electronics' and type_id == 'electronics_workshop':
        iso_level = context.get('iso_level', '') or level_name
        iso_level = str(iso_level or '').strip().upper().replace('ISO ', '').replace('ISO', '')
        semantics['standard_code'] = 'GB 50472-2008 + GB 50073-2013'
        semantics['object_branch'] = f"ISO {iso_level}" if iso_level else ''
        semantics['level_raw'] = f"ISO {iso_level}" if iso_level else ''
        semantics['level_semantic_key'] = f"electronics.electronics_workshop.iso.{iso_level if iso_level else 'unknown'}"
        semantics['semantic_note'] = '电子车间ISO等级属于电子工业洁净环境体系，语义键应统一归一到纯数字等级。'
        semantics['impacts'] = ['template_rule', 'report_context', 'parameter_profile']

    elif domain == 'hospital' and type_id == 'negative_pressure':
        mode = context.get('negative_pressure_mode', 'ward-pressure-driven')
        semantics['standard_code'] = 'GB/T 35428-2017 + WS/T 368-2012'
        semantics['object_branch'] = mode
        semantics['level_raw'] = level_name or '无洁净等级要求'
        semantics['level_semantic_key'] = 'hospital.negative_pressure.no-clean-class'
        semantics['semantic_note'] = '负压病房对象核心不在洁净等级，而在压差、气流流向、换气与感染控制要求。'
        semantics['impacts'] = ['template_rule', 'report_context', 'pressure_chain']

    elif domain == 'biosafety' and type_id == 'animal_room':
        animal_environment = context.get('animal_environment', '') or level_name
        barrier_room_class = context.get('barrier_room_class', '')
        barrier_aux_room = context.get('barrier_aux_room', '')
        branch = '/'.join([v for v in [animal_environment, barrier_room_class, barrier_aux_room] if v])
        semantics['standard_code'] = 'GB 14925-2023'
        semantics['object_branch'] = branch or animal_environment
        semantics['level_raw'] = animal_environment or level_name

        aux_map = {
            '洁物储存室': 'clean_storage',
            '灭菌后室/区': 'after_sterilization',
            '灭菌后室区': 'after_sterilization',
            '洁净走廊': 'clean_corridor',
            '污物走廊': 'dirty_corridor',
            '缓冲间': 'buffer',
            '二更': 'change_room_2',
            '清洗消毒室': 'cleaning_disinfection',
            '一更': 'change_room_1',
        }
        if animal_environment == '屏障环境' and barrier_room_class == '洁净辅房':
            semantics['level_semantic_key'] = f"biosafety.animal_room.barrier_aux.{aux_map.get(barrier_aux_room, 'unknown')}"
        elif animal_environment == '屏障环境':
            semantics['level_semantic_key'] = 'biosafety.animal_room.barrier_main'
        elif animal_environment == '隔离环境':
            semantics['level_semantic_key'] = 'biosafety.animal_room.isolation'
        else:
            semantics['level_semantic_key'] = 'biosafety.animal_room.normal'
        semantics['semantic_note'] = '动物房环境表达需要结合普通/屏障/隔离环境、房间类别与洁净辅房共同理解。'
        semantics['impacts'] = ['template_rule', 'report_context', 'parameter_profile']

    return semantics
