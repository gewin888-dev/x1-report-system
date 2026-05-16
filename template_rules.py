from typing import Any, Dict
from clean_class_semantics import build_clean_class_semantics, _normalize_operating_room_context

TEMPLATE_RULE_REGISTRY = {
    'hospital.operating_room': {
        'main-room': {
            'Ⅰ级': {
                'template_key': 'hospital/operating_room/main/level1',
                'template_name': '洁净手术部-百级手术室',
            },
            'Ⅱ级': {
                'template_key': 'hospital/operating_room/main/level2',
                'template_name': '洁净手术部-千级手术室',
            },
            'Ⅲ级': {
                'template_key': 'hospital/operating_room/main/level3',
                'template_name': '洁净手术部-万级手术室',
            },
            'Ⅳ级': {
                'template_key': 'hospital/operating_room/main/level4',
                'template_name': '洁净手术部-十万级手术室',
            },
        },
        'auxiliary-room': {
            'Ⅰ级（局部5级其他6级）': {
                'template_key': 'hospital/operating_room/aux/level1',
                'template_name': '洁净手术部-辅房I级',
            },
            'Ⅱ级（7级）': {
                'template_key': 'hospital/operating_room/aux/level2',
                'template_name': '洁净手术部-辅房II级',
            },
            'Ⅲ级（8级）': {
                'template_key': 'hospital/operating_room/aux/level3',
                'template_name': '洁净手术部-辅房III级',
            },
            'Ⅳ级（8.5级）': {
                'template_key': 'hospital/operating_room/aux/level4',
                'template_name': '洁净手术部-辅房IV级',
            },
        },
    },
    'hospital.clean_function_room': {
        'subroom-default': {
            'ICU病房': {
                'template_key': 'hospital/clean_function_room/icu',
                'template_name': '洁净功能用房-ICU病房',
            },
            '消毒供应中心': {
                'template_key': 'hospital/clean_function_room/cssd',
                'template_name': '洁净功能用房-消毒供应中心',
            },
            '透析室': {
                'template_key': 'hospital/clean_function_room/dialysis',
                'template_name': '洁净功能用房-透析室',
            },
            '通用洁净功能用房': {
                'template_key': 'hospital/clean_function_room/general',
                'template_name': '洁净功能用房-通用',
            },
        },
    },
    'biosafety.bsl': {
        'bsl-default': {
            'P2': {
                'template_key': 'biosafety/bsl/p2',
                'template_name': '生物安全实验室-P2',
            },
            'P3': {
                'template_key': 'biosafety/bsl/p3',
                'template_name': '生物安全实验室-P3',
            },
            'BSL-2（P2）': {
                'template_key': 'biosafety/bsl/p2',
                'template_name': '生物安全实验室-P2',
            },
            'BSL-3（P3）': {
                'template_key': 'biosafety/bsl/p3',
                'template_name': '生物安全实验室-P3',
            },
        },
    },
    'pharma.pass_box': {
        'default': {
            'default': {
                'template_key': 'pharma/pass_box/default',
                'template_name': '传递窗检测报告模板.docx',
            },
        },
    },
    'pharma.laminar_hood': {
        'default': {
            'default': {
                'template_key': 'pharma/laminar_hood/default',
                'template_name': '层流罩检测报告模板.docx',
            },
        },
    },
    'biosafety.bsc': {
        'default': {
            'default': {
                'template_key': 'biosafety/bsc/default',
                'template_name': '生物安全柜检测报告模板.docx',
            },
        },
    },
    'biosafety.clean_bench': {
        'default': {
            'default': {
                'template_key': 'biosafety/clean_bench/default',
                'template_name': '洁净工作台检测报告模板.docx',
            },
        },
    },
    'biosafety.ivc': {
        'default': {
            'default': {
                'template_key': 'biosafety/ivc/default',
                'template_name': 'IVC笼具检测报告模板.docx',
            },
        },
    },
    'pharma.gmp_workshop': {
        'grade-default': {
            'A级': {
                'template_key': 'pharma/gmp_workshop/a',
                'template_name': 'GMP车间-A级',
            },
            'B级': {
                'template_key': 'pharma/gmp_workshop/b/c',
                'template_name': 'GMP车间-B级',
            },
            'C级': {
                'template_key': 'pharma/gmp_workshop/b/c',
                'template_name': 'GMP车间-C级',
            },
            'D级': {
                'template_key': 'pharma/gmp_workshop/d',
                'template_name': 'GMP车间-D级',
            },
        },
    },
    'pharma.veterinary_gmp_workshop': {
        'grade-default': {
            'A级': {
                'template_key': 'pharma/veterinary_gmp_workshop/grade/a',
                'template_name': '兽药车间-A级',
            },
            'B级': {
                'template_key': 'pharma/veterinary_gmp_workshop/grade/b',
                'template_name': '兽药车间-B级',
            },
            'C级': {
                'template_key': 'pharma/veterinary_gmp_workshop/grade/c',
                'template_name': '兽药车间-C级',
            },
            'D级': {
                'template_key': 'pharma/veterinary_gmp_workshop/grade/d',
                'template_name': '兽药车间-D级',
            },
            '万级': {
                'template_key': 'pharma/veterinary_gmp_workshop/grade/d',
                'template_name': '兽药车间-D级',
            },
            '十万级': {
                'template_key': 'pharma/veterinary_gmp_workshop/grade/d',
                'template_name': '兽药车间-D级',
            },
        },
    },
    'food.food_workshop': {
        'grade-default': {
            'Ⅰ级（百级）': {
                'template_key': 'food/food_workshop/default/1',
                'template_name': '食品加工洁净车间百级',
            },
            'Ⅰ级': {
                'template_key': 'food/food_workshop/default/1',
                'template_name': '食品加工洁净车间百级',
            },
            'Ⅱ级（千级）': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
            'Ⅱ级（万级）': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
            'Ⅱ级': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
            'Ⅲ级（万级）': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
            'Ⅲ级（十万级）': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
            'Ⅲ级': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
            'Ⅳ级（三十万级）': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
            'Ⅳ级': {
                'template_key': 'food/food_workshop/default/234',
                'template_name': '食品加工洁净车间万级十万级三十万级',
            },
        },
    },
    'electronics.electronics_workshop': {
        'iso-default': {
            'ISO 5': {
                'template_key': 'electronics/electronics_workshop/iso/5',
                'template_name': '电子车间-ISO 5',
            },
            'ISO5级': {
                'template_key': 'electronics/electronics_workshop/iso/5',
                'template_name': '电子车间-ISO 5',
            },
            'ISO 6': {
                'template_key': 'electronics/electronics_workshop/iso/6',
                'template_name': '电子车间-ISO 6',
            },
            'ISO6级': {
                'template_key': 'electronics/electronics_workshop/iso/6',
                'template_name': '电子车间-ISO 6',
            },
            'ISO 7': {
                'template_key': 'electronics/electronics_workshop/iso/7',
                'template_name': '电子车间-ISO 7',
            },
            'ISO7级': {
                'template_key': 'electronics/electronics_workshop/iso/7',
                'template_name': '电子车间-ISO 7',
            },
            'ISO 8': {
                'template_key': 'electronics/electronics_workshop/iso/8',
                'template_name': '电子车间-ISO 8',
            },
            'ISO8级': {
                'template_key': 'electronics/electronics_workshop/iso/8',
                'template_name': '电子车间-ISO 8',
            },
            'ISO 9': {
                'template_key': 'electronics/electronics_workshop/iso/9',
                'template_name': '电子车间-ISO 9',
            },
            'ISO9级': {
                'template_key': 'electronics/electronics_workshop/iso/9',
                'template_name': '电子车间-ISO 9',
            },
        },
    },
    'hospital.negative_pressure': {
        'default': {
            'default': {
                'template_key': 'hospital/negative_pressure/default',
                'template_name': '负压病房',
            },
        },
    },
    'biosafety.animal_room': {
        'environment-default': {
            '普通环境': {
                'template_key': 'biosafety/animal_room/normal',
                'template_name': '动物房-普通环境',
            },
            '屏障环境': {
                'template_key': 'biosafety/animal_room/barrier-main',
                'template_name': '动物房-屏障环境主房间',
            },
            '隔离环境': {
                'template_key': 'biosafety/animal_room/isolation',
                'template_name': '动物房-隔离环境',
            },
        },
        'barrier-aux-room': {
            '洁物储存室': {
                'template_key': 'biosafety/animal_room/barrier-aux/洁物储存室',
                'template_name': '动物房-屏障环境洁净辅房-洁物储存室',
            },
            '灭菌后室/区': {
                'template_key': 'biosafety/animal_room/barrier-aux/灭菌后室区',
                'template_name': '动物房-屏障环境洁净辅房-灭菌后室区',
            },
            '洁净走廊': {
                'template_key': 'biosafety/animal_room/barrier-aux/洁净走廊',
                'template_name': '动物房-屏障环境洁净辅房-洁净走廊',
            },
            '污物走廊': {
                'template_key': 'biosafety/animal_room/barrier-aux/污物走廊',
                'template_name': '动物房-屏障环境洁净辅房-污物走廊',
            },
            '缓冲间': {
                'template_key': 'biosafety/animal_room/barrier-aux/缓冲间',
                'template_name': '动物房-屏障环境洁净辅房-缓冲间',
            },
            '二更': {
                'template_key': 'biosafety/animal_room/barrier-aux/二更',
                'template_name': '动物房-屏障环境洁净辅房-二更',
            },
            '清洗消毒室': {
                'template_key': 'biosafety/animal_room/barrier-aux/清洗消毒室',
                'template_name': '动物房-屏障环境洁净辅房-清洗消毒室',
            },
            '一更': {
                'template_key': 'biosafety/animal_room/barrier-aux/一更',
                'template_name': '动物房-屏障环境洁净辅房-一更',
            },
        },
    },
}


def resolve_template_rule(project: Dict[str, Any]) -> Dict[str, Any]:
    rooms = project.get('rooms') or []
    room = rooms[0] if rooms else {}
    context = room.get('context') or {}
    semantics = build_clean_class_semantics(project)

    domain = project.get('domain', '')
    type_id = room.get('type_id', '')
    level_name = room.get('level_name') or room.get('clean_class') or ''
    surgery_room_type = context.get('surgery_room_type', '')
    surgery_aux_clean_class = context.get('surgery_aux_clean_class', '')
    if type_id == 'operating_room' and domain == 'hospital':
        normalized = _normalize_operating_room_context(room)
        surgery_room_type = normalized.get('surgery_room_type', surgery_room_type)
        surgery_aux_clean_class = normalized.get('surgery_aux_clean_class', surgery_aux_clean_class)
    clean_function_subroom = context.get('clean_function_subroom', '')
    bsl_level = context.get('bsl_level') or context.get('bsl') or ''
    if not bsl_level and type_id == 'bsl':
        bsl_level = level_name
    negative_pressure_mode = context.get('negative_pressure_mode', '')
    animal_environment = context.get('animal_environment', '')
    barrier_room_class = context.get('barrier_room_class', '')
    barrier_aux_room = context.get('barrier_aux_room', '')

    rule = {
        'domain': domain,
        'type_id': type_id,
        'template_family': '',
        'template_variant': '',
        'template_key': '',
        'template_name': '',
        'report_context_mode': '',
        'level_name': level_name,
        'clean_class_semantics': semantics,
        'facts': {
            'surgery_room_type': surgery_room_type,
            'surgery_aux_clean_class': surgery_aux_clean_class,
            'clean_function_subroom': clean_function_subroom,
            'bsl_level': bsl_level,
            'negative_pressure_mode': negative_pressure_mode,
            'animal_environment': animal_environment,
            'barrier_room_class': barrier_room_class,
            'barrier_aux_room': barrier_aux_room,
        }
    }

    if type_id == 'operating_room' and domain == 'hospital':
        family = 'hospital.operating_room'
        rule['template_family'] = family
        if surgery_room_type in ('洁净辅房', '辅房'):
            variant = 'auxiliary-room'
            rule['template_variant'] = variant
            rule['report_context_mode'] = 'operating-room-aux'
            matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                       .get(surgery_aux_clean_class, {}))
            rule['template_key'] = matched.get('template_key', f"operating_room:aux:{surgery_aux_clean_class or 'unknown'}")
            rule['template_name'] = matched.get('template_name', '')
        elif surgery_room_type == '眼科手术室':
            variant = 'eye-room'
            rule['template_variant'] = variant
            rule['report_context_mode'] = 'operating-room-eye'
            # 眼科手术室直接映射到 hospital/operating_room/eye/levelN
            level_map = {'百级': 'level1', 'I级': 'level1', 'Ⅰ级': 'level1',
                         '千级': 'level2', 'II级': 'level2', 'Ⅱ级': 'level2',
                         '万级': 'level3', 'III级': 'level3', 'Ⅲ级': 'level3',
                         '十万级': 'level4', 'IV级': 'level4', 'Ⅳ级': 'level4'}
            level_suffix = level_map.get(level_name, 'level1')
            rule['template_key'] = f"hospital/operating_room/eye/{level_suffix}"
            rule['template_name'] = f'眼科手术室-{level_name}'
        else:
            variant = 'main-room'
            rule['template_variant'] = variant
            rule['report_context_mode'] = 'operating-room-main'
            main_level_key = next((k for k in TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {}) if k in level_name), '')
            matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                       .get(main_level_key, {}))
            rule['template_key'] = matched.get('template_key', f"operating_room:{level_name or 'unknown'}")
            rule['template_name'] = matched.get('template_name', '')

    elif type_id == 'clean_function_room' and domain == 'hospital':
        family = 'hospital.clean_function_room'
        variant = 'subroom-default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'clean-function-room'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(clean_function_subroom, {}))
        rule['template_key'] = matched.get('template_key', f"clean_function_room:{clean_function_subroom or 'unknown'}")
        rule['template_name'] = matched.get('template_name', '')

    elif type_id == 'bsl' and domain == 'biosafety':
        family = 'biosafety.bsl'
        variant = 'bsl-default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'biosafety-bsl'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(bsl_level, {}))
        rule['template_key'] = matched.get('template_key', f"bsl:{bsl_level or 'unknown'}")
        rule['template_name'] = matched.get('template_name', '')

    elif type_id == 'pass_box' and domain == 'pharma':
        family = 'pharma.pass_box'
        variant = 'default'
        mode_key = 'default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'pharma-pass-box-default'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(mode_key, {}))
        rule['template_key'] = matched.get('template_key', 'pharma/pass_box/default')
        rule['template_name'] = matched.get('template_name', '传递窗检测报告模板.docx')

    elif type_id == 'laminar_hood' and domain == 'pharma':
        family = 'pharma.laminar_hood'
        variant = 'default'
        mode_key = 'default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'pharma-laminar-hood-default'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(mode_key, {}))
        rule['template_key'] = matched.get('template_key', 'pharma/laminar_hood/default')
        rule['template_name'] = matched.get('template_name', '层流罩检测报告模板.docx')

    elif type_id == 'bsc' and domain == 'biosafety':
        family = 'biosafety.bsc'
        variant = 'default'
        mode_key = 'default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'biosafety-bsc-default'
        semantics['standard_code'] = 'YY 0569-2011'
        semantics['object_branch'] = 'bsc'
        semantics['level_semantic_key'] = 'biosafety.bsc.default'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(mode_key, {}))
        rule['template_key'] = matched.get('template_key', 'biosafety/bsc/default')
        rule['template_name'] = matched.get('template_name', '生物安全柜检测报告模板.docx')

    elif type_id == 'clean_bench' and domain == 'biosafety':
        family = 'biosafety.clean_bench'
        variant = 'default'
        mode_key = 'default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'biosafety-clean-bench-default'
        semantics['standard_code'] = 'GB/T 25915.4-2010'
        semantics['object_branch'] = 'clean_bench'
        semantics['level_semantic_key'] = 'biosafety.clean_bench.default'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(mode_key, {}))
        rule['template_key'] = matched.get('template_key', 'biosafety/clean_bench/default')
        rule['template_name'] = matched.get('template_name', '洁净工作台检测报告模板.docx')

    elif type_id == 'ivc' and domain == 'biosafety':
        family = 'biosafety.ivc'
        variant = 'default'
        mode_key = 'default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'biosafety-ivc-default'
        semantics['standard_code'] = 'GB 14925-2010'
        semantics['object_branch'] = 'ivc'
        semantics['level_semantic_key'] = 'biosafety.ivc.default'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(mode_key, {}))
        rule['template_key'] = matched.get('template_key', 'biosafety/ivc/default')
        rule['template_name'] = matched.get('template_name', 'IVC笼具检测报告模板.docx')

    elif domain == 'pharma' and type_id == 'gmp_workshop':
        gmp_grade = context.get('gmp_grade', '') or level_name
        semantics['standard_code'] = 'GB 50457-2019 + GMP 2010'
        semantics['object_branch'] = gmp_grade
        semantics['level_raw'] = gmp_grade
        semantics['level_semantic_key'] = f"pharma.gmp_workshop.grade.{gmp_grade or 'unknown'}"
        semantics['semantic_note'] = 'GMP车间等级表达属于制药工业洁净环境体系，应独立于医院等级和ISO等级理解。'
        semantics['impacts'] = ['template_rule', 'report_context', 'parameter_profile']
        family = 'pharma.gmp_workshop'
        variant = 'grade-default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'pharma-gmp-grade'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(gmp_grade, {}))
        rule['template_key'] = matched.get('template_key', f"pharma/gmp_workshop/{gmp_grade.lower() if gmp_grade else 'unknown'}")
        rule['template_name'] = matched.get('template_name', 'GMP车间检测报告模板.docx')
        rule['facts']['gmp_grade'] = gmp_grade

    elif type_id == 'veterinary_gmp_workshop' and domain == 'pharma':
        family = 'pharma.veterinary_gmp_workshop'
        variant = 'grade-default'
        gmp_grade = context.get('gmp_grade', '') or room.get('gmp_grade', '') or level_name
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'pharma-veterinary-gmp-grade'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(gmp_grade, {}))
        rule['template_key'] = matched.get('template_key', f"pharma/veterinary_gmp_workshop/grade/{gmp_grade.lower() if gmp_grade else 'unknown'}")
        rule['template_name'] = matched.get('template_name', '')
        rule['facts']['gmp_grade'] = gmp_grade

    elif type_id == 'food_workshop' and domain == 'food':
        family = 'food.food_workshop'
        variant = 'grade-default'
        food_grade = context.get('food_grade', '') or level_name
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'food-workshop-grade'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(food_grade, {}))
        rule['template_key'] = matched.get('template_key', f"food/food_workshop/default/{food_grade or 'unknown'}")
        rule['template_name'] = matched.get('template_name', '')
        rule['facts']['food_grade'] = food_grade

    elif type_id == 'electronics_workshop' and domain == 'electronics':
        family = 'electronics.electronics_workshop'
        variant = 'iso-default'
        iso_level = context.get('iso_level', '') or level_name or room.get('clean_class', '')
        # 标准化 ISO 等级格式：ISO-7 -> ISO 7
        iso_level_norm = iso_level.replace('-', ' ').strip() if iso_level else iso_level
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'electronics-workshop-iso'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(iso_level_norm, {}))
        rule['template_key'] = matched.get('template_key', f"electronics/electronics_workshop/iso/{iso_level_norm or 'unknown'}")
        rule['template_name'] = matched.get('template_name', '')
        rule['facts']['iso_level'] = iso_level_norm
        semantics['standard_code'] = 'GB 50472-2008 + GB 50073-2013'
        semantics['object_branch'] = iso_level
        semantics['level_raw'] = iso_level
        semantics['level_semantic_key'] = f"electronics.electronics_workshop.iso.{iso_level.replace(' ', '') if iso_level else 'unknown'}"
        semantics['semantic_note'] = '电子车间ISO等级属于电子工业洁净环境体系，ISO 5为单向流（wind_speed），ISO 6~9为乱流（airchange）。'
        semantics['impacts'] = ['template_rule', 'report_context', 'parameter_profile']

    elif type_id == 'negative_pressure' and domain == 'hospital':
        family = 'hospital.negative_pressure'
        variant = 'default'
        mode_key = 'default'
        rule['template_family'] = family
        rule['template_variant'] = variant
        rule['report_context_mode'] = 'negative-pressure-default'
        matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                   .get(mode_key, {}))
        rule['template_key'] = matched.get('template_key', 'hospital/negative_pressure/default')
        rule['template_name'] = matched.get('template_name', '负压病房')
        rule['facts']['negative_pressure_mode'] = negative_pressure_mode or 'ward-pressure-driven'

    elif type_id == 'animal_room' and domain == 'biosafety':
        family = 'biosafety.animal_room'
        animal_environment = animal_environment or level_name
        if animal_environment == '屏障环境':
            if barrier_room_class == '洁净辅房':
                variant = 'barrier-aux-room'
                aux_key = barrier_aux_room or 'default'
                rule['template_family'] = family
                rule['template_variant'] = variant
                rule['report_context_mode'] = 'animal-room-barrier-aux'
                matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                           .get(aux_key, {}))
                rule['template_key'] = matched.get('template_key', f"biosafety/animal_room/barrier-aux/{aux_key}")
                rule['template_name'] = matched.get('template_name', f"动物房-屏障环境洁净辅房-{aux_key}")
            else:
                variant = 'environment-default'
                env_key = '屏障环境'
                rule['template_family'] = family
                rule['template_variant'] = variant
                rule['report_context_mode'] = 'animal-room-barrier-main'
                matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                           .get(env_key, {}))
                rule['template_key'] = matched.get('template_key', 'biosafety/animal_room/barrier-main')
                rule['template_name'] = matched.get('template_name', '动物房-屏障环境主房间')
        else:
            variant = 'environment-default'
            env_key = animal_environment
            rule['template_family'] = family
            rule['template_variant'] = variant
            rule['report_context_mode'] = 'animal-room-environment'
            matched = (TEMPLATE_RULE_REGISTRY.get(family, {}).get(variant, {})
                       .get(env_key, {}))
            rule['template_key'] = matched.get('template_key', f"biosafety/animal_room/{env_key or 'unknown'}")
            rule['template_name'] = matched.get('template_name', '')
        rule['facts']['animal_environment'] = animal_environment
        rule['facts']['barrier_room_class'] = barrier_room_class
        rule['facts']['barrier_aux_room'] = barrier_aux_room

    return rule
