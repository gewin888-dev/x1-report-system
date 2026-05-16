#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""electronics_workshop 内容级回归：验证 ISO5 / ISO6 模板三层填充 + 仪器表零污染。"""

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

ISO5_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/精密制造/精密制造电子洁净车间ISO5检测报告模板.docx'
ISO6789_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/精密制造/精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx'
OUT_DIR = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/electronics_content_regression_20260508'


def rows_from(path, table_index):
    with ZipFile(path, 'r') as zf:
        xml = zf.read('word/document.xml').decode('utf-8', 'ignore')
    tables = list(TBL_PAT.finditer(xml))
    rows = ROW_PAT.findall(tables[table_index].group(0))
    return [[''.join(TEXT_PAT.findall(c)).strip() for c in CELL_PAT.findall(row)] for row in rows]


def mk_payload(level, tpl, params):
    return {
        'project': {
            'project_name': '电子回归探针', 'client_name': '某电子厂', 'project_address': '呼和浩特',
            'contact_info': '13800000004', 'detection_date': '2026-05-08', 'report_number': f'ELEC-{level}-REG',
            'domain': 'electronics', 'domain_name': '精密制造', 'inspection_area': '电子车间'
        },
        'room': {
            'room_id': 'r1', 'room_name': f'{level}测试间', 'type_id': 'electronics_workshop', 'type_name': '电子洁净车间',
            'level_name': level, 'clean_class': level, 'basis': ['GB 50472-2008', 'GB 50073-2013'],
            'judgement': ['GB 50472-2008'], 'summary': {'result_state': 'pass'},
            'length': '8', 'width': '6', 'height': '3', 'context': {'iso_level': level}, 'params': params,
        },
        'report_context': {
            'project_context': {
                'project_name': '电子回归探针', 'client_name': '某电子厂', 'project_address': '呼和浩特',
                'contact_info': '13800000004', 'detection_date': '2026-05-08', 'inspection_area': '电子车间',
                'weather_text': '温度：22℃ 湿度：50%', 'project_overview_text': 'probe'
            },
            'room_context': {
                'room_id': 'r1', 'room_name': f'{level}测试间', 'type_id': 'electronics_workshop', 'type_name': '电子洁净车间',
                'level_name': level, 'clean_class': level, 'basis': ['GB 50472-2008', 'GB 50073-2013'],
                'basis_text': 'GB 50472-2008\nGB 50073-2013', 'judgement': ['GB 50472-2008'],
                'judgement_text': 'GB 50472-2008', 'conclusion_text': '各项参数符合要求',
                'summary': {'result_state': 'pass'}, 'business_context': {}
            }
        },
        'template_rule': {'template_key': f'electronics/electronics_workshop/default/{5 if level == "ISO 5" else "6789"}', 'domain': 'electronics', 'type_id': 'electronics_workshop'},
        'template_resource': {'template_path': tpl, 'resource_status': 'confirmed'},
        'export_type': 'electronics_workshop', 'source': 'probe'
    }


def check(condition, label, failures):
    if condition:
        print(f'✅ {label}')
        return 1
    print(f'❌ {label}')
    failures.append(label)
    return 0


def run_case(level, tpl, params, expectations):
    payload = mk_payload(level, tpl, params)
    out = os.path.join(OUT_DIR, f'{level.replace(" ", "_")}.filled.docx')
    os.makedirs(OUT_DIR, exist_ok=True)
    build_template_filled_docx(payload, out)
    result_rows = rows_from(out, 3)
    tpl_inst = rows_from(tpl, 2)
    out_inst = rows_from(out, 2)
    failures = []
    score = 0

    score += check(out_inst == tpl_inst, f'{level} 仪器表 IDENTICAL', failures)
    for label, row_idx, cell_idx, expected in expectations:
        actual = result_rows[row_idx][cell_idx] if row_idx < len(result_rows) and cell_idx < len(result_rows[row_idx]) else ''
        score += check(actual == expected, f'{level} {label}: {actual!r} == {expected!r}', failures)

    return score, len(expectations) + 1, failures


def main():
    total = passed = 0
    all_failures = []

    iso5_params = {
        'wind_speed': {'type': 'numeric', 'values': [0.36, 0.38, 0.37], 'result': '0.37  ✅'},
        'pressure': {'type': 'numeric', 'values': [12, 11, 13], 'result': '12.0  ✅'},
        'hepa_leak': {'type': 'hepa_leak_multi', 'objects': [{'name': '1#', 'value': '0.005'}], 'result': '-'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '3000', 'p05_ucl': '3200', 'p5_max': '20', 'p5_ucl': '24'}, 'result': '✅'},
        'temperature': {'type': 'numeric', 'values': [22, 23, 21], 'result': '22.0  ✅'},
        'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
        'illumination': {'type': 'numeric', 'values': [350, 340, 360], 'result': '350  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
    }
    iso5_expect = [
        ('ROW0级别', 0, 5, 'ISO 5'), ('ROW1_SV', 1, 1, '面积S（m2）=48              体积V（m3）=144'),
        ('ROW3标准', 3, 2, '0.20～0.45'), ('ROW3值', 3, 3, '0.37'), ('ROW3结论', 3, 4, '合格'),
        ('ROW4标准', 4, 2, '≥5'), ('ROW5检漏值', 5, 3, '0.005'), ('ROW6洁净度结论', 6, 6, '合格'),
        ('ROW7_05标准', 7, 2, '≥0.5㎛：≤3520'), ('ROW7_05值', 7, 5, '3000'), ('ROW8_05ucl', 8, 5, '3200'),
        ('ROW9_5标准', 9, 2, '≥5㎛：≤29'), ('ROW9_5值', 9, 5, '20'), ('ROW10_5ucl', 10, 5, '24'),
        ('ROW11温度', 11, 2, '22～24'), ('ROW12湿度', 12, 2, '45～65'), ('ROW13照度', 13, 2, '300～500'),
        ('ROW14噪声值', 14, 3, '41.2'), ('ROW14噪声结论', 14, 4, '合格'),
    ]
    p, t, f = run_case('ISO 5', ISO5_TPL, iso5_params, iso5_expect)
    passed += p; total += t; all_failures.extend(f)

    iso6_params = {
        'airchange_rate': {'type': 'numeric', 'values': [55, 56, 54], 'result': '55.0  ✅'},
        'pressure': {'type': 'numeric', 'values': [12, 11, 13], 'result': '12.0  ✅'},
        'hepa_leak': {'type': 'hepa_leak_multi', 'objects': [{'name': '1#', 'value': '0.005'}], 'result': '-'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '30000', 'p05_ucl': '32000', 'p5_max': '200', 'p5_ucl': '240'}, 'result': '✅'},
        'temperature': {'type': 'numeric', 'values': [22, 23, 21], 'result': '22.0  ✅'},
        'humidity': {'type': 'numeric', 'values': [50, 52, 48], 'result': '50.0  ✅'},
        'illumination': {'type': 'numeric', 'values': [350, 340, 360], 'result': '350  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
    }
    iso6_expect = [
        ('ROW0级别', 0, 5, 'ISO 6'), ('ROW1_SV', 1, 1, '面积S（m2）=48              体积V（m3）=144'),
        ('ROW3标准', 3, 2, '50～60'), ('ROW3值', 3, 3, '55'), ('ROW3结论', 3, 4, '合格'),
        ('ROW4标准', 4, 2, '≥5'), ('ROW5检漏值', 5, 3, '0.005'), ('ROW6洁净度结论', 6, 6, '合格'),
        ('ROW7_05标准', 7, 2, '≥0.5㎛：≤35200'), ('ROW7_05值', 7, 5, '30000'), ('ROW8_05ucl', 8, 5, '32000'),
        ('ROW9_5标准', 9, 2, '≥5㎛：≤293'), ('ROW9_5值', 9, 5, '200'), ('ROW10_5ucl', 10, 5, '240'),
        ('ROW11温度', 11, 2, '21～25'), ('ROW12湿度', 12, 2, '45～65'), ('ROW13照度', 13, 2, '300～500'),
        ('ROW14噪声值', 14, 3, '41.2'), ('ROW14噪声结论', 14, 4, '合格'),
    ]
    p, t, f = run_case('ISO 6', ISO6789_TPL, iso6_params, iso6_expect)
    passed += p; total += t; all_failures.extend(f)

    print(f'\nSUMMARY {passed}/{total}')
    if all_failures:
        print('FAILURES:')
        for item in all_failures:
            print('-', item)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
