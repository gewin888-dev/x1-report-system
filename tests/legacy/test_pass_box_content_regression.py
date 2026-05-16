#!/usr/bin/env python3
"""pass_box 内容级回归测试"""
import sys, re, os
from zipfile import ZipFile
sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from adapters.template_fill import build_template_filled_docx

OUT_DIR = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/pass_box_content_regression'
TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/制药工业/制药工业传递窗检测报告模板.docx'
text_pat = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
tbl_pat = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
row_pat = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
cell_pat = re.compile(r'<w:tc\b.*?</w:tc>', re.S)

def rows_from(path, ti):
    with ZipFile(path, 'r') as zf:
        x = zf.read('word/document.xml').decode('utf-8', 'ignore')
    return [[''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)]
            for row in row_pat.findall(list(tbl_pat.finditer(x))[ti].group(0))]

def mk_payload(name, params):
    return {
        'project': {'project_name': '传递窗回归', 'client_name': '某制药公司', 'project_address': '呼和浩特',
                     'contact_info': '13800000001', 'detection_date': '2026-05-08', 'report_number': 'PB-REG',
                     'domain': 'pharmaceutical', 'domain_name': '制药工业', 'inspection_area': '车间'},
        'room': {'room_id': 'r1', 'room_name': name, 'type_id': 'pass_box', 'type_name': '传递窗',
                 'level_name': '', 'clean_class': '', 'basis': ['JG/T 382-2012'], 'judgement': ['JG/T 382-2012'],
                 'summary': {'result_state': '合格'}, 'length': '0.6', 'width': '0.6', 'height': '0.6',
                 'context': {'inner_length': '0.5', 'inner_width': '0.5', 'inner_height': '0.5'}, 'params': params},
        'report_context': {
            'project_context': {'project_name': '传递窗回归', 'client_name': '某制药公司', 'project_address': '呼和浩特',
                                'contact_info': '13800000001', 'detection_date': '2026-05-08', 'inspection_area': '车间',
                                'weather_text': '温度：22℃ 湿度：50%', 'project_overview_text': 'regression'},
            'room_context': {'room_id': 'r1', 'room_name': name, 'type_id': 'pass_box', 'type_name': '传递窗',
                             'level_name': '', 'clean_class': '', 'basis': ['JG/T 382-2012'],
                             'basis_text': 'JG/T 382-2012', 'judgement': ['JG/T 382-2012'],
                             'judgement_text': 'JG/T 382-2012', 'conclusion_text': '各项参数符合要求',
                             'summary': {'result_state': '合格'}, 'business_context': {}}},
        'template_rule': {'template_key': 'pharmaceutical/pass_box', 'domain': 'pharmaceutical', 'type_id': 'pass_box'},
        'template_resource': {'template_path': TPL, 'resource_status': 'confirmed'},
        'export_type': 'pass_box', 'source': 'regression'
    }

def run_case(case_name, payload, tpl_path, expectations):
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f'{case_name}.docx')
    build_template_filled_docx(payload, out)
    passed = 0; fails = []
    orig_inst = rows_from(tpl_path, 2); filled_inst = rows_from(out, 2)
    if orig_inst == filled_inst:
        print(f'✅ {case_name} 仪器表 IDENTICAL'); passed += 1
    else:
        print(f'❌ {case_name} 仪器表 CHANGED'); fails.append(f'{case_name} 仪器表 CHANGED')
    filled_rows = rows_from(out, 3)
    for label, row_idx, col_idx, expected in expectations:
        actual = filled_rows[row_idx][col_idx] if row_idx < len(filled_rows) and col_idx < len(filled_rows[row_idx]) else '<MISSING>'
        if actual == expected:
            print(f'✅ {case_name} {label}: {repr(actual)} == {repr(expected)}'); passed += 1
        else:
            print(f'❌ {case_name} {label}: {repr(actual)} != {repr(expected)}')
            fails.append(f'{case_name} {label}: {repr(actual)} != {repr(expected)}')
    return passed, len(expectations) + 1, fails

def main():
    total = passed = 0; fails = []
    params = {
        'appearance': {'type': 'text', 'values': ['外形平整光洁'], 'result': '合格  ✅'},
        'door_interlock': {'type': 'text', 'values': ['互锁功能正常'], 'result': '合格  ✅'},
        'airchange_b12': {'type': 'numeric', 'values': [60], 'result': '60  ✅'},
        'noise': {'type': 'noise_corrected', 'background': '35', 'indoor': '42', 'result': '41.2 dB(A)  ✅'},
        'hepa_leak': {'type': 'numeric', 'values': [0.005], 'result': '0.005  ✅'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '200000', 'p05_ucl': '250000', 'p5_max': '1500', 'p5_ucl': '2000'}, 'result': '✅'},
    }
    p, t, f = run_case('pass_box_pass', mk_payload('传递窗#1', params), TPL, [
        ('row0_device', 0, 1, '传递窗'), ('row0_room', 0, 3, '传递窗#1'),
        ('row3_appearance_val', 3, 3, '外形平整光洁'), ('row3_appearance_concl', 3, 4, '合格'),
        ('row6_door_val', 6, 3, '互锁功能正常'), ('row6_door_concl', 6, 4, '合格'),
        ('row8_air_val', 8, 3, '60'), ('row8_air_concl', 8, 4, '合格'),
        ('row9_particle_concl', 9, 6, '合格'),
        ('row10_05max', 10, 5, '200000'), ('row11_05ucl', 11, 5, '250000'),
        ('row12_5max', 12, 5, '1500'), ('row13_5ucl', 13, 5, '2000'),
        ('row14_noise_val', 14, 3, '41.2'), ('row14_noise_concl', 14, 4, '合格'),
        ('row15_hepa_val', 15, 3, '0.005'), ('row15_hepa_concl', 15, 4, '合格'),
    ])
    passed += p; total += t; fails.extend(f)

    print(f'\nSUMMARY {passed}/{total}')
    if fails:
        print('FAILURES:')
        for x in fails: print('-', x)
        raise SystemExit(1)

if __name__ == '__main__':
    main()
