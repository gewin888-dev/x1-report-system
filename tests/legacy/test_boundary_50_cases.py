#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
X1 后端判定引擎 48+ 对象/子对象/等级范围边界验证
目标：至少 48 个场景，验证 build_export 判定链是否会把明显超标值判为“不合格”。

说明：
- 仅覆盖 judgement_engine.py 当前已接入的对象类型
- 每个场景构造一个明显超界值，并故意把输入 summary.result_state 伪装成“合格”
- 通过 /api/x/build_export 走后端判定链，避免真实导出和飞书上传
- 若返回 export_payload.room.summary.result_state == 不合格，则说明后端纠偏成功
"""
import json
import requests
from collections import Counter

BASE = 'http://localhost:8082'
s = requests.Session()


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def build_room(case):
    room = {
        'room_id': case['id'],
        'room_name': case['room_name'],
        'type_id': case['type_id'],
        'type_name': case['type_id'],
        'level_name': case.get('level_name', ''),
        'clean_class': case.get('clean_class', case.get('level_name', '')),
        'params': [
            {
                'key': case['param_key'],
                'value': str(case['bad_value']),
                'result': f"{case['bad_value']}{case.get('unit','')}"
            }
        ],
        'summary': {'result_state': '合格'},
        'context': case.get('context', {}),
    }
    return room


def build_project(case):
    return {
        'project_name': f"边界批测-{case['id']}",
        'report_number': f"BOUNDARY-{case['id']}",
        'client_name': '测试客户',
        'contact_info': '测试联系人',
        'project_address': '测试地址',
        'inspection_area': '测试区域',
        'detection_date': '2026-05-01',
        'domain': case['domain'],
        'domain_name': case['domain'],
        'rooms': [build_room(case)],
    }


def submit(case):
    project = build_project(case)
    r = s.post(f'{BASE}/api/x/build_export', json={'project': project}, timeout=30)
    if r.status_code != 200:
        return {'ok': False, 'http': r.status_code, 'error': r.text[:200]}
    data = r.json()
    payload = data.get('export_payload') or {}
    room = payload.get('room') or {}
    summary = room.get('summary') or {}
    judgement_result = payload.get('judgement_result') or data.get('judgement_result') or {}
    actual = summary.get('result_state')
    engine = judgement_result.get('engine') or summary.get('judgement_engine') or ''
    abnormal_items = judgement_result.get('abnormal_items') or []
    return {
        'ok': actual == '不合格',
        'http': 200,
        'actual': actual,
        'engine': engine,
        'abnormal_count': len(abnormal_items),
    }


CASES = []

def add(case_id, domain, type_id, room_name, level_name, param_key, bad_value, unit='', context=None, clean_class=None):
    CASES.append({
        'id': case_id,
        'domain': domain,
        'type_id': type_id,
        'room_name': room_name,
        'level_name': level_name,
        'clean_class': clean_class if clean_class is not None else level_name,
        'param_key': param_key,
        'bad_value': bad_value,
        'unit': unit,
        'context': context or {},
    })

# 1-8 operating_room 主房/辅房
add('01','hospital','operating_room','百级手术室','Ⅰ级','temperature',30,'℃',{'room_type':'main-room'})
add('02','hospital','operating_room','千级手术室','Ⅱ级','humidity',80,'%',{'room_type':'main-room'})
add('03','hospital','operating_room','万级手术室','Ⅲ级','pressure',-5,'Pa',{'room_type':'main-room'})
add('04','hospital','operating_room','十万级手术室','Ⅳ级','illumination',50,'lx',{'room_type':'main-room'})
add('05','hospital','operating_room','体外循环室','Ⅰ级辅房','temperature',35,'℃',{'room_type':'洁净辅房','surgery_aux_clean_class':'Ⅰ级辅房'})
add('06','hospital','operating_room','刷手间','Ⅱ级辅房','temperature',35,'℃',{'room_type':'洁净辅房','surgery_aux_clean_class':'Ⅱ级辅房'})
add('07','hospital','operating_room','术前准备室','Ⅲ级辅房','temperature',35,'℃',{'room_type':'洁净辅房','surgery_aux_clean_class':'Ⅲ级辅房'})
add('08','hospital','operating_room','恢复室','Ⅳ级辅房','temperature',35,'℃',{'room_type':'洁净辅房','surgery_aux_clean_class':'Ⅳ级辅房'})

# 9-12 clean_function_room
add('09','hospital','clean_function_room','ICU病房','ICU病房','humidity',90,'%',{'clean_function_subroom':'ICU病房'})
add('10','hospital','clean_function_room','消毒供应中心','消毒供应中心','temperature',35,'℃',{'clean_function_subroom':'消毒供应中心'})
add('11','hospital','clean_function_room','透析室','透析室','pressure',-10,'Pa',{'clean_function_subroom':'透析室'})
add('12','hospital','clean_function_room','通用洁净功能用房','通用洁净功能用房','noise',90,'dB(A)',{'clean_function_subroom':'通用洁净功能用房'})

# 13 negative_pressure
add('13','hospital','negative_pressure','负压病房01','负压病房','humidity',85,'%',{'negative_pressure_mode':'ward-pressure-driven'})

# 14-18 bsl ISO5-9
add('14','biosafety','bsl','BSL实验室1','BSL-3（P3）','pressure',-9,'Pa',{'bsl_level':'BSL-3（P3）'})
add('15','biosafety','bsl','BSL实验室2','BSL-2（P2）','pressure',-9,'Pa',{'bsl_level':'BSL-2（P2）'})
add('16','biosafety','bsl','BSL实验室3','ISO-5','pressure',-9,'Pa',{'bsl_level':'ISO-5'})
add('17','biosafety','bsl','BSL实验室4','ISO-7','pressure',-9,'Pa',{'bsl_level':'ISO-7'})
add('18','biosafety','bsl','BSL实验室5','ISO-9','pressure',-9,'Pa',{'bsl_level':'ISO-9'})

# 19-29 animal_room 11项
add('19','biosafety','animal_room','普通动物房1','普通环境','temperature',35,'℃',{'animal_environment':'普通环境'})
add('20','biosafety','animal_room','屏障主房间1','屏障环境','humidity',90,'%',{'animal_environment':'屏障环境'})
add('21','biosafety','animal_room','洁物储存室1','屏障环境','temperature_aux',35,'℃',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'洁物储存室'})
add('22','biosafety','animal_room','灭菌后室1','屏障环境','humidity_aux',90,'%',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'灭菌后室/区'})
add('23','biosafety','animal_room','洁净走廊1','屏障环境','illumination_min',10,'lx',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'洁净走廊'})
add('24','biosafety','animal_room','污物走廊1','屏障环境','noise',90,'dB(A)',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'污物走廊'})
add('25','biosafety','animal_room','缓冲间1','屏障环境','pressure',-10,'Pa',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'缓冲间'})
add('26','biosafety','animal_room','二更1','屏障环境','temperature_aux',35,'℃',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'二更'})
add('27','biosafety','animal_room','清洗消毒室1','屏障环境','temperature_aux',35,'℃',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'清洗消毒室'})
add('28','biosafety','animal_room','一更1','屏障环境','illumination_min',10,'lx',{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'一更'})
add('29','biosafety','animal_room','隔离动物房1','隔离环境','temperature',35,'℃',{'animal_environment':'隔离环境'})

# 30-32 设备类
add('30','biosafety','bsc','BSC01','A2型','wind_speed_down',0.05,'m/s')
add('31','biosafety','clean_bench','洁净工作台1','默认','avg_speed',0.05,'m/s')
add('32','biosafety','ivc','IVC笼具1','默认','air_changes',1,'次/h')

# 33-36 gmp_workshop A-D
add('33','pharma','gmp_workshop','GMP A级','A级','pressure',-10,'Pa')
add('34','pharma','gmp_workshop','GMP B级','B级','pressure',-10,'Pa')
add('35','pharma','gmp_workshop','GMP C级','C级','pressure',-10,'Pa')
add('36','pharma','gmp_workshop','GMP D级','D级','pressure',-10,'Pa')

# 37-40 veterinary_gmp_workshop A-D
add('37','pharma','veterinary_gmp_workshop','兽药A级','A级','pressure',-10,'Pa')
add('38','pharma','veterinary_gmp_workshop','兽药B级','B级','pressure',-10,'Pa')
add('39','pharma','veterinary_gmp_workshop','兽药C级','C级','pressure',-10,'Pa')
add('40','pharma','veterinary_gmp_workshop','兽药D级','D级','pressure',-10,'Pa')

# 41-44 food_workshop I-IV
add('41','food','food_workshop','食品I级','Ⅰ级','temperature',35,'℃')
add('42','food','food_workshop','食品II级','Ⅱ级','humidity',85,'％')
add('43','food','food_workshop','食品III级','Ⅲ级','pressure',-10,'Pa')
add('44','food','food_workshop','食品IV级','Ⅳ级','noise',90,'dB(A)')

# 45-49 electronics_workshop ISO5-9
add('45','electronics','electronics_workshop','电子ISO5','ISO 5','pressure',-20,'Pa',{'iso_level':'ISO 5'})
add('46','electronics','electronics_workshop','电子ISO6','ISO 6','pressure',-20,'Pa',{'iso_level':'ISO 6'})
add('47','electronics','electronics_workshop','电子ISO7','ISO 7','pressure',-20,'Pa',{'iso_level':'ISO 7'})
add('48','electronics','electronics_workshop','电子ISO8','ISO 8','pressure',-20,'Pa',{'iso_level':'ISO 8'})
add('49','electronics','electronics_workshop','电子ISO9','ISO 9','pressure',-20,'Pa',{'iso_level':'ISO 9'})

# 50 pass_box
add('50','pharma','pass_box','传递窗01','默认','hepa_leak',1,'')


def main():
    if not login():
        print('LOGIN_FAIL')
        raise SystemExit(1)

    results = []
    for idx, case in enumerate(CASES, 1):
        ret = submit(case)
        ret['id'] = case['id']
        ret['type_id'] = case['type_id']
        ret['room_name'] = case['room_name']
        ret['level_name'] = case['level_name']
        results.append(ret)
        flag = 'PASS' if ret['ok'] else 'FAIL'
        print(f"{idx:02d}. {case['id']} {case['type_id']} / {case['room_name']} / {case['level_name']} -> {flag} actual={ret.get('actual')} engine={ret.get('engine')} abnormal={ret.get('abnormal_count')}")

    passed = sum(1 for r in results if r['ok'])
    total = len(results)
    by_type = Counter(r['type_id'] for r in results)
    by_type_pass = Counter(r['type_id'] for r in results if r['ok'])

    print(f"\nSUMMARY {passed}/{total}")
    print('BY_TYPE')
    for t in sorted(by_type):
        print(f"- {t}: {by_type_pass[t]}/{by_type[t]}")

    failed = [r for r in results if not r['ok']]
    if failed:
        print('FAILED_LIST')
        for r in failed:
            print(json.dumps(r, ensure_ascii=False))

if __name__ == '__main__':
    main()
