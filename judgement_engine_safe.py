"""
judgement_engine.py 安全包装器
为判定引擎添加统一异常处理，避免直接修改663行核心代码
"""

from typing import Any, Dict, Optional
from functools import wraps
import traceback

# 导入原始判定引擎
from judgement_engine import judge_room as _judge_room_original


def safe_judge_wrapper(func):
    """
    判定函数安全包装器装饰器
    """
    @wraps(func)
    def wrapper(project: Dict[str, Any], room: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            # 基础参数校验
            if not isinstance(room, dict):
                return {
                    'engine': 'error',
                    'error': 'room参数类型错误',
                    'result_state': '判定失败',
                }
            
            room_name = room.get('room_name', '未知房间')
            type_id = room.get('type_id', '')
            
            if not type_id:
                return {
                    'engine': 'error',
                    'error': 'type_id缺失',
                    'room_name': room_name,
                    'result_state': '判定失败',
                }
            
            # 调用原始判定函数
            try:
                result = func(project, room)
                return result
                
            except (ValueError, TypeError, KeyError) as e:
                # 数据格式错误
                return {
                    'engine': 'error',
                    'error': f'数据格式错误: {str(e)}',
                    'room_name': room_name,
                    'type_id': type_id,
                    'result_state': '判定失败',
                    'traceback': traceback.format_exc(),
                }
                
            except Exception as e:
                # 其他未知错误
                return {
                    'engine': 'error',
                    'error': f'判定异常: {type(e).__name__}: {str(e)}',
                    'room_name': room_name,
                    'type_id': type_id,
                    'result_state': '判定失败',
                    'traceback': traceback.format_exc(),
                }
                
        except Exception as e:
            # 最外层兜底异常捕获
            return {
                'engine': 'error',
                'error': f'系统错误: {type(e).__name__}: {str(e)}',
                'result_state': '判定失败',
                'traceback': traceback.format_exc(),
            }
    
    return wrapper


# 导出安全包装后的judge_room
judge_room = safe_judge_wrapper(_judge_room_original)


def test_safe_wrapper():
    """
    测试安全包装器
    """
    # 测试1: 正常数据
    print("测试1: 正常数据")
    result = judge_room(
        {},
        {
            'room_name': '测试房间',
            'type_id': 'operating_room',
            'clean_class': 'Ⅰ级',
            'params': []
        }
    )
    print(f"  结果: {result.get('result_state') if result else 'None'}")
    
    # 测试2: type_id缺失
    print("\n测试2: type_id缺失")
    result = judge_room({}, {'room_name': '测试房间'})
    print(f"  结果: {result.get('error')}")
    
    # 测试3: room不是字典
    print("\n测试3: room类型错误")
    result = judge_room({}, "not_a_dict")
    print(f"  结果: {result.get('error')}")
    
    print("\n✅ 安全包装器测试完成")


if __name__ == '__main__':
    test_safe_wrapper()
