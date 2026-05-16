#!/usr/bin/env python3
"""参数级回填闭环验证：保存草稿 -> /api/get -> 逐参数比对。"""
import json
import time
from pathlib import Path

import requests

BASE = 'http://127.0.0.1:8082'
ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
REPORT_DIR = ROOT / 'reports_x1'
OUT_TS = time.strftime('%Y%m%d_%H%M%S')
OUT_JSON = REPORT_DIR / f'param_restore_loop_{OUT_TS}.json'


def login(session):
    r = session.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=False, timeout=20)
    return r.status_code in (200, 302)


def P(key, input_type, values=None, result='', value='', data=None, **extra):
    item = {'key': key, 'inputType': input_type}
    if values is not None:
        item['values'] = values
    if result != '':
        item['result'] = result
    if value != '':
        item['value'] = value
    if data is not None:
        item['data'] = data
    item.update(extra)
    return item


CASES = [
    {
        'name': 'operating_room_single_main',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_OR_MAIN',
            'project_name': 'param_restore_or_main',
            'client_name': 'test',
            'project_address': 'addr',
            'report_number': 'PR-OR-001',
            'detection_date': '2026-05-12',
            'domain': 'hospital',
            'rooms': [{
                'room_id': 'R1', 'room_name': '百级手术室', 'type_id': 'operating_room', 'type_name': '手术室',
                'clean_class': 'Ⅰ级（百级）', 'level_name': 'Ⅰ级（百级）', 'surgery_room_type': '手术室',
                'context': {'surgery_room_type': '手术室'},
                'params': [
                    P('temperature', 'numeric', values=['22'], result='合格', value='22', data={'total': '22'}),
                    P('humidity', 'numeric', values=['55'], result='合格', value='55', data={'total': '55'}),
                    P('noise', 'numeric', values=['58'], result='合格', value='58', data={'total': '58'}),
                    P('work_illumination', 'numeric', values=['350'], result='合格', value='350', data={'total': '350'}),
                ]
            }]
        }
    },
    {
        'name': 'operating_room_multi_mix',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_OR_MULTI',
            'project_name': 'param_restore_or_multi',
            'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-OR-002', 'detection_date': '2026-05-12', 'domain': 'hospital',
            'rooms': [
                {
                    'room_id': 'R1', 'room_name': '刷手间', 'type_id': 'operating_room', 'type_name': '手术室',
                    'clean_class': 'Ⅱ级（7级）', 'level_name': 'Ⅱ级（7级）', 'surgery_room_type': '洁净辅房', 'surgery_aux_room': '刷手间', 'surgery_aux_clean_class': 'Ⅱ级（7级）',
                    'context': {'surgery_room_type': '洁净辅房', 'surgery_aux_room': '刷手间', 'surgery_aux_clean_class': 'Ⅱ级（7级）'},
                    'params': [P('temperature', 'numeric', values=['21'], result='合格', value='21', data={'total': '21'}), P('noise', 'numeric', values=['60'], result='合格', value='60', data={'total': '60'})]
                },
                {
                    'room_id': 'R2', 'room_name': '万级手术室', 'type_id': 'operating_room', 'type_name': '手术室',
                    'clean_class': 'Ⅲ级（万级）', 'level_name': 'Ⅲ级（万级）', 'surgery_room_type': '手术室',
                    'context': {'surgery_room_type': '手术室'},
                    'params': [P('temperature', 'numeric', values=['23'], result='合格', value='23', data={'total': '23'}), P('humidity', 'numeric', values=['52'], result='合格', value='52', data={'total': '52'})]
                }
            ]
        }
    },
    {
        'name': 'clean_function_room_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_CFR_SINGLE',
            'project_name': 'param_restore_cfr_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-CFR-001', 'detection_date': '2026-05-12', 'domain': 'hospital',
            'rooms': [{
                'room_id': 'R1', 'room_name': 'ICU病房1', 'type_id': 'clean_function_room', 'type_name': '洁净功能用房',
                'clean_class': 'Ⅲ级（万级）', 'level_name': 'Ⅲ级（万级）', 'clean_function_subroom': 'ICU病房',
                'context': {'clean_function_subroom': 'ICU病房'},
                'params': [P('temperature', 'numeric', values=['24'], result='合格', value='24', data={'total': '24'}), P('humidity', 'numeric', values=['50'], result='合格', value='50', data={'total': '50'})]
            }]
        }
    },
    {
        'name': 'clean_function_room_multi',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_CFR_MULTI',
            'project_name': 'param_restore_cfr_multi', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-CFR-002', 'detection_date': '2026-05-12', 'domain': 'hospital',
            'rooms': [
                {'room_id': 'R1', 'room_name': 'ICU病房1', 'type_id': 'clean_function_room', 'type_name': '洁净功能用房', 'clean_class': 'Ⅲ级（万级）', 'level_name': 'Ⅲ级（万级）', 'clean_function_subroom': 'ICU病房', 'context': {'clean_function_subroom': 'ICU病房'}, 'params': [P('temperature', 'numeric', values=['24'], result='合格', value='24', data={'total': '24'})]},
                {'room_id': 'R2', 'room_name': '透析室1', 'type_id': 'clean_function_room', 'type_name': '洁净功能用房', 'clean_class': 'Ⅳ级（十万级）', 'level_name': 'Ⅳ级（十万级）', 'clean_function_subroom': '透析室', 'context': {'clean_function_subroom': '透析室'}, 'params': [P('humidity', 'numeric', values=['48'], result='合格', value='48', data={'total': '48'})]}
            ]
        }
    },
    {
        'name': 'animal_room_single_barrier_aux',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_ANIMAL_SINGLE',
            'project_name': 'param_restore_animal_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-AN-001', 'detection_date': '2026-05-12', 'domain': 'biosafety',
            'rooms': [{
                'room_id': 'R1', 'room_name': '传递间A', 'type_id': 'animal_room', 'type_name': '动物房', 'clean_class': '屏障环境', 'level_name': '屏障环境',
                'barrier_room_class': '洁净辅房', 'barrier_aux_room': '传递间',
                'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '传递间'},
                'params': [P('temperature', 'numeric', values=['23'], result='合格', value='23', data={'total': '23'}), P('animal_illumination', 'numeric_range_manual', values=['200'], result='合格', value='200', manualMin='150', manualMax='300', manualRange='150~300', data={'total': '200'})]
            }]
        }
    },
    {
        'name': 'animal_room_multi_mix',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_ANIMAL_MULTI',
            'project_name': 'param_restore_animal_multi', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-AN-002', 'detection_date': '2026-05-12', 'domain': 'biosafety',
            'rooms': [
                {'room_id': 'R1', 'room_name': '主房间A', 'type_id': 'animal_room', 'type_name': '动物房', 'clean_class': '屏障环境', 'level_name': '屏障环境', 'barrier_room_class': '主房间', 'context': {'animal_environment': '屏障环境', 'barrier_room_class': '主房间'}, 'params': [P('temperature', 'numeric', values=['22'], result='合格', value='22', data={'total': '22'})]},
                {'room_id': 'R2', 'room_name': '缓冲间A', 'type_id': 'animal_room', 'type_name': '动物房', 'clean_class': '屏障环境', 'level_name': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '缓冲间', 'context': {'animal_environment': '屏障环境', 'barrier_room_class': '洁净辅房', 'barrier_aux_room': '缓冲间'}, 'params': [P('humidity', 'numeric', values=['51'], result='合格', value='51', data={'total': '51'})]}
            ]
        }
    },
    {
        'name': 'bsl_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_BSL_SINGLE',
            'project_name': 'param_restore_bsl_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-BSL-001', 'detection_date': '2026-05-12', 'domain': 'biosafety',
            'rooms': [{
                'room_id': 'R1', 'room_name': 'P2实验室', 'type_id': 'bsl', 'type_name': '实验室', 'clean_class': 'ISO 7', 'level_name': 'BSL-2（P2）', 'bsl': 'BSL-2（P2）',
                'context': {'bsl_level': 'BSL-2（P2）'},
                'params': [P('pressure', 'numeric', values=['-12'], result='合格', value='-12', data={'total': '-12'}, primarySummary='走廊:-12.0 Pa[数据库:-10~-15]')]
            }]
        }
    },
    {
        'name': 'pass_box_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_PASSBOX_SINGLE',
            'project_name': 'param_restore_passbox_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-PB-001', 'detection_date': '2026-05-12', 'domain': 'pharma',
            'rooms': [{
                'room_id': 'R1', 'room_name': '传递窗01', 'type_id': 'pass_box', 'type_name': '传递窗', 'clean_class': '无等级要求', 'level_name': '无等级要求',
                'context': {},
                'params': [P('noise', 'numeric', values=['66'], result='合格', value='66', data={'total': '66'}), P('hepa_leak', 'numeric', values=['0.01'], result='合格', value='0.01', data={'total': '0.01'})],
                'hepa_leak_summary': '过滤器1:0.01', 'pass_box_result_state': '合格'
            }]
        }
    },
    {
        'name': 'electronics_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_ELEC_SINGLE',
            'project_name': 'param_restore_elec_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-ELEC-001', 'detection_date': '2026-05-12', 'domain': 'electronics',
            'rooms': [{
                'room_id': 'R1', 'room_name': '电子车间A', 'type_id': 'electronics_workshop', 'type_name': '洁净车间', 'clean_class': 'ISO 6', 'level_name': 'ISO 6',
                'context': {'iso_level': 'ISO 6'},
                'electronics_manual_range_keys': ['temperature'],
                'params': [P('temperature', 'numeric', values=['22'], result='合格', value='22', data={'total': '22'}), P('humidity', 'numeric', values=['45'], result='合格', value='45', data={'total': '45'})]
            }]
        }
    },
    {
        'name': 'negative_pressure_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_NP_SINGLE',
            'project_name': 'param_restore_np_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-NP-001', 'detection_date': '2026-05-12', 'domain': 'hospital',
            'rooms': [{
                'room_id': 'R1', 'room_name': '负压病房A', 'type_id': 'negative_pressure', 'type_name': '负压病房', 'clean_class': '无洁净等级要求', 'level_name': '无洁净等级要求',
                'context': {},
                'params': [P('temperature', 'numeric', values=['24'], result='合格', value='24', data={'total': '24'}), P('pressure', 'numeric', values=['-12'], result='合格', value='-12', data={'total': '-12'})]
            }]
        }
    },
    {
        'name': 'gmp_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_GMP_SINGLE',
            'project_name': 'param_restore_gmp_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-GMP-001', 'detection_date': '2026-05-12', 'domain': 'pharma',
            'rooms': [{
                'room_id': 'R1', 'room_name': 'GMP C级间', 'type_id': 'gmp_workshop', 'type_name': 'GMP车间', 'clean_class': 'C级', 'level_name': 'C级',
                'context': {'gmp_grade': 'C级'},
                'params': [P('temperature', 'numeric', values=['23'], result='合格', value='23', data={'total': '23'}), P('humidity', 'numeric', values=['50'], result='合格', value='50', data={'total': '50'})]
            }]
        }
    },
    {
        'name': 'vet_gmp_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_VET_GMP_SINGLE',
            'project_name': 'param_restore_vet_gmp_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-VGMP-001', 'detection_date': '2026-05-12', 'domain': 'pharma',
            'rooms': [{
                'room_id': 'R1', 'room_name': '兽药A级间', 'type_id': 'veterinary_gmp_workshop', 'type_name': '兽药车间', 'clean_class': 'A级', 'level_name': 'A级',
                'context': {'gmp_grade': 'A级'},
                'params': [P('temperature', 'numeric', values=['22'], result='合格', value='22', data={'total': '22'}), P('humidity', 'numeric', values=['48'], result='合格', value='48', data={'total': '48'})]
            }]
        }
    },
    {
        'name': 'laminar_hood_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_LH_SINGLE',
            'project_name': 'param_restore_lh_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-LH-001', 'detection_date': '2026-05-12', 'domain': 'pharma',
            'rooms': [{
                'room_id': 'R1', 'room_name': '层流罩A', 'type_id': 'laminar_hood', 'type_name': '层流罩', 'clean_class': '无等级要求', 'level_name': '无等级要求',
                'context': {'business_domain_hint': 'pharma'},
                'hepa_leak_summary': '过滤器1:0.01',
                'params': [P('noise', 'numeric', values=['62'], result='合格', value='62', data={'total': '62'}), P('hepa_leak', 'numeric', values=['0.01'], result='合格', value='0.01', data={'total': '0.01'})]
            }]
        }
    },
    {
        'name': 'bsc_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_BSC_SINGLE',
            'project_name': 'param_restore_bsc_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-BSC-001', 'detection_date': '2026-05-12', 'domain': 'biosafety',
            'rooms': [{
                'room_id': 'R1', 'room_name': 'BSC-A', 'type_id': 'bsc', 'type_name': '生物安全柜', 'clean_class': '无等级要求', 'level_name': '无等级要求',
                'context': {},
                'params': [P('noise', 'numeric', values=['60'], result='合格', value='60', data={'total': '60'}), P('work_illumination', 'numeric', values=['320'], result='合格', value='320', data={'total': '320'})]
            }]
        }
    },
    {
        'name': 'clean_bench_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_CB_SINGLE',
            'project_name': 'param_restore_cb_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-CB-001', 'detection_date': '2026-05-12', 'domain': 'biosafety',
            'rooms': [{
                'room_id': 'R1', 'room_name': '洁净工作台A', 'type_id': 'clean_bench', 'type_name': '洁净工作台', 'clean_class': '无等级要求', 'level_name': '无等级要求',
                'context': {},
                'params': [P('noise', 'numeric', values=['58'], result='合格', value='58', data={'total': '58'}), P('work_illumination', 'numeric', values=['300'], result='合格', value='300', data={'total': '300'})]
            }]
        }
    },
    {
        'name': 'ivc_single',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_IVC_SINGLE',
            'project_name': 'param_restore_ivc_single', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-IVC-001', 'detection_date': '2026-05-12', 'domain': 'biosafety',
            'rooms': [{
                'room_id': 'R1', 'room_name': 'IVC-A', 'type_id': 'ivc', 'type_name': 'IVC笼具', 'clean_class': '默认', 'level_name': '默认', 'length': '4', 'width': '3', 'height': '2.8',
                'context': {},
                'params': [P('temperature', 'numeric', values=['22'], result='合格', value='22', data={'total': '22'}), P('airchange', 'airchange_speed', result='合格', value='403.2', vents=[{'area':'0.20','speed':'0.56','volume':'403.2'}])]
            }]
        }
    },
    {
        'name': 'food_multi',
        'payload': {
            'draft_id': 'X1DRAFT_PARAM_RESTORE_FOOD_MULTI',
            'project_name': 'param_restore_food_multi', 'client_name': 'test', 'project_address': 'addr', 'report_number': 'PR-FOOD-001', 'detection_date': '2026-05-12', 'domain': 'food',
            'rooms': [
                {'room_id': 'R1', 'room_name': '百级车间', 'type_id': 'food_workshop', 'type_name': '食品洁净车间', 'clean_class': 'Ⅰ级（百级）', 'level_name': 'Ⅰ级（百级）', 'context': {'food_grade': 'Ⅰ级（百级）'}, 'params': [P('temperature', 'numeric', values=['20'], result='合格', value='20', data={'total': '20'})]},
                {'room_id': 'R2', 'room_name': '万级车间', 'type_id': 'food_workshop', 'type_name': '食品洁净车间', 'clean_class': 'Ⅲ级（万级）', 'level_name': 'Ⅲ级（万级）', 'context': {'food_grade': 'Ⅲ级（万级）'}, 'params': [P('humidity', 'numeric', values=['52'], result='合格', value='52', data={'total': '52'})]}
            ]
        }
    }
]


def canonical_param_map(room):
    out = {}
    params = room.get('params') or []
    if isinstance(params, dict):
        for k, v in params.items():
            out[k] = v
        return out
    for item in params:
        if isinstance(item, dict) and item.get('key'):
            out[item['key']] = item
    return out


def room_context(room):
    ctx = dict(room.get('context') or {})
    for key in ['surgery_room_type', 'surgery_aux_room', 'surgery_aux_clean_class', 'clean_function_subroom', 'barrier_room_class', 'barrier_aux_room', 'bsl', 'clean_class', 'level_name']:
        if room.get(key) is not None and room.get(key) != '':
            ctx[key] = room.get(key)
    return ctx


def compare_case(saved_payload, loaded_record):
    expected_rooms = saved_payload.get('rooms') or []
    actual_rooms = loaded_record.get('rooms') or []
    checks = []
    checks.append({'name': 'room_count', 'ok': len(expected_rooms) == len(actual_rooms), 'expected': len(expected_rooms), 'actual': len(actual_rooms)})
    for idx, exp_room in enumerate(expected_rooms):
        act_room = actual_rooms[idx] if idx < len(actual_rooms) else {}
        checks.append({'name': f'room_{idx+1}_type', 'ok': exp_room.get('type_id') == act_room.get('type_id'), 'expected': exp_room.get('type_id'), 'actual': act_room.get('type_id')})
        checks.append({'name': f'room_{idx+1}_clean_class', 'ok': exp_room.get('clean_class') == act_room.get('clean_class'), 'expected': exp_room.get('clean_class'), 'actual': act_room.get('clean_class')})
        exp_ctx = room_context(exp_room)
        act_ctx = room_context(act_room)
        for key, exp_val in exp_ctx.items():
            checks.append({'name': f'room_{idx+1}_ctx_{key}', 'ok': act_ctx.get(key) == exp_val, 'expected': exp_val, 'actual': act_ctx.get(key)})
        exp_params = canonical_param_map(exp_room)
        act_params = canonical_param_map(act_room)
        for key, exp_param in exp_params.items():
            act_param = act_params.get(key) or {}
            checks.append({'name': f'room_{idx+1}_param_{key}_exists', 'ok': key in act_params, 'expected': True, 'actual': key in act_params})
            for field in ['inputType', 'result', 'value', 'manualMin', 'manualMax', 'manualRange', 'primarySummary']:
                if field in exp_param:
                    checks.append({'name': f'room_{idx+1}_param_{key}_{field}', 'ok': act_param.get(field) == exp_param.get(field), 'expected': exp_param.get(field), 'actual': act_param.get(field)})
            if 'values' in exp_param:
                checks.append({'name': f'room_{idx+1}_param_{key}_values', 'ok': (act_param.get('values') or []) == (exp_param.get('values') or []), 'expected': exp_param.get('values') or [], 'actual': act_param.get('values') or []})
            if 'data' in exp_param:
                checks.append({'name': f'room_{idx+1}_param_{key}_data_total', 'ok': (act_param.get('data') or {}).get('total') == (exp_param.get('data') or {}).get('total'), 'expected': (exp_param.get('data') or {}).get('total'), 'actual': (act_param.get('data') or {}).get('total')})
        if exp_room.get('hepa_leak_summary') is not None:
            checks.append({'name': f'room_{idx+1}_hepa_leak_summary', 'ok': act_room.get('hepa_leak_summary') == exp_room.get('hepa_leak_summary'), 'expected': exp_room.get('hepa_leak_summary'), 'actual': act_room.get('hepa_leak_summary')})
        if exp_room.get('pass_box_result_state') is not None:
            checks.append({'name': f'room_{idx+1}_pass_box_result_state', 'ok': act_room.get('pass_box_result_state') == exp_room.get('pass_box_result_state'), 'expected': exp_room.get('pass_box_result_state'), 'actual': act_room.get('pass_box_result_state')})
        if exp_room.get('electronics_manual_range_keys') is not None:
            checks.append({'name': f'room_{idx+1}_electronics_manual_range_keys', 'ok': (act_room.get('electronics_manual_range_keys') or []) == (exp_room.get('electronics_manual_range_keys') or []), 'expected': exp_room.get('electronics_manual_range_keys') or [], 'actual': act_room.get('electronics_manual_range_keys') or []})
    return checks


def main():
    s = requests.Session()
    assert login(s), 'login failed'
    results = []
    for case in CASES:
        payload = case['payload']
        wrapped = {'project': payload}
        save_res = s.post(f'{BASE}/api/x/save_draft', json=wrapped, timeout=30)
        save_body = save_res.json()
        draft_id = save_body.get('draft_id') or payload['draft_id']
        load_res = s.get(f'{BASE}/api/get/{draft_id}', timeout=30)
        load_body = load_res.json()
        loaded = load_body.get('record') or {}
        checks = compare_case(payload, loaded)
        ok = all(c['ok'] for c in checks)
        results.append({'name': case['name'], 'draft_id': draft_id, 'save_status': save_res.status_code, 'load_status': load_res.status_code, 'ok': ok, 'check_count': len(checks), 'failed_checks': [c for c in checks if not c['ok']], 'passed_checks': sum(1 for c in checks if c['ok'])})
    report = {'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'), 'summary': {'total_cases': len(results), 'passed_cases': sum(1 for r in results if r['ok']), 'total_checks': sum(r['check_count'] for r in results), 'failed_checks': sum(len(r['failed_checks']) for r in results)}, 'results': results}
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'out': str(OUT_JSON), 'summary': report['summary']}, ensure_ascii=False))
    if report['summary']['failed_checks']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
