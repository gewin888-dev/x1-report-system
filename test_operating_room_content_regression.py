#!/usr/bin/env python3
"""operating_room 全变体内容级回归：百级/千级/十万级 × 普通/眼科 + 辅房"""
import sys, re, os
from zipfile import ZipFile
sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from adapters.template_fill import build_template_filled_docx

OUT = '/Users/fuwuqi/检测报告生成系统_X1/reports_x1/or_content_regression'
TPL_DIR = '/Users/fuwuqi/公司资料/检测部/检测报告模板/医院洁净部'

text_pat = re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
tbl_pat = re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
row_pat = re.compile(r'<w:tr\b.*?</w:tr>', re.S)
cell_pat = re.compile(r'<w:tc\b.*?</w:tc>', re.S)

def rows_from(path, ti):
    with ZipFile(path, 'r') as zf:
        x = zf.read('word/document.xml').decode('utf-8', 'ignore')
    return [[''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)]
            for row in row_pat.findall(list(tbl_pat.finditer(x))[ti].group(0))]

def mk(level, eye, tpl):
    classes = {'1':'Ⅰ级（百级）','2':'Ⅱ级（千级）','3':'Ⅲ级（万级）','4':'Ⅳ级（十万级）'}
    cc = classes[level]; srt = '眼科手术室' if eye else '手术室'
    keys = {'1': f'hospital/operating_room/{"eye/level1-1" if eye else "main/level1"}',
            '2': f'hospital/operating_room/{"eye/level1-2" if eye else "main/level2"}',
            '3': f'hospital/operating_room/{"eye/level1-3" if eye else "main/level3"}',
            '4': f'hospital/operating_room/{"eye/level1-4" if eye else "main/level4"}'}
    params = {
        'pressure':{'type':'numeric','values':[10],'result':'10  ✅'},
        'hepa_leak':{'type':'hepa_objects','objects':[{'name':'1#','value':'0.005'},{'name':'2#','value':'0.003'}],'result':'✅'},
        'temperature':{'type':'numeric','values':[23],'result':'23  ✅'},
        'humidity':{'type':'numeric','values':[45],'result':'45  ✅'},
        'illumination_min':{'type':'numeric','values':[400],'result':'400  ✅'},
        'illumination_uniformity':{'type':'numeric','values':[0.8],'result':'0.8  ✅'},
        'noise':{'type':'noise_corrected','background':'35','indoor':'42','result':'41.2 dB(A)  ✅'},
        'bacteria':{'type':'bacteria_control','data':{'op_values':['0','0'],'surr_values':['0.2']},'result':'0  ✅'},
        'particle':{'type':'particle_4','data':{'op_05_max':'2800','op_05_ucl':'3200','op_5_max':'0','op_5_ucl':'0',
                    'surr_05_max':'300000','surr_05_ucl':'320000','surr_5_max':'2000','surr_5_ucl':'2400'},'result':'✅'},
    }
    if level == '1':
        params['wind_speed'] = {'type':'numeric','values':[0.18],'result':'0.18  ✅'}
        params['wind_uniformity'] = {'type':'numeric','values':[0.20],'result':'0.20  ✅'}
        params['particle_door'] = {'type':'particle_4','data':{'p05_max':'300000','p05_ucl':'320000','p5_max':'2000','p5_ucl':'2400'},'result':'✅'}
    else:
        params['airchange'] = {'type':'numeric','values':[25],'result':'25  ✅'}
    return {
      'project':{'project_name':f'{srt}回归{level}','client_name':'某医院','project_address':'呼和浩特',
                 'contact_info':'13800000001','detection_date':'2026-05-09','report_number':f'OR-{level}',
                 'domain':'hospital','domain_name':'医院洁净部','inspection_area':'手术部'},
      'room':{'room_id':'r1','room_name':f'{srt}#{level}','type_id':'operating_room','type_name':'手术室',
              'level_name':cc,'clean_class':cc,'basis':['GB 50333-2013'],'judgement':['GB 50333-2013'],
              'summary':{'result_state':'合格'},'length':'6','width':'5','height':'3',
              'context':{'surgery_room_type':srt},'params':params},
      'report_context':{'project_context':{'project_name':f'{srt}回归{level}','client_name':'某医院','project_address':'呼和浩特',
                        'contact_info':'13800000001','detection_date':'2026-05-09','inspection_area':'手术部',
                        'weather_text':'温度：22℃ 湿度：50%','project_overview_text':'regression'},
                        'room_context':{'room_id':'r1','room_name':f'{srt}#{level}','type_id':'operating_room','type_name':'手术室',
                        'level_name':cc,'clean_class':cc,'basis':['GB 50333-2013'],'basis_text':'GB 50333-2013',
                        'judgement':['GB 50333-2013'],'judgement_text':'GB 50333-2013','conclusion_text':'各项参数符合要求',
                        'summary':{'result_state':'合格'},'business_context':{}}},
      'template_rule':{'template_key':keys[level],'domain':'hospital','type_id':'operating_room'},
      'template_resource':{'template_path':tpl,'resource_status':'confirmed'},'export_type':'operating_room','source':'regression'}

def check(cname, tpl, payload, expects):
    os.makedirs(OUT, exist_ok=True)
    out = os.path.join(OUT, f'{cname}.docx')
    build_template_filled_docx(payload, out)
    p = 0; f = []
    # Instrument table check
    if rows_from(tpl, 2) == rows_from(out, 2):
        print(f'✅ {cname} 仪器表 IDENTICAL'); p += 1
    else:
        print(f'❌ {cname} 仪器表 CHANGED'); f.append(f'{cname} inst')
    # Cell checks
    with ZipFile(out, 'r') as zf:
        xml = zf.read('word/document.xml').decode('utf-8', 'ignore')
    tbls = list(tbl_pat.finditer(xml))
    for label, ti, ri, ci, expected in expects:
        rows = [[''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)]
                for row in row_pat.findall(tbls[ti].group(0))]
        actual = rows[ri][ci] if ri < len(rows) and ci < len(rows[ri]) else '<MISS>'
        if actual == expected:
            print(f'✅ {cname} {label}'); p += 1
        else:
            print(f'❌ {cname} {label}: {repr(actual)} != {repr(expected)}'); f.append(f'{cname} {label}')
    return p, len(expects) + 1, f

def main():
    total = passed = 0; fails = []

    # === 百级普通手术室 ===
    tpl1 = f'{TPL_DIR}/医院洁净部洁净手术部手术室百级检测报告模板.docx'
    p,t,f = check('main_L1', tpl1, mk('1', False, tpl1), [
        ('风速标准', 3, 3, 2, '0.20～0.25'), ('风速值', 3, 3, 3, '10'), ('风速结论', 3, 3, 4, '合格'),
        ('不均匀度结论', 3, 4, 4, '合格'), ('静压差标准', 3, 5, 2, '5～20'), ('静压差结论', 3, 5, 4, '合格'),
        ('开门0.5max', 3, 6, 5, '300000'), ('开门结论', 3, 6, 6, '合格'),
        ('检漏值', 3, 10, 3, '1#:0.005% / 2#:0.003%'), ('检漏结论', 3, 10, 4, '合格'),
        ('严密性结论', 3, 11, 4, '合格'), ('洁净度总结论', 3, 12, 6, '合格'),
        ('手术区0.5max', 3, 13, 6, '2800'), ('手术区ISO', 3, 13, 7, 'ISO-5'),
        ('温度值', 3, 21, 3, '23'), ('温度结论', 3, 21, 4, '合格'),
        ('湿度结论', 3, 22, 4, '合格'), ('照度值', 3, 23, 4, '400'), ('噪声值', 3, 25, 3, '41.2'),
        ('菌手术区', 3, 26, 4, '0.0'), ('菌周边区', 3, 27, 4, '0.2'),
    ])
    passed += p; total += t; fails.extend(f)

    # === 千级普通手术室 ===
    tpl2 = f'{TPL_DIR}/医院洁净部洁净手术部手术室千级万级检测报告模板.docx'
    p,t,f = check('main_L2', tpl2, mk('2', False, tpl2), [
        ('换气标准', 3, 3, 2, '≥24'), ('静压差标准', 3, 4, 2, '5～15'), ('静压差结论', 3, 4, 4, '合格'),
        ('检漏结论', 3, 5, 4, '合格'), ('严密性结论', 3, 6, 4, '合格'),
        ('洁净度总结论', 3, 7, 6, '合格'),
        ('手术区0.5max', 3, 8, 6, '2800'),
        ('周边区0.5max', 3, 12, 6, '300000'),
        ('温度值', 3, 16, 3, '23'), ('温度结论', 3, 16, 4, '合格'),
        ('湿度结论', 3, 17, 4, '合格'), ('噪声标准', 3, 20, 2, '≤49'), ('噪声值', 3, 20, 3, '41.2'),
        ('菌手术区', 3, 21, 4, '0.0'), ('菌周边区', 3, 22, 4, '0.2'),
    ])
    passed += p; total += t; fails.extend(f)

    # === 十万级普通手术室 ===
    tpl4 = f'{TPL_DIR}/医院洁净部洁净手术部手术室十万级检测报告模板.docx'
    p,t,f = check('main_L4', tpl4, mk('4', False, tpl4), [
        ('换气标准', 3, 3, 2, '≥12'), ('静压差标准', 3, 4, 2, '≥5'), ('静压差结论', 3, 4, 4, '合格'),
        ('检漏结论', 3, 5, 4, '合格'), ('严密性结论', 3, 6, 4, '合格'),
        ('洁净度总结论', 3, 7, 6, '合格'),
        ('粒子0.5max', 3, 8, 5, '2800'),
        ('温度值', 3, 12, 3, '23'), ('温度结论', 3, 12, 4, '合格'),
        ('噪声标准', 3, 16, 2, '≤49'), ('噪声值', 3, 16, 3, '41.2'),
    ])
    passed += p; total += t; fails.extend(f)

    # === 眼科百级 ===
    etpl1 = f'{TPL_DIR}/医院洁净部洁净手术部眼科手术室百级检测报告模板.docx'
    p,t,f = check('eye_L1', etpl1, mk('1', True, etpl1), [
        ('风速标准', 3, 3, 2, '0.15～0.20'),  # 眼科百级风速标准不同！
        ('静压差标准', 3, 5, 2, '5～20'), ('静压差结论', 3, 5, 4, '合格'),
        ('开门ISO', 3, 6, 3, 'ISO-7'),  # 眼科particle_door用ISO-7
        ('检漏结论', 3, 10, 4, '合格'),
        ('洁净度总结论', 3, 12, 6, '合格'),
        ('手术区0.5max', 3, 13, 6, '2800'),
        ('温度值', 3, 21, 3, '23'), ('噪声标准', 3, 25, 2, '≤51'),
        ('菌手术区', 3, 26, 4, '0.0'),
    ])
    passed += p; total += t; fails.extend(f)

    # === 眼科千级 ===
    etpl2 = f'{TPL_DIR}/医院洁净部洁净手术部眼科手术室千级万级检测报告模板.docx'
    p,t,f = check('eye_L2', etpl2, mk('2', True, etpl2), [
        ('换气标准', 3, 3, 2, '≥24'), ('静压差标准', 3, 4, 2, '5～20'),  # 眼科千级静压差不同
        ('静压差结论', 3, 4, 4, '合格'),
        ('洁净度总结论', 3, 7, 6, '合格'),
        ('手术区0.5max', 3, 8, 6, '2800'),
        ('温度值', 3, 16, 3, '23'), ('噪声标准', 3, 20, 2, '≤49'),
        ('菌手术区', 3, 21, 4, '0.0'),
    ])
    passed += p; total += t; fails.extend(f)

    # === 眼科十万级 ===
    etpl4 = f'{TPL_DIR}/医院洁净部洁净手术部眼科手术室十万级检测报告模板.docx'
    p,t,f = check('eye_L4', etpl4, mk('4', True, etpl4), [
        ('换气标准', 3, 3, 2, '≥12'), ('静压差标准', 3, 4, 2, '5～20'),
        ('静压差结论', 3, 4, 4, '合格'),
        ('洁净度总结论', 3, 7, 6, '合格'),
        ('温度值', 3, 12, 3, '23'), ('噪声标准', 3, 16, 2, '≤49'),
    ])
    passed += p; total += t; fails.extend(f)

    print(f'\nSUMMARY {passed}/{total}')
    if fails:
        print('FAILURES:')
        for x in fails: print(f'  - {x}')
        raise SystemExit(1)

if __name__ == '__main__':
    main()
