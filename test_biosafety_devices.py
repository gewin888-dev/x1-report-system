#!/usr/bin/env python3
"""
生物安全设备类导出验证脚本
验证 bsc / clean_bench / ivc 三个对象的后端填充逻辑
"""

import json
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from adapters.template_fill import build_template_filled_docx
from template_rules import resolve_template_rule
from template_resources import resolve_template_resource

def test_export(payload_file: str, output_name: str):
    """测试单个对象的导出"""
    print(f"\n{'='*60}")
    print(f"测试对象: {output_name}")
    print(f"Payload: {payload_file}")
    print(f"{'='*60}")
    
    # 读取 payload
    with open(payload_file, 'r', encoding='utf-8') as f:
        project_data = json.load(f)
    
    # 解析模板规则
    template_rule = resolve_template_rule(project_data)
    print(f"   模板键: {template_rule.get('template_key', 'N/A')}")
    
    # 解析模板资源
    template_resource = resolve_template_resource(template_rule)
    print(f"   模板路径: {template_resource.get('template_path', 'N/A')}")
    print(f"   模板存在: {template_resource.get('template_found', False)}")
    
    if not template_resource.get('template_found'):
        print(f"❌ 模板文件不存在")
        return False
    
    # 构造完整的 export_payload
    export_payload = {
        'project_context': project_data.get('project_context', {}),
        'room': project_data['rooms'][0] if project_data.get('rooms') else {},
        'template_rule': template_rule,
        'template_resource': template_resource,
    }
    
    # 构造输出路径
    output_path = f"reports_x1/TEST_{output_name}_20260429.filled.docx"
    
    try:
        # 调用填充函数
        result_path = build_template_filled_docx(export_payload, output_path)
        
        # 检查文件是否存在
        if result_path and Path(result_path).exists():
            file_size = Path(result_path).stat().st_size
            print(f"✅ 导出成功: {result_path}")
            print(f"   文件大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")
            return True
        else:
            print(f"❌ 文件未生成或路径为空: {result_path}")
            return False
            
    except Exception as e:
        print(f"❌ 导出失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("\n" + "="*60)
    print("生物安全设备类导出验证")
    print("="*60)
    
    tests = [
        ("test_payloads/bsc_minimal.json", "BSC"),
        ("test_payloads/clean_bench_minimal.json", "CLEAN_BENCH"),
        ("test_payloads/ivc_minimal.json", "IVC"),
    ]
    
    results = []
    for payload_file, name in tests:
        success = test_export(payload_file, name)
        results.append((name, success))
    
    # 汇总结果
    print("\n" + "="*60)
    print("验证结果汇总")
    print("="*60)
    
    for name, success in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name:20s} {status}")
    
    # 返回状态码
    all_passed = all(success for _, success in results)
    sys.exit(0 if all_passed else 1)

if __name__ == "__main__":
    main()
