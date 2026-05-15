#!/usr/bin/env python3
"""边界值审计：验证 submit_export 是否会对明显超标值进行后端强判定。"""
import requests

BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def check(name, project):
    r=s.post(f'{BASE}/api/x/submit_export', json={'project': project}, timeout=60)
    if r.status_code != 200:
        return False, f'HTTP {r.status_code}'
    data=r.json()
    payload=data.get('export_payload', {})
    room=payload.get('room', {})
    summary=room.get('summary', {})
    result_state=summary.get('result_state')
    return True, result_state

CASES = [
    ('operating_room_L1_超温仍标合格', {
        'domain':'hospital','project_name':'边界测试1','rooms':[{
            'type_id':'operating_room','room_name':'百级手术室','level_name':'Ⅰ级','clean_class':'Ⅰ级',
            'context':{'room_type':'main-room','clean_class_code':'level1'},
            'params':[{'key':'temperature','value':'40','result':'40℃'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('clean_function_cssd_超湿仍标合格', {
        'domain':'hospital','project_name':'边界测试2','rooms':[{
            'type_id':'clean_function_room','room_name':'消毒供应中心','level_name':'消毒供应中心','clean_class':'消毒供应中心',
            'context':{'clean_function_subroom':'消毒供应中心'},
            'params':[{'key':'humidity','value':'90','result':'90%'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('negative_pressure_超湿仍标合格', {
        'domain':'hospital','project_name':'边界测试3','rooms':[{
            'type_id':'negative_pressure','room_name':'负压病房01','level_name':'负压病房','clean_class':'负压病房',
            'context':{'negative_pressure_mode':'ward-pressure-driven'},
            'params':[{'key':'humidity','value':'85','result':'85%'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('animal_room_隔离环境超温仍标合格', {
        'domain':'biosafety','project_name':'边界测试4','rooms':[{
            'type_id':'animal_room','room_name':'隔离环境01','level_name':'隔离环境','clean_class':'隔离环境',
            'context':{'animal_environment':'隔离环境','barrier_room_class':'饲养室'},
            'params':[{'key':'temperature','value':'35','result':'35℃'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('bsc_超低风速仍标合格', {
        'domain':'biosafety','project_name':'边界测试5','rooms':[{
            'type_id':'bsc','room_name':'BSC01','level_name':'A2型','clean_class':'A2型',
            'params':[{'key':'wind_speed_down','value':'0.05','result':'0.05m/s'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('gmp_A_超温仍标合格', {
        'domain':'pharma','project_name':'边界测试6','rooms':[{
            'type_id':'gmp_workshop','room_name':'GMP A级','level_name':'A级','clean_class':'A级',
            'params':[{'key':'temperature','value':'40','result':'40℃'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('veterinary_gmp_D_超温仍标合格', {
        'domain':'pharma','project_name':'边界测试7','rooms':[{
            'type_id':'veterinary_gmp_workshop','room_name':'兽药D级','level_name':'D级','clean_class':'D级',
            'params':[{'key':'temperature','value':'40','result':'40℃'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('food_workshop_III_超温仍标合格', {
        'domain':'food','project_name':'边界测试8','rooms':[{
            'type_id':'food_workshop','room_name':'食品Ⅲ级','level_name':'Ⅲ级','clean_class':'Ⅲ级',
            'params':[{'key':'temperature','value':'40','result':'40℃'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('electronics_ISO7_超压差仍标合格', {
        'domain':'electronics','project_name':'边界测试9','rooms':[{
            'type_id':'electronics_workshop','room_name':'电子ISO7','level_name':'ISO 7','clean_class':'ISO 7',
            'context':{'iso_level':'ISO 7'},
            'params':[{'key':'pressure','value':'-20','result':'-20Pa'}],
            'summary':{'result_state':'合格'}
        }]
    }),
    ('pass_box_异常结果仍标合格', {
        'domain':'pharma','project_name':'边界测试10','rooms':[{
            'type_id':'pass_box','room_name':'传递窗01',
            'params':[{'key':'hepa_leak','value':'','result':'发现泄漏'}],
            'summary':{'result_state':'合格'}
        }]
    }),
]

if __name__=='__main__':
    if not login():
        print('LOGIN_FAIL')
        raise SystemExit(1)
    suspicious=[]
    for name, project in CASES:
        ok, result = check(name, project)
        print(name, '->', result if ok else f'FAIL {result}')
        if ok and result == '合格':
            suspicious.append(name)
    print(f'SUMMARY suspicious_pass_through={len(suspicious)}/{len(CASES)}')
    for x in suspicious:
        print('SUSPECT', x)
