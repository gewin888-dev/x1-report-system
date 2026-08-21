"""
template_rules.py 安全包装器
为模板规则解析添加统一异常处理，避免直接修改620行核心代码
"""

from typing import Any, Dict
from functools import wraps
import traceback

# 导入原始模板规则函数
from template_rules import resolve_template_rule as _resolve_template_rule_original


def safe_template_rule_wrapper(func):
    """
    模板规则解析安全包装器装饰器
    """
    @wraps(func)
    def wrapper(project: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # 基础参数校验
            if not isinstance(project, dict):
                return {
                    'error': 'project参数类型错误',
                    'domain': 'unknown',
                    'type_id': 'unknown',
                    'level': 'unknown',
                }
            
            domain = project.get('domain', '')
            type_id = project.get('type_id', '')
            
            if not domain or not type_id:
                return {
                    'error': 'domain或type_id缺失',
                    'domain': domain,
                    'type_id': type_id,
                    'level': project.get('level', 'unknown'),
                }
            
            # 调用原始模板规则函数
            try:
                result = func(project)
                return result
                
            except (ValueError, TypeError, KeyError, AttributeError) as e:
                # 数据格式或属性错误
                return {
                    'error': f'模板规则解析错误: {str(e)}',
                    'domain': domain,
                    'type_id': type_id,
                    'level': project.get('level', 'unknown'),
                    'traceback': traceback.format_exc(),
                }
                
            except Exception as e:
                # 其他未知错误
                return {
                    'error': f'模板规则异常: {type(e).__name__}: {str(e)}',
                    'domain': domain,
                    'type_id': type_id,
                    'level': project.get('level', 'unknown'),
                    'traceback': traceback.format_exc(),
                }
                
        except Exception as e:
            # 最外层兜底异常捕获
            return {
                'error': f'系统错误: {type(e).__name__}: {str(e)}',
                'traceback': traceback.format_exc(),
            }
    
    return wrapper


# 导出安全包装后的resolve_template_rule
resolve_template_rule = safe_template_rule_wrapper(_resolve_template_rule_original)


def test_safe_wrapper():
    """
    测试安全包装器
    """
    # 测试1: 正常数据
    print("测试1: 正常数据")
    result = resolve_template_rule({
        'domain': 'hospital',
        'type_id': 'operating_room',
        'level': 'Ⅰ级',
    })
    print(f"  结果: {'error' in result and result['error'] or '成功'}")
    
    # 测试2: domain缺失
    print("\n测试2: domain缺失")
    result = resolve_template_rule({'type_id': 'operating_room'})
    print(f"  错误: {result.get('error')}")
    
    # 测试3: project不是字典
    print("\n测试3: project类型错误")
    result = resolve_template_rule("not_a_dict")
    print(f"  错误: {result.get('error')}")
    
    print("\n✅ 安全包装器测试完成")


if __name__ == '__main__':
    test_safe_wrapper()
