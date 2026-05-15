#!/usr/bin/env python3
"""
医院洁净部导出产物内容终验（抽样版）
样本：main L1 / eye L1 / aux L1
输出：filled.docx + 文本抽取摘要
"""
import json
import sys
from pathlib import Path
from zipfile import ZipFile

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from app_x1 import _build_export_payload, build_template_filled_docx  # noqa: E402

OUT_DIR = BASE_DIR / 'reports_x1' / 'sentinel_20260507'
OUT_DIR.mkdir(parents=True, exist_ok=True)

CASES = [
    {"case_id":"main_l1","label":"主手术室 L1","room_name":"百级手术室","level_name":"Ⅰ级","clean_class":"Ⅰ级","context":{"room_type":"main-room","clean_class_code":"level1","surgery_room_type":"手术室"},"expected_template_key":"hospital/operating_room/main/level1"},
    {"case_id":"eye_l1","label":"眼科手术室 L1","room_name":"眼科手术室1","level_name":"Ⅰ级","clean_class":"Ⅰ级","context":{"room_type":"main-room","clean_class_code":"level1","surgery_room_type":"眼科手术室"},"expected_template_key":"hospital/operating_room/main/level1"},
    {"case_id":"aux_l1","label":"洁净辅房 L1","room_name":"体外循环室","level_name":"Ⅰ级（局部5级其他6级）","clean_class":"Ⅰ级（局部5级其他6级）","context":{"surgery_room_type":"辅房","surgery_aux_room":"体外循环室","surgery_aux_clean_class":"Ⅰ级辅房"},"expected_template_key":"hospital/operating_room/aux/level1-local5-surround6"},
]


def build_project(case):
    return {
        "project_name": f"终验产物-{case['case_id']}",
        "report_number": f"PROD-{case['case_id']}",
        "client_name": "测试医院",
        "contact_info": "13800000000",
        "project_address": "上海测试地址",
        "inspection_area": "医院洁净部",
        "detection_date": "2026-05-07",
        "domain": "hospital",
        "rooms": [{
            "room_id": "r1",
            "room_name": case["room_name"],
            "type_id": "operating_room",
            "type_name": "手术室",
            "level_name": case["level_name"],
            "clean_class": case["clean_class"],
            "basis": ["GB 50333-2013"],
            "judgement": ["GB 50333-2013"],
            "summary": {"result_state": "合格"},
            "params": [
                {"key": "temperature", "value": "23"},
                {"key": "humidity", "value": "55"},
                {"key": "pressure", "value": "12"},
                {"key": "noise", "value": "58"},
                {"key": "illumination_main_room", "value": "350"},
                {"key": "illumination_aux_room", "value": "220"},
            ],
            "context": case["context"],
        }]
    }


def extract_doc_text(docx_path: Path) -> str:
    with ZipFile(docx_path, 'r') as zf:
        xml = zf.read('word/document.xml').decode('utf-8', errors='ignore')
    return xml


def inspect_case(case):
    payload = _build_export_payload(build_project(case))
    out_path = OUT_DIR / f"{case['case_id']}.filled.docx"
    built = build_template_filled_docx(payload, str(out_path))
    built_path = Path(built or out_path)
    text = extract_doc_text(built_path) if built_path.exists() else ''
    checks = {
        'file_exists': built_path.exists(),
        'template_key_match': (payload.get('template_rule') or {}).get('template_key') == case['expected_template_key'],
        'project_name_written': '终验产物-' + case['case_id'] in text,
        'client_name_written': '测试医院' in text,
        'report_number_written': 'PROD-' + case['case_id'] in text,
        'room_name_written': case['room_name'] in text,
    }
    return {
        'case_id': case['case_id'],
        'label': case['label'],
        'template_key': (payload.get('template_rule') or {}).get('template_key'),
        'semantic_key': (payload.get('clean_class_semantics') or {}).get('level_semantic_key'),
        'filled_docx': str(built_path),
        'checks': checks,
        'all_pass': all(checks.values()),
    }


def main():
    rows = [inspect_case(case) for case in CASES]
    out_json = OUT_DIR / 'content_probe_summary.json'
    out_json.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
    passed = 0
    for row in rows:
        print(f"\n=== {row['label']} ===")
        print(f"semantic_key: {row['semantic_key']}")
        print(f"template_key: {row['template_key']}")
        print(f"filled_docx: {row['filled_docx']}")
        for k, v in row['checks'].items():
            print(f"  - {k}: {'PASS' if v else 'FAIL'}")
        print(f"RESULT: {'PASS' if row['all_pass'] else 'FAIL'}")
        if row['all_pass']:
            passed += 1
    print(f"\nSUMMARY {passed}/{len(rows)}")
    print(f"JSON: {out_json}")


if __name__ == '__main__':
    main()
