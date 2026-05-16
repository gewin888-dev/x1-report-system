#!/usr/bin/env python3
import requests
from zipfile import ZipFile
from pathlib import Path

BASE='http://localhost:8082'
REPORTS=Path('/Users/fuwuqi/检测报告生成系统_X1/reports_x1')
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name,payload,keywords):
    r=s.post(f'{BASE}/api/x/submit_export', json={'project': payload}, timeout=60)
    if r.status_code!=200:
        return False, f'HTTP {r.status_code}'
    d=r.json()
    export_id=d.get('export_id','')
    p=Path(d.get('filled_docx_path') or REPORTS / f'{export_id}.filled.docx')
    if not p.exists():
        return False, f'文件不存在: {p}'
    try:
        with ZipFile(p,'r') as z:
            xml=z.read('word/document.xml').decode('utf-8','ignore')
        missing=[k for k in keywords if k not in xml]
        if missing:
            return False, f'缺失关键字: {missing[:3]}'
        return True, export_id
    except Exception as e:
        return False, f'docx读取失败: {e}'

if __name__=='__main__':
    if not login():
        print('LOGIN_FAIL')
        raise SystemExit(1)
    cases = []
    # negative_pressure
    cases.append(('negative_pressure', {
        'project_name':'测试项目-负压病房','report_number':'TEST-NP-001','client_name':'测试医院','contact_info':'王医生','project_address':'上海','inspection_area':'负压病房','detection_date':'2026-05-01','domain':'hospital','domain_name':'医院洁净部',
        'rooms':[{'room_id':'r1','room_name':'负压病房01','type_id':'negative_pressure','type_name':'负压病房','level_name':'负压病房','clean_class':'负压病房','basis':['WS/T 368-2012'],'judgement':['WS/T 368-2012'],'params':[],'summary':{'result_state':'合格','judgement_primary':'WS/T 368-2012'},'context':{'negative_pressure_mode':'ward-pressure-driven'}}]
    }, ['测试项目-负压病房','测试医院','负压病房01','合格']))
    # electronics ISO5-9
    for iso in ['ISO 5','ISO 6','ISO 7','ISO 8','ISO 9']:
        n=iso.replace(' ','')
        cases.append((f'electronics_{n}', {
            'project_name':f'测试项目-电子车间-{n}','report_number':f'TEST-EL-{n}','client_name':'测试电子厂','contact_info':'李工','project_address':'苏州','inspection_area':f'{n}车间','detection_date':'2026-05-01','domain':'electronics','domain_name':'精密制造',
            'rooms':[{'room_id':'r1','room_name':f'{n}车间01','type_id':'electronics_workshop','type_name':'电子车间','level_name':iso,'clean_class':iso,'basis':['GB 50472-2008'],'judgement':['GB 50472-2008'],'params':[],'summary':{'result_state':'合格','judgement_primary':'GB 50472-2008'},'context':{'iso_level':iso}}]
        }, [f'测试项目-电子车间-{n}','测试电子厂',f'{n}车间01','合格']))
    ok=0
    for name,payload,kw in cases:
        passed,detail=run_case(name,payload,kw)
        print(('PASS' if passed else 'FAIL'), name, detail)
        if passed: ok+=1
    print(f'SUMMARY {ok}/{len(cases)}')
