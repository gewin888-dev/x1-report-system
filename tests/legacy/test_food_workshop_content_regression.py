#!/usr/bin/env python3
"""Food Workshop content-level regression test.

Tests both Ⅰ级（百级）and Ⅱ级（万级）templates for complete 3-layer fill:
standard / value / conclusion for every row, plus instrument table protection.
"""
import sys, re, os
from zipfile import ZipFile
sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from adapters.template_fill import build_template_filled_docx

TPL_1 = '/Users/fuwuqi/公司资料/检测部/检测报告模板/食品加工/食品加工洁净车间百级检测报告模板.docx'
TPL_234 = '/Users/fuwuqi/公司资料/检测部/检测报告模板/食品加工/食品加工洁净车间万级十万级三十万级检测报告模板.docx'

text_pat = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
tbl_pat = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
row_pat = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
cell_pat = re.compile(r'<w:tc\b.*?</w:tc>', re.S)

def rows_from(path, ti):
    with ZipFile(path, 'r') as zf:
        xml = zf.read('word/document.xml').decode('utf-8', 'ignore')
    tables = list(tbl_pat.finditer(xml))
    if ti >= len(tables):
        return []
    return [
        [''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)]
        for row in row_pat.findall(tables[ti].group(0))
    ]

passed = 0
failed = 0

def check(name, condition, detail=''):
    global passed, failed
    if condition:
        print(f'PASS {name}')
        passed += 1
    else:
        print(f'FAIL {name} — {detail}')
        failed += 1

def make_payload(tpl, room_name, grade, params, basis, judgement):
    return {
        'project': {'project_name': '食品回归', 'client_name': '某食品厂', 'project_address': '呼和浩特',
                     'contact_info': '13900000000', 'detection_date': '2026-05-08',
                     'report_number': 'FOOD-REG', 'domain': 'food', 'domain_name': '食品加工', 'inspection_area': '车间'},
        'room': {'room_id': 'r1', 'room_name': room_name, 'type_id': 'food_workshop',
                 'type_name': '食品车间', 'level_name': grade, 'clean_class': grade,
                 'basis': basis, 'judgement': judgement, 'summary': {'result_state': 'pass'},
                 'length': '10', 'width': '5', 'height': '3', 'context': {}, 'params': params},
        'report_context': {'project_context': {'project_name': '食品回归', 'client_name': '某食品厂',
                 'project_address': '呼和浩特', 'contact_info': '13900000000',
                 'detection_date': '2026-05-08', 'inspection_area': '车间',
                 'weather_text': '温度：22℃ 湿度：50%RH', 'project_overview_text': 'reg'},
            'room_context': {'room_id': 'r1', 'room_name': room_name, 'type_id': 'food_workshop',
                 'type_name': '食品车间', 'level_name': grade, 'clean_class': grade,
                 'basis': basis, 'basis_text': '\n'.join(basis), 'judgement': judgement,
                 'judgement_text': '\n'.join(judgement), 'conclusion_text': '各项参数符合要求',
                 'summary': {'result_state': 'pass'}, 'business_context': {}}},
        'template_rule': {'template_key': 'food/food_workshop/default/1', 'domain': 'food', 'type_id': 'food_workshop'},
        'template_resource': {'template_path': tpl, 'resource_status': 'confirmed'},
        'export_type': 'food_workshop', 'source': 'regression',
    }

# ===== Test 1: Ⅰ级（百级）=====
print('--- Ⅰ级（百级）---')
params_1 = {
    'wind_speed': {'type': 'numeric', 'values': [0.25, 0.28, 0.26], 'result': '0.26  ✅'},
    'pressure': {'type': 'numeric', 'values': [15, 14, 16], 'result': '15.0  ✅'},
    'hepa_leak': {'type': 'hepa_leak_multi', 'objects': [{'name': '1#', 'value': '0.003'}], 'result': '-'},
    'particle': {'type': 'particle_4', 'data': {'p05_max': '1200', 'p05_ucl': '1500', 'p5_max': '5', 'p5_ucl': '8'}, 'result': '✅'},
    'temperature': {'type': 'numeric', 'values': [22, 23, 21], 'result': '22.0  ✅'},
    'humidity': {'type': 'numeric', 'values': [45, 50, 48], 'result': '47.7  ✅'},
    'illumination': {'type': 'numeric', 'values': [320, 310, 330], 'result': '320  ✅'},
    'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
    'settle_bacteria': {'type': 'bacteria_control', 'values': ['0', '0', '0'], 'blank': '0', 'neg': '0', 'result': '0  ✅'},
    'floating_bacteria': {'type': 'numeric', 'values': [1, 2, 1], 'result': '1.3  ✅'},
}
payload_1 = make_payload(TPL_1, 'Ⅰ级灌装间', 'Ⅰ级（百级）', params_1,
                         ['GB 50687-2011', 'GB/T 16294-2010', 'GB/T 16293-2010'], ['GB 50687-2011'])
out_1 = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/food_regression/food_1_reg.filled.docx'
os.makedirs(os.path.dirname(out_1), exist_ok=True)
build_template_filled_docx(payload_1, out_1)
r3 = rows_from(out_1, 3)

check('1_row0_date', '2026-05-08' in str(r3[0]))
check('1_row0_grade', 'Ⅰ级（百级）' in str(r3[0]))
check('1_row1_sv', '50' in str(r3[1]) and '150' in str(r3[1]))
check('1_wind_speed', '0.26' in str(r3[3]) and '合格' in str(r3[3]))
check('1_pressure', '15' in str(r3[4]) and '合格' in str(r3[4]))
check('1_particle_header', 'Ⅰ级（百级）' in str(r3[6]) and '合格' in str(r3[6]))
check('1_p05_max', '1200' in str(r3[7]))
check('1_p05_ucl', '1500' in str(r3[8]))
check('1_p5_max', '5' in str(r3[9]) and '≤29' in str(r3[9]))
check('1_p5_ucl', '8' in str(r3[10]))
check('1_temperature', '22' in str(r3[11]) and '合格' in str(r3[11]))
check('1_humidity', '47' in str(r3[12]) and '合格' in str(r3[12]))
check('1_illumination', '320' in str(r3[13]) and '合格' in str(r3[13]))
check('1_noise', '41.2' in str(r3[14]) and '合格' in str(r3[14]) and 'dB(A)' not in str(r3[14][3]))
check('1_settling', '0' in str(r3[15]) and '合格' in str(r3[15]))
check('1_floating', '1' in str(r3[16]) and '合格' in str(r3[16]))
check('1_instrument_identical', rows_from(out_1, 2) == rows_from(TPL_1, 2))

# ===== Test 2: Ⅱ级（万级）=====
print('--- Ⅱ级（万级）---')
params_2 = {
    'airchange': {'type': 'numeric', 'values': [25, 28, 26], 'result': '26.3  ✅'},
    'pressure': {'type': 'numeric', 'values': [12, 11, 13], 'result': '12.0  ✅'},
    'hepa_leak': {'type': 'hepa_leak_multi', 'objects': [{'name': '1#', 'value': '0.002'}], 'result': '-'},
    'particle': {'type': 'particle_4', 'data': {'p05_max': '120000', 'p05_ucl': '150000', 'p5_max': '800', 'p5_ucl': '1000'}, 'result': '✅'},
    'temperature': {'type': 'numeric', 'values': [22, 23, 21], 'result': '22.0  ✅'},
    'humidity': {'type': 'numeric', 'values': [45, 50, 48], 'result': '47.7  ✅'},
    'illumination': {'type': 'numeric', 'values': [320, 310, 330], 'result': '320  ✅'},
    'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
    'settle_bacteria': {'type': 'bacteria_control', 'values': ['1', '2', '1'], 'blank': '0', 'neg': '0', 'result': '1.33  ✅'},
    'floating_bacteria': {'type': 'numeric', 'values': [30, 25, 35], 'result': '30.0  ✅'},
}
payload_2 = make_payload(TPL_234, 'Ⅱ级包装间', 'Ⅱ级（万级）', params_2,
                         ['GB 50687-2011', 'GB/T 16294-2010', 'GB/T 16293-2010'], ['GB 50687-2011'])
out_2 = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/food_regression/food_2_reg.filled.docx'
build_template_filled_docx(payload_2, out_2)
r3_2 = rows_from(out_2, 3)

check('2_row0_date', '2026-05-08' in str(r3_2[0]))
check('2_row0_grade', 'Ⅱ级（万级）' in str(r3_2[0]))
check('2_row1_sv', '50' in str(r3_2[1]) and '150' in str(r3_2[1]))
check('2_airchange_std', '≥20' in str(r3_2[3]))
check('2_airchange_val', '26' in str(r3_2[3]) and '合格' in str(r3_2[3]))
check('2_pressure_std', '≥5' in str(r3_2[4]))
check('2_pressure_val', '12' in str(r3_2[4]) and '合格' in str(r3_2[4]))
check('2_particle_header', 'Ⅱ级（万级）' in str(r3_2[6]) and '合格' in str(r3_2[6]))
check('2_p05_limit', '352000' in str(r3_2[7]))
check('2_p05_max', '120000' in str(r3_2[7]))
check('2_p05_ucl', '150000' in str(r3_2[8]))
check('2_p5_limit', '2930' in str(r3_2[9]))
check('2_p5_max', '800' in str(r3_2[9]))
check('2_p5_ucl', '1000' in str(r3_2[10]))
check('2_temp_std', '20～25' in str(r3_2[11]))
check('2_temp_val', '22' in str(r3_2[11]) and '合格' in str(r3_2[11]))
check('2_hum_std', '30～65' in str(r3_2[12]))
check('2_hum_val', '47' in str(r3_2[12]) and '合格' in str(r3_2[12]))
check('2_illu_std', '≥200' in str(r3_2[13]))
check('2_illu_val', '320' in str(r3_2[13]) and '合格' in str(r3_2[13]))
check('2_noise_std', '≤60' in str(r3_2[14]))
check('2_noise_val', '41.2' in str(r3_2[14]) and '合格' in str(r3_2[14]))
check('2_settle_std', '≤1.5' in str(r3_2[15]))
check('2_settle_val', '1.33' in str(r3_2[15]) and '合格' in str(r3_2[15]))
check('2_float_std', '≤50' in str(r3_2[16]))
check('2_float_val', '30' in str(r3_2[16]) and '合格' in str(r3_2[16]))
check('2_instrument_identical', rows_from(out_2, 2) == rows_from(TPL_234, 2))
check('2_no_emoji', all('✅' not in str(r3_2[i][3]) and '❌' not in str(r3_2[i][3])
                        for i in [3, 4, 11, 12, 13, 14, 15, 16] if len(r3_2[i]) > 3))

print(f'\nSUMMARY {passed}/{passed + failed}')
