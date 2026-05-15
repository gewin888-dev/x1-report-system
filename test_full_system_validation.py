#!/usr/bin/env python3
"""X系统全量验证测试 - 14个对象完整链路"""
import sys
import json
import time
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))

from app_x1 import app

# 14个对象的最小测试payload
TEST_CASES = [
    {
        'name': 'operating_room',
        'payload': {
            'domain': 'hospital',
            'project_name': '某医院手术室检测',
            'client_name': '某医院',
            'rooms': [{'type_id': 'operating_room', 'room_name': '手术室-01', 'clean_class': '百级', 'level_name': 'Ⅰ级', 'context': {'surgery_room_type': '手术室'}}]
        }
    },
    {
        'name': 'clean_function_room',
        'payload': {
            'domain': 'hospital',
            'project_name': '某医院洁净功能用房检测',
            'client_name': '某医院',
            'rooms': [{'type_id': 'clean_function_room', 'room_name': 'ICU-01', 'clean_class': '万级', 'level_name': 'Ⅲ级', 'context': {'clean_function_subroom': 'ICU病房'}}]
        }
    },
    {
        'name': 'negative_pressure',
        'payload': {
            'domain': 'hospital',
            'project_name': '某医院负压病房检测',
            'client_name': '某医院',
            'rooms': [{'type_id': 'negative_pressure', 'room_name': '负压病房-01', 'clean_class': '万级', 'level_name': 'Ⅲ级', 'context': {'negative_pressure_mode': 'standard'}}]
        }
    },
    {
        'name': 'bsl',
        'payload': {
            'domain': 'biosafety',
            'project_name': '某实验室检测',
            'client_name': '某研究所',
            'rooms': [{'type_id': 'bsl', 'room_name': 'P2实验室-01', 'clean_class': 'BSL-2（P2）', 'level_name': 'BSL-2（P2）', 'context': {'bsl_level': 'BSL-2（P2）'}}]
        }
    },
    {
        'name': 'animal_room',
        'payload': {
            'domain': 'biosafety',
            'project_name': '某动物房检测',
            'client_name': '某实验动物中心',
            'rooms': [{'type_id': 'animal_room', 'room_name': '屏障环境主房间-01', 'clean_class': '屏障环境', 'level_name': '屏障环境', 'context': {'animal_environment': '屏障环境', 'barrier_room_class': 'main'}}]
        }
    },
    {
        'name': 'bsc',
        'payload': {
            'domain': 'biosafety',
            'project_name': '某生物安全柜检测',
            'client_name': '某实验室',
            'rooms': [{'type_id': 'bsc', 'room_name': '生物安全柜-01'}]
        }
    },
    {
        'name': 'clean_bench',
        'payload': {
            'domain': 'biosafety',
            'project_name': '某洁净工作台检测',
            'client_name': '某实验室',
            'rooms': [{'type_id': 'clean_bench', 'room_name': '洁净工作台-01'}]
        }
    },
    {
        'name': 'ivc',
        'payload': {
            'domain': 'biosafety',
            'project_name': '某IVC笼具检测',
            'client_name': '某动物中心',
            'rooms': [{'type_id': 'ivc', 'room_name': 'IVC笼具-01'}]
        }
    },
    {
        'name': 'food_workshop',
        'payload': {
            'domain': 'food',
            'project_name': '某食品厂洁净车间检测',
            'client_name': '某食品有限公司',
            'rooms': [{'type_id': 'food_workshop', 'room_name': '包装车间-01', 'clean_class': 'Ⅰ级', 'level_name': 'Ⅰ级', 'food_grade': 'Ⅰ级'}]
        }
    },
    {
        'name': 'laminar_hood',
        'payload': {
            'domain': 'pharma',
            'project_name': '某层流罩检测',
            'client_name': '某制药厂',
            'rooms': [{'type_id': 'laminar_hood', 'room_name': '层流罩-01'}]
        }
    },
    {
        'name': 'pass_box',
        'payload': {
            'domain': 'pharma',
            'project_name': '某传递窗检测',
            'client_name': '某制药厂',
            'rooms': [{'type_id': 'pass_box', 'room_name': '传递窗-01'}]
        }
    },
    {
        'name': 'gmp_workshop',
        'payload': {
            'domain': 'pharma',
            'project_name': '某GMP车间检测',
            'client_name': '某制药有限公司',
            'rooms': [{'type_id': 'gmp_workshop', 'room_name': '无菌制剂车间-01', 'clean_class': 'A级', 'level_name': 'A级', 'gmp_grade': 'A级'}]
        }
    },
    {
        'name': 'veterinary_gmp_workshop',
        'payload': {
            'domain': 'pharma',
            'project_name': '某兽药厂洁净车间检测',
            'client_name': '某兽药有限公司',
            'rooms': [{'type_id': 'veterinary_gmp_workshop', 'room_name': '无菌制剂车间-01', 'clean_class': 'A级', 'level_name': 'A级', 'gmp_grade': 'A级'}]
        }
    },
    {
        'name': 'electronics_workshop',
        'payload': {
            'domain': 'electronics',
            'project_name': '某电子厂洁净车间检测',
            'client_name': '某电子科技有限公司',
            'rooms': [{'type_id': 'electronics_workshop', 'room_name': '组装车间-01', 'clean_class': 'ISO-7', 'level_name': 'ISO-7'}]
        }
    }
]

def test_object(case):
    """测试单个对象的完整链路"""
    name = case['name']
    payload = case['payload']
    
    print(f"\n{'='*60}")
    print(f"测试对象: {name}")
    print(f"{'='*60}")
    
    results = {
        'name': name,
        'template_ready': False,
        'filled_generated': False,
        'filled_size': 0,
        'record_generated': False,
        'record_size': 0,
        'error': None
    }
    
    try:
        with app.test_client() as client:
            # 登录
            client.post('/login', data={'username': 'admin', 'password': 'pudi2026'}, follow_redirects=True)
            # 补齐必填字段
            payload.setdefault('report_number', f'TEST-{name}-001')
            payload.setdefault('detection_date', '2026-05-08')
            for room in payload.get('rooms', []):
                room.setdefault('room_id', f'test-{name}-r1')
                room.setdefault('params', {})
            # 1. 导出测试
            resp = client.post('/api/x/submit_export',
                              data=json.dumps({'project': payload}),
                              content_type='application/json')
            data = resp.get_json()
            if data is None:
                results['error'] = f'响应非JSON: status={resp.status_code}'
                print(f'❌ 响应非JSON: {resp.status_code}')
                return results
            if data.get('error'):
                results['error'] = data['error']
                print(f'❌ 后端错误: {data["error"]}')
                return results
            
            results['template_ready'] = data.get('template_ready', False)
            
            # 检查报告生成（优先使用 docx_path，其次 filled_docx_path）
            report_path = data.get('docx_path') or data.get('filled_docx_path')
            if report_path and Path(report_path).exists():
                results['filled_generated'] = True
                results['filled_size'] = Path(report_path).stat().st_size
                print(f"✅ 报告生成: {results['filled_size']} bytes")
            else:
                print(f"❌ 报告生成失败")
                
            # 检查原始记录生成（bound_docx_path 或 record_docx_path）
            record_path = data.get('bound_docx_path') or data.get('record_docx_path')
            if record_path and Path(record_path).exists():
                results['record_generated'] = True
                results['record_size'] = Path(record_path).stat().st_size
                print(f"✅ 原始记录生成: {results['record_size']} bytes")
            else:
                print(f"❌ 原始记录生成失败")
                
    except Exception as e:
        results['error'] = str(e)
        print(f"❌ 异常: {e}")
    
    return results

def main():
    print("X系统全量验证测试")
    print(f"测试对象数量: {len(TEST_CASES)}")
    print(f"开始时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_results = []
    success_count = 0
    
    for case in TEST_CASES:
        result = test_object(case)
        all_results.append(result)
        if result['filled_generated'] and result['record_generated']:
            success_count += 1
    
    # 汇总报告
    print(f"\n{'='*60}")
    print("测试汇总")
    print(f"{'='*60}")
    print(f"总计: {len(TEST_CASES)} 个对象")
    print(f"成功: {success_count} 个")
    print(f"失败: {len(TEST_CASES) - success_count} 个")
    print(f"成功率: {success_count/len(TEST_CASES)*100:.1f}%")
    
    print(f"\n详细结果:")
    for r in all_results:
        status = "✅" if r['filled_generated'] and r['record_generated'] else "❌"
        print(f"{status} {r['name']}: 报告={r['filled_size']}B, 记录={r['record_size']}B")
        if r['error']:
            print(f"   错误: {r['error']}")
    
    print(f"\n结束时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    return 0 if success_count == len(TEST_CASES) else 1

if __name__ == '__main__':
    sys.exit(main())
