#!/usr/bin/env python3
"""测试 pass_box 新字段的真实导出"""
import sys
import os
import requests
from pathlib import Path
from datetime import datetime

BASE_URL = "http://127.0.0.1:8082"

ts = int(datetime.now().timestamp())

payload = {
    "domain": "pharma",
    "record_id": f"test_pass_box_fields_{ts}",
    "report_date": "2026-04-30",
    "rooms": [{
        "type_id": "pass_box",
        "room_name": "传递窗1",
        "context": {
            "detection_area": "A区洁净走廊",
            "inner_length": "600",
            "inner_width": "600",
            "inner_height": "500",
            "紫外灯辐照强度": "120",
            "照度": "300"
        }
    }]
}

print("=" * 60)
print("测试场景: pass_box 新字段验证")
print("=" * 60)

# 1. 保存草稿
r = requests.post(f"{BASE_URL}/api/x/save_draft", json=payload)
draft_id = r.json().get("draft_id")
print(f"1. 草稿保存: {draft_id}")

# 2. 提交导出
r = requests.post(f"{BASE_URL}/api/x/submit_export", json=payload)
result = r.json()
export_id = result.get("export_id")
template_ready = result.get("template_ready")
filled_path = result.get("filled_docx_path", "")

print(f"2. 导出提交: {export_id}")
print(f"   template_ready: {template_ready}")

if template_ready and filled_path and os.path.exists(filled_path):
    size = os.path.getsize(filled_path)
    print(f"   ✅ filled.docx: {size:,} bytes")

    # 检查新字段是否落位
    try:
        from docx import Document
        doc = Document(filled_path)
        found_area = False
        found_length = False

        for table in doc.tables:
            for row in table.rows:
                for cell in row.cells:
                    text = cell.text
                    if "A区洁净走廊" in text:
                        found_area = True
                    if "600" in text:
                        found_length = True

        print(f"   {'✅' if found_area else '⚠️ '} 检测区域(detection_area): {'已落位' if found_area else '未找到'}")
        print(f"   {'✅' if found_length else '⚠️ '} 内部尺寸(600mm): {'已落位' if found_length else '未找到'}")
    except ImportError:
        print("   ⚠️  python-docx 未安装，跳过内容检查")
else:
    print(f"   ❌ 导出失败或文件不存在")
    print(f"   响应: {result}")
