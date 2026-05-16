#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from app_x1 import app, _build_export_payload
from template_resources import (
    set_semantic_default_template,
    attach_template_key_to_semantic,
    get_semantic_template_mapping,
)

ADMIN_HTML = (ROOT / 'templates' / 'admin.html').read_text(encoding='utf-8')


def ok(cond, msg):
    if not cond:
        raise AssertionError(msg)


def seed_template(template_key, type_id, template_name):
    path = ROOT / 'uploads' / 'templates' / f"{template_key.replace('/', '_')}.docx"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(b'PK\x03\x04semantic-acceptance')
    registry_path = ROOT / 'template_registry.json'
    data = json.loads(registry_path.read_text(encoding='utf-8') or '{}') if registry_path.exists() else {}
    data[template_key] = {
        'template_name': template_name,
        'template_path': str(path),
        'type_id': type_id,
        'enabled': True,
        'version': 'v-acceptance',
        'last_verified_at': '',
        'last_verify_result': '',
        'last_verify_error': '',
    }
    registry_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return path


def payload(project):
    return _build_export_payload(project)


def main():
    gmp_a = 'pharma/gmp_workshop/grade/a'
    gmp_b = 'pharma/gmp_workshop/grade/b'
    gmp_type = 'gmp_workshop'
    gmp_sem = 'pharma.gmp_workshop.grade.a'
    seed_template(gmp_a, gmp_type, 'GMP-A模板.docx')
    seed_template(gmp_b, gmp_type, 'GMP-B模板.docx')
    attach_template_key_to_semantic(gmp_sem, gmp_a, 'acceptance')
    attach_template_key_to_semantic(gmp_sem, gmp_b, 'acceptance')
    set_semantic_default_template(gmp_sem, gmp_a, 'acceptance', '2026-05-06 22:00:00')

    p1 = {
        'project_name': '验收-GMP-A级',
        'domain': 'pharma',
        'rooms': [{'type_id': gmp_type, 'level_name': 'A级', 'context': {'gmp_grade': 'A级'}, 'samples': []}]
    }
    r1 = payload(p1)
    ok(r1['template_rule']['template_key'] == gmp_a, f'CASE1 页面/语义默认与导出链不一致: {r1}')
    print('✅ CASE1 semantic 默认模板与导出链一致')

    food_1 = 'food/food_workshop/grade/1'
    food_2 = 'food/food_workshop/grade/2'
    seed_template(food_1, 'food_workshop', '食品-I模板.docx')
    seed_template(food_2, 'food_workshop', '食品-II模板.docx')
    set_semantic_default_template('food.food_workshop.grade.1', food_1, 'acceptance', '2026-05-06 22:00:00')
    set_semantic_default_template('food.food_workshop.grade.2', food_2, 'acceptance', '2026-05-06 22:00:00')
    p2a = {'project_name': '验收-食品1', 'domain': 'food', 'rooms': [{'type_id': 'food_workshop', 'level_name': 'Ⅰ级', 'context': {'food_grade': 'Ⅰ级'}, 'samples': []}]}
    p2b = {'project_name': '验收-食品2', 'domain': 'food', 'rooms': [{'type_id': 'food_workshop', 'level_name': 'Ⅱ级', 'context': {'food_grade': 'Ⅱ级'}, 'samples': []}]}
    r2a = payload(p2a)
    r2b = payload(p2b)
    ok(r2a['template_rule']['template_key'] == food_1 and r2b['template_rule']['template_key'] == food_2, 'CASE2 不同等级 semantic 串扰')
    print('✅ CASE2 不同等级 semantic 默认模板不串扰')

    mapping = get_semantic_template_mapping(gmp_sem)
    ok(gmp_a in (mapping.get('allowed_template_keys') or []) and gmp_b in (mapping.get('allowed_template_keys') or []), 'CASE3 semantic 候选集缺失')
    ok(mapping.get('default_template_key') == gmp_a, 'CASE3 semantic 默认模板错误')
    print('✅ CASE3 semantic 候选/默认映射状态正确')

    ok('filterTemplateDetailBySemantic' in ADMIN_HTML and 'data-template-id' in ADMIN_HTML and '保存当前模板' in ADMIN_HTML, 'CASE4 页面联动/局部刷新/候选摘要未接入')
    print('✅ CASE4 页面已接入 semantic 联动与局部刷新能力')

    with app.test_client() as client:
        resp = client.post('/login', data={'username': 'admin', 'password': 'pudi2026'}, follow_redirects=True)
        ok(resp.status_code == 200, '登录失败')
        detail = client.get('/admin/api/template-semantic-mappings/pharma.gmp_workshop.grade.a').get_json() or {}
        ok(detail.get('mapping', {}).get('default_template_key') == gmp_a, f'CASE5 semantic detail 接口状态不一致: {detail}')
        print('✅ CASE5 semantic detail 接口与映射状态一致')

    print('\n✅ SEMANTIC ACCEPTANCE ALL PASS')


if __name__ == '__main__':
    main()
