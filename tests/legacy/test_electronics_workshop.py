#!/usr/bin/env python3
"""
electronics_workshop 后端逻辑测试
验证模板规则、语义层、报告上下文构建
"""

import json
from template_rules import resolve_template_rule
from clean_class_semantics import build_clean_class_semantics
from report_context_builder import build_report_context


def test_electronics_workshop_iso5():
    """测试 ISO 5（单向流）"""
    project = {
        "domain": "electronics",
        "project_name": "某电子厂洁净车间检测",
        "client_name": "某电子科技有限公司",
        "rooms": [
            {
                "type_id": "electronics_workshop",
                "type_name": "洁净车间",
                "room_name": "芯片封装车间",
                "level_name": "ISO 5",
                "context": {
                    "iso_level": "ISO 5"
                },
                "params": [
                    {"key": "wind_speed", "value": "0.35", "result": ""},
                    {"key": "pressure", "value": "8", "result": ""},
                    {"key": "hepa_leak", "value": "", "result": "未检出泄漏"},
                    {"key": "particle", "value": "", "result": "ISO 5"},
                    {"key": "temperature", "value": "23", "result": ""},
                    {"key": "humidity", "value": "55", "result": ""},
                    {"key": "noise", "value": "62", "result": ""},
                    {"key": "illumination_main", "value": "420", "result": ""},
                    {"key": "illumination_aux", "value": "250", "result": ""},
                    {"key": "airflow_pattern", "value": "", "result": "合格"}
                ],
                "summary": {"result_state": "合格"}
            }
        ]
    }

    print("=" * 60)
    print("测试 1: electronics_workshop ISO 5（单向流）")
    print("=" * 60)

    # 测试模板规则
    rule = resolve_template_rule(project)
    print("\n【模板规则】")
    print(f"  template_family: {rule['template_family']}")
    print(f"  template_variant: {rule['template_variant']}")
    print(f"  template_key: {rule['template_key']}")
    print(f"  template_name: {rule['template_name']}")
    print(f"  report_context_mode: {rule['report_context_mode']}")

    # 测试语义层
    semantics = build_clean_class_semantics(project)
    print("\n【洁净等级语义层】")
    print(f"  standard_code: {semantics['standard_code']}")
    print(f"  object_branch: {semantics['object_branch']}")
    print(f"  level_raw: {semantics['level_raw']}")
    print(f"  level_semantic_key: {semantics['level_semantic_key']}")
    print(f"  semantic_note: {semantics['semantic_note']}")
    print(f"  impacts: {semantics['impacts']}")

    # 测试报告上下文
    context = build_report_context(project, rule)
    print("\n【报告上下文】")
    print(f"  project_name: {context.get('project_name')}")
    print(f"  client_name: {context.get('client_name')}")
    print(f"  detection_type: {context.get('detection_type')}")
    print(f"  clean_class: {context.get('clean_class')}")

    # 验证关键字段
    assert rule['template_family'] == 'electronics.electronics_workshop'
    assert rule['template_variant'] == 'iso-default'
    assert rule['template_key'] == 'electronics/electronics_workshop/iso/5'
    assert rule['report_context_mode'] == 'electronics-workshop-iso'
    assert semantics['standard_code'] == 'GB 50472-2008 + GB 50073-2013'
    assert semantics['level_semantic_key'] == 'electronics.electronics_workshop.iso.ISO5'
    assert 'wind_speed' in semantics['semantic_note']

    print("\n✅ ISO 5 测试通过")


def test_electronics_workshop_iso7():
    """测试 ISO 7（乱流）"""
    project = {
        "domain": "electronics",
        "project_name": "某电子厂洁净车间检测",
        "client_name": "某电子科技有限公司",
        "rooms": [
            {
                "type_id": "electronics_workshop",
                "type_name": "洁净车间",
                "room_name": "组装车间",
                "level_name": "ISO 7",
                "context": {
                    "iso_level": "ISO 7"
                },
                "params": [
                    {"key": "airchange", "value": "20", "result": ""},
                    {"key": "pressure", "value": "6", "result": ""},
                    {"key": "hepa_leak", "value": "", "result": "未检出泄漏"},
                    {"key": "particle", "value": "", "result": "ISO 7"},
                    {"key": "temperature", "value": "24", "result": ""},
                    {"key": "humidity", "value": "58", "result": ""},
                    {"key": "noise", "value": "58", "result": ""},
                    {"key": "illumination_main", "value": "380", "result": ""},
                    {"key": "illumination_aux", "value": "220", "result": ""},
                    {"key": "airflow_pattern", "value": "", "result": "合格"}
                ],
                "summary": {"result_state": "合格"}
            }
        ]
    }

    print("\n" + "=" * 60)
    print("测试 2: electronics_workshop ISO 7（乱流）")
    print("=" * 60)

    # 测试模板规则
    rule = resolve_template_rule(project)
    print("\n【模板规则】")
    print(f"  template_key: {rule['template_key']}")
    print(f"  template_name: {rule['template_name']}")

    # 测试语义层
    semantics = build_clean_class_semantics(project)
    print("\n【洁净等级语义层】")
    print(f"  level_semantic_key: {semantics['level_semantic_key']}")
    print(f"  semantic_note: {semantics['semantic_note']}")

    # 验证关键字段
    assert rule['template_key'] == 'electronics/electronics_workshop/iso/7'
    assert semantics['level_semantic_key'] == 'electronics.electronics_workshop.iso.ISO7'
    assert 'airchange' in semantics['semantic_note']

    print("\n✅ ISO 7 测试通过")


def test_electronics_workshop_all_levels():
    """测试所有 ISO 等级"""
    levels = ['ISO 5', 'ISO 6', 'ISO 7', 'ISO 8', 'ISO 9']

    print("\n" + "=" * 60)
    print("测试 3: 所有 ISO 等级覆盖")
    print("=" * 60)

    for level in levels:
        project = {
            "domain": "electronics",
            "rooms": [{
                "type_id": "electronics_workshop",
                "level_name": level,
                "context": {"iso_level": level},
                "params": [],
                "summary": {}
            }]
        }

        rule = resolve_template_rule(project)
        semantics = build_clean_class_semantics(project)

        level_num = level.split()[-1]
        expected_key = f'electronics/electronics_workshop/iso/{level_num}'
        expected_semantic = f'electronics.electronics_workshop.iso.ISO{level_num}'

        assert rule['template_key'] == expected_key, f"{level} template_key 不匹配"
        assert semantics['level_semantic_key'] == expected_semantic, f"{level} semantic_key 不匹配"

        print(f"  ✓ {level}: {rule['template_key']}")

    print("\n✅ 所有等级测试通过")


if __name__ == '__main__':
    test_electronics_workshop_iso5()
    test_electronics_workshop_iso7()
    test_electronics_workshop_all_levels()

    print("\n" + "=" * 60)
    print("🎉 所有测试通过！electronics_workshop 后端逻辑正常")
    print("=" * 60)
