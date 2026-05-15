#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, level, params, expected):
    payload={'project_name':name,'domain':'food','rooms':[{
        'type_id':'food_workshop','room_name':level+'车间01','level_name':level,'clean_class':level,
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
        ('food_I_温度正常','Ⅰ级', {'temperature':{'values':['22']}}, '合格'),
        ('food_I_温度超标','Ⅰ级', {'temperature':{'values':['30']}}, '不合格'),
        ('food_II_换气正常','Ⅱ级', {'airchange':{'values':['25']}}, '合格'),
        ('food_II_换气不足','Ⅱ级', {'airchange':{'values':['10']}}, '不合格'),
        ('food_III_湿度正常','Ⅲ级', {'humidity':{'values':['60']}}, '合格'),
        ('food_III_湿度超标','Ⅲ级', {'humidity':{'values':['90']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d) for a,b,c,d in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
