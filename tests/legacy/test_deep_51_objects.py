#!/usr/bin/env python3
"""
X1 51对象全业务链深度测试记录器（Canonical执行版）
目标：
1. 模拟用户使用，对 51 个业务对象/业务变体逐项执行 save_draft + submit_export
2. 统一记录在线主链结果、判定摘要结果、模板结果、导出结果
3. 输出可审计 JSON + Markdown，直接暴露系统问题点

判定口径：
- chain_ok: 基础在线主链通过
- deep_ok: chain_ok + summary中存在 judgement_engine/judgement_reason
"""
import importlib.util
import json
import time
from datetime import datetime
from pathlib import Path
from zipfile import ZipFile

import requests

BASE = 'http://localhost:8082'
ROOT = Path('/Users/fuwuqi/检测报告生成系统_X1')
REPORTS = ROOT / 'reports_x1'
VARIANT_FILE = ROOT / 'test_x1_all_variants.py'
s = requests.Session()


def login():
    s.get(f'{BASE}/login', timeout=10)
    r = s.post(f'{BASE}/login', data={'username': 'admin', 'password': 'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def load_variants_module():
    spec = importlib.util.spec_from_file_location('variants_mod', VARIANT_FILE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def normalize_case(scenario_id, domain, type_id, room_name, level_name, clean_class, extra_ctx):
    return {
        'scenario_id': scenario_id,
        'domain': domain,
        'type_id': type_id,
        'room_name': room_name,
        'level_name': level_name,
        'clean_class': clean_class,
        'extra_ctx': extra_ctx or {},
    }


def build_51_cases(mod):
    cases = [normalize_case(*v) for v in mod.VARIANTS]
    # 现有 VARIANTS 为 48 项；按 51 台账补齐 3 个传递窗分支口径，模拟真实业务组合
    cases.extend([
        {
            'scenario_id': 'pass_box_B1B2',
            'domain': 'pharma',
            'type_id': 'pass_box',
            'room_name': '传递窗B1B2',
            'level_name': 'B1/B2',
            'clean_class': 'B1/B2',
            'extra_ctx': {'pass_box_model': 'B1/B2'}
        },
        {
            'scenario_id': 'pass_box_B3',
            'domain': 'pharma',
            'type_id': 'pass_box',
            'room_name': '传递窗B3',
            'level_name': 'B3',
            'clean_class': 'B3',
            'extra_ctx': {'pass_box_model': 'B3'}
        },
        {
            'scenario_id': 'negative_pressure_recheck',
            'domain': 'hospital',
            'type_id': 'negative_pressure',
            'room_name': '负压病房复核样本',
            'level_name': '负压病房',
            'clean_class': '负压病房',
            'extra_ctx': {'negative_pressure_mode': 'standard'}
        },
    ])
    return cases


def run_case(mod, case):
    payload = mod.build_payload(
        case['domain'], case['type_id'], case['room_name'], case['level_name'], case['clean_class'], case['extra_ctx']
    )

    row = {
        'scenario_id': case['scenario_id'],
        'domain': case['domain'],
        'type_id': case['type_id'],
        'room_name': case['room_name'],
        'level_name': case['level_name'],
        'clean_class': case['clean_class'],
        'save_draft': False,
        'submit_export': False,
        'http_status': None,
        'export_id': '',
        'export_type': '',
        'template_key': '',
        'template_ready': False,
        'result_state': '',
        'judgement_engine': '',
        'judgement_reason': '',
        'abnormal_count': 0,
        'filled_exists': False,
        'docx_valid': False,
        'chain_ok': False,
        'deep_ok': False,
        'detail': '',
    }

    r = s.post(f'{BASE}/api/x/save_draft', json={'project': payload}, timeout=30)
    row['save_draft'] = (r.status_code == 200)

    r = s.post(f'{BASE}/api/x/submit_export', json={'project': payload}, timeout=90)
    row['http_status'] = r.status_code
    if r.status_code != 200:
        try:
            body = r.json()
        except Exception:
            body = {'raw': r.text[:300]}
        row['detail'] = f'submit_export HTTP {r.status_code}: {body}'
        return row

    row['submit_export'] = True
    data = r.json()
    ep = data.get('export_payload') or {}
    room = ep.get('room') or {}
    summary = room.get('summary') or {}
    jr = ep.get('judgement_result') or {}
    template_rule = ep.get('template_rule') or data.get('template_rule') or {}

    row['export_id'] = data.get('export_id', '')
    row['export_type'] = (room.get('type_id') or ep.get('export_type') or '')
    row['template_key'] = template_rule.get('template_key', '')
    row['template_ready'] = bool(data.get('template_ready'))
    row['result_state'] = summary.get('result_state', '')
    row['judgement_engine'] = summary.get('judgement_engine', '')
    row['judgement_reason'] = summary.get('judgement_reason', '')
    row['abnormal_count'] = len(jr.get('abnormal_items') or [])

    if row['export_id']:
        filled = REPORTS / f"{row['export_id']}.filled.docx"
        row['filled_exists'] = filled.exists()
        if filled.exists():
            try:
                for attempt in range(5):
                    try:
                        with ZipFile(filled, 'r') as z:
                            z.read('word/document.xml')
                        row['docx_valid'] = True
                        break
                    except Exception:
                        if attempt == 4:
                            raise
                        time.sleep(0.6)
            except Exception as e:
                row['detail'] = f'docx invalid: {e}'

    row['chain_ok'] = all([
        row['save_draft'],
        row['submit_export'],
        bool(row['export_id']),
        bool(row['template_key']),
        bool(row['result_state']),
        row['filled_exists'],
        row['docx_valid'],
    ])
    row['deep_ok'] = all([
        row['chain_ok'],
        bool(row['judgement_engine']),
        bool(row['judgement_reason']),
    ])

    if not row['detail']:
        row['detail'] = (
            f"export_id={row['export_id']}, template_key={row['template_key']}, result_state={row['result_state']}, "
            f"chain_ok={row['chain_ok']}, deep_ok={row['deep_ok']}, judgement_engine={row['judgement_engine'] or 'null'}"
        )
    return row


def write_md(ts, rows):
    total = len(rows)
    chain_ok = sum(1 for r in rows if r['chain_ok'])
    deep_ok = sum(1 for r in rows if r['deep_ok'])
    missing_judgement = [r for r in rows if r['chain_ok'] and not r['deep_ok']]
    lines = [
        f'# X1 51对象全业务链深测汇总 {ts}',
        '',
        f'- 总数：{total}',
        f'- 在线主链通过：{chain_ok}/{total}',
        f'- 深度通过（含 judgement 摘要）：{deep_ok}/{total}',
        f'- 主链通过但缺 judgement 摘要：{len(missing_judgement)}',
        '',
        '## 逐项记录',
        '',
        '| scenario_id | type_id | level | chain_ok | deep_ok | result_state | judgement_engine | template_key | export_id |',
        '|---|---|---|---|---|---|---|---|---|',
    ]
    for r in rows:
        lines.append(
            f"| {r['scenario_id']} | {r['type_id']} | {r['level_name']} | {'PASS' if r['chain_ok'] else 'FAIL'} | {'PASS' if r['deep_ok'] else 'FAIL'} | {r['result_state'] or '-'} | {r['judgement_engine'] or '-'} | {r['template_key'] or '-'} | {r['export_id'] or '-'} |"
        )
    if missing_judgement:
        lines.extend(['', '## 已发现问题：主链通过但缺少判定摘要', '', '| scenario_id | type_id | level | detail |', '|---|---|---|---|'])
        for r in missing_judgement:
            lines.append(f"| {r['scenario_id']} | {r['type_id']} | {r['level_name']} | {r['detail']} |")
    out = REPORTS / f'deep51_summary_{ts}.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    return out


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    mod = load_variants_module()
    assert login(), 'login failed'
    cases = build_51_cases(mod)
    print(f'X1 51对象全业务链深测启动，共 {len(cases)} 项')
    rows = []
    for i, case in enumerate(cases, 1):
        row = run_case(mod, case)
        rows.append(row)
        print(f"{i:02d}. {row['scenario_id']}: {'DEEP_PASS' if row['deep_ok'] else ('CHAIN_PASS' if row['chain_ok'] else 'FAIL')} - {row['detail']}")

    json_out = REPORTS / f'deep51_records_{ts}.json'
    json_out.write_text(json.dumps({'generated_at': ts, 'total': len(rows), 'records': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    md_out = write_md(ts, rows)
    chain_ok = sum(1 for r in rows if r['chain_ok'])
    deep_ok = sum(1 for r in rows if r['deep_ok'])
    print(f'\nSUMMARY chain_ok={chain_ok}/{len(rows)} deep_ok={deep_ok}/{len(rows)}')
    print(f'JSON {json_out}')
    print(f'MD {md_out}')
    if chain_ok != len(rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
