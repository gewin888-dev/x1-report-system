"""
tests/test_business/test_template_rules.py - 模板规则引擎回归测试
验证 resolve_template_rule 对各对象类型返回正确的模板 key
"""
import sys
sys.path.insert(0, '.')
import pytest
from template_rules import resolve_template_rule


def _make_project(domain, type_id, level_name='', context=None):
    """构造最小 project 对象"""
    room = {'type_id': type_id, 'level_name': level_name}
    if context:
        room['context'] = context
    return {'domain': domain, 'rooms': [room]}


class TestOperatingRoom:
    def test_main_level1(self):
        p = _make_project('hospital', 'operating_room', 'Ⅰ级',
                          context={'surgery_room_type': '手术室'})
        result = resolve_template_rule(p)
        assert result['template_key'] == 'hospital/operating_room/main/level1'

    def test_main_level3(self):
        p = _make_project('hospital', 'operating_room', 'Ⅲ级',
                          context={'surgery_room_type': '手术室'})
        result = resolve_template_rule(p)
        assert result['template_key'] == 'hospital/operating_room/main/level3'

    def test_auxiliary_room_level2(self):
        p = _make_project('hospital', 'operating_room', '',
                          context={'surgery_room_type': '辅房', 'surgery_aux_clean_class': 'Ⅱ级（7级）'})
        result = resolve_template_rule(p)
        assert result['template_key'] == 'hospital/operating_room/aux/level2'

    def test_eye_room(self):
        p = _make_project('hospital', 'operating_room', '',
                          context={'surgery_room_type': '眼科手术室'})
        result = resolve_template_rule(p)
        assert 'eye' in result.get('template_variant', '') or 'eye' in result.get('template_key', '')


class TestGMPWorkshop:
    def test_grade_a(self):
        p = _make_project('pharma', 'gmp_workshop', 'A级')
        result = resolve_template_rule(p)
        assert result['template_key'] == 'pharma/gmp_workshop/a'

    def test_grade_b(self):
        p = _make_project('pharma', 'gmp_workshop', 'B级')
        result = resolve_template_rule(p)
        assert result['template_key'] == 'pharma/gmp_workshop/b/c'

    def test_grade_c(self):
        p = _make_project('pharma', 'gmp_workshop', 'C级')
        result = resolve_template_rule(p)
        assert result['template_key'] == 'pharma/gmp_workshop/b/c'

    def test_grade_d(self):
        p = _make_project('pharma', 'gmp_workshop', 'D级')
        result = resolve_template_rule(p)
        assert result['template_key'] == 'pharma/gmp_workshop/d'


class TestNegativePressure:
    def test_basic(self):
        p = _make_project('hospital', 'negative_pressure', '')
        result = resolve_template_rule(p)
        assert 'negative_pressure' in result['template_key']


class TestElectronicsWorkshop:
    def test_iso5(self):
        p = _make_project('electronics', 'electronics_workshop', 'ISO 5级')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']

    def test_iso7(self):
        p = _make_project('electronics', 'electronics_workshop', 'ISO 7级')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']


class TestFoodWorkshop:
    def test_level1(self):
        p = _make_project('food', 'food_workshop', 'Ⅰ级')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']

    def test_level3(self):
        p = _make_project('food', 'food_workshop', 'Ⅲ级')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']


class TestBSL:
    def test_p2(self):
        p = _make_project('biosafety', 'bsl', '',
                          context={'bsl_level': 'P2'})
        result = resolve_template_rule(p)
        assert 'bsl' in result['template_key']

    def test_p3(self):
        p = _make_project('biosafety', 'bsl', '',
                          context={'bsl_level': 'P3'})
        result = resolve_template_rule(p)
        assert 'bsl' in result['template_key']


class TestEquipment:
    def test_bsc(self):
        p = _make_project('biosafety', 'bsc', '')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']

    def test_clean_bench(self):
        p = _make_project('biosafety', 'clean_bench', '')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']

    def test_pass_box(self):
        p = _make_project('pharma', 'pass_box', '')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']

    def test_laminar_hood(self):
        p = _make_project('pharma', 'laminar_hood', '')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']

    def test_ivc(self):
        p = _make_project('biosafety', 'ivc', '')
        result = resolve_template_rule(p)
        assert 'template_key' in result and result['template_key']


class TestCleanFunctionRoom:
    def test_icu(self):
        p = _make_project('hospital', 'clean_function_room', '',
                          context={'clean_function_subroom': 'ICU病房'})
        result = resolve_template_rule(p)
        assert 'icu' in result['template_key']

    def test_cssd(self):
        p = _make_project('hospital', 'clean_function_room', '',
                          context={'clean_function_subroom': '消毒供应中心'})
        result = resolve_template_rule(p)
        assert 'cssd' in result['template_key']


class TestAnimalRoom:
    def test_barrier(self):
        p = _make_project('biosafety', 'animal_room', '',
                          context={'animal_environment': '屏障环境'})
        result = resolve_template_rule(p)
        assert 'animal' in result['template_key']

    def test_ordinary(self):
        p = _make_project('biosafety', 'animal_room', '',
                          context={'animal_environment': '普通环境'})
        result = resolve_template_rule(p)
        assert 'animal' in result['template_key']
