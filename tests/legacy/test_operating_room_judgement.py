#!/usr/bin/env python3
import requests

BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, temp, expected):
    payload = {
        'project_name': name,
        'domain':'hospital',
        'rooms':[{
            'type_id':'operating_room',
            'room_name':'手术室01',
            'level_name':'Ⅰ级',
            'clean_class':'Ⅰ级',
            'context':{'room_type':'main-room','clean_class_code':'level1'},
            'params':[{'key':'temperature','value':str(temp),'result':f'{temp}℃'}],
            'summary':{'result_state':'合格'}
        }]
    }
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    data=r.json()['export_payload']
    summary=data['room']['summary']
    jr=data.get('judgement_result') or {}
    actual=summary.get('result_state')
    ok=(actual==expected)
    print(('PASS' if ok else 'FAIL'), name, 'actual=', actual, 'expected=', expected, 'engine=', summary.get('judgement_engine'), 'override=', summary.get('judgement_overridden'), 'reason=', summary.get('judgement_reason'), 'abnormal=', len(jr.get('abnormal_items',[])))
    return ok

if __name__=='__main__':
    assert login(), 'login failed'
    total=2
    passed=0
    passed += run_case('operating_room_正常温度', 23, '合格')
    passed += run_case('operating_room_超标温度', 40, '不合格')
    print(f'SUMMARY {passed}/{total}')
