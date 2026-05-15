#!/usr/bin/env python3
import re
from zipfile import ZipFile
from pathlib import Path
import sys

ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(ROOT))
from adapters.template_fill import build_template_filled_docx

TEMPLATE = ROOT.parent / '公司资料/检测部/检测报告模板/医院洁净部/医院洁净部洁净功能用房检测报告模板.docx'
OUTDIR = ROOT / 'reports_x1' / 'cf_probe_20260508'
OUTDIR.mkdir(parents=True, exist_ok=True)


def payload():
    return {
        'project': {'project_name':'XX医院ICU','client_name':'XX医院','project_address':'呼和浩特','contact_info':'13800000000','detection_date':'2026-05-08','report_number':'PDJC-TEST-CF001','domain':'hospital','domain_name':'医院洁净部','inspection_area':'5楼ICU'},
        'room': {
            'room_id':'r1','room_name':'ICU病房','type_id':'clean_function_room','type_name':'洁净功能用房','level_name':'ICU','clean_class':'Ⅳ级（十万级）',
            'length':'8','width':'6','height':'3',
            'basis':['国家卫生健康委办公厅','WS/T 368-2012','GB 50591-2010'],
            'judgement':['国家卫生健康委办公厅'],'summary':{'result_state':'pass'},'context':{},
            'params': {
                'airchange':{'type':'numeric','values':[25,26,24],'result':'25.0  ✅'},
                'pressure':{'type':'numeric','values':[8,9,7],'result':'8.0  ✅'},
                'temperature':{'type':'numeric','values':[23,24,22],'result':'23.0  ✅'},
                'humidity':{'type':'numeric','values':[45,50,48],'result':'47.7  ✅'},
                'illumination_min':{'type':'numeric','values':[320,350,310],'result':'320  ✅'},
                'noise':{'type':'noise_corrected','background':'38','indoor':'45','result':'44.3 dB(A)  ✅'},
                'particle':{'type':'particle_4','data':{'p05_max':'152000','p05_ucl':'155000','p5_max':'890','p5_ucl':'910'},'result':'✅'},
                'hepa_leak':{'type':'hepa_leak_multi','objects':[{'name':'1#','value':'0.003'}],'result':'-'},
                'bacteria':{'type':'bacteria_control','values':['0.2','0.3','0.1'],'blank':'0','neg':'0','result':'0.2  ✅'},
                'floating_bacteria':{'type':'numeric','values':[50,55,52],'result':'52.3  ✅'}
            }
        },
        'report_context': {
            'project_context': {'project_name':'XX医院ICU','client_name':'XX医院','project_address':'呼和浩特','contact_info':'13800000000','detection_date':'2026-05-08','inspection_area':'5楼ICU','weather_text':'温度：22.0℃  湿度：50.0%RH  大气压力：890.0hPa','project_overview_text':'本次委托检测项目为XX医院ICU，项目地点位于呼和浩特，本次检测区域为5楼ICU。'},
            'room_context': {'room_id':'r1','room_name':'ICU病房','type_id':'clean_function_room','type_name':'洁净功能用房','level_name':'ICU','clean_class':'Ⅳ级（十万级）','basis':['国家卫生健康委办公厅','WS/T 368-2012','GB 50591-2010'],'basis_text':'国家卫生健康委办公厅\nWS/T 368-2012\nGB 50591-2010','judgement':['国家卫生健康委办公厅'],'judgement_text':'国家卫生健康委办公厅','conclusion_text':'本次检测的各项参数均符合判定依据中的相应规定。','summary':{'result_state':'pass'},'business_context':{}}
        },
        'template_rule': {'template_key':'icu','domain':'hospital','type_id':'clean_function_room'},
        'template_resource': {'template_path': str(TEMPLATE),'resource_status':'confirmed'},
        'export_type':'clean_function_room','source':'probe'
    }


def rows_from_docx(path, table_index=3):
    with ZipFile(path,'r') as zf:
        xml=zf.read('word/document.xml').decode('utf-8','ignore')
    text_pat=re.compile(r'<w:t(?:\s[^>]*)?>([^<]*)</w:t>', re.S)
    tbl_pat=re.compile(r'<w:tbl\b.*?</w:tbl>', re.S)
    row_pat=re.compile(r'<w:tr\b.*?</w:tr>', re.S)
    cell_pat=re.compile(r'<w:tc\b.*?</w:tc>', re.S)
    tbl = list(tbl_pat.finditer(xml))[table_index].group(0)
    rows=[]
    for row in row_pat.findall(tbl):
        rows.append([''.join(text_pat.findall(c)).strip() for c in cell_pat.findall(row)])
    return rows, xml


def main():
    out = OUTDIR / 'cf_icu_regression.filled.docx'
    build_template_filled_docx(payload(), str(out))
    rows, xml = rows_from_docx(out, 3)
    checks = [
        ('row0_date', rows[0][3] == '2026-05-08'),
        ('row0_level', rows[0][5] == 'Ⅳ级（十万级）'),
        ('row1_sv', '面积S（m²）=48' in rows[1][1] and '体积V（m³）=144' in rows[1][1]),
        ('airchange', rows[3][2] == '≥15' and rows[3][3] == '25' and rows[3][4] == '合格'),
        ('pressure', rows[4][2] == '≥10' and rows[4][3] == '8' and rows[4][4] == '合格'),
        ('hepa', rows[5][2] == '≤0.01%' and rows[5][3] == '0.003' and rows[5][4] == '合格'),
        ('particle_05', rows[7][2] == '≥0.5μm≤3500000' and rows[7][5] == '152000' and rows[7][6] == '合格'),
        ('particle_5', rows[9][2] == '≥5μm≤20000' and rows[9][5] == '890'),
        ('temperature', rows[11][2] == '18～26' and rows[11][3] == '23' and rows[11][4] == '合格'),
        ('humidity', rows[12][2] == '35～75' and rows[12][3] == '47.67' and rows[12][4] == '合格'),
        ('illumination', rows[13][2] == '≥300' and rows[13][3] == '326.67' and rows[13][4] == '合格'),
        ('noise', rows[14][2] == '≤60' and rows[14][3] == '44.3' and rows[14][4] == '合格'),
        ('settling', rows[15][2] == '≤10' and rows[15][3] == '0.2' and rows[15][4] == '合格'),
        ('floating', rows[16][2] == '≤500' and rows[16][3] == '52.33' and rows[16][4] == '合格'),
    ]

    # table 2 identical
    out_tbl2, _ = rows_from_docx(out, 2)
    tpl_tbl2, _ = rows_from_docx(TEMPLATE, 2)
    checks.append(('instrument_table_identical', out_tbl2 == tpl_tbl2))

    ok = 0
    for name, passed in checks:
        print(('PASS' if passed else 'FAIL'), name)
        ok += 1 if passed else 0
    print(f'SUMMARY {ok}/{len(checks)}')
    raise SystemExit(0 if ok == len(checks) else 1)


if __name__ == '__main__':
    main()
