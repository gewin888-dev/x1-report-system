#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, params, expected):
    payload={'project_name':name,'domain':'hospital','rooms':[{
        'type_id':'negative_pressure','room_name':'负压病房01','level_name':'负压病房','clean_class':'负压病房',
        'context':{'negative_pressure_mode':'ward-pressure-driven'},
        'params':params,'summary':{'result_state':'合格'}
    }]}
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    ep=r.json()['export_payload']
    summary=ep['room']['summary']
    jr=ep.get('judgement_result') or {}
    actual=summary.get('result_state')
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'), name, 'actual=', actual, 'expected=', expected, 'engine=', summary.get('judgement_engine'), 'override=', summary.get('judgement_overridden'), 'abnormal=', len(jr.get('abnormal_items',[])))
    return ok

if __name__=='__main__':
    assert login(), 'login failed'
    cases=[
        ('negative_pressure_湿度正常', {'humidity':{'values':['50']}}, '合格'),
        ('negative_pressure_湿度超标', {'humidity':{'values':['85']}}, '不合格'),
        ('negative_pressure_压差正常', {'pressure':{'values':['-8']}}, '合格'),
        ('negative_pressure_压差超标', {'pressure':{'values':['-2']}}, '不合格'),
        ('negative_pressure_换气正常', {'airchange':{'values':['12']}}, '合格'),
        ('negative_pressure_换气超标', {'airchange':{'values':['20']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c) for a,b,c in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
