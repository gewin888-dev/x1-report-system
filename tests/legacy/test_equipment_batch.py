#!/usr/bin/env python3
"""测试 bsc/clean_bench/ivc 三个设备对象的完整链路"""
import json
import sys
from pathlib import Path
from adapters.template_fill import _build_placeholder_fill_plan
from adapters.export_docx import OBJECT_TITLE_MAP, OBJECT_NOTE_MAP

def test_bsc():
    payload = {
        "report_context": {
            "project_context": {"project_name": "测试项目-生物安全柜"},
            "room_context": {}
        },
        "room": {
            "type_id": "bsc",
            "type_name": "生物安全柜",
            "room_name": "BSC-01",
            "params": [
                {"key": "bsc_model", "value": "BSC-1300IIA2", "result": ""},
                {"key": "bsc_type", "value": "II级A2型", "result": ""},
                {"key": "appearance", "value": "", "result": "合格"},
                {"key": "downflow_velocity", "value": "0.35", "result": ""},
                {"key": "inflow_velocity", "value": "0.52", "result": ""},
                {"key": "hepa_leak", "value": "", "result": "未检出泄漏"},
                {"key": "particle", "value": "", "result": "ISO-5"},
                {"key": "noise", "value": "62", "result": ""},
                {"key": "illumination", "value": "580", "result": ""},
                {"key": "vibration", "value": "3", "result": ""}
            ],
            "summary": {"result_state": "合格"}
        }
    }
    plan = _build_placeholder_fill_plan(payload)
    print(f"DEBUG bsc plan: {plan[:20]}")  # 打印前20个字段
    assert len(plan) > 0, "bsc fill plan empty"
    assert any(k == '生物安全柜型号' and v == 'BSC-1300IIA2' for k, v in plan), f"bsc_model missing, plan keys: {[k for k,v in plan[:30]]}"
    assert any(k == '下降气流平均风速' and v == '0.35' for k, v in plan), "downflow_velocity missing"
    assert any(k == '设备状态' and v == '可正常启动' for k, v in plan), "equipment_status missing"
    print(f"✅ bsc: {len(plan)} fields")
    return True

def test_clean_bench():
    payload = {
        "report_context": {
            "project_context": {"project_name": "测试项目-洁净工作台"},
            "room_context": {}
        },
        "room": {
            "type_id": "clean_bench",
            "type_name": "洁净工作台",
            "room_name": "CB-01",
            "params": [
                {"key": "bench_model", "value": "SW-CJ-1FD", "result": ""},
                {"key": "appearance", "value": "", "result": "合格"},
                {"key": "air_velocity", "value": "0.42", "result": ""},
                {"key": "hepa_leak", "value": "", "result": "未检出泄漏"},
                {"key": "particle", "value": "", "result": "ISO-5"},
                {"key": "noise", "value": "58", "result": ""},
                {"key": "illumination", "value": "620", "result": ""},
                {"key": "vibration", "value": "2", "result": ""}
            ],
            "summary": {"result_state": "合格"}
        }
    }
    plan = _build_placeholder_fill_plan(payload)
    assert len(plan) > 0, "clean_bench fill plan empty"
    assert any(k == '工作台型号' and v == 'SW-CJ-1FD' for k, v in plan), "bench_model missing"
    assert any(k == '平均风速' and v == '0.42' for k, v in plan), "air_velocity missing"
    print(f"✅ clean_bench: {len(plan)} fields")
    return True

def test_ivc():
    payload = {
        "report_context": {
            "project_context": {"project_name": "测试项目-IVC笼具"},
            "room_context": {}
        },
        "room": {
            "type_id": "ivc",
            "type_name": "IVC笼具",
            "room_name": "IVC-01",
            "params": [
                {"key": "ivc_model", "value": "IVC-M60", "result": ""},
                {"key": "cage_count", "value": "60", "result": ""},
                {"key": "appearance", "value": "", "result": "合格"},
                {"key": "air_velocity", "value": "0.38", "result": ""},
                {"key": "hepa_leak", "value": "", "result": "未检出泄漏"},
                {"key": "particle", "value": "", "result": "ISO-7"},
                {"key": "noise", "value": "55", "result": ""},
                {"key": "illumination", "value": "350", "result": ""},
                {"key": "ammonia", "value": "8", "result": ""}
            ],
            "summary": {"result_state": "合格"}
        }
    }
    plan = _build_placeholder_fill_plan(payload)
    assert len(plan) > 0, "ivc fill plan empty"
    assert any(k == 'IVC型号' and v == 'IVC-M60' for k, v in plan), "ivc_model missing"
    assert any(k == '笼具数量' and v == '60' for k, v in plan), "cage_count missing"
    assert any(k == '氨浓度' and v == '8' for k, v in plan), "ammonia missing"
    print(f"✅ ivc: {len(plan)} fields")
    return True

def test_export_mappings():
    assert 'bsc' in OBJECT_TITLE_MAP, "bsc not in OBJECT_TITLE_MAP"
    assert 'clean_bench' in OBJECT_TITLE_MAP, "clean_bench not in OBJECT_TITLE_MAP"
    assert 'ivc' in OBJECT_TITLE_MAP, "ivc not in OBJECT_TITLE_MAP"
    assert 'bsc' in OBJECT_NOTE_MAP, "bsc not in OBJECT_NOTE_MAP"
    assert 'clean_bench' in OBJECT_NOTE_MAP, "clean_bench not in OBJECT_NOTE_MAP"
    assert 'ivc' in OBJECT_NOTE_MAP, "ivc not in OBJECT_NOTE_MAP"
    print("✅ export mappings")
    return True

if __name__ == '__main__':
    try:
        test_export_mappings()
        test_bsc()
        test_clean_bench()
        test_ivc()
        print("\n🎉 所有测试通过")
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
