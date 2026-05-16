#!/usr/bin/env python3
import requests, os, importlib.util
from pathlib import Path
from zipfile import ZipFile

BASE='http://localhost:8082'
ROOT=Path('/Users/fuwuqi/检测报告生成系统_X1')
REPORTS=ROOT/'reports_x1'
s=requests.Session()

def login():
    s.get(f'{BASE}/login', timeout=10)
    r=s.post(f'{BASE}/login', data={'username':'admin','password':'pudi2026'}, allow_redirects=True, timeout=10)
    return r.status_code==200

def load_variants_module():
    p=ROOT/'test_x1_all_variants.py'
    spec=importlib.util.spec_from_file_location('variants_mod', p)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def run_variant(mod, scenario_id, payload):
    r=s.post(f'{BASE}/api/x/save_draft', json={'project': payload}, timeout=30)
    if r.status_code!=200:
        return False, f'save_draft HTTP {r.status_code}'
    try:
        draft=r.json().get('draft_id')
    except Exception:
        return False, f'save_draft non-json: {r.text[:120]}'
    if not draft:
        return False, 'no draft_id'

    r=s.post(f'{BASE}/api/x/submit_export', json={'project': payload}, timeout=60)
    if r.status_code!=200:
        return False, f'submit_export HTTP {r.status_code}'
    try:
        data=r.json()
    except Exception:
        return False, f'submit_export non-json: {r.text[:120]}'

    export_id=data.get('export_id')
    template_key=data.get('template_rule',{}).get('template_key','N/A')
    if not export_id:
        return False, f'no export_id template_key={template_key}'
    filled=REPORTS/f'{export_id}.filled.docx'
    if not filled.exists():
        return False, f'no filled.docx template_key={template_key}'
    size=filled.stat().st_size
    if size < 5000:
        return False, f'filled too small {size}B template_key={template_key}'
    try:
        with ZipFile(filled,'r') as z:
            z.read('word/document.xml')
    except Exception as e:
        return False, f'docx invalid: {e} template_key={template_key}'
    return True, f'export_id={export_id}, template_key={template_key}, size={size}B'

if __name__=='__main__':
    mod=load_variants_module()
    if not login():
        print('LOGIN_FAIL')
        raise SystemExit(1)
    passed=[]; failed=[]
    print(f'X3 全量业务变体认证测试 — 共{len(mod.VARIANTS)}项')
    for i,(scenario_id, domain, type_id, room_name, level_name, clean_class, extra_ctx) in enumerate(mod.VARIANTS,1):
        payload=mod.build_payload(domain, type_id, room_name, level_name, clean_class, extra_ctx)
        ok,detail=run_variant(mod, scenario_id, payload)
        print(f'{i:02d}. {scenario_id}: {"PASS" if ok else "FAIL"} - {detail}')
        (passed if ok else failed).append((scenario_id, detail))
    print(f'\nSUMMARY {len(passed)}/{len(mod.VARIANTS)}')
    if failed:
        print('FAILED_LIST')
        for sid,detail in failed:
            print(f'- {sid}: {detail}')
