#!/usr/bin/env python3
"""GMP Workshop A级 content-level regression test.

Verifies that build_template_filled_docx for gmp_workshop (A级) correctly fills:
- TABLE 3 ROW 0: date + grade
- TABLE 3 ROW 1: S/V
- TABLE 3 ROW 3-5: wind_speed, pressure, hepa_leak (standard + value + conclusion)
- TABLE 3 ROW 6-10: particle block (grade + limits + values)
- TABLE 3 ROW 11-16: temperature, humidity, illumination, noise, settling, floating
- TABLE 1 (info table): all 10 rows
- TABLE 2 (instrument table): IDENTICAL to template
"""
import sys, re, os
from zipfile import ZipFile
sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from adapters.template_fill import build_template_filled_docx

TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/制药工业/制药工业GMP车间A级检测报告模板.docx'
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


payload = {
    'project': {
        'project_name': 'GMP回归', 'client_name': '某药厂', 'project_address': '呼和浩特',
        'contact_info': '13800000000', 'detection_date': '2026-05-08',
        'report_number': 'GMP-REG-001', 'domain': 'pharma', 'domain_name': '制药工业',
        'inspection_area': 'A车间',
    },
    'room': {
        'room_id': 'r1', 'room_name': 'A级灌装间', 'type_id': 'gmp_workshop',
        'type_name': 'GMP车间', 'level_name': 'A级', 'clean_class': 'A级',
        'basis': ['GB 50457-2019', 'GB/T 16294-2010'], 'judgement': ['GB 50457-2019'],
        'summary': {'result_state': 'pass'},
        'length': '8', 'width': '6', 'height': '3', 'context': {},
        'params': {
            'wind_speed': {'type': 'numeric', 'values': [0.4, 0.42, 0.41], 'result': '0.41  ✅'},
            'pressure': {'type': 'numeric', 'values': [12, 11, 13], 'result': '12.0  ✅'},
            'hepa_leak': {'type': 'hepa_leak_multi', 'objects': [{'name': '1#', 'value': '0.005'}], 'result': '-'},
            'particle': {'type': 'particle_4', 'data': {'p05_max': '2800', 'p05_ucl': '3000', 'p5_max': '10', 'p5_ucl': '12'}, 'result': '✅'},
            'temperature': {'type': 'numeric', 'values': [22, 23, 21], 'result': '22.0  ✅'},
            'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
            'illumination': {'type': 'numeric', 'values': [350, 340, 360], 'result': '350  ✅'},
            'noise': {'type': 'noise_corrected', 'background': '38', 'indoor': '45', 'result': '44.3 dB(A)  ✅'},
            'settle_bacteria': {'type': 'bacteria_control', 'values': ['0', '1', '0'], 'blank': '0', 'neg': '0', 'result': '0.33  ✅'},
            'floating_bacteria': {'type': 'numeric', 'values': [2, 3, 4], 'result': '3.0  ✅'},
        },
    },
    'report_context': {
        'project_context': {
            'project_name': 'GMP回归', 'client_name': '某药厂', 'project_address': '呼和浩特',
            'contact_info': '13800000000', 'detection_date': '2026-05-08',
            'inspection_area': 'A车间',
            'weather_text': '温度：22.0℃  湿度：50.0%RH  大气压力：890.0hPa',
            'project_overview_text': 'regression',
        },
        'room_context': {
            'room_id': 'r1', 'room_name': 'A级灌装间', 'type_id': 'gmp_workshop',
            'type_name': 'GMP车间', 'level_name': 'A级', 'clean_class': 'A级',
            'basis': ['GB 50457-2019', 'GB/T 16294-2010'],
            'basis_text': 'GB 50457-2019\nGB/T 16294-2010',
            'judgement': ['GB 50457-2019'], 'judgement_text': 'GB 50457-2019',
            'conclusion_text': '各项参数符合要求',
            'summary': {'result_state': 'pass'}, 'business_context': {},
        },
    },
    'template_rule': {'template_key': 'pharma/gmp_workshop/grade/a', 'domain': 'pharma', 'type_id': 'gmp_workshop'},
    'template_resource': {'template_path': TPL, 'resource_status': 'confirmed'},
    'export_type': 'gmp_workshop', 'source': 'regression',
}

out = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/gmp_regression/gmp_a_regression.filled.docx'
os.makedirs(os.path.dirname(out), exist_ok=True)
build_template_filled_docx(payload, out)

r3 = rows_from(out, 3)
r1 = rows_from(out, 1)

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


# --- TABLE 3 (Conclusion table) ---

# ROW 0: header — date + grade
check('row0_date', '2026-05-08' in str(r3[0]), f'got {r3[0]}')
check('row0_grade', 'A级' in str(r3[0]), f'got {r3[0]}')

# ROW 1: S/V
check('row1_sv', '48' in str(r3[1]) and '144' in str(r3[1]), f'got {r3[1]}')

# ROW 3: 截面风速
check('wind_speed_std', '0.36～0.54' in str(r3[3]), f'got {r3[3]}')
check('wind_speed_val', '0.41' in str(r3[3]), f'got {r3[3]}')
check('wind_speed_concl', '合格' in str(r3[3]), f'got {r3[3]}')

# ROW 4: 静压差
check('pressure_std', '≥10' in str(r3[4]), f'got {r3[4]}')
check('pressure_val', '12' in str(r3[4]) and '✅' not in str(r3[4]), f'got {r3[4]}')
check('pressure_concl', '合格' in str(r3[4]), f'got {r3[4]}')

# ROW 5: 检漏
check('hepa_val', '0.005' in str(r3[5]), f'got {r3[5]}')
check('hepa_concl', '合格' in str(r3[5]), f'got {r3[5]}')

# ROW 6: 洁净度级别 header
check('particle_header_grade', r3[6][3] == 'A级' or 'A级' in str(r3[6]), f'got {r3[6]}')
check('particle_header_concl', '合格' in str(r3[6]), f'got {r3[6]}')

# ROW 7: 0.5μm max
check('particle_05_max', '2800' in str(r3[7]), f'got {r3[7]}')
# ROW 8: 0.5μm UCL
check('particle_05_ucl', '3000' in str(r3[8]), f'got {r3[8]}')
# ROW 9: 5μm max
check('particle_5_max', '10' in str(r3[9]), f'got {r3[9]}')
# ROW 10: 5μm UCL
check('particle_5_ucl', '12' in str(r3[10]), f'got {r3[10]}')

# ROW 11-16: simple params
check('temperature', '22' in str(r3[11]) and '合格' in str(r3[11]), f'got {r3[11]}')
check('humidity', '50' in str(r3[12]) and '合格' in str(r3[12]), f'got {r3[12]}')
check('illumination', '350' in str(r3[13]) and '合格' in str(r3[13]), f'got {r3[13]}')
check('noise', '44.3' in str(r3[14]) and '合格' in str(r3[14]) and 'dB(A)' not in str(r3[14][3]), f'got {r3[14]}')
check('settling', '0.33' in str(r3[15]) and '合格' in str(r3[15]) and '✅' not in str(r3[15][3]), f'got {r3[15]}')
check('floating', '3' in str(r3[16]) and '合格' in str(r3[16]) and '✅' not in str(r3[16][3]), f'got {r3[16]}')

# --- TABLE 1 (Info table) ---
check('info_client', r1[0][1] == '某药厂', f'got {r1[0]}')
check('info_address', r1[1][1] == '呼和浩特', f'got {r1[1]}')
check('info_contact', '13800000000' in str(r1[1]), f'got {r1[1]}')
check('info_project', r1[2][1] == 'GMP回归', f'got {r1[2]}')
check('info_weather_no_dup', str(r1[6]).count('温度') == 1, f'got {r1[6]}')
check('info_basis', 'GB 50457-2019' in str(r1[7]), f'got {r1[7]}')
check('info_judgement', 'GB 50457-2019' in str(r1[8]), f'got {r1[8]}')
check('info_conclusion', '各项参数符合要求' in str(r1[9]), f'got {r1[9]}')

# --- TABLE 2 (Instrument table) — must be IDENTICAL to template ---
check('instrument_table_identical', rows_from(out, 2) == rows_from(TPL, 2),
      'instrument table differs from template')

# --- No emoji in values ---
for i in [3, 4, 5, 11, 12, 13, 14, 15, 16]:
    val_cell = r3[i][3] if len(r3[i]) > 3 else ''
    if '✅' in val_cell or '❌' in val_cell:
        check(f'no_emoji_row{i}', False, f'value has emoji: {val_cell}')
        break
else:
    check('no_emoji_in_values', True)

print(f'\nSUMMARY {passed}/{passed + failed}')
