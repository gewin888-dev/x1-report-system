#!/usr/bin/env python3
"""bsc / clean_bench / ivc 内容级回归测试"""
import sys, re, os
from zipfile import ZipFile
sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from adapters.template_fill import build_template_filled_docx

OUT_DIR = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/device_content_regression'
BSC_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/生物安全/生物安全生物安全柜检测报告模板.docx'
CB_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/生物安全/生物安全洁净工作台检测报告模板.docx'
IVC_TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/生物安全/生物安全IVC笼具检测报告模板.docx'

text_pat = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
tbl_pat = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
row_pat = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
cell_pat = re.compile(r'<w:tc\b.*?</w:tc>', re.S)

def rows_from(path, ti):
    with ZipFile(path, 'r') as zf:
        x = zf.read('word/document.xml').decode('utf-8', 'ignore')
    return [[''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)]
            for row in row_pat.findall(list(tbl_pat.finditer(x))[ti].group(0))]

def mk_payload(tid, tname, tpl, params):
    return {
        'project': {'project_name': f'{tname}回归', 'client_name': '某公司', 'project_address': '呼和浩特',
                     'contact_info': '13800000001', 'detection_date': '2026-05-08', 'report_number': f'{tid.upper()}-REG',
                     'domain': 'biosafety', 'domain_name': '生物安全', 'inspection_area': '实验室'},
        'room': {'room_id': 'r1', 'room_name': f'{tname}#1', 'type_id': tid, 'type_name': tname,
                 'level_name': '', 'clean_class': '', 'basis': ['YY 0569-2011'], 'judgement': ['YY 0569-2011'],
                 'summary': {'result_state': '合格'}, 'length': '1', 'width': '0.6', 'height': '0.8',
                 'context': {}, 'params': params},
        'report_context': {
            'project_context': {'project_name': f'{tname}回归', 'client_name': '某公司', 'project_address': '呼和浩特',
                                'contact_info': '13800000001', 'detection_date': '2026-05-08', 'inspection_area': '实验室',
                                'weather_text': '温度：22℃ 湿度：50%', 'project_overview_text': 'regression'},
            'room_context': {'room_id': 'r1', 'room_name': f'{tname}#1', 'type_id': tid, 'type_name': tname,
                             'level_name': '', 'clean_class': '', 'basis': ['YY 0569-2011'],
                             'basis_text': 'YY 0569-2011', 'judgement': ['YY 0569-2011'],
                             'judgement_text': 'YY 0569-2011', 'conclusion_text': '各项参数符合要求',
                             'summary': {'result_state': '合格'}, 'business_context': {}}},
        'template_rule': {'template_key': f'biosafety/{tid}', 'domain': 'biosafety', 'type_id': tid},
        'template_resource': {'template_path': tpl, 'resource_status': 'confirmed'},
        'export_type': tid, 'source': 'regression'
    }

def run_case(case_name, payload, tpl_path, expectations, inst_table=2):
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f'{case_name}.docx')
    build_template_filled_docx(payload, out)
    passed = 0; fails = []
    if rows_from(tpl_path, inst_table) == rows_from(out, inst_table):
        print(f'✅ {case_name} 仪器表 IDENTICAL'); passed += 1
    else:
        print(f'❌ {case_name} 仪器表 CHANGED'); fails.append(f'{case_name} 仪器表 CHANGED')
    with ZipFile(out, 'r') as zf:
        xml = zf.read('word/document.xml').decode('utf-8', 'ignore')
    all_tables = list(tbl_pat.finditer(xml))
    for label, tbl_idx, row_idx, col_idx, expected in expectations:
        tbl_rows = [[''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)]
                    for row in row_pat.findall(all_tables[tbl_idx].group(0))]
        actual = tbl_rows[row_idx][col_idx] if row_idx < len(tbl_rows) and col_idx < len(tbl_rows[row_idx]) else '<MISSING>'
        if actual == expected:
            print(f'✅ {case_name} {label}: {repr(actual)} == {repr(expected)}'); passed += 1
        else:
            print(f'❌ {case_name} {label}: {repr(actual)} != {repr(expected)}')
            fails.append(f'{case_name} {label}: {repr(actual)} != {repr(expected)}')
    return passed, len(expectations) + 1, fails

def main():
    total = passed = 0; fails = []

    # BSC
    bsc_params = {
        'appearance': {'type': 'text', 'values': ['外形平整'], 'result': '合格  ✅'},
        'alarm_interlock': {'type': 'text', 'values': ['报警联锁正常'], 'result': '合格  ✅'},
        'downflow_speed': {'type': 'numeric', 'values': [0.35], 'result': '0.35  ✅'},
        'inflow_speed': {'type': 'numeric', 'values': [0.55], 'result': '0.55  ✅'},
        'airflow_pattern': {'type': 'text', 'values': ['气流垂直向下无旋涡'], 'result': '合格  ✅'},
        'hepa_leak': {'type': 'numeric', 'values': [0.005], 'result': '0.005  ✅'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '2800', 'p05_ucl': '3200', 'p5_max': '15', 'p5_ucl': '18'}, 'result': '✅'},
        'noise': {'type': 'numeric', 'values': [60], 'result': '60  ✅'},
        'illumination': {'type': 'numeric', 'values': [700], 'result': '700  ✅'},
        'uv_intensity': {'type': 'numeric', 'values': [500], 'result': '500  ✅'},
    }
    p, t, f = run_case('bsc', mk_payload('bsc', '生物安全柜', BSC_TPL, bsc_params), BSC_TPL, [
        # TABLE 3
        ('t3r1_appear_val', 3, 1, 3, '外形平整'), ('t3r1_appear_concl', 3, 1, 4, '合格'),
        ('t3r4_alarm_val', 3, 4, 3, '报警联锁正常'), ('t3r4_alarm_concl', 3, 4, 4, '合格'),
        ('t3r5_downflow', 3, 5, 3, '0.35'), ('t3r5_concl', 3, 5, 4, '合格'),
        ('t3r6_inflow', 3, 6, 3, '0.55'), ('t3r6_concl', 3, 6, 4, '合格'),
        ('t3r7_airflow', 3, 7, 3, '气流垂直向下无旋涡'), ('t3r7_concl', 3, 7, 4, '合格'),
        ('t3r11_hepa', 3, 11, 3, '0.005'), ('t3r11_concl', 3, 11, 4, '合格'),
        # TABLE 4
        ('t4r1_particle_concl', 4, 1, 6, '合格'),
        ('t4r2_05max', 4, 2, 5, '2800'), ('t4r3_05ucl', 4, 3, 5, '3200'),
        ('t4r4_5max', 4, 4, 5, '15'), ('t4r5_5ucl', 4, 5, 5, '18'),
        ('t4r6_noise_concl', 4, 6, 4, '合格'), ('t4r7_illum_concl', 4, 7, 4, '合格'),
        ('t4r12_uv_concl', 4, 12, 4, '合格'),
    ])
    passed += p; total += t; fails.extend(f)

    # Clean Bench
    cb_params = {
        'appearance': {'type': 'text', 'values': ['外形平整'], 'result': '合格  ✅'},
        'function': {'type': 'text', 'values': ['功能正常'], 'result': '合格  ✅'},
        'hepa_leak': {'type': 'numeric', 'values': [0.005], 'result': '0.005  ✅'},
        'avg_speed': {'type': 'numeric', 'values': [0.35], 'result': '0.35  ✅'},
        'speed_uniformity': {'type': 'numeric', 'values': [10], 'result': '10  ✅'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '2800', 'p05_ucl': '3200', 'p5_max': '15', 'p5_ucl': '18'}, 'result': '✅'},
        'settling': {'type': 'bacteria_control', 'values': ['0', '0', '0'], 'blank': '0', 'neg': '0', 'result': '0  ✅'},
        'airflow_pattern': {'type': 'text', 'values': ['气流垂直无死角'], 'result': '合格  ✅'},
        'illumination': {'type': 'numeric', 'values': [350], 'result': '350  ✅'},
        'noise': {'type': 'numeric', 'values': [58], 'result': '58  ✅'},
    }
    p, t, f = run_case('clean_bench', mk_payload('clean_bench', '洁净工作台', CB_TPL, cb_params), CB_TPL, [
        ('r1_appear', 3, 1, 3, '外形平整'), ('r1_concl', 3, 1, 4, '合格'),
        ('r3_func', 3, 3, 3, '功能正常'), ('r3_concl', 3, 3, 4, '合格'),
        ('r6_hepa_concl', 3, 6, 4, '合格'), ('r7_speed_concl', 3, 7, 4, '合格'), ('r8_unif_concl', 3, 8, 4, '合格'),
        ('r9_particle_concl', 3, 9, 6, '合格'),
        ('r10_05max', 3, 10, 5, '2800'), ('r11_05ucl', 3, 11, 5, '3200'),
        ('r12_5max', 3, 12, 5, '15'), ('r13_5ucl', 3, 13, 5, '18'),
        ('r14_settle_concl', 3, 14, 4, '合格'),
        ('r15_airflow', 3, 15, 3, '气流垂直无死角'), ('r15_concl', 3, 15, 4, '合格'),
        ('r16_illum_concl', 3, 16, 4, '合格'), ('r17_noise_concl', 3, 17, 4, '合格'),
    ])
    passed += p; total += t; fails.extend(f)

    # IVC
    ivc_params = {
        'airflow_speed': {'type': 'numeric', 'values': [0.15], 'result': '0.15  ✅'},
        'airchange': {'type': 'numeric', 'values': [25], 'result': '25  ✅'},
        'pressure': {'type': 'numeric', 'values': [-25], 'result': '-25  ✅'},
        'cage_airtightness': {'type': 'numeric', 'values': [8], 'result': '8  ✅'},
        'hepa_leak_supply': {'type': 'numeric', 'values': [0.005], 'result': '0.005  ✅'},
        'hepa_leak_exhaust': {'type': 'numeric', 'values': [0.003], 'result': '0.003  ✅'},
    }
    p, t, f = run_case('ivc', mk_payload('ivc', 'IVC笼具', IVC_TPL, ivc_params), IVC_TPL, [
        ('r1_speed_concl', 3, 1, 4, '合格'), ('r2_air_concl', 3, 2, 4, '合格'), ('r3_pressure_concl', 3, 3, 4, '合格'),
        ('r4_seal_val', 3, 4, 3, '8'), ('r4_seal_concl', 3, 4, 4, '合格'),
        ('r5_hepa_supply_val', 3, 5, 4, '0.005'), ('r5_hepa_supply_concl', 3, 5, 5, '合格'),
        ('r6_hepa_exhaust_val', 3, 6, 4, '0.003'), ('r6_hepa_exhaust_concl', 3, 6, 5, '合格'),
    ])
    passed += p; total += t; fails.extend(f)

    print(f'\nSUMMARY {passed}/{total}')
    if fails:
        print('FAILURES:')
        for x in fails: print('-', x)
        raise SystemExit(1)

if __name__ == '__main__':
    main()
