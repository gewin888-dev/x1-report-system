#!/usr/bin/env python3
"""重新执行 20 份带完整基础信息+完整房间参数的 X1 导出测试。"""
import json
import os
import subprocess
import time
from pathlib import Path

import requests

BASE = 'http://127.0.0.1:8082'
ROOT = Path('.')
REPORT_DIR = ROOT / 'reports_x1'
OUT_TS = time.strftime('%Y%m%d_%H%M%S')
OUT_JSON = REPORT_DIR / f'fullparam_20_cases_{OUT_TS}.json'
OUT_MD = REPORT_DIR / f'fullparam_20_cases_{OUT_TS}.md'


def load_detection_types():
    code = r'''
const db=require('./static/standards_db.js');
const out=[];
for (const [domain, arr] of Object.entries(db.detectionTypes||{})) {
  for (const item of arr) out.push({...item, domain});
}
console.log(JSON.stringify(out));
'''
    r = subprocess.run(['node', '-e', code], capture_output=True, text=True, check=True)
    rows = json.loads(r.stdout)
    return {row['id']: row for row in rows}


def build_param_value(param):
    key = param.get('key', '')
    input_type = param.get('inputType', '')
    name = param.get('name', key)
    if input_type in ('pass_fail', 'text'):
        return {'value': '符合要求', 'result': '合格', 'name': name}
    if input_type == 'numeric':
        return {'value': '23.5', 'result': '合格', 'name': name}
    if input_type in ('noise_corrected', 'airchange', 'airchange_speed_only', 'pressure_bsl', 'floating', 'floating_control', 'settling', 'settling_control'):
        return {'value': '12', 'result': '合格', 'name': name}
    if input_type == 'particle_4':
        return {'value': '0.5μm≤3520；5μm≤29', 'result': '合格', 'name': name}
    if input_type == 'particle_zone':
        return {'value': '手术区：0.5μm≤3520；周边区：0.5μm≤35200', 'result': '合格', 'name': name}
    if input_type in ('bacteria_zone_control', 'bacteria_zone_control_control', 'bacteria_control'):
        return {'value': '平均菌落数合格', 'result': '合格', 'name': name}
    if input_type == 'hepa_leak_multi':
        return {'value': '0.01', 'result': '合格', 'name': name}
    if input_type in ('wind_uniformity', 'illumination_uniformity'):
        return {'value': '0.12', 'result': '合格', 'name': name}
    if input_type == 'pass_box_volume':
        return {'value': '1.20×0.80×1.50', 'result': '合格', 'name': name}
    return {'value': '已录入', 'result': '合格', 'name': name}


def build_room(type_cfg, case):
    clean_class = case.get('clean_class', '')
    level_name = case.get('level_name', clean_class)
    params_def = []
    level_params = type_cfg.get('levelParams') or {}
    if clean_class and clean_class in level_params:
        params_def = level_params[clean_class]
    elif level_name and level_name in level_params:
        params_def = level_params[level_name]
    else:
        params_def = type_cfg.get('params') or []
    params = {p['key']: build_param_value(p) for p in params_def if p.get('key')}
    room = {
        'room_id': f"{case['case_id']}_room",
        'room_name': case['room_name'],
        'type_id': case['type_id'],
        'type_name': type_cfg.get('name') or case['type_name'],
        'clean_class': clean_class,
        'level_name': level_name,
        'basis': type_cfg.get('defaultBasis') or [],
        'judgement': type_cfg.get('defaultJudgement') or [],
        'params': params,
        'context': dict(case.get('context') or {}),
        'length': '6.5',
        'width': '4.2',
        'height': '2.8',
    }
    if case['type_id'] == 'bsl':
        room['bsl'] = case.get('context', {}).get('bsl_level', 'BSL-2（P2）')
    if case['type_id'] == 'animal_room':
        room['barrier_room_class'] = case.get('context', {}).get('barrier_room_class', '')
        room['barrier_aux_room'] = case.get('context', {}).get('barrier_aux_room', '')
    if case['type_id'] == 'operating_room':
        room['surgery_room_type'] = case.get('context', {}).get('surgery_room_type', '')
        if case.get('context', {}).get('surgery_aux_room'):
            room['surgery_aux_room'] = case['context']['surgery_aux_room']
    if case['type_id'] == 'clean_function_room':
        room['clean_function_subroom'] = case.get('context', {}).get('clean_function_subroom', '')
    return room


def make_payload(case, type_cfg):
    ts = case['stamp']
    room = build_room(type_cfg, case)
    return {
        'project_name': f"{case['type_name']}-完整参数项目-{ts}",
        'client_name': f"{case['domain_name']}委托单位{case['index']:02d}",
        'project_address': f"上海市浦东新区完整参数路{case['index']}号",
        'report_number': f"FP{ts}{case['index']:02d}",
        'contact': '13800001234',
        'detection_date': '2026-05-09',
        'domain': case['domain'],
        'rooms': [room],
    }


def unzip_contains_values(docx_path, room):
    import zipfile
    try:
        with zipfile.ZipFile(docx_path) as zf:
            xml = zf.read('word/document.xml').decode('utf-8', errors='ignore')
    except Exception as e:
        return {'ok': False, 'error': f'解析docx失败: {e}', 'hits': 0}
    hits = 0
    for item in list((room.get('params') or {}).values())[:6]:
        val = str(item.get('value') or '')
        if val and val in xml:
            hits += 1
    return {'ok': True, 'hits': hits}


def login(session):
    r = session.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=False)
    return r.status_code in (200, 302)


def main():
    type_map = load_detection_types()
    cases = [
        {'type_id':'pass_box','type_name':'传递窗','domain':'pharma','domain_name':'制药','room_name':'传递窗A','clean_class':'无等级要求'},
        {'type_id':'laminar_hood','type_name':'层流罩','domain':'pharma','domain_name':'制药','room_name':'层流罩A','clean_class':'无等级要求'},
        {'type_id':'gmp_workshop','type_name':'GMP车间','domain':'pharma','domain_name':'制药','room_name':'GMP A级间','clean_class':'A级','level_name':'A级','context':{'gmp_grade':'A级'}},
        {'type_id':'gmp_workshop','type_name':'GMP车间','domain':'pharma','domain_name':'制药','room_name':'GMP C级间','clean_class':'C级','level_name':'C级','context':{'gmp_grade':'C级'}},
        {'type_id':'veterinary_gmp_workshop','type_name':'兽药车间','domain':'pharma','domain_name':'兽药','room_name':'兽药A级间','clean_class':'A级','level_name':'A级','context':{'gmp_grade':'A级'}},
        {'type_id':'veterinary_gmp_workshop','type_name':'兽药车间','domain':'pharma','domain_name':'兽药','room_name':'兽药C级间','clean_class':'C级','level_name':'C级','context':{'gmp_grade':'C级'}},
        {'type_id':'food_workshop','type_name':'食品车间','domain':'food','domain_name':'食品','room_name':'食品Ⅱ级间','clean_class':'Ⅱ级（千级）','level_name':'Ⅱ级（千级）','context':{'food_grade':'Ⅱ级（千级）'}},
        {'type_id':'food_workshop','type_name':'食品车间','domain':'food','domain_name':'食品','room_name':'食品Ⅲ级间','clean_class':'Ⅲ级（万级）','level_name':'Ⅲ级（万级）','context':{'food_grade':'Ⅲ级（万级）'}},
        {'type_id':'negative_pressure','type_name':'负压病房','domain':'hospital','domain_name':'医院','room_name':'负压病房A','clean_class':'无洁净等级要求'},
        {'type_id':'animal_room','type_name':'动物房','domain':'biosafety','domain_name':'生物安全','room_name':'动物主房间','clean_class':'屏障环境','level_name':'屏障环境','context':{'animal_environment':'屏障环境','barrier_room_class':'主房间'}},
        {'type_id':'animal_room','type_name':'动物房','domain':'biosafety','domain_name':'生物安全','room_name':'动物洁净辅房','clean_class':'屏障环境','level_name':'屏障环境','context':{'animal_environment':'屏障环境','barrier_room_class':'洁净辅房','barrier_aux_room':'缓冲间'}},
        {'type_id':'operating_room','type_name':'手术室','domain':'hospital','domain_name':'医院','room_name':'百级手术室','clean_class':'Ⅰ级（百级）','level_name':'Ⅰ级（百级）','context':{'surgery_room_type':'手术室'}},
        {'type_id':'operating_room','type_name':'手术室','domain':'hospital','domain_name':'医院','room_name':'眼科手术室','clean_class':'Ⅱ级（千级）','level_name':'Ⅱ级（千级）','context':{'surgery_room_type':'眼科手术室'}},
        {'type_id':'operating_room','type_name':'手术室','domain':'hospital','domain_name':'医院','room_name':'刷手间','clean_class':'Ⅲ级（万级）','level_name':'Ⅲ级（万级）','context':{'surgery_room_type':'洁净辅房','surgery_aux_room':'刷手间'}},
        {'type_id':'clean_function_room','type_name':'洁净功能用房','domain':'hospital','domain_name':'医院','room_name':'ICU病房','clean_class':'Ⅲ级（万级）','level_name':'Ⅲ级（万级）','context':{'clean_function_subroom':'ICU病房'}},
        {'type_id':'clean_function_room','type_name':'洁净功能用房','domain':'hospital','domain_name':'医院','room_name':'透析室','clean_class':'Ⅳ级（十万级）','level_name':'Ⅳ级（十万级）','context':{'clean_function_subroom':'透析室'}},
        {'type_id':'bsl','type_name':'生物安全实验室','domain':'biosafety','domain_name':'生物安全','room_name':'P2实验室','clean_class':'ISO-7','level_name':'BSL-2（P2）','context':{'bsl_level':'BSL-2（P2）'}},
        {'type_id':'bsl','type_name':'生物安全实验室','domain':'biosafety','domain_name':'生物安全','room_name':'P3实验室','clean_class':'ISO-8','level_name':'BSL-3（P3）','context':{'bsl_level':'BSL-3（P3）'}},
        {'type_id':'bsc','type_name':'生物安全柜','domain':'biosafety','domain_name':'生物安全','room_name':'BSC-A','clean_class':'无等级要求'},
        {'type_id':'clean_bench','type_name':'洁净工作台','domain':'biosafety','domain_name':'生物安全','room_name':'洁净工作台A','clean_class':'无等级要求'},
    ]

    s = requests.Session()
    assert login(s), '登录失败'
    results = []
    stamp = time.strftime('%Y%m%d%H%M%S')
    for idx, case in enumerate(cases, 1):
        case['index'] = idx
        case['case_id'] = f'fullparam_{idx:02d}_{case["type_id"]}'
        case['stamp'] = stamp
        type_cfg = type_map[case['type_id']]
        payload = make_payload(case, type_cfg)
        room = payload['rooms'][0]
        r = s.post(f'{BASE}/api/x/submit_export', json=payload, timeout=120)
        item = {
            'case_id': case['case_id'],
            'type_id': case['type_id'],
            'room_name': room['room_name'],
            'report_number': payload['report_number'],
            'param_count': len(room.get('params') or {}),
            'base_info_complete': all(payload.get(k) for k in ['project_name','client_name','project_address','report_number','detection_date','domain']),
            'success': False,
        }
        if r.status_code != 200:
            item['error'] = f'HTTP {r.status_code}'
            results.append(item)
            continue
        data = r.json()
        item['response_success'] = data.get('success')
        item['export_id'] = data.get('export_id')
        item['docx_path'] = data.get('filled_docx_path') or data.get('docx_path')
        item['xlsx_path'] = ((data.get('dual_chain') or {}).get('raw_record') or {}).get('path')
        item['success'] = bool(data.get('success'))
        item['report_exists'] = bool(item.get('docx_path') and os.path.exists(item['docx_path']))
        item['record_exists'] = bool(item.get('xlsx_path') and os.path.exists(item['xlsx_path']))
        export_json = REPORT_DIR / f"{item['export_id']}.json"
        item['export_json_exists'] = export_json.exists()
        if export_json.exists():
            saved = json.loads(export_json.read_text(encoding='utf-8'))
            saved_room = (((saved.get('export_payload') or {}).get('room')) or {})
            item['saved_param_count'] = len(saved_room.get('params') or {})
        else:
            item['saved_param_count'] = 0
        if item['report_exists']:
            probe = unzip_contains_values(item['docx_path'], room)
            item['docx_param_hits'] = probe.get('hits', 0)
            if probe.get('error'):
                item['docx_probe_error'] = probe['error']
        results.append(item)
        time.sleep(1.1)

    passed = sum(1 for x in results if x['success'] and x['report_exists'] and x['record_exists'] and x['saved_param_count'] > 0)
    report = {
        'generated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'summary': {'total': len(results), 'passed': passed},
        'cases': results,
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [f"# 20 份完整基础信息+完整房间参数导出测试（{report['generated_at']}）", '', f"- 总数：{len(results)}", f"- 通过：{passed}", '']
    for item in results:
        lines.append(f"## {item['case_id']}")
        lines.append(f"- 对象：{item['type_id']} / {item['room_name']}")
        lines.append(f"- 报告编号：{item['report_number']}")
        lines.append(f"- 基础信息完整：{'是' if item['base_info_complete'] else '否'}")
        lines.append(f"- 房间参数数：payload {item['param_count']} / saved {item.get('saved_param_count',0)}")
        lines.append(f"- 导出成功：{'是' if item['success'] else '否'}")
        lines.append(f"- 报告存在：{'是' if item.get('report_exists') else '否'}")
        lines.append(f"- 记录存在：{'是' if item.get('record_exists') else '否'}")
        lines.append(f"- 报告参数命中数：{item.get('docx_param_hits', 0)}")
        if item.get('error'):
            lines.append(f"- 错误：{item['error']}")
        lines.append('')
    OUT_MD.write_text('\n'.join(lines), encoding='utf-8')
    print(json.dumps({'json': str(OUT_JSON), 'md': str(OUT_MD), 'passed': passed, 'total': len(results)}, ensure_ascii=False))


if __name__ == '__main__':
    main()
