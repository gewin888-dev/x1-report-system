#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, params, expected):
    payload={'project_name':name,'domain':'biosafety','rooms':[{
        'type_id':'bsc','room_name':'BSC01','level_name':'A2型','clean_class':'A2型',
        'params':params,'summary':{'result_state':'合格'}
    }]}
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
        ('bsc_下降气流正常', {'wind_speed_down':{'values':['0.35']}}, '合格'),
        ('bsc_下降气流超标', {'wind_speed_down':{'values':['0.10']}}, '不合格'),
        ('bsc_噪声正常', {'noise':{'values':['60']}}, '合格'),
        ('bsc_噪声超标', {'noise':{'values':['80']}}, '不合格'),
        ('bsc_照度正常', {'illumination':{'values':['700']}}, '合格'),
        ('bsc_照度不足', {'illumination':{'values':['300']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c) for a,b,c in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
