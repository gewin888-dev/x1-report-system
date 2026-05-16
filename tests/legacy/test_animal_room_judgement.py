#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def run_case(name, context, params, expected):
    payload={'project_name':name,'domain':'biosafety','rooms':[{
        'type_id':'animal_room','room_name':name,'level_name':context.get('animal_environment',''), 'clean_class':context.get('animal_environment',''),
        'context':context,
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
        ('animal_normal_温度正常', {'animal_environment':'普通环境'}, {'temperature':{'values':['23']}}, '合格'),
        ('animal_normal_温度超标', {'animal_environment':'普通环境'}, {'temperature':{'values':['35']}}, '不合格'),
        ('animal_barrier_压差正常', {'animal_environment':'屏障环境','barrier_room_class':'饲养室'}, {'pressure':{'values':['12']}}, '合格'),
        ('animal_barrier_压差不足', {'animal_environment':'屏障环境','barrier_room_class':'饲养室'}, {'pressure':{'values':['2']}}, '不合格'),
        ('animal_aux_洁净走廊_温度正常', {'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'洁净走廊'}, {'temperature_aux':{'values':['24']}}, '合格'),
        ('animal_aux_洁净走廊_温度超标', {'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'洁净走廊'}, {'temperature_aux':{'values':['35']}}, '不合格'),
        ('animal_isolation_湿度正常', {'animal_environment':'隔离环境'}, {'humidity':{'values':['50']}}, '合格'),
        ('animal_isolation_湿度超标', {'animal_environment':'隔离环境'}, {'humidity':{'values':['90']}}, '不合格'),
    ]
    passed=sum(run_case(a,b,c,d) for a,b,c,d in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
