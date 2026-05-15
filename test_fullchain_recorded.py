#!/usr/bin/env python3
"""
X1 全量主链真实测试记录器
目标：对 test_x1_all_variants.py 中全部 48 个变体逐项实跑，产出可审计的 JSON 记录与 Markdown 汇总。

输出：
- reports_x1/fullchain_records_<timestamp>.json
- reports_x1/fullchain_summary_<timestamp>.md
"""
import importlib.util
import json
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


def run_variant(mod, variant):
    scenario_id, domain, type_id, room_name, level_name, clean_class, extra_ctx = variant
    payload = mod.build_payload(domain, type_id, room_name, level_name, clean_class, extra_ctx)

    row = {
        'scenario_id': scenario_id,
        'domain': domain,
        'type_id': type_id,
        'room_name': room_name,
        'level_name': level_name,
        'clean_class': clean_class,
        'save_draft': False,
        'submit_export': False,
        'http_status': None,
        'export_id': '',
        'template_key': '',
        'template_ready': False,
        'result_state': '',
        'judgement_engine': '',
        'judgement_reason': '',
        'abnormal_count': 0,
        'filled_exists': False,
        'docx_valid': False,
        'ok': False,
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
    template_rule = ep.get('template_rule') or {}

    row['export_id'] = data.get('export_id', '')
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
                with ZipFile(filled, 'r') as z:
                    z.read('word/document.xml')
                row['docx_valid'] = True
            except Exception as e:
                row['detail'] = f'docx invalid: {e}'

    row['ok'] = all([
        row['save_draft'],
        row['submit_export'],
        bool(row['export_id']),
        bool(row['template_key']),
        bool(row['result_state']),
        row['filled_exists'],
        row['docx_valid'],
    ])
    if not row['detail']:
        row['detail'] = (
            f"export_id={row['export_id']}, template_key={row['template_key']}, "
            f"result_state={row['result_state']}, judgement_engine={row['judgement_engine'] or 'null'}"
        )
    return row


def write_summary(ts: str, rows):
    total = len(rows)
    passed = sum(1 for r in rows if r['ok'])
    with_judgement = sum(1 for r in rows if r['judgement_engine'])
    no_judgement = total - with_judgement
    by_type = {}
    for r in rows:
        item = by_type.setdefault(r['type_id'], {'total': 0, 'ok': 0, 'with_judgement': 0})
        item['total'] += 1
        item['ok'] += 1 if r['ok'] else 0
        item['with_judgement'] += 1 if r['judgement_engine'] else 0

    lines = []
    lines.append(f'# X1 全量主链真实测试汇总 {ts}')
    lines.append('')
    lines.append(f'- 总数：{total}')
    lines.append(f'- 主链通过：{passed}/{total}')
    lines.append(f'- 带判定摘要返回：{with_judgement}/{total}')
    lines.append(f'- 未带判定摘要返回：{no_judgement}/{total}')
    lines.append('')
    lines.append('## 分对象统计')
    lines.append('')
    lines.append('| 对象 | 总数 | 主链通过 | 带判定摘要 |')
    lines.append('|---|---:|---:|---:|')
    for k in sorted(by_type):
        v = by_type[k]
        lines.append(f"| {k} | {v['total']} | {v['ok']} | {v['with_judgement']} |")
    lines.append('')
    lines.append('## 逐项记录')
    lines.append('')
    lines.append('| scenario_id | type_id | level | 主链 | result_state | judgement_engine | abnormal_count | export_id |')
    lines.append('|---|---|---|---|---|---|---:|---|')
    for r in rows:
        lines.append(
            f"| {r['scenario_id']} | {r['type_id']} | {r['level_name']} | {'PASS' if r['ok'] else 'FAIL'} | "
            f"{r['result_state'] or '-'} | {r['judgement_engine'] or '-'} | {r['abnormal_count']} | {r['export_id'] or '-'} |"
        )
    out = REPORTS / f'fullchain_summary_{ts}.md'
    out.write_text('\n'.join(lines), encoding='utf-8')
    return out


def main():
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    mod = load_variants_module()
    variants = list(mod.VARIANTS)
    assert login(), 'login failed'

    rows = []
    print(f'X1 全量主链真实测试启动，共 {len(variants)} 项')
    for i, variant in enumerate(variants, 1):
        row = run_variant(mod, variant)
        rows.append(row)
        print(f"{i:02d}. {row['scenario_id']}: {'PASS' if row['ok'] else 'FAIL'} - {row['detail']}")

    json_out = REPORTS / f'fullchain_records_{ts}.json'
    json_out.write_text(json.dumps({'generated_at': ts, 'total': len(rows), 'records': rows}, ensure_ascii=False, indent=2), encoding='utf-8')
    md_out = write_summary(ts, rows)
    passed = sum(1 for r in rows if r['ok'])
    print(f'\nSUMMARY {passed}/{len(rows)}')
    print(f'JSON {json_out}')
    print(f'MD {md_out}')
    if passed != len(rows):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
