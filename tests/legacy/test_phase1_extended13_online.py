#!/usr/bin/env python3
"""
X1 第一阶段深测：扩展 13 项在线主链批量验证
覆盖：
- veterinary_gmp_workshop 4级
- food_workshop 4级
- electronics_workshop ISO5~9

验证层：
1. save_draft
2. submit_export
3. export_payload/template_key
4. judgement summary 字段存在性
5. filled docx 存在且可打开
"""
import importlib.util
import json
import time
from pathlib import Path
from zipfile import ZipFile

import requests

BASE = 'http://localhost:8082'
ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
REPORTS = ROOT / 'reports_x1'
s = requests.Session()

TARGET_PREFIXES = (
    'veterinary_gmp_workshop_',
    'veterinary_gmp_',
    'food_workshop_',
    'electronics_workshop_iso',
    'electronics_iso',
)


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def load_variants_module():
    p = ROOT / 'test_x1_all_variants.py'
    spec = importlib.util.spec_from_file_location('variants_mod', p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def is_target_variant(scenario_id: str) -> bool:
    return scenario_id.startswith(TARGET_PREFIXES)


def run_variant(payload):
    result = {
        'save_draft': False,
        'submit_export': False,
        'has_export_id': False,
        'filled_exists': False,
        'docx_valid': False,
        'has_template_key': False,
        'has_result_state': False,
        'has_judgement_engine': False,
        'has_judgement_reason': False,
        'online_chain_ok': False,
        'deep_ready_ok': False,
        'ok': False,
        'detail': '',
    }

    r = s.post(f'{BASE}/api/x/save_draft', json={'project': payload}, timeout=30)
    if r.status_code != 200:
        result['detail'] = f'save_draft HTTP {r.status_code}'
        return result
    result['save_draft'] = True

    r = s.post(f'{BASE}/api/x/submit_export', json={'project': payload}, timeout=90)
    if r.status_code != 200:
        result['detail'] = f'submit_export HTTP {r.status_code}'
        return result
    result['submit_export'] = True

    data = r.json()
    export_id = data.get('export_id')
    template_rule = data.get('template_rule') or ((data.get('export_payload') or {}).get('template_rule')) or {}
    template_key = template_rule.get('template_key', '')
    summary = (((data.get('export_payload') or {}).get('room') or {}).get('summary') or {})

    result['has_export_id'] = bool(export_id)
    result['has_template_key'] = bool(template_key)
    result['has_result_state'] = bool(summary.get('result_state', ''))
    result['has_judgement_engine'] = 'judgement_engine' in summary
    result['has_judgement_reason'] = 'judgement_reason' in summary

    if not export_id:
        result['detail'] = f'no export_id template_key={template_key}'
        return result

    filled = REPORTS / f'{export_id}.filled.docx'
    result['filled_exists'] = filled.exists()
    if not filled.exists():
        result['detail'] = f'no filled.docx export_id={export_id} template_key={template_key}'
        return result

    try:
        for attempt in range(5):
            try:
                with ZipFile(filled, 'r') as z:
                    z.read('word/document.xml')
                result['docx_valid'] = True
                break
            except Exception as e:
                if attempt == 4:
                    raise
                time.sleep(0.6)
    except Exception as e:
        result['detail'] = f'docx invalid: {e}'
        return result

    result['online_chain_ok'] = all([
        result['save_draft'],
        result['submit_export'],
        result['has_export_id'],
        result['filled_exists'],
        result['docx_valid'],
        result['has_template_key'],
        result['has_result_state'],
    ])
    result['deep_ready_ok'] = all([
        result['online_chain_ok'],
        result['has_judgement_engine'],
        result['has_judgement_reason'],
    ])
    result['ok'] = result['deep_ready_ok']
    result['detail'] = (
        f"export_id={export_id}, template_key={template_key}, result_state={summary.get('result_state','')}, "
        f"online_chain_ok={result['online_chain_ok']}, deep_ready_ok={result['deep_ready_ok']}"
    )
    return result


def main():
    mod = load_variants_module()
    targets = [v for v in mod.VARIANTS if is_target_variant(v[0])]
    assert len(targets) == 13, f'expected 13 targets, got {len(targets)}'
    assert login(), 'login failed'

    passed, failed = [], []
    print(f'X1 第一阶段扩展13项在线主链深测 — 共{len(targets)}项')
    for i, (scenario_id, domain, type_id, room_name, level_name, clean_class, extra_ctx) in enumerate(targets, 1):
        payload = mod.build_payload(domain, type_id, room_name, level_name, clean_class, extra_ctx)
        res = run_variant(payload)
        line = f"{i:02d}. {scenario_id}: {'PASS' if res['ok'] else ('CHAIN_PASS/DEEP_PENDING' if res['online_chain_ok'] else 'FAIL')} - {res['detail']}"
        print(line)
        (passed if res['ok'] else failed).append({
            'scenario_id': scenario_id,
            'type_id': type_id,
            'level_name': level_name,
            'clean_class': clean_class,
            'result': res,
        })

    report = {
        'total': len(targets),
        'passed': len(passed),
        'failed': len(failed),
        'passed_items': passed,
        'failed_items': failed,
    }
    out = ROOT / 'reports_x1' / 'phase1_extended13_report.json'
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nSUMMARY deep_ready={len(passed)}/{len(targets)}')
    chain_pass = sum(1 for item in passed + failed if item['result'].get('online_chain_ok'))
    print(f'CHAIN_PASS {chain_pass}/{len(targets)}')
    print(f'REPORT {out}')
    if failed and chain_pass != len(targets):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
