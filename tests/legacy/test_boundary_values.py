#!/usr/bin/env python3
"""
边界值测试：验证系统当前是否存在“后端自动标准判定”。
结论导向：如果 summary.result_state 原样回传，而不是随 params 自动变化，
则说明当前系统并未在 submit_export 时执行真正的标准边界判定。
"""
import requests
import json

BASE = "http://localhost:8082"
s = requests.Session()


def login():
    s.get(f"{BASE}/login", timeout=10)
    r = s.post(f"{BASE}/login", data={"username": "admin", "password": "pudi2026"}, allow_redirects=True, timeout=10)
    return r.status_code == 200


def submit(project):
    r = s.post(f"{BASE}/api/x/submit_export", json={"project": project}, timeout=30)
    return r.status_code, r.json() if 'application/json' in r.headers.get('content-type','') else {"raw": r.text[:200]}


def build_project(type_id, room_name, clean_class, summary_state, params, domain="hospital", extra_context=None):
    room = {
        "room_id": "r1",
        "room_name": room_name,
        "type_id": type_id,
        "type_name": type_id,
        "level_name": clean_class,
        "clean_class": clean_class,
        "basis": ["TEST"],
        "judgement": ["TEST"],
        "params": params,
        "summary": {"result_state": summary_state},
        "context": extra_context or {},
    }
    return {
        "project_name": f"边界值测试-{type_id}",
        "report_number": f"BOUNDARY-{type_id}",
        "client_name": "测试客户",
        "contact_info": "测试联系人",
        "project_address": "测试地址",
        "inspection_area": "测试区域",
        "detection_date": "2026-05-01",
        "domain": domain,
        "domain_name": domain,
        "rooms": [room],
    }


def extract_state(resp_json):
    ep = resp_json.get("export_payload") or {}
    room = ep.get("room") or {}
    summary = room.get("summary") or {}
    return summary.get("result_state")


def run_case(name, project, expected_echo):
    code, data = submit(project)
    actual = extract_state(data) if code == 200 else None
    ok = code == 200 and actual == expected_echo
    print(("✅" if ok else "❌"), name, f"HTTP={code}", f"result_state={actual!r}", f"expected_echo={expected_echo!r}")
    return ok, {"name": name, "http": code, "actual": actual, "expected": expected_echo}


if __name__ == '__main__':
    if not login():
        print("❌ 登录失败")
        raise SystemExit(1)

    cases = []

    # 1) operating_room I级：给明显超标温度，但 summary 强行写 合格
    cases.append(run_case(
        "operating_room I级 超标温度 + summary=合格",
        build_project("operating_room", "手术室1", "Ⅰ级（百级）", "合格", {"temperature": {"type": "numeric", "values": ["30"], "result": "30 ❌"}}),
        "合格"
    ))

    # 2) operating_room I级：给明显正常温度，但 summary 强行写 不合格
    cases.append(run_case(
        "operating_room I级 正常温度 + summary=不合格",
        build_project("operating_room", "手术室2", "Ⅰ级（百级）", "不合格", {"temperature": {"type": "numeric", "values": ["23"], "result": "23 ✅"}}),
        "不合格"
    ))

    # 3) gmp_workshop A级
    cases.append(run_case(
        "gmp_workshop A级 超标温度 + summary=合格",
        build_project("gmp_workshop", "A级间", "A级", "合格", {"temperature": {"type": "numeric", "values": ["35"], "result": "35 ❌"}}, domain="pharma", extra_context={"gmp_grade": "A级", "gmp_context_mode": "grade-driven"}),
        "合格"
    ))

    # 4) bsc
    cases.append(run_case(
        "bsc 超低风速 + summary=合格",
        build_project("bsc", "BSC-01", "_default", "合格", {"wind_speed": {"type": "numeric", "values": ["0.10"], "result": "0.10 ❌"}}, domain="biosafety"),
        "合格"
    ))

    # 5) animal_room 屏障环境
    cases.append(run_case(
        "animal_room 屏障环境 超标温度 + summary=不合格",
        build_project("animal_room", "屏障饲养室", "屏障环境", "不合格", {"temperature": {"type": "numeric", "values": ["30"], "result": "30 ❌"}}, domain="biosafety", extra_context={"animal_environment": "屏障环境", "barrier_room_class": "饲养室"}),
        "不合格"
    ))

    passed = sum(1 for ok, _ in cases if ok)
    total = len(cases)
    print(f"\n汇总: {passed}/{total} 用例按预期回传 summary.result_state")
    if passed == total:
        print("结论: 当前 submit_export 未见后端自动边界判定；result_state 主要由输入 payload 的 summary 直接驱动。")
    else:
        print("结论: 存在与直接回传不一致的情况，需要继续排查。")
