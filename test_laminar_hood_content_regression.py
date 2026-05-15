#!/usr/bin/env python3
"""laminar_hood 内容级回归测试"""
import sys, re, os, json
from zipfile import ZipFile

sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from adapters.template_fill import build_template_filled_docx

OUT_DIR = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/laminar_hood_content_regression'
TPL = '/Users/fuwuqi/公司资料/检测部/检测报告模板/制药工业/制药工业层流罩检测报告模板.docx'

text_pat = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
tbl_pat = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
row_pat = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
cell_pat = re.compile(r'<w:tc\b.*?</w:tc>', re.S)

def rows_from(path, ti):
    with ZipFile(path, 'r') as zf:
        x = zf.read('word/document.xml').decode('utf-8', 'ignore')
    return [[''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)]
            for row in row_pat.findall(list(tbl_pat.finditer(x))[ti].group(0))]


def mk_payload(name, params, template_key='pharmaceutical/laminar_hood'):
    return {
        'project': {'project_name': '层流罩回归', 'client_name': '某制药公司', 'project_address': '呼和浩特',
                     'contact_info': '13800000001', 'detection_date': '2026-05-08', 'report_number': 'LH-REG-001',
                     'domain': 'pharmaceutical', 'domain_name': '制药工业', 'inspection_area': '车间'},
        'room': {'room_id': 'r1', 'room_name': name, 'type_id': 'laminar_hood', 'type_name': '层流罩',
                 'level_name': 'A级', 'clean_class': 'A级', 'basis': ['GB 50457-2019'], 'judgement': ['GB 50457-2019'],
                 'summary': {'result_state': '合格'}, 'length': '1.2', 'width': '0.6', 'height': '0.8',
                 'context': {}, 'params': params},
        'report_context': {
            'project_context': {'project_name': '层流罩回归', 'client_name': '某制药公司', 'project_address': '呼和浩特',
                                'contact_info': '13800000001', 'detection_date': '2026-05-08', 'inspection_area': '车间',
                                'weather_text': '温度：22℃ 湿度：50%', 'project_overview_text': 'regression'},
            'room_context': {'room_id': 'r1', 'room_name': name, 'type_id': 'laminar_hood', 'type_name': '层流罩',
                             'level_name': 'A级', 'clean_class': 'A级', 'basis': ['GB 50457-2019'],
                             'basis_text': 'GB 50457-2019', 'judgement': ['GB 50457-2019'],
                             'judgement_text': 'GB 50457-2019', 'conclusion_text': '各项参数符合要求',
                             'summary': {'result_state': '合格'}, 'business_context': {}}},
        'template_rule': {'template_key': template_key, 'domain': 'pharmaceutical', 'type_id': 'laminar_hood'},
        'template_resource': {'template_path': TPL, 'resource_status': 'confirmed'},
        'export_type': 'laminar_hood', 'source': 'regression'
    }


def run_case(case_name, payload, tpl_path, expectations):
    os.makedirs(OUT_DIR, exist_ok=True)
    out = os.path.join(OUT_DIR, f'{case_name}.docx')
    build_template_filled_docx(payload, out)

    passed = 0
    fails = []

    # Instrument table check
    orig_inst = rows_from(tpl_path, 2)
    filled_inst = rows_from(out, 2)
    if orig_inst == filled_inst:
        print(f'✅ {case_name} 仪器表 IDENTICAL')
        passed += 1
    else:
        print(f'❌ {case_name} 仪器表 CHANGED')
        fails.append(f'{case_name} 仪器表 CHANGED')

    filled_rows = rows_from(out, 3)
    for label, row_idx, col_idx, expected in expectations:
        actual = filled_rows[row_idx][col_idx] if row_idx < len(filled_rows) and col_idx < len(filled_rows[row_idx]) else '<MISSING>'
        if actual == expected:
            print(f'✅ {case_name} {label}: {repr(actual)} == {repr(expected)}')
            passed += 1
        else:
            print(f'❌ {case_name} {label}: {repr(actual)} != {repr(expected)}')
            fails.append(f'{case_name} {label}: {repr(actual)} != {repr(expected)}')

    return passed, len(expectations) + 1, fails


def main():
    total = passed = 0
    fails = []

    params = {
        'avg_speed': {'type': 'numeric', 'values': [0.42, 0.44, 0.40], 'result': '0.42  ✅'},
        'speed_uniformity': {'type': 'numeric', 'values': [15], 'result': '15  ✅'},
        'airflow_pattern': {'type': 'text', 'values': ['气流垂直向下、无旋涡'], 'result': '合格  ✅'},
        'hepa_leak': {'type': 'numeric', 'values': [0.005], 'result': '0.005  ✅'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '2800', 'p05_ucl': '3200', 'p5_max': '15', 'p5_ucl': '18'}, 'result': '✅'},
    }

    p, t, f = run_case('laminar_hood_a', mk_payload('层流罩#1', params), TPL, [
        # ROW 0: 受检设备名称 + 检测日期
        ('row0_device', 0, 1, '层流罩'),
        ('row0_date', 0, 3, '2026-05-08'),
        # ROW 1: 所在房间
        ('row1_room', 1, 3, '层流罩#1'),
        # ROW 3: 垂直气流平均风速 - 值 + 结论
        ('row3_value', 3, 3, '0.42'),
        ('row3_conclusion', 3, 4, '合格'),
        # ROW 4: 风速不均匀度 - 值 + 结论
        ('row4_value', 4, 3, '15'),
        ('row4_conclusion', 4, 4, '合格'),
        # ROW 5: 气流流型 - 值 + 结论
        ('row5_value', 5, 3, '气流垂直向下、无旋涡'),
        ('row5_conclusion', 5, 4, '合格'),
        # ROW 6: 送风高效过滤器检漏 - 值 + 结论
        ('row6_value', 6, 3, '0.005'),
        ('row6_conclusion', 6, 4, '合格'),
        # ROW 7: 洁净度级别 + 结论
        ('row7_class', 7, 3, 'A级'),
        ('row7_conclusion', 7, 6, '合格'),
        # ROW 8: 0.5μm max
        ('row8_05max', 8, 5, '2800'),
        # ROW 9: 0.5μm UCL
        ('row9_05ucl', 9, 5, '3200'),
        # ROW 10: 5μm max
        ('row10_5max', 10, 5, '15'),
        # ROW 11: 5μm UCL
        ('row11_5ucl', 11, 5, '18'),
    ])
    passed += p; total += t; fails.extend(f)

    # Test 2: 不合格 case
    fail_params = {
        'avg_speed': {'type': 'numeric', 'values': [0.60], 'result': '0.60  ❌'},
        'speed_uniformity': {'type': 'numeric', 'values': [25], 'result': '25  ❌'},
        'airflow_pattern': {'type': 'text', 'values': ['有旋涡'], 'result': '不合格  ❌'},
        'hepa_leak': {'type': 'numeric', 'values': [0.02], 'result': '0.02  ❌'},
        'particle': {'type': 'particle_4', 'data': {'p05_max': '5000', 'p05_ucl': '5500', 'p5_max': '30', 'p5_ucl': '35'}, 'result': '❌'},
    }

    p, t, f = run_case('laminar_hood_fail', mk_payload('层流罩#2', fail_params), TPL, [
        ('row3_value', 3, 3, '0.6'),
        ('row3_conclusion', 3, 4, '不合格'),
        ('row4_value', 4, 3, '25'),
        ('row4_conclusion', 4, 4, '不合格'),
        ('row5_value', 5, 3, '有旋涡'),
        ('row5_conclusion', 5, 4, '不合格'),
        ('row6_value', 6, 3, '0.02'),
        ('row6_conclusion', 6, 4, '不合格'),
        ('row7_conclusion', 7, 6, '不合格'),
        ('row8_05max', 8, 5, '5000'),
        ('row9_05ucl', 9, 5, '5500'),
        ('row10_5max', 10, 5, '30'),
        ('row11_5ucl', 11, 5, '35'),
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
