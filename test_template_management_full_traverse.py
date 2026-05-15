#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""模板管理全量遍历统一测试"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CASES = [
    ('template_management_v2', ['test_template_management_v2.py']),
    ('template_management_manual_sync', ['test_template_management_manual_sync.py']),
    ('template_management_default_switch', ['test_template_management_default_switch.py']),
    ('template_management_default_warning', ['test_template_management_default_warning.py']),
    ('template_management_export_closure', ['test_template_management_export_closure.py']),
    ('template_management_isolation', ['test_template_management_isolation.py']),
    ('template_management_page_contract', ['test_template_management_page_contract.py']),
    ('template_semantic_management', ['test_template_semantic_management.py']),
    ('template_semantic_acceptance', ['test_template_semantic_acceptance.py']),
    ('maintenance_regression_20260507', ['test_maintenance_regression_20260507.py']),
    ('full_system_validation', ['test_full_system_validation.py']),
    ('minimal_validation_guards', ['test_minimal_validation_guards.py']),
]

results = []
for name, parts in CASES:
    print('=' * 80)
    print('[RUN]', name)
    cmd = [sys.executable, str(ROOT / parts[0])]
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    print(p.stdout)
    if p.stderr:
        print(p.stderr)
    results.append({'name': name, 'ok': p.returncode == 0, 'returncode': p.returncode})

passed = sum(1 for r in results if r['ok'])
print('=' * 80)
print('SUMMARY', passed, '/', len(results))
print(json.dumps(results, ensure_ascii=False, indent=2))
raise SystemExit(0 if passed == len(results) else 1)
