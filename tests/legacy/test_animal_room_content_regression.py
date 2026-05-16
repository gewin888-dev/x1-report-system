#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""animal_room 内容级回归（第一阶段）：普通环境 + 屏障环境主房间。"""

import os
import re
import sys
from zipfile import ZipFile

sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from adapters.template_fill import build_template_filled_docx

TEXT_PAT = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
TBL_PAT = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
ROW_PAT = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
CELL_PAT = re.compile(r'<w:tc\b.*?</w:tc>', re.S)
OUT_DIR = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/animal_content_regression_20260508'
NORMAL_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/生物安全/生物安全动物房普通环境检测报告模板.docx'
BARRIER_MAIN_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/生物安全/生物安全动物房屏障环境主房间检测报告模板.docx'
ISOLATION_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/生物安全/生物安全动物房隔离环境检测报告模板.docx'


def rows_from(path, ti):
    with ZipFile(path, 'r') as zf:
        xml = zf.read('word/document.xml').decode('utf-8', 'ignore')
    rows = ROW_PAT.findall(list(TBL_PAT.finditer(xml))[ti].group(0))
    return [[''.join(TEXT_PAT.findall(c)).strip() for c in CELL_PAT.findall(row)] for row in rows]


def check(cond, label, fails):
    if cond:
        print(f'✅ {label}')
        return 1
    print(f'❌ {label}')
    fails.append(label)
    return 0


def mk_payload(name, tpl, level, context, params, template_key):
    return {
        'project': {'project_name': '动物房回归探针', 'client_name': '某动物中心', 'project_address': '呼和浩特', 'contact_info': '13800000005', 'detection_date': '2026-05-08', 'report_number': 'AR-REG', 'domain': 'biosafety', 'domain_name': '生物安全', 'inspection_area': '动物房区'},
        'room': {'room_id': 'r1', 'room_name': name, 'type_id': 'animal_room', 'type_name': '动物房', 'level_name': level, 'clean_class': level, 'basis': ['GB 14925-2023'], 'judgement': ['GB 14925-2023'], 'summary': {'result_state': 'pass'}, 'length': '8', 'width': '6', 'height': '3', 'context': context, 'params': params},
        'report_context': {'project_context': {'project_name': '动物房回归探针', 'client_name': '某动物中心', 'project_address': '呼和浩特', 'contact_info': '13800000005', 'detection_date': '2026-05-08', 'inspection_area': '动物房区', 'weather_text': '温度：22℃ 湿度：50%', 'project_overview_text': 'probe'}, 'room_context': {'room_id': 'r1', 'room_name': name, 'type_id': 'animal_room', 'type_name': '动物房', 'level_name': level, 'clean_class': level, 'basis': ['GB 14925-2023'], 'basis_text': 'GB 14925-2023', 'judgement': ['GB 14925-2023'], 'judgement_text': 'GB 14925-2023', 'conclusion_text': '各项参数符合要求', 'summary': {'result_state': 'pass'}, 'business_context': {}}},
        'template_rule': {'template_key': template_key, 'domain': 'biosafety', 'type_id': 'animal_room'},
        'template_resource': {'template_path': tpl, 'resource_status': 'confirmed'},
        'export_type': 'animal_room', 'source': 'probe'
    }


def run_case(case_name, payload, tpl, expectations):
    out = os.path.join(OUT_DIR, f'{case_name}.filled.docx')
    os.makedirs(OUT_DIR, exist_ok=True)
    build_template_filled_docx(payload, out)
    rows = rows_from(out, 3)
    tpl_inst = rows_from(tpl, 2)
    out_inst = rows_from(out, 2)
    fails = []
    passed = 0
    passed += check(out_inst == tpl_inst, f'{case_name} 仪器表 IDENTICAL', fails)
    for label, ri, ci, expected in expectations:
        actual = rows[ri][ci] if ri < len(rows) and ci < len(rows[ri]) else ''
        passed += check(actual == expected, f'{case_name} {label}: {actual!r} == {expected!r}', fails)
    return passed, len(expectations) + 1, fails


def main():
    total = passed = 0
    fails = []

    normal_params = {
        'airchange': {'type': 'numeric', 'values': [10, 11, 9], 'result': '10.0  ✅'},
        'cage_airspeed': {'type': 'numeric', 'values': [0.15], 'result': '0.15  ✅'},
        'temperature': {'type': 'numeric', 'values': [23, 24, 22], 'result': '23.0  ✅'},
        'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
        'temp_diff': {'type': 'numeric', 'values': [2], 'result': '2.0  ✅'},
        'work_illumination': {'type': 'numeric', 'values': [180], 'result': '180  ✅'},
        'animal_illumination': {'type': 'numeric', 'values': [80], 'result': '80  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
    }
    p, t, f = run_case('animal_normal', mk_payload('普通环境饲养室', NORMAL_TPL, '普通环境', {'animal_environment': '普通环境'}, normal_params, 'biosafety/animal_room/normal'), NORMAL_TPL, [
        ('row0级别', 0, 5, '普通环境'), ('row1_sv', 1, 1, '面积S（m2）=48                体积V（m3）=144'),
        ('row3标准', 3, 2, '≥8'), ('row3值', 3, 3, '10'), ('row4值', 4, 3, '0.15'),
        ('row5标准', 5, 2, '20～26'), ('row6标准', 6, 2, '30～70'), ('row7标准', 7, 2, '≤4'),
        ('row8工作照度标准', 8, 3, '≥150'), ('row8工作照度值', 8, 4, '180'), ('row9动物照度值', 9, 4, '80'),
        ('row10噪声值', 10, 3, '41.2'), ('row10噪声结论', 10, 4, '合格'),
    ])
    passed += p; total += t; fails.extend(f)

    barrier_params = {
        'airchange': {'type': 'numeric', 'values': [18, 17, 19], 'result': '18.0  ✅'},
        'cage_airspeed': {'type': 'numeric', 'values': [0.15], 'result': '0.15  ✅'},
        'pressure': {'type': 'numeric', 'values': [12, 11, 13], 'result': '12.0  ✅'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '300000', 'p05_ucl': '320000', 'p5_max': '2000', 'p5_ucl': '2400'}, 'result': '✅'},
        'temperature': {'type': 'numeric', 'values': [23, 24, 22], 'result': '23.0  ✅'},
        'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
        'temp_diff': {'type': 'numeric', 'values': [2], 'result': '2.0  ✅'},
        'work_illumination': {'type': 'numeric', 'values': [180], 'result': '180  ✅'},
        'animal_illumination': {'type': 'numeric', 'values': [80], 'result': '80  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
        'settling': {'type': 'bacteria_control', 'values': ['1', '2', '1'], 'blank': '0', 'neg': '0', 'result': '1.33  ✅'},
    }
    p, t, f = run_case('animal_barrier_main', mk_payload('大鼠饲养室', BARRIER_MAIN_TPL, '屏障环境', {'animal_environment': '屏障环境', 'barrier_room_class': '主房间'}, barrier_params, 'biosafety/animal_room/barrier-main'), BARRIER_MAIN_TPL, [
        ('row0级别', 0, 5, '屏障环境'), ('row3标准', 3, 2, '≥15'), ('row3值', 3, 3, '18'),
        ('row5标准', 5, 2, '≥10'), ('row6洁净度等级', 6, 3, 'ISO-7'), ('row6结论', 6, 6, '合格'),
        ('row7_05标准', 7, 2, '35200＜0.5μm≤352000'), ('row7_05值', 7, 5, '300000'), ('row8_05ucl', 8, 5, '320000'),
        ('row9_5标准', 9, 2, '293＜5μm≤2930'), ('row9_5值', 9, 5, '2000'), ('row10_5ucl', 10, 5, '2400'),
        ('row14工作照度标准', 14, 3, '≥150'), ('row15动物照度标准', 15, 3, '100～200'), ('row17沉降菌值', 17, 3, '1.33'),
    ])
    passed += p; total += t; fails.extend(f)

    isolation_params = {
        'airchange': {'type': 'numeric', 'values': [22, 21, 23], 'result': '22.0  ✅'},
        'cage_airspeed': {'type': 'numeric', 'values': [0.15], 'result': '0.15  ✅'},
        'pressure': {'type': 'numeric', 'values': [55, 56, 54], 'result': '55.0  ✅'},
        'particle_negative': {'type': 'particle_4', 'data': {'p05_max': '300000', 'p05_ucl': '320000', 'p5_max': '2000', 'p5_ucl': '2400'}, 'result': '✅'},
        'temperature': {'type': 'numeric', 'values': [23, 24, 22], 'result': '23.0  ✅'},
        'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
        'temp_diff': {'type': 'numeric', 'values': [2], 'result': '2.0  ✅'},
        'work_illumination': {'type': 'numeric', 'values': [180], 'result': '180  ✅'},
        'animal_illumination': {'type': 'numeric', 'values': [80], 'result': '80  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
        'settling': {'type': 'bacteria_control', 'values': ['0', '0', '0'], 'blank': '0', 'neg': '0', 'result': '0  ✅'},
    }
    p, t, f = run_case('animal_isolation', mk_payload('隔离检疫室', ISOLATION_TPL, '隔离环境', {'animal_environment': '隔离环境'}, isolation_params, 'biosafety/animal_room/isolation'), ISOLATION_TPL, [
        ('row0级别', 0, 5, '隔离环境'), ('row3标准', 3, 2, '≥20'), ('row3值', 3, 3, '22'),
        ('row5标准', 5, 2, '≥50'), ('row6洁净度等级', 6, 3, 'ISO-7'),
        ('row7_05标准', 7, 2, '35200＜0.5μm≤352000'), ('row7_05值', 7, 5, '300000'), ('row8_05ucl', 8, 5, '320000'),
        ('row9_5值', 9, 5, '2000'), ('row10_5ucl', 10, 5, '2400'),
        ('row14工作照度标准', 14, 3, '≥150'), ('row15动物照度标准', 15, 3, '100～200'), ('row17沉降菌值', 17, 3, '0'),
    ])
    passed += p; total += t; fails.extend(f)

    aux_particle_params = {
        'airchange': {'type': 'numeric', 'values': [18, 17, 19], 'result': '18.0  ✅'},
        'pressure': {'type': 'numeric', 'values': [12, 11, 13], 'result': '12.0  ✅'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '300000', 'p05_ucl': '320000', 'p5_max': '2000', 'p5_ucl': '2400'}, 'result': '✅'},
        'temperature': {'type': 'numeric', 'values': [23, 24, 22], 'result': '23.0  ✅'},
        'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
        'work_illumination': {'type': 'numeric', 'values': [180], 'result': '180  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
    }
    aux_simple_params = {
        'airchange': {'type': 'numeric', 'values': [18, 17, 19], 'result': '18.0  ✅'},
        'pressure': {'type': 'numeric', 'values': [12, 11, 13], 'result': '12.0  ✅'},
        'temperature': {'type': 'numeric', 'values': [23, 24, 22], 'result': '23.0  ✅'},
        'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
        'work_illumination': {'type': 'numeric', 'values': [180], 'result': '180  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
    }
    aux_tpl = '/Users/fuwuqi/公司资料/检测部/检测报告模板/生物安全/生物安全动物房屏障环境洁净辅房检测报告模板.docx'

    p, t, f = run_case('animal_barrier_aux_clean_corridor', mk_payload('洁净走廊', aux_tpl, '屏障环境', {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '洁净走廊'}, aux_particle_params, 'biosafety/animal_room/barrier-aux/洁净走廊'), aux_tpl, [
        ('row3标准', 3, 2, '≥15'), ('row4标准', 4, 2, '≥10'), ('row5洁净度等级', 5, 3, 'ISO-7'),
        ('row6_05标准', 6, 2, '35200＜0.5μm≤352000'), ('row6_05值', 6, 5, '300000'), ('row7_05ucl', 7, 5, '320000'),
        ('row8_5标准', 8, 2, '293＜5μm≤2930'), ('row8_5值', 8, 5, '2000'), ('row9_5ucl', 9, 5, '2400'),
        ('row10温度标准', 10, 2, '18～28'), ('row11湿度标准', 11, 2, '≤70'), ('row12照度标准', 12, 2, '≥150'), ('row13噪声标准', 13, 2, '≤60'),
    ])
    passed += p; total += t; fails.extend(f)

    p, t, f = run_case('animal_barrier_aux_dirty_corridor', mk_payload('污物走廊', aux_tpl, '屏障环境', {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '污物走廊'}, aux_simple_params, 'biosafety/animal_room/barrier-aux/污物走廊'), aux_tpl, [
        ('row3标准', 3, 2, '≥10'), ('row4标准', 4, 2, '≥5'), ('row10温度标准', 10, 2, '18～28'), ('row11湿度标准', 11, 2, '—'), ('row12照度标准', 12, 2, '≥150'), ('row13噪声标准', 13, 2, '≤60'),
    ])
    passed += p; total += t; fails.extend(f)

    p, t, f = run_case('animal_barrier_aux_wash', mk_payload('清洗消毒室', aux_tpl, '屏障环境', {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '清洗消毒室'}, aux_simple_params, 'biosafety/animal_room/barrier-aux/清洗消毒室'), aux_tpl, [
        ('row3标准', 3, 2, '≥4'), ('row10温度标准', 10, 2, '18～28'), ('row11湿度标准', 11, 2, '—'), ('row12照度标准', 12, 2, '≥150'), ('row13噪声标准', 13, 2, '≤60'),
    ])
    passed += p; total += t; fails.extend(f)

    p, t, f = run_case('animal_barrier_aux_first_change', mk_payload('一更', aux_tpl, '屏障环境', {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '一更'}, aux_simple_params, 'biosafety/animal_room/barrier-aux/一更'), aux_tpl, [
        ('row10温度标准', 10, 2, '18～28'), ('row11湿度标准', 11, 2, '—'), ('row12照度标准', 12, 2, '≥100'), ('row13噪声标准', 13, 2, '≤60'),
    ])
    passed += p; total += t; fails.extend(f)

    print(f'\nSUMMARY {passed}/{total}')
    if fails:
        print('FAILURES:')
        for x in fails:
            print('-', x)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
