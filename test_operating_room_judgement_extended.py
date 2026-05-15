#!/usr/bin/env python3
import requests
BASE='http://localhost:8082'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def check(label, room, expected):
    payload={'domain':'hospital','project_name':label,'rooms':[room]}
    r=s.post(f'{BASE}/api/x/build_export', json={'project':payload}, timeout=30)
    ep=r.json()['export_payload']
    summary=ep['room']['summary']
    actual=summary.get('result_state')
    print(('PASS' if actual==expected else 'FAIL'), label, actual, expected, summary.get('judgement_reason'))
    return actual==expected

if __name__=='__main__':
    assert login()
    cases=[
        ('L1温度超标', {'type_id':'operating_room','room_name':'r1','level_name':'Ⅰ级（百级）','clean_class':'Ⅰ级（百级）','summary':{'result_state':'合格'},'params':{'temperature':{'values':['30']}}}, '不合格'),
        ('L2噪声超标', {'type_id':'operating_room','room_name':'r2','level_name':'Ⅱ级（千级）','clean_class':'Ⅱ级（千级）','summary':{'result_state':'合格'},'params':{'noise':{'values':['55']}}}, '不合格'),
        ('L3换气不足', {'type_id':'operating_room','room_name':'r3','level_name':'Ⅲ级（万级）','clean_class':'Ⅲ级（万级）','summary':{'result_state':'合格'},'params':{'airchange':{'values':['10']}}}, '不合格'),
        ('L4压差不足', {'type_id':'operating_room','room_name':'r4','level_name':'Ⅳ级（十万级）','clean_class':'Ⅳ级（十万级）','summary':{'result_state':'合格'},'params':{'pressure':{'values':['2']}}}, '不合格'),
        ('L2混合一项超标', {'type_id':'operating_room','room_name':'r5','level_name':'Ⅱ级（千级）','clean_class':'Ⅱ级（千级）','summary':{'result_state':'合格'},'params':{'temperature':{'values':['23']},'humidity':{'values':['75']},'noise':{'values':['45']}}}, '不合格'),
        ('L1温度正常', {'type_id':'operating_room','room_name':'r6','level_name':'Ⅰ级（百级）','clean_class':'Ⅰ级（百级）','summary':{'result_state':'不合格'},'params':{'temperature':{'values':['23']}}}, '合格'),
    ]
    passed=sum(check(a,b,c) for a,b,c in cases)
    print(f'SUMMARY {passed}/{len(cases)}')
