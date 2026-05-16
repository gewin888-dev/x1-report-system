#!/usr/bin/env python3
"""judgement_engine 专项回归：修复粒子/细菌多区域判定后的防回退验证"""
import sys
sys.path.insert(0, '/Users/fuwuqi/检测报告生成系统_X1')
from judgement_engine import judge_room


def assert_true(name, cond):
    if cond:
        print(f'✅ {name}')
        return 1, 1, []
    print(f'❌ {name}')
    return 0, 1, [name]


def main():
    passed = total = 0
    fails = []
    project = {}

    # 1. 手术室百级：手术区/周边区粒子 + 细菌必须参与判定，超标必须不合格
    room = {
        'type_id': 'operating_room',
        'level_name': 'Ⅰ级（百级）',
        'clean_class': 'Ⅰ级（百级）',
        'room_name': '1#手术室',
        'context': {'surgery_room_type': '手术室'},
        'params': {
            'particle': {'type': 'particle_4', 'data': {
                'op_05_max': '999999', 'op_5_max': '1',
                'surr_05_max': '999999', 'surr_5_max': '9999'
            }},
            'bacteria': {'type': 'bacteria_control', 'data': {
                'op_values': ['1.0'], 'surr_values': ['0.5']
            }},
            'temperature': {'values': [23]}
        }
    }
    res = judge_room(project, room)
    p, t, f = assert_true('OR百级超标应判不合格', res is not None and res['result_state'] == '不合格')
    passed += p; total += t; fails += f
    abnormal_keys = sorted([x['key'] for x in (res or {}).get('abnormal_items', [])])
    for key in ['particle.op_05_max', 'particle.surr_05_max', 'particle.surr_5_max', 'bacteria.op', 'bacteria.surr']:
        p, t, f = assert_true(f'OR百级异常项包含 {key}', key in abnormal_keys)
        passed += p; total += t; fails += f

    # 2. 手术室百级：全部合规应判合格
    room_ok = {
        'type_id': 'operating_room',
        'level_name': 'Ⅰ级（百级）',
        'clean_class': 'Ⅰ级（百级）',
        'room_name': '2#手术室',
        'context': {'surgery_room_type': '手术室'},
        'params': {
            'particle': {'type': 'particle_4', 'data': {
                'op_05_max': '2800', 'op_5_max': '0',
                'surr_05_max': '30000', 'surr_5_max': '200'
            }},
            'bacteria': {'type': 'bacteria_control', 'data': {
                'op_values': ['0.1'], 'surr_values': ['0.2']
            }},
            'temperature': {'values': [23]}
        }
    }
    res = judge_room(project, room_ok)
    p, t, f = assert_true('OR百级合规应判合格', res is not None and res['result_state'] == '合格')
    passed += p; total += t; fails += f

    # 3. 电子车间 ISO5：复合粒子标准不能再误判为“≥0.5就合格”
    room = {
        'type_id': 'electronics_workshop',
        'level_name': 'ISO 5',
        'clean_class': 'ISO 5',
        'context': {'iso_level': 'ISO 5'},
        'params': {
            'particle': {'type': 'particle_4', 'data': {'p05_max': '500000', 'p5_max': '1000'}},
            'temperature': {'values': [23]}
        }
    }
    res = judge_room(project, room)
    p, t, f = assert_true('electronics ISO5 粒子超标应判不合格', res is not None and res['result_state'] == '不合格')
    passed += p; total += t; fails += f
    abnormal_keys = sorted([x['key'] for x in (res or {}).get('abnormal_items', [])])
    for key in ['particle.p05_max', 'particle.p5_max']:
        p, t, f = assert_true(f'electronics 异常项包含 {key}', key in abnormal_keys)
        passed += p; total += t; fails += f

    # 4. 电子车间 ISO5：合规粒子应判合格
    room = {
        'type_id': 'electronics_workshop',
        'level_name': 'ISO 5',
        'clean_class': 'ISO 5',
        'context': {'iso_level': 'ISO 5'},
        'params': {
            'particle': {'type': 'particle_4', 'data': {'p05_max': '3000', 'p5_max': '20'}},
            'temperature': {'values': [23]}
        }
    }
    res = judge_room(project, room)
    p, t, f = assert_true('electronics ISO5 粒子合规应判合格', res is not None and res['result_state'] == '合格')
    passed += p; total += t; fails += f

    # 5. BSL ISO-6 湿度：修复 30-70 分隔符后应正常参与判定
    room = {
        'type_id': 'bsl',
        'level_name': 'BSL-2（P2）',
        'clean_class': 'BSL-2（P2）',
        'context': {'bsl_level': 'BSL-2（P2）'},
        'params': {
            'humidity': {'values': [80]},
            'temperature': {'values': [24]}
        }
    }
    res = judge_room(project, room)
    p, t, f = assert_true('BSL P2 湿度80应判不合格', res is not None and res['result_state'] == '不合格')
    passed += p; total += t; fails += f
    abnormal_keys = sorted([x['standard_key'] for x in (res or {}).get('abnormal_items', [])])
    p, t, f = assert_true('BSL P2 异常项包含 humidity', 'humidity' in abnormal_keys)
    passed += p; total += t; fails += f

    # 6. 眼科手术室：必须走 eye_operating_room 标准，不是普通手术室标准
    room = {
        'type_id': 'operating_room',
        'level_name': 'Ⅰ级（百级）',
        'clean_class': 'Ⅰ级（百级）',
        'room_name': '眼科1',
        'context': {'surgery_room_type': '眼科手术室'},
        'params': {
            'particle_door': {'type': 'particle_4', 'data': {'p05_max': '300000', 'p5_max': '2000'}},
            'temperature': {'values': [23]}
        }
    }
    res = judge_room(project, room)
    p, t, f = assert_true('眼科手术室应能被判定', res is not None and res.get('room_branch') == 'eye-operating-room')
    passed += p; total += t; fails += f

    print(f'\nSUMMARY {passed}/{total}')
    if fails:
        print('FAILURES:')
        for x in fails:
            print(' -', x)
        raise SystemExit(1)


if __name__ == '__main__':
    main()
