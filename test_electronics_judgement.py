#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, iso, params, expected):
    payload={'project_name':name,'domain':'electronics','rooms':[{
        'type_id':'electronics_workshop','room_name':iso+'车间01','level_name':iso,'clean_class':iso,
        'context':{'iso_level':iso},
        'params':params,'summary':{'result_state':'合格'}
    }]}
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    ep=r.json()['export_payload']
    summary=ep['room']['summary']
    jr=ep.get('judgement_result') or {}
    actual=summary.get('result_state')
    ok=actual==expected
    print(('PASS' if ok else 'FAIL'), name, 'actual=', actual, 'expected=', expected, 'engine=', summary.get('judgement_engine'), 'level=', jr.get('matched_level'), 'abnormal=', len(jr.get('abnormal_items',[])))
    return ok

if __name__=='__main__':
    assert login(), 'login failed'
    cases=[
        ('ISO5_风速正常','ISO 5', {'wind_speed':{'values':['0.35']}}, '合格'),
        ('ISO5_风速超标','ISO 5', {'wind_speed':{'values':['0.10']}}, '不合格'),
        ('ISO7_换气正常','ISO 7', {'airchange':{'values':['20']}}, '合格'),
        ('ISO7_换气超标','ISO 7', {'airchange':{'values':['30']}}, '不合格'),
        ('ISO8_湿度正常','ISO 8', {'humidity':{'values':['60']}}, '合格'),
        ('ISO8_湿度超标','ISO 8', {'humidity':{'values':['80']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d) for a,b,c,d in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
