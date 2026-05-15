#!/usr/bin/env python3
"""模板治理防回退：正式语义默认模板不能被测试/验收模板抢占。"""
import json
from pathlib import Path


def test_formal_template_defaults():
    semantic = json.loads(Path('template_semantic_mappings.json').read_text(encoding='utf-8'))
    registry = json.loads(Path('template_registry.json').read_text(encoding='utf-8'))

    expected_defaults = {
        'food.food_workshop.grade.1': 'food/food_workshop/default/1',
        'food.food_workshop.grade.2': 'food/food_workshop/default/234',
        'food.food_workshop.grade.3': 'food/food_workshop/default/234',
        'food.food_workshop.grade.4': 'food/food_workshop/default/234',
        'pharma.gmp_workshop.grade.a': 'pharma/gmp_workshop/a',
        'pharma.gmp_workshop.grade.b': 'pharma/gmp_workshop/b/c',
        'pharma.gmp_workshop.grade.c': 'pharma/gmp_workshop/b/c',
        'pharma.gmp_workshop.grade.d': 'pharma/gmp_workshop/d',
    }

    for semantic_key, template_key in expected_defaults.items():
        item = semantic.get(semantic_key)
        assert item, f'缺少语义映射: {semantic_key}'
        assert item.get('default_template_key') == template_key, (semantic_key, item.get('default_template_key'))
        allowed = item.get('allowed_template_keys') or []
        assert template_key in allowed, f'{semantic_key} 未允许正式模板 {template_key}'

        reg = registry.get(template_key)
        assert reg, f'注册表缺少模板: {template_key}'
        assert reg.get('enabled') is True, f'正式模板未启用: {template_key}'
        assert reg.get('resource_status') == 'confirmed', f'正式模板状态异常: {template_key}'
        path = str(reg.get('template_path') or '')
        assert '/公司资料/' in path, f'默认模板未指向正式模板库: {template_key} -> {path}'
        assert '/uploads/templates/' not in path, f'默认模板误指向上传测试模板: {template_key} -> {path}'


if __name__ == '__main__':
    test_formal_template_defaults()
    print('PASS test_template_governance_regression')
