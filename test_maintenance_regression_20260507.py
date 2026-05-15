#!/usr/bin/env python3
"""
维护态对象抽样回归（2026-05-07）
覆盖：pass_box / laminar_hood / bsc / clean_bench / ivc / clean_function_room
"""
import json
import sys
from pathlib import Path
from zipfile import ZipFile

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload, build_template_filled_docx  # noqa: E402

OUT_DIR = BASE_DIR / 'reports_x1' / 'maintenance_regression_20260507'
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_JSON = BASE_DIR / 'logs_x1' / 'maintenance_regression_20260507.json'

COMMON = {
    'project_name': '维护态回归项目',
    'report_number': 'MAINT-20260507-001',
    'client_name': '上海维护态抽样',
    'contact_info': '13912345678',
    'project_address': '上海市终验回归区',
    'inspection_area': '维护态抽样区',
    'detection_date': '2026-05-07',
}

CASES = [
    {
        'case_id': 'pass_box', 'domain': 'pharma', 'type_id': 'pass_box', 'type_name': '传递窗',
        'level_name': '无等级要求', 'room_name': 'A区传递窗', 'context': {},
        'basis': ['GB 50457-2019'], 'judgement': ['GB 50457-2019'],
        'expected_template_key': 'pharma/pass_box/default', 'expected_semantic_key': 'pharma.pass_box.default',
        'params': [{'key':'temperature','value':'23'},{'key':'humidity','value':'55'},{'key':'noise','value':'58'}],
    },
    {
        'case_id': 'laminar_hood', 'domain': 'pharma', 'type_id': 'laminar_hood', 'type_name': '层流罩',
        'level_name': 'A级', 'room_name': '层流罩1', 'context': {'gmp_grade':'A级'},
        'basis': ['GB 50457-2019'], 'judgement': ['GB 50457-2019'],
        'expected_template_key': 'pharma/laminar_hood/default', 'expected_semantic_key': 'pharma.laminar_hood.default',
        'params': [{'key':'temperature','value':'23'},{'key':'humidity','value':'55'},{'key':'noise','value':'58'}],
    },
    {
        'case_id': 'bsc', 'domain': 'biosafety', 'type_id': 'bsc', 'type_name': '生物安全柜',
        'level_name': 'A2型', 'room_name': 'BSC-1', 'context': {'bsc_class':'II A2'},
        'basis': ['NSF/ANSI 49'], 'judgement': ['NSF/ANSI 49'],
        'expected_template_key': 'biosafety/bsc/default', 'expected_semantic_key': 'biosafety.bsc.default',
        'params': [{'key':'temperature','value':'23'},{'key':'humidity','value':'55'},{'key':'noise','value':'58'}],
    },
    {
        'case_id': 'clean_bench', 'domain': 'biosafety', 'type_id': 'clean_bench', 'type_name': '洁净工作台',
        'level_name': 'ISO 5', 'room_name': '超净台1', 'context': {},
        'basis': ['JG/T 292-2010'], 'judgement': ['JG/T 292-2010'],
        'expected_template_key': 'biosafety/clean_bench/default', 'expected_semantic_key': 'biosafety.clean_bench.default',
        'params': [{'key':'temperature','value':'23'},{'key':'humidity','value':'55'},{'key':'noise','value':'58'}],
    },
    {
        'case_id': 'ivc', 'domain': 'biosafety', 'type_id': 'ivc', 'type_name': 'IVC笼具',
        'level_name': 'IVC', 'room_name': 'IVC-1', 'context': {},
        'basis': ['GB 14925-2023'], 'judgement': ['GB 14925-2023'],
        'expected_template_key': 'biosafety/ivc/default', 'expected_semantic_key': 'biosafety.ivc.default',
        'params': [{'key':'temperature','value':'23'},{'key':'humidity','value':'55'},{'key':'noise','value':'58'}],
    },
    {
        'case_id': 'clean_function_room_icu', 'domain': 'hospital', 'type_id': 'clean_function_room', 'type_name': '洁净功能用房',
        'level_name': 'ICU', 'room_name': 'ICU病房', 'context': {'room_usage':'ICU'},
        'basis': ['GB 50333-2013'], 'judgement': ['GB 50333-2013'],
        'expected_template_key': 'hospital/clean_function_room/icu', 'expected_semantic_key': 'hospital.clean_function_room.icu',
        'params': [{'key':'temperature','value':'23'},{'key':'humidity','value':'55'},{'key':'noise','value':'58'}],
    },
]


def extract_text(docx_path: Path) -> str:
    with ZipFile(docx_path, 'r') as zf:
        return zf.read('word/document.xml').decode('utf-8', errors='ignore')


def build_project(case):
    return {
        **COMMON,
        'domain': case['domain'],
        'rooms': [{
            'room_id': 'r1',
            'room_name': case['room_name'],
            'type_id': case['type_id'],
            'type_name': case['type_name'],
            'level_name': case['level_name'],
            'clean_class': case['level_name'],
            'basis': case['basis'],
            'judgement': case['judgement'],
            'summary': {'result_state': '合格'},
            'params': case['params'],
            'context': case['context'],
        }]
    }


def inspect(case):
    payload = _build_export_payload(build_project(case))
    out_path = OUT_DIR / f"{case['case_id']}.filled.docx"
    built = build_template_filled_docx(payload, str(out_path))
    built_path = Path(built or out_path)
    text = extract_text(built_path) if built_path.exists() else ''
    sem = (payload.get('clean_class_semantics') or {}).get('level_semantic_key', '')
    key = (payload.get('template_rule') or {}).get('template_key', '')
    res = payload.get('template_resource') or {}
    checks = {
        'semantic_key_match': sem == case['expected_semantic_key'],
        'template_key_match': key == case['expected_template_key'],
        'resource_confirmed': res.get('resource_status') == 'confirmed',
        'template_found': res.get('template_found') is True,
        'file_exists': built_path.exists(),
        'project_name_written': COMMON['project_name'] in text,
        'report_number_written': COMMON['report_number'] in text,
    }
    if case['type_id'] in ('pass_box', 'laminar_hood', 'clean_function_room'):
        checks['room_name_written'] = case['room_name'] in text
    return {
        'case_id': case['case_id'],
        'semantic_key': sem,
        'template_key': key,
        'template_path': res.get('template_path', ''),
        'filled_docx': str(built_path),
        'checks': checks,
        'all_pass': all(checks.values()),
    }


def main():
    rows = [inspect(c) for c in CASES]
    passed = 0
    for row in rows:
        print(f"\n=== {row['case_id']} ===")
        print('semantic_key:', row['semantic_key'])
        print('template_key:', row['template_key'])
        for k,v in row['checks'].items():
            print(f"  - {k}: {'PASS' if v else 'FAIL'}")
        print('RESULT:', 'PASS' if row['all_pass'] else 'FAIL')
        if row['all_pass']:
            passed += 1
    OUT_JSON.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\nSUMMARY {passed}/{len(rows)}")
    print('JSON:', OUT_JSON)


if __name__ == '__main__':
    main()
