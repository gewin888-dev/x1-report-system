#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, params, expected):
    payload={
        'schema_version':'1.1',
        'project_name':name,
        'report_number':'TEST-LH-001',
        'client_name':'测试制药厂',
        'contact_info':'刘工 13800000000',
        'project_address':'上海测试区',
        'inspection_area':'灌装区',
        'detection_date':'2026-05-02',
        'domain':'pharma',
        'domain_name':'制药工业',
        'rooms':[{
            'room_id':'r1',
            'type_id':'laminar_hood','room_name':'层流罩01','level_name':'默认','clean_class':'默认',
            'params':params,'summary':{'result_state':'合格'}
        }]
    }
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    ep=r.json()['export_payload']
    summary=ep['room']['summary']
    jr=ep.get('judgement_result') or {}
    actual=summary.get('result_state')
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'), name, 'actual=', actual, 'expected=', expected, 'engine=', summary.get('judgement_engine'), 'abnormal=', len(jr.get('abnormal_items',[])))
    return ok

if __name__=='__main__':
    assert login(), 'login failed'
    cases=[
        ('laminar_hood_风速正常', {'avg_speed':{'values':['0.45']}}, '合格'),
        ('laminar_hood_风速过低', {'avg_speed':{'values':['0.20']}}, '不合格'),
        ('laminar_hood_检漏正常', {'hepa_leak':{'values':['0.005']}}, '合格'),
        ('laminar_hood_检漏超标', {'hepa_leak':{'values':['0.05']}}, '不合格'),
        ('laminar_hood_气流正常', {'airflow_pattern':{'values':['气流垂直向下,无旋涡']}}, '合格'),
        ('laminar_hood_气流异常', {'airflow_pattern':{'values':['存在旋涡和回流']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c) for a,b,c in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
