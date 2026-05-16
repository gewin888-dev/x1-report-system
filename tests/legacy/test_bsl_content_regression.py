#!/usr/bin/env python3
import re
from zipfile import ZipFile
from pathlib import Path
import sys

ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(ROOT))
from adapters.template_fill import build_template_filled_docx

TEMPLATE = ROOT.parent / '公司资料/检测部/检测报告模板/生物安全/生物安全实验室ISO6、ISO7、ISO8、ISO9检测报告模板.docx'
OUTDIR = ROOT / 'reports_x1' / 'bsl_probe_20260508'
OUTDIR.mkdir(parents=True, exist_ok=True)


def payload():
    return {
        'project': {'project_name':'BSL探针','client_name':'测试研究所','project_address':'呼和浩特','contact_info':'13800000000','detection_date':'2026-05-08','report_number':'BSL-PROBE-001','domain':'biosafety','domain_name':'生物安全','inspection_area':'P2实验室'},
        'room': {
            'room_id':'r1','room_name':'P2主实验间','type_id':'bsl','type_name':'生物安全实验室','level_name':'ISO 8','clean_class':'ISO 8',
            'basis':['GB 50346-2011','GB 50591-2010'],'judgement':['GB 50346-2011'],'summary':{'result_state':'pass'},
            'context':{'bsl_level':'BSL-2（P2）'},'length':'8','width':'6','height':'3',
            'params': {
                'airchange':{'type':'numeric','values':[13,12,14],'result':'13.0  ✅'},
                'pressure':{'type':'numeric','values':[-12,-11,-13],'result':'-12.0  ✅'},
                'airflow_direction':{'type':'text','result':'符合要求  ✅'},
                'hepa_leak':{'type':'hepa_leak_multi','objects':[{'name':'1#','value':'0.004'}],'result':'-'},
                'particle':{'type':'particle_4','data':{'p05_max':'2100000','p05_ucl':'2200000','p5_max':'12000','p5_ucl':'13000'},'result':'✅'},
                'temperature':{'type':'numeric','values':[23,24,22],'result':'23.0  ✅'},
                'humidity':{'type':'numeric','values':[45,50,48],'result':'47.7  ✅'},
                'illumination':{'type':'numeric','values':[320,330,310],'result':'320  ✅'},
                'noise':{'type':'noise_corrected','background':'38','indoor':'45','result':'44.3 dB(A)  ✅'},
                'settle_bacteria':{'type':'bacteria_control','values':['2','1','3'],'blank':'0','neg':'0','result':'2.0  ✅'},
                'floating_bacteria':{'type':'numeric','values':[80,90,85],'result':'85.0  ✅'}
            }
        },
        'report_context': {
            'project_context': {'project_name':'BSL探针','client_name':'测试研究所','project_address':'呼和浩特','contact_info':'13800000000','detection_date':'2026-05-08','inspection_area':'P2实验室','weather_text':'温度：22.0℃  湿度：50.0%RH  大气压力：890.0hPa','project_overview_text':'probe'},
            'room_context': {'room_id':'r1','room_name':'P2主实验间','type_id':'bsl','type_name':'生物安全实验室','level_name':'ISO 8','clean_class':'ISO 8','basis':['GB 50346-2011','GB 50591-2010'],'basis_text':'GB 50346-2011\nGB 50591-2010','judgement':['GB 50346-2011'],'judgement_text':'GB 50346-2011','conclusion_text':'各项参数符合要求','summary':{'result_state':'pass'},'business_context':{}}
        },
        'template_rule': {'template_key':'biosafety/bsl/p2','domain':'biosafety','type_id':'bsl'},
        'template_resource': {'template_path': str(TEMPLATE),'resource_status':'confirmed'},
        'export_type':'bsl','source':'probe'
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
    out = OUTDIR / 'bsl_p2_regression.filled.docx'
    build_template_filled_docx(payload(), str(out))
    rows, _ = rows_from_docx(out, 3)
    checks = [
        ('row0_date', rows[0][3] == '2026-05-08'),
        ('row0_level', rows[0][5] == 'ISO 8'),
        ('row1_sv', '面积S（m2）=48' in rows[1][1] and '体积V（m3）=144' in rows[1][1]),
        ('airchange', rows[3][2] == '≥12' and rows[3][3] == '13' and rows[3][4] == '合格'),
        ('pressure', rows[4][2] == '-10～-15' and rows[4][3] == '-12' and rows[4][4] == '合格'),
        ('airflow_direction', rows[5][3] == '符合要求' and rows[5][4] == '合格'),
        ('hepa', rows[6][3] == '0.004' and rows[6][4] == '合格'),
        ('particle_05', rows[8][2] == '≥0.5μm≤3520000' and rows[8][4] == '2100000'),
        ('particle_05_ucl', rows[9][5] == '2200000'),
        ('particle_5', rows[10][2] == '≥5μm≤29300' and rows[10][4] == '12000'),
        ('particle_5_ucl', rows[11][5] == '13000'),
        ('temperature', rows[12][2] == '18～27' and rows[12][3] == '23' and rows[12][4] == '合格'),
        ('humidity', rows[13][2] == '30～70' and rows[13][3] == '47.67' and rows[13][4] == '合格'),
        ('illumination', rows[14][2] == '≥300' and rows[14][3] == '320' and rows[14][4] == '合格'),
        ('noise', rows[15][2] == '≤60' and rows[15][3] == '44.3' and rows[15][4] == '合格'),
        ('settling', rows[16][2] == '≤10' and rows[16][3] == '2' and rows[16][4] == '合格'),
        ('floating', rows[17][2] == '≤500' and rows[17][3] == '85' and rows[17][4] == '合格'),
    ]

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
