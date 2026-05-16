"""
tests/test_business/test_judgement_engine.py - 判定引擎回归测试
验证 judge_room 对各对象类型返回正确的判定结果
"""
import sys
sys.path.insert(0, '.')
import pytest
from judgement_engine import judge_room


def _make_room(type_id, params, level_name='', context=None):
    """构造最小 room 对象，params 为 {key: value} 简写"""
    formatted = {k: {'value': str(v)} for k, v in params.items()}
    room = {'type_id': type_id, 'params': formatted, 'level_name': level_name}
    if context:
        room['context'] = context
    return room


class TestOperatingRoom:
    def test_all_pass(self):
        """所有参数合格应判定为合格"""
        params = {
            'temperature': '23',
            'humidity': '50',
            'noise': '48',
            'illumination': '400',
        }
        room = _make_room('operating_room', params, 'Ⅰ级',
                          context={'surgery_room_type': '手术室'})
        project = {'domain': 'hospital', 'type_id': 'operating_room'}
        result = judge_room(project, room)
        assert result is not None
        assert result['result_state'] == '合格'

    def test_temperature_fail(self):
        """温度超标应判定为不合格"""
        params = {
            'temperature': '35',  # 严重超标
            'humidity': '50',
            'noise': '48',
            'illumination': '400',
        }
        room = _make_room('operating_room', params, 'Ⅰ级',
                          context={'surgery_room_type': '手术室'})
        project = {'domain': 'hospital', 'type_id': 'operating_room'}
        result = judge_room(project, room)
        assert result is not None
        assert result['result_state'] == '不合格'

    def test_level3(self):
        """Ⅲ级手术室判定"""
        params = {'temperature': '23', 'humidity': '50', 'noise': '48', 'illumination': '350'}
        room = _make_room('operating_room', params, 'Ⅲ级',
                          context={'surgery_room_type': '手术室'})
        project = {'domain': 'hospital', 'type_id': 'operating_room'}
        result = judge_room(project, room)
        assert result is not None
        assert result['result_state'] == '合格'


class TestGMPWorkshop:
    def test_grade_d_pass(self):
        """GMP D级 合格场景"""
        params = {'pressure': '12', 'noise': '60'}
        room = _make_room('gmp_workshop', params, 'D级')
        project = {'domain': 'pharma', 'type_id': 'gmp_workshop'}
        result = judge_room(project, room)
        assert result is not None
        assert result['result_state'] == '合格'

    def test_grade_a_pass(self):
        """GMP A级 合格场景"""
        params = {'pressure': '15', 'noise': '55'}
        room = _make_room('gmp_workshop', params, 'A级')
        project = {'domain': 'pharma', 'type_id': 'gmp_workshop'}
        result = judge_room(project, room)
        assert result is not None


class TestBSC:
    def test_basic(self):
        """生物安全柜基本判定"""
        params = {'inflow_velocity': '0.55', 'downflow_speed': '0.35', 'noise': '60'}
        room = _make_room('bsc', params)
        project = {'domain': 'biosafety', 'type_id': 'bsc'}
        result = judge_room(project, room)
        assert result is not None


class TestNegativePressure:
    def test_basic(self):
        """负压病房基本判定"""
        params = {'pressure': '-8', 'airchange': '12', 'temperature': '22', 'humidity': '55'}
        room = _make_room('negative_pressure', params)
        project = {'domain': 'hospital', 'type_id': 'negative_pressure'}
        result = judge_room(project, room)
        assert result is not None


class TestElectronicsWorkshop:
    def test_iso7(self):
        """精密制造 ISO7 判定"""
        params = {'pressure': '10', 'temperature': '22', 'humidity': '50', 'noise': '60'}
        room = _make_room('electronics_workshop', params, 'ISO 7')
        room['context'] = {'iso_level': 'ISO 7'}
        project = {'domain': 'electronics', 'type_id': 'electronics_workshop'}
        result = judge_room(project, room)
        assert result is not None
        assert result['result_state'] == '合格'


class TestFoodWorkshop:
    def test_level2(self):
        """食品 Ⅱ级判定"""
        params = {'pressure': '10', 'temperature': '22', 'humidity': '55'}
        room = _make_room('food_workshop', params, 'Ⅱ级')
        project = {'domain': 'food', 'type_id': 'food_workshop'}
        result = judge_room(project, room)
        assert result is not None


class TestReturnFormat:
    def test_result_has_state(self):
        """判定结果必须包含 result_state"""
        params = {'temperature': '22', 'humidity': '50'}
        room = _make_room('operating_room', params, 'Ⅲ级',
                          context={'surgery_room_type': '手术室'})
        project = {'domain': 'hospital', 'type_id': 'operating_room'}
        result = judge_room(project, room)
        assert result is not None
        assert 'result_state' in result

    def test_result_has_items(self):
        """判定结果应包含 item_results"""
        params = {'temperature': '22', 'humidity': '50'}
        room = _make_room('operating_room', params, 'Ⅲ级',
                          context={'surgery_room_type': '手术室'})
        project = {'domain': 'hospital', 'type_id': 'operating_room'}
        result = judge_room(project, room)
        assert result is not None
        assert 'item_results' in result
        assert len(result['item_results']) > 0

    def test_item_result_structure(self):
        """每个 item_result 应有 key/passed/range"""
        params = {'temperature': '22'}
        room = _make_room('operating_room', params, 'Ⅲ级',
                          context={'surgery_room_type': '手术室'})
        project = {'domain': 'hospital', 'type_id': 'operating_room'}
        result = judge_room(project, room)
        assert result is not None
        for item in result['item_results']:
            assert 'key' in item
            assert 'passed' in item
