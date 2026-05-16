#!/usr/bin/env python3
import json
import sys
from pathlib import Path

BASE = Path('/Users/fuwuqi/检测报告生成系统_X1')
sys.path.insert(0, str(BASE))

from app_x1 import app, _x_draft_path, _x_export_path  # noqa: E402

CASES = [
    {
        'name': 'electronics_iso6',
        'draft_id': 'X1DRAFT_CONSIST_ELECTRONICS_ISO6',
        'payload': {
            'draft_id': 'X1DRAFT_CONSIST_ELECTRONICS_ISO6',
            'project_name': '一致性专项-electronics-ISO6',
            'report_number': 'CONSIST-E-001',
            'client_name': '一致性测试单位',
            'contact_info': '13800000000',
            'project_address': '上海市测试路1号',
            'inspection_area': '电子车间A',
            'detection_date': '2026-05-04',
            'domain': 'electronics',
            'domain_name': '电子工业',
            'rooms': [{
                'room_id': 'R1',
                'room_name': '电子车间1',
                'type_id': 'electronics_workshop',
                'type_name': '洁净车间',
                'clean_class': 'ISO 6',
                'context': {'iso_level': 'ISO 6'},
                'summary': {
                    'result_state': '不合格',
                    'input_result_state': '合格',
                    'judgement_engine': 'electronics_workshop_v1',
                    'judgement_reason': '一致性测试',
                    'judgement_overridden': True,
                    'abnormal_items': [{'item_name': '压差', 'result': '不合格'}]
                },
                'params': {
                    'pressure': {
                        'pairs': [{'refRoom': '相对房间1', 'range': '≥5', 'values': ['3']}],
                        'primarySummary': '相对房间1:3.0 Pa[数据库:≥5]',
                        'result': '不合格'
                    }
                }
            }]
        },
        'expect': {
            'type_id': 'electronics_workshop',
            'clean_class': 'ISO 6',
            'context_key': 'iso_level',
            'context_value': 'ISO 6',
        }
    },
    {
        'name': 'bsl_iso7_p2',
        'draft_id': 'X1DRAFT_CONSIST_BSL_ISO7',
        'payload': {
            'draft_id': 'X1DRAFT_CONSIST_BSL_ISO7',
            'project_name': '一致性专项-bsl-ISO7',
            'report_number': 'CONSIST-BSL-001',
            'client_name': '一致性测试单位',
            'contact_info': '13800000000',
            'project_address': '上海市测试路2号',
            'inspection_area': 'P2实验室',
            'detection_date': '2026-05-04',
            'domain': 'biosafety',
            'domain_name': '生物安全',
            'rooms': [{
                'room_id': 'R1',
                'room_name': 'P2实验室1',
                'type_id': 'bsl',
                'type_name': '实验室',
                'clean_class': 'ISO 7',
                'bsl': 'BSL-2（P2）',
                'context': {'bsl_level': 'BSL-2（P2）'},
                'summary': {
                    'result_state': '不合格',
                    'input_result_state': '合格',
                    'judgement_engine': 'bsl_v1',
                    'judgement_reason': '一致性测试',
                    'judgement_overridden': True,
                    'abnormal_items': [{'item_name': '温度', 'result': '不合格'}]
                },
                'params': {
                    'pressure': {
                        'pairs': [{'refRoom': '走廊', 'type': 'negative', 'range': '-10~-15', 'values': ['-20']}],
                        'primarySummary': '走廊:-20.0 Pa[数据库:-10~-15]',
                        'result': '不合格'
                    }
                }
            }]
        },
        'expect': {
            'type_id': 'bsl',
            'clean_class': 'ISO 7',
            'context_key': 'bsl_level',
            'context_value': 'BSL-2（P2）',
        }
    },
    {
        'name': 'operating_room_aux',
        'draft_id': 'X1DRAFT_CONSIST_OR_AUX',
        'payload': {
            'draft_id': 'X1DRAFT_CONSIST_OR_AUX',
            'project_name': '一致性专项-operating-room-aux',
            'report_number': 'CONSIST-OR-001',
            'client_name': '一致性测试单位',
            'contact_info': '13800000000',
            'project_address': '上海市测试路3号',
            'inspection_area': '手术部',
            'detection_date': '2026-05-04',
            'domain': 'hospital',
            'domain_name': '医院洁净部',
            'rooms': [{
                'room_id': 'R1',
                'room_name': '刷手间1',
                'type_id': 'operating_room',
                'type_name': '手术室',
                'clean_class': 'Ⅱ级（7级）',
                'context': {
                    'surgery_room_type': '洁净辅房',
                    'surgery_aux_room': '刷手间',
                    'surgery_aux_clean_class': 'Ⅱ级（7级）'
                },
                'summary': {
                    'result_state': '不合格',
                    'input_result_state': '合格',
                    'judgement_engine': 'operating_room_v1',
                    'judgement_reason': '一致性测试',
                    'judgement_overridden': True,
                    'abnormal_items': [{'item_name': '噪声', 'result': '不合格'}]
                },
                'params': {}
            }]
        },
        'expect': {
            'type_id': 'operating_room',
            'clean_class': 'Ⅱ级（7级）',
            'context_key': 'surgery_aux_room',
            'context_value': '刷手间',
        }
    },
    {
        'name': 'ivc_default',
        'draft_id': 'X1DRAFT_CONSIST_IVC_DEFAULT',
        'payload': {
            'draft_id': 'X1DRAFT_CONSIST_IVC_DEFAULT',
            'project_name': '一致性专项-ivc-default',
            'report_number': 'CONSIST-IVC-001',
            'client_name': '一致性测试单位',
            'contact_info': '13800000000',
            'project_address': '上海市测试路4号',
            'inspection_area': 'IVC区域',
            'detection_date': '2026-05-04',
            'domain': 'biosafety',
            'domain_name': '生物安全',
            'rooms': [{
                'room_id': 'R1',
                'room_name': 'IVC笼具1',
                'type_id': 'ivc',
                'type_name': 'IVC笼具',
                'clean_class': '默认',
                'length': '4',
                'width': '3',
                'height': '4.2',
                'summary': {
                    'result_state': '合格',
                    'input_result_state': '合格',
                    'judgement_engine': 'ivc_v1',
                    'judgement_reason': '一致性测试',
                    'judgement_overridden': False,
                    'abnormal_items': []
                },
                'params': {
                    'airchange': {
                        'type': 'airchange_speed',
                        'vents': [{'area': '0.20', 'speed': '0.56', 'volume': '403.2'}],
                        'result': '合格'
                    }
                }
            }]
        },
        'expect': {
            'type_id': 'ivc',
            'clean_class': '默认',
            'context_key': None,
            'context_value': None,
        }
    },
    {
        'name': 'clean_function_room_icu',
        'draft_id': 'X1DRAFT_CONSIST_CFR_ICU',
        'payload': {
            'draft_id': 'X1DRAFT_CONSIST_CFR_ICU',
            'project_name': '一致性专项-clean-function-room-icu',
            'report_number': 'CONSIST-CFR-001',
            'client_name': '一致性测试单位',
            'contact_info': '13800000000',
            'project_address': '上海市测试路5号',
            'inspection_area': 'ICU病房区',
            'detection_date': '2026-05-04',
            'domain': 'hospital',
            'domain_name': '医院洁净部',
            'rooms': [{
                'room_id': 'R1',
                'room_name': 'ICU病房1',
                'type_id': 'clean_function_room',
                'type_name': '洁净功能用房',
                'clean_class': 'Ⅲ级（万级）',
                'context': {
                    'clean_function_subroom': 'ICU病房'
                },
                'summary': {
                    'result_state': '不合格',
                    'input_result_state': '合格',
                    'judgement_engine': 'clean_function_room_v1',
                    'judgement_reason': '一致性测试',
                    'judgement_overridden': True,
                    'abnormal_items': [{'item_name': '温度', 'result': '不合格'}]
                },
                'params': {}
            }]
        },
        'expect': {
            'type_id': 'clean_function_room',
            'clean_class': 'Ⅲ级（万级）',
            'context_key': 'clean_function_subroom',
            'context_value': 'ICU病房',
        }
    },
    {
        'name': 'animal_room_barrier_aux',
        'draft_id': 'X1DRAFT_CONSIST_ANIMAL_BARRIER_AUX',
        'payload': {
            'draft_id': 'X1DRAFT_CONSIST_ANIMAL_BARRIER_AUX',
            'project_name': '一致性专项-animal-room-barrier-aux',
            'report_number': 'CONSIST-ANIMAL-001',
            'client_name': '一致性测试单位',
            'contact_info': '13800000000',
            'project_address': '上海市测试路6号',
            'inspection_area': '动物房屏障区',
            'detection_date': '2026-05-04',
            'domain': 'biosafety',
            'domain_name': '生物安全',
            'rooms': [{
                'room_id': 'R1',
                'room_name': '传递间A',
                'type_id': 'animal_room',
                'type_name': '动物房',
                'clean_class': '屏障环境',
                'context': {
                    'animal_environment': '屏障环境',
                    'barrier_room_class': '洁净辅房',
                    'barrier_aux_room': '传递间'
                },
                'summary': {
                    'result_state': '不合格',
                    'input_result_state': '合格',
                    'judgement_engine': 'animal_room_v1',
                    'judgement_reason': '一致性测试',
                    'judgement_overridden': True,
                    'abnormal_items': [{'item_name': '压差', 'result': '不合格'}]
                },
                'params': {}
            }]
        },
        'expect': {
            'type_id': 'animal_room',
            'clean_class': '屏障环境',
            'context_key': 'barrier_aux_room',
            'context_value': '传递间',
        }
    }
]


def get_room_from_get_response(data):
    if isinstance(data, dict) and isinstance(data.get('record'), dict):
        rooms = data['record'].get('rooms') or []
        return rooms[0] if rooms else {}
    rooms = data.get('rooms') or []
    return rooms[0] if rooms else {}


def main():
    client = app.test_client()
    login_resp = client.post('/login', data={'username': 'admin', 'password': 'pudi2026'}, follow_redirects=True)
    if login_resp.status_code != 200:
        raise RuntimeError(f'login failed: {login_resp.status_code}')
    results = []

    for case in CASES:
        draft_path = _x_draft_path(case['draft_id'])
        draft_path.unlink(missing_ok=True)

        export_id = None
        export_path = None
        try:
            save_res = client.post('/api/save', json=case['payload'])
            save_json = save_res.get_json(silent=True) or {}

            load_res = client.get(f"/api/get/{case['draft_id']}")
            load_json = load_res.get_json(silent=True) or {}
            loaded_room = get_room_from_get_response(load_json)

            build_res = client.post('/api/x/build_export', json={'project': case['payload']})
            build_json = build_res.get_json(silent=True) or {}
            export_payload = build_json.get('export_payload') or {}

            submit_res = client.post('/api/x/submit_export', json={'project': case['payload']})
            submit_json = submit_res.get_json(silent=True) or {}
            export_id = submit_json.get('export_id')
            export_path = _x_export_path(export_id) if export_id else None

            export_json = {}
            if export_path and export_path.exists():
                export_json = json.loads(export_path.read_text(encoding='utf-8'))

            expect = case['expect']
            built_room = export_payload.get('room') or {}
            built_ctx = built_room.get('business_context') or {}
            built_sem = export_payload.get('clean_class_semantics') or {}

            ok = all([
                save_res.status_code == 200,
                save_json.get('success') is True,
                load_res.status_code == 200,
                loaded_room.get('type_id') == expect['type_id'],
                loaded_room.get('clean_class') == expect['clean_class'],
                (loaded_room.get('context') or {}).get(expect['context_key']) == expect['context_value'],
                build_res.status_code == 200,
                build_json.get('success') is True,
                export_payload.get('export_type') == expect['type_id'],
                submit_res.status_code == 200,
                submit_json.get('success') is True,
                submit_json.get('export_payload', {}).get('export_type') == expect['type_id'],
                bool(export_json),
            ])

            results.append({
                'name': case['name'],
                'ok': ok,
                'save_status': save_res.status_code,
                'load_status': load_res.status_code,
                'build_status': build_res.status_code,
                'submit_status': submit_res.status_code,
                'loaded': {
                    'type_id': loaded_room.get('type_id'),
                    'clean_class': loaded_room.get('clean_class'),
                    'context': loaded_room.get('context'),
                    'summary': loaded_room.get('summary'),
                },
                'build_export': {
                    'export_type': export_payload.get('export_type'),
                    'room_type_name': built_room.get('type_name'),
                    'clean_class_semantics': built_sem,
                    'business_context': built_ctx,
                },
                'submit_export': {
                    'export_id': export_id,
                    'export_type': (submit_json.get('export_payload') or {}).get('export_type'),
                    'template_ready': submit_json.get('template_ready'),
                    'export_stage': submit_json.get('export_stage'),
                }
            })
        finally:
            draft_path.unlink(missing_ok=True)
            if export_path and export_path.exists():
                export_path.unlink(missing_ok=True)

    out = BASE / 'reports_x1' / 'consistency_probe_20260504_0012.json'
    out.write_text(json.dumps({'results': results}, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'ok': all(r['ok'] for r in results), 'results': results, 'out': str(out)}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
