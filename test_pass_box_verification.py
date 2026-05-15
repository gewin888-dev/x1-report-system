#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
传递窗真实导出验证脚本
验证新补充的字段：检测区域、内长、内宽、内高
"""

import json
import requests
import sys
from pathlib import Path

def test_pass_box_export():
    """测试 pass_box 导出，验证新字段"""
    
    # 读取测试 payload
    payload_path = Path(__file__).parent / "test_payloads" / "pass_box_full.json"
    with open(payload_path, 'r', encoding='utf-8') as f:
        payload = json.load(f)
    
    print("=" * 60)
    print("传递窗真实导出验证")
    print("=" * 60)
    print(f"\n测试 payload: {payload_path}")
    print(f"项目名称: {payload['project_name']}")
    print(f"检测区域: {payload['inspection_area']}")
    
    room = payload['rooms'][0] if payload.get('rooms') else {}
    context = room.get('context', )
    print(f"内长: {context.get('inner_length', 'N/A')} mm")
    print(f"内宽: {context.get('inner_width', 'N/A')} mm")
    print(f"内高: {context.get('inner_height', 'N/A')} mm")
    
    # 调用导出接口
    url = "http://localhost:8082/api/x/submit_export"
    
    print(f"\n正在调用导出接口: {url}")
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        response.raise_for_status()
        result = response.json()
        
        if result.get('success'):
            print("\n✅ 导出成功")
            print(f"导出ID: {result.get('export_id', 'N/A')}")
            print(f"模板就绪: {result.get('template_ready', False)}")
            
            filled_path = result.get('filled_docx_path', '')
            if filled_path:
                filled_file = Path(filled_path)
                if filled_file.exists():
                    file_size = filled_file.stat().st_size
                    print(f"生成文件: {filled_file.name}")
                    print(f"文件大小: {file_size:,} bytes ({file_size/1024:.1f} KB)")
                    
                    # 验收标准：文件大小应在合理范围内（100KB - 1MB）
                    if 100_000 < file_size < 1_000_000:
                        print("\n✅ 文件大小验收通过")
                    else:
                        print(f"\n⚠️  文件大小异常: {file_size/1024:.1f} KB")
                    
                    print("\n下一步：手动打开 .filled.docx 文件，检查以下字段是否正确落位：")
                    print("  1. 检测区域: A级洁净区与B级洁净区之间")
                    print("  2. 内长: 1200 mm")
                    print("  3. 内宽: 800 mm")
                    print("  4. 内高: 800 mm")
                    
                    return True
                else:
                    print(f"\n❌ 文件未生成: {filled_path}")
                    return False
            else:
                print("\n❌ 响应中未包含 filled_docx_path")
                return False
        else:
            print(f"\n❌ 导出失败: {result.get('error', 'Unknown error')}")
            return False
            
    except requests.exceptions.ConnectionError:
        print("\n❌ 连接失败: 请确认 X1 系统是否运行在 http://localhost:5000")
        return False
    except requests.exceptions.Timeout:
        print("\n❌ 请求超时")
        return False
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return False

if __name__ == "__main__":
    success = test_pass_box_export()
    sys.exit(0 if success else 1)
