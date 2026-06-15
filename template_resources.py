from pathlib import Path
from typing import Dict, Any
import json
import os
import re
import hashlib
import shutil
import logging
from datetime import datetime

from config_loader import load_x1_config

_logger = logging.getLogger('template_resources')

BASE_DIR = Path(__file__).resolve().parent
CFG = load_x1_config(BASE_DIR)

# 从配置文件读取模板基础路径（运行时动态解析，避免模块导入时 HOME 被污染）
def _get_template_base():
    template_base = str(CFG.get('template_base', '~/公司资料/检测部/检测报告模板') or '~/公司资料/检测部/检测报告模板')
    # 强制用 passwd 数据库中的真实 home，不依赖 HOME 环境变量
    import pwd
    real_home = pwd.getpwuid(os.getuid()).pw_dir
    resolved = template_base.replace('~', real_home, 1) if template_base.startswith('~') else template_base
    return Path(resolved).resolve()

BASE = _get_template_base()
REGISTRY_FILE = BASE_DIR / 'template_registry.json'
TYPE_MAPPINGS_FILE = BASE_DIR / 'template_type_mappings.json'
SEMANTIC_MAPPINGS_FILE = BASE_DIR / 'template_semantic_mappings.json'

# ─── 启动自检 & 加载防护 ───────────────────────────────────────────
_HASH_FILE = Path(__file__).parent / 'logs_x1' / 'template_config_hashes.json'

def _file_sha256(path: Path) -> str:
    if not path.exists():
        return ''
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _save_hashes():
    """保存三张配置表的当前哈希，用于变更检测"""
    hashes = {
        'registry': _file_sha256(REGISTRY_FILE),
        'type_mappings': _file_sha256(TYPE_MAPPINGS_FILE),
        'semantic_mappings': _file_sha256(SEMANTIC_MAPPINGS_FILE),
        'saved_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    _HASH_FILE.parent.mkdir(parents=True, exist_ok=True)
    _HASH_FILE.write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    return hashes

def _check_config_integrity():
    """启动时校验三张配置表的 JSON 完整性 + 变更检测"""
    files = [
        ('template_registry', REGISTRY_FILE),
        ('template_type_mappings', TYPE_MAPPINGS_FILE),
        ('template_semantic_mappings', SEMANTIC_MAPPINGS_FILE),
    ]
    errors = []
    warnings = []
    for label, path in files:
        if not path.exists():
            warnings.append(f'[WARN] {label}: 文件不存在，将使用空配置')
            continue
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                errors.append(f'[ERROR] {label}: 顶层结构不是 dict，实际类型 {type(data).__name__}')
        except json.JSONDecodeError as e:
            errors.append(f'[CRITICAL] {label}: JSON 解析失败 → {e}')
            # 自动备份损坏文件
            bak = path.with_suffix(f'.corrupt_{datetime.now().strftime("%Y%m%d_%H%M%S")}.bak')
            shutil.copy2(path, bak)
            errors.append(f'  已备份损坏文件到 {bak.name}')

    # 变更检测
    if _HASH_FILE.exists():
        try:
            prev = json.loads(_HASH_FILE.read_text(encoding='utf-8'))
            for label, path in files:
                key = label.replace('template_', '')
                old_hash = prev.get(key, '')
                new_hash = _file_sha256(path)
                if old_hash and new_hash and old_hash != new_hash:
                    warnings.append(f'[CHANGE] {label}: 自上次启动以来文件已被修改')
        except Exception:
            pass

    # 更新哈希
    _save_hashes()

    for w in warnings:
        _logger.warning(w)
    for e in errors:
        _logger.error(e)
    if errors:
        print('\n'.join(['⚠️  模板配置完整性检查发现问题：'] + errors + ['请立即修复上述问题。']))
    return errors

def _safe_load_json(path: Path, label: str) -> Dict[str, Any]:
    """带防护的 JSON 加载：损坏时告警而非静默返回空"""
    if not path.exists():
        return {}
    try:
        raw = path.read_text(encoding='utf-8')
        data = json.loads(raw)
        if not isinstance(data, dict):
            _logger.error(f'{label}: 顶层结构不是 dict，返回空配置')
            return {}
        return data
    except json.JSONDecodeError as e:
        _logger.critical(f'{label}: JSON 解析失败 → {e}，返回空配置！请检查文件。')
        # 备份损坏文件
        bak = path.with_suffix(f'.corrupt_{datetime.now().strftime("%Y%m%d_%H%M%S")}.bak')
        try:
            shutil.copy2(path, bak)
            _logger.critical(f'{label}: 已备份损坏文件到 {bak.name}')
        except Exception:
            pass
        return {}
    except Exception as e:
        _logger.error(f'{label}: 加载异常 → {e}')
        return {}


def _normalize_template_entry(key: str, item: Dict[str, Any]) -> Dict[str, Any]:
    item = dict(item or {})
    rel = str(item.get('template_relpath') or '').strip()
    project_rel = str(item.get('template_project_relpath') or '').strip()
    path_value = str(item.get('template_path') or '').strip()
    _base = _get_template_base()  # 每次动态计算，避免模块级 BASE 被污染时拼错路径
    if rel:
        item['template_relpath'] = rel.replace('\\', '/')
        item['template_path'] = str((_base / item['template_relpath']).resolve())
    elif project_rel:
        item['template_project_relpath'] = project_rel.replace('\\', '/')
        item['template_path'] = str((BASE_DIR / item['template_project_relpath']).resolve())
    elif path_value:
        try:
            import pwd
            real_home = pwd.getpwuid(os.getuid()).pw_dir
            pv = path_value.replace('~', real_home, 1) if path_value.startswith('~') else path_value
            p = Path(pv).resolve()
            try:
                item['template_relpath'] = str(p.relative_to(_base)).replace('\\', '/')
            except Exception:
                try:
                    item['template_project_relpath'] = str(p.relative_to(BASE_DIR)).replace('\\', '/')
                except Exception:
                    pass
            item['template_path'] = str(p)
        except Exception:
            item['template_path'] = path_value
    return item


def _normalize_registry_dict(data: Dict[str, Any]) -> Dict[str, Any]:
    normalized = {}
    for key, value in (data or {}).items():
        if isinstance(value, dict):
            normalized[key] = _normalize_template_entry(key, value)
        else:
            normalized[key] = value
    return normalized

# 模块加载时执行自检
_check_config_integrity()
# ───────────────────────────────────────────────────────────────────

TEMPLATE_RESOURCE_REGISTRY = {
    'hospital/operating_room/main/level1': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净手术部手术室百级检测报告模板.docx'),
        'template_name': '医院洁净部洁净手术部手术室百级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已实测命中本机模板资源。',
    },
    'hospital/operating_room/main/level2': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净手术部手术室千级检测报告模板.docx'),
        'template_name': '医院洁净部洁净手术部手术室千级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已实测命中本机模板资源。',
    },
    'hospital/operating_room/main/level3': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净手术部手术室万级检测报告模板.docx'),
        'template_name': '医院洁净部洁净手术部手术室万级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已实测命中本机模板资源。',
    },
    'hospital/operating_room/main/level4': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净手术部手术室十万级检测报告模板.docx'),
        'template_name': '医院洁净部洁净手术部手术室十万级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已实测命中本机模板资源。',
    },
    'hospital/operating_room/aux/level1-local5-surround6': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前先映射到医院洁净部统一洁净功能用房模板，后续再细化辅房专属落点。',
    },
    'hospital/operating_room/aux/level2-iso7': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前先映射到医院洁净部统一洁净功能用房模板，后续再细化辅房专属落点。',
    },
    'hospital/operating_room/aux/level3-iso8': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前先映射到医院洁净部统一洁净功能用房模板，后续再细化辅房专属落点。',
    },
    'hospital/operating_room/aux/level4-iso85': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前先映射到医院洁净部统一洁净功能用房模板，后续再细化辅房专属落点。',
    },
    'hospital/clean_function_room/icu': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认 ICU 病房专属模板存在，当前优先映射到 ICU 专属模板。',
    },
    'hospital/clean_function_room/cssd': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认消毒供应中心专属模板存在，当前优先映射到消毒供应中心专属模板。',
    },
    'hospital/clean_function_room/dialysis': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认透析室专属模板存在，当前优先映射到透析室专属模板。',
    },
    'hospital/clean_function_room/general': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部洁净功能用房检测报告模板.docx'),
        'template_name': '医院洁净部洁净功能用房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认通用洁净功能用房专属模板存在。',
    },
    'biosafety/bsl/p2': {
        'template_path': str(BASE / '生物安全' / '生物安全实验室ISO6、ISO7、ISO8、ISO9检测报告模板.docx'),
        'template_name': '生物安全实验室ISO6、ISO7、ISO8、ISO9检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认生物安全目录存在实验室统一模板，当前 P2 先映射到该模板。',
    },
    'biosafety/bsl/p3': {
        'template_path': str(BASE / '生物安全' / '生物安全实验室ISO6、ISO7、ISO8、ISO9检测报告模板.docx'),
        'template_name': '生物安全实验室ISO6、ISO7、ISO8、ISO9检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认生物安全目录存在实验室统一模板，当前 P3 先映射到该模板。',
    },
    'pharma/gmp_workshop/grade/a': {
        'template_path': str(BASE / '制药工业' / '制药工业GMP车间A级检测报告模板.docx'),
        'template_name': '制药工业GMP车间A级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前 GMP A级先映射到制药工业统一 GMP 车间模板，后续再细化更具体模板落点。',
    },
    'pharma/gmp_workshop/grade/b': {
        'template_path': str(BASE / '制药工业' / '制药工业GMP车间B级C级检测报告模板.docx'),
        'template_name': '制药工业GMP车间B级C级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前 GMP B级先映射到制药工业统一 GMP 车间模板，后续再细化更具体模板落点。',
    },
    'pharma/gmp_workshop/grade/c': {
        'template_path': str(BASE / '制药工业' / '制药工业GMP车间B级C级检测报告模板.docx'),
        'template_name': '制药工业GMP车间B级C级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前 GMP C级先映射到制药工业统一 GMP 车间模板，后续再细化更具体模板落点。',
    },
    'pharma/gmp_workshop/grade/d': {
        'template_path': str(BASE / '制药工业' / '制药工业GMP车间D级检测报告模板.docx'),
        'template_name': '制药工业GMP车间D级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '当前 GMP D级先映射到制药工业统一 GMP 车间模板，后续再细化更具体模板落点。',
    },
    'pharma/veterinary_gmp_workshop/grade/a': {
        'template_path': str(BASE / '制药工业' / '制药工业兽药车间A级检测报告模板.docx'),
        'template_name': '制药工业兽药车间A级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '刘总新加入的兽药车间 A级专属模板，已落到本地模板目录并按正式文件名注册。',
    },
    'pharma/veterinary_gmp_workshop/grade/b': {
        'template_path': str(BASE / '制药工业' / '制药工业兽药车间B级C级检测报告模板.docx'),
        'template_name': '制药工业兽药车间B级C级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '兽药车间 B级当前映射到 B/C 级共用正式模板。',
    },
    'pharma/veterinary_gmp_workshop/grade/c': {
        'template_path': str(BASE / '制药工业' / '制药工业兽药车间B级C级检测报告模板.docx'),
        'template_name': '制药工业兽药车间B级C级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '兽药车间 C级当前映射到 B/C 级共用正式模板。',
    },
    'pharma/veterinary_gmp_workshop/grade/d': {
        'template_path': str(BASE / '制药工业' / '制药工业兽药车间D级检测报告模板.docx'),
        'template_name': '制药工业兽药车间D级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '兽药车间 D级当前映射到 D 级正式模板。',
    },
    'food/food_workshop/grade/1': {
        'template_path': str(BASE / '食品加工' / '食品加工洁净车间百级检测报告模板.docx'),
        'template_name': '食品加工洁净车间百级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '食品车间Ⅰ级当前先映射到食品加工统一洁净车间模板。',
    },
    'food/food_workshop/grade/2': {
        'template_path': str(BASE / '食品加工' / '食品加工洁净车间万级十万级三十万级检测报告模板.docx'),
        'template_name': '食品加工洁净车间万级十万级三十万级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '食品车间Ⅱ级当前先映射到食品加工统一洁净车间模板。',
    },
    'food/food_workshop/grade/3': {
        'template_path': str(BASE / '食品加工' / '食品加工洁净车间万级十万级三十万级检测报告模板.docx'),
        'template_name': '食品加工洁净车间万级十万级三十万级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '食品车间Ⅲ级当前先映射到食品加工统一洁净车间模板。',
    },
    'food/food_workshop/grade/4': {
        'template_path': str(BASE / '食品加工' / '食品加工洁净车间万级十万级三十万级检测报告模板.docx'),
        'template_name': '食品加工洁净车间万级十万级三十万级检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '食品车间Ⅳ级当前先映射到食品加工统一洁净车间模板。',
    },
    'hospital/negative_pressure/default': {
        'template_path': str(BASE / '医院洁净部' / '医院洁净部负压病房检测报告模板.docx'),
        'template_name': '医院洁净部负压病房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认医院洁净部存在负压病房模板，当前负压病房统一映射到该模板。',
    },
    'biosafety/animal_room/normal': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房普通环境检测报告模板.docx'),
        'template_name': '生物安全动物房普通环境检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认动物房普通环境专属模板存在。',
    },
    'biosafety/animal_room/barrier-main': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境主房间检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境主房间检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认动物房屏障环境主房间专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/洁物储存室': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-洁物储存室专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/灭菌后室区': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-灭菌后室区专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/洁净走廊': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-洁净走廊专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/污物走廊': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-污物走廊专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/缓冲间': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-缓冲间专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/二更': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-二更专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/清洗消毒室': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-清洗消毒室专属模板存在。',
    },
    'biosafety/animal_room/barrier-aux/一更': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房屏障环境洁净辅房检测报告模板.docx'),
        'template_name': '生物安全动物房屏障环境洁净辅房检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认屏障环境洁净辅房-一更专属模板存在。',
    },
    'biosafety/animal_room/isolation': {
        'template_path': str(BASE / '生物安全' / '生物安全动物房隔离环境检测报告模板.docx'),
        'template_name': '生物安全动物房隔离环境检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认动物房隔离环境专属模板存在。',
    },
    'pharma/pass_box/default': {
        'template_path': str(BASE / '制药工业' / '制药工业传递窗检测报告模板.docx'),
        'template_name': '制药工业传递窗检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认传递窗模板存在。',
    },
    'pharma/laminar_hood/default': {
        'template_path': str(BASE / '制药工业' / '制药工业层流罩检测报告模板.docx'),
        'template_name': '制药工业层流罩检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '已确认层流罩模板存在。',
    },
    'biosafety/bsc/default': {
        'template_path': str(BASE / '生物安全' / '生物安全生物安全柜检测报告模板.docx'),
        'template_name': '生物安全生物安全柜检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '生物安全柜检测报告模板，标准 YY 0569-2011。',
    },
    'biosafety/clean_bench/default': {
        'template_path': str(BASE / '生物安全' / '生物安全洁净工作台检测报告模板.docx'),
        'template_name': '生物安全洁净工作台检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '洁净工作台检测报告模板，标准 GB/T 25915.4-2010。',
    },
    'biosafety/ivc/default': {
        'template_path': str(BASE / '生物安全' / '生物安全IVC笼具检测报告模板.docx'),
        'template_name': '生物安全IVC笼具检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': 'IVC独立通气笼具检测报告模板，标准 GB 14925-2010。',
    },
    'electronics/electronics_workshop/iso/5': {
        'template_path': str(BASE / '精密制造' / '精密制造电子洁净车间ISO5检测报告模板.docx'),
        'template_name': '精密制造电子洁净车间ISO5检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '电子车间 ISO 5 等级，当前映射到精密制造统一洁净车间模板。',
    },
    'electronics/electronics_workshop/iso/6': {
        'template_path': str(BASE / '精密制造' / '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx'),
        'template_name': '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '电子车间 ISO 6 等级，当前映射到精密制造统一洁净车间模板。',
    },
    'electronics/electronics_workshop/iso/7': {
        'template_path': str(BASE / '精密制造' / '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx'),
        'template_name': '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '电子车间 ISO 7 等级，当前映射到精密制造统一洁净车间模板。',
    },
    'electronics/electronics_workshop/iso/8': {
        'template_path': str(BASE / '精密制造' / '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx'),
        'template_name': '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '电子车间 ISO 8 等级，当前映射到精密制造统一洁净车间模板。',
    },
    'electronics/electronics_workshop/iso/9': {
        'template_path': str(BASE / '精密制造' / '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx'),
        'template_name': '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx',
        'resource_status': 'confirmed',
        'resource_note': '电子车间 ISO 9 等级，当前映射到精密制造统一洁净车间模板。',
    },
}


def _load_registry_overlay() -> Dict[str, Any]:
    return _normalize_registry_dict(_safe_load_json(REGISTRY_FILE, 'template_registry'))


def _atomic_save_json(path: Path, data: Dict[str, Any]) -> None:
    """原子写入 JSON 文件：先写临时文件再 rename，防止截断"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)  # 原子替换

def _save_registry_overlay(data: Dict[str, Any]) -> None:
    normalized = _normalize_registry_dict(data)
    persist = {}
    for key, value in normalized.items():
        if isinstance(value, dict):
            item = dict(value)
            if item.get('template_relpath'):
                item['template_path'] = str((BASE / str(item['template_relpath']).replace('\\', '/')).resolve())
            elif item.get('template_project_relpath'):
                item['template_path'] = str((BASE_DIR / str(item['template_project_relpath']).replace('\\', '/')).resolve())
            persist[key] = item
        else:
            persist[key] = value
    _atomic_save_json(REGISTRY_FILE, persist)
    _save_hashes()  # 每次写入后更新哈希


def _load_type_mappings() -> Dict[str, Any]:
    return _safe_load_json(TYPE_MAPPINGS_FILE, 'template_type_mappings')


def _save_type_mappings(data: Dict[str, Any]) -> None:
    _atomic_save_json(TYPE_MAPPINGS_FILE, data)
    _save_hashes()


def _load_semantic_mappings() -> Dict[str, Any]:
    return _safe_load_json(SEMANTIC_MAPPINGS_FILE, 'template_semantic_mappings')


def _save_semantic_mappings(data: Dict[str, Any]) -> None:
    _atomic_save_json(SEMANTIC_MAPPINGS_FILE, data)
    _save_hashes()


def _semantic_key_aliases(semantic_key: str) -> list:
    raw = str(semantic_key or '').strip()
    if not raw:
        return []
    aliases = [raw]
    normalized = raw.lower().replace('（', '(').replace('）', ')')
    normalized = normalized.replace(' ', '').replace('/', '.').replace('-', '_')
    normalized = normalized.replace('a级', 'a').replace('b级', 'b').replace('c级', 'c').replace('d级', 'd')
    normalized = normalized.replace('Ⅰ级'.lower(), '1').replace('Ⅱ级'.lower(), '2').replace('Ⅲ级'.lower(), '3').replace('Ⅳ级'.lower(), '4')
    normalized = re.sub(r'\.+', '.', normalized)
    aliases.append(normalized)
    tail = normalized.split('.')[-1]
    base = '.'.join(normalized.split('.')[:-1])
    if tail in ('a', 'b', 'c', 'd', '1', '2', '3', '4', 'p2', 'p3'):
        aliases.append(f"{base}.{tail}")
    if 'iso' in normalized:
        aliases.append(normalized.replace('iso5', 'iso.5').replace('iso6', 'iso.6').replace('iso7', 'iso.7').replace('iso8', 'iso.8').replace('iso9', 'iso.9'))
    room_aliases = {
        'icu病房': 'icu',
        '消毒供应中心': 'cssd',
        '透析室': 'dialysis',
        '通用洁净功能用房': 'general',
    }
    for src, dst in room_aliases.items():
        aliases.append(normalized.replace(src, dst))
    dedup = []
    for item in aliases:
        item = str(item).strip('. ')
        if item and item not in dedup:
            dedup.append(item)
    return dedup


def list_template_semantic_mappings() -> Dict[str, Any]:
    return _load_semantic_mappings()


def get_semantic_template_mapping(semantic_key: str) -> Dict[str, Any]:
    data = _load_semantic_mappings()
    for alias in _semantic_key_aliases(semantic_key):
        current = data.get(alias)
        if isinstance(current, dict):
            current = dict(current)
            current.setdefault('allowed_template_keys', [])
            current.setdefault('default_template_key', '')
            current.setdefault('updated_at', '')
            current.setdefault('updated_by', '')
            current.setdefault('semantic_key', alias)
            return current
    return {
        'semantic_key': str(semantic_key or '').strip(),
        'allowed_template_keys': [],
        'default_template_key': '',
        'updated_at': '',
        'updated_by': '',
    }


def attach_template_key_to_semantic(semantic_key: str, template_key: str, updated_by: str = '') -> Dict[str, Any]:
    data = _load_semantic_mappings()
    key = _semantic_key_aliases(semantic_key)[0] if _semantic_key_aliases(semantic_key) else str(semantic_key or '').strip()
    current = data.get(key, {}) if isinstance(data.get(key, {}), dict) else {}
    allowed = list(current.get('allowed_template_keys', []) or [])
    if template_key and template_key not in allowed:
        allowed.append(template_key)
    current['allowed_template_keys'] = allowed
    current['semantic_key'] = key
    current['updated_at'] = current.get('updated_at') or ''
    current['updated_by'] = updated_by or current.get('updated_by', '')
    data[key] = current
    _save_semantic_mappings(data)
    return get_semantic_template_mapping(key)


def set_semantic_default_template(semantic_key: str, template_key: str, updated_by: str = '', updated_at: str = '') -> Dict[str, Any]:
    data = _load_semantic_mappings()
    key = _semantic_key_aliases(semantic_key)[0] if _semantic_key_aliases(semantic_key) else str(semantic_key or '').strip()
    current = data.get(key, {}) if isinstance(data.get(key, {}), dict) else {}
    allowed = list(current.get('allowed_template_keys', []) or [])
    if template_key and template_key not in allowed:
        allowed.append(template_key)
    current['semantic_key'] = key
    current['allowed_template_keys'] = allowed
    current['default_template_key'] = template_key
    current['updated_at'] = updated_at or current.get('updated_at', '')
    current['updated_by'] = updated_by or current.get('updated_by', '')
    data[key] = current
    _save_semantic_mappings(data)
    return get_semantic_template_mapping(key)


def list_template_type_mappings() -> Dict[str, Any]:
    return _load_type_mappings()


def get_type_template_mapping(type_id: str) -> Dict[str, Any]:
    data = _load_type_mappings()
    current = data.get(type_id, {}) if isinstance(data.get(type_id, {}), dict) else {}
    current.setdefault('allowed_template_keys', [])
    current.setdefault('default_template_key', '')
    current.setdefault('updated_at', '')
    current.setdefault('updated_by', '')
    return current


def attach_template_key_to_type(type_id: str, template_key: str, updated_by: str = '') -> Dict[str, Any]:
    data = _load_type_mappings()
    current = data.get(type_id, {}) if isinstance(data.get(type_id, {}), dict) else {}
    allowed = list(current.get('allowed_template_keys', []) or [])
    if template_key and template_key not in allowed:
        allowed.append(template_key)
    current['allowed_template_keys'] = allowed
    current['updated_at'] = current.get('updated_at') or ''
    current['updated_by'] = updated_by or current.get('updated_by', '')
    data[type_id] = current
    _save_type_mappings(data)
    return get_type_template_mapping(type_id)


def set_type_default_template(type_id: str, template_key: str, updated_by: str = '', updated_at: str = '') -> Dict[str, Any]:
    data = _load_type_mappings()
    current = data.get(type_id, {}) if isinstance(data.get(type_id, {}), dict) else {}
    allowed = list(current.get('allowed_template_keys', []) or [])
    if template_key and template_key not in allowed:
        allowed.append(template_key)
    current['allowed_template_keys'] = allowed
    current['default_template_key'] = template_key
    current['updated_at'] = updated_at or current.get('updated_at', '')
    current['updated_by'] = updated_by or current.get('updated_by', '')
    data[type_id] = current
    _save_type_mappings(data)
    return get_type_template_mapping(type_id)


def apply_type_default_template(template_rule: Dict[str, Any]) -> Dict[str, Any]:
    rule = dict(template_rule or {})
    if str(rule.get('resolver', '')).strip() == 'x1-template-rule+semantic-default':
        return rule
    # 若模板规则已命中特定模板（非兜底占位），不要再被 type default 覆盖
    existing_key = str(rule.get('template_key', '')).strip()
    if existing_key and ':' not in existing_key:
        return rule
    type_id = str(rule.get('type_id', '')).strip()
    if not type_id:
        return rule
    mapping = get_type_template_mapping(type_id)
    default_key = str(mapping.get('default_template_key', '')).strip()
    allowed = list(mapping.get('allowed_template_keys', []) or [])
    if not default_key or default_key not in allowed:
        return rule
    rule['template_key'] = default_key
    rule['resolver'] = 'x1-template-rule+type-default'
    return rule


def apply_semantic_default_template(project: Dict[str, Any], template_rule: Dict[str, Any]) -> Dict[str, Any]:
    from clean_class_semantics import build_clean_class_semantics
    rule = dict(template_rule or {})
    semantics = build_clean_class_semantics(project or {})
    semantic_key = str((semantics or {}).get('level_semantic_key', '')).strip()
    if not semantic_key:
        return rule
    mapping = get_semantic_template_mapping(semantic_key)
    default_key = str(mapping.get('default_template_key', '')).strip()
    allowed = list(mapping.get('allowed_template_keys', []) or [])
    if not default_key or default_key not in allowed:
        return rule
    rule['template_key'] = default_key
    rule['resolver'] = 'x1-template-rule+semantic-default'
    rule['semantic_key'] = semantic_key
    return rule


def get_effective_template_registry() -> Dict[str, Any]:
    merged = dict(TEMPLATE_RESOURCE_REGISTRY)
    overlay = _load_registry_overlay()
    for key, value in overlay.items():
        if isinstance(value, dict):
            merged[key] = value
    return merged


def register_template_resource(template_key: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    overlay = _load_registry_overlay()
    payload.setdefault('enabled', True)
    payload.setdefault('version', 'v1')
    payload.setdefault('last_verified_at', '')
    payload.setdefault('last_verify_result', '')
    payload.setdefault('last_verify_error', '')
    overlay[template_key] = payload
    _save_registry_overlay(overlay)
    return overlay[template_key]


def list_registered_template_resources() -> Dict[str, Any]:
    return _load_registry_overlay()


def update_template_resource(template_key: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    overlay = _load_registry_overlay()
    current = overlay.get(template_key, {})
    current.update(patch)
    current.setdefault('enabled', True)
    current.setdefault('version', 'v1')
    current.setdefault('last_verified_at', '')
    current.setdefault('last_verify_result', '')
    current.setdefault('last_verify_error', '')
    overlay[template_key] = current
    _save_registry_overlay(overlay)
    return current


def resolve_template_resource(template_rule: Dict[str, Any]) -> Dict[str, Any]:
    key = template_rule.get('template_key', '')
    overlay = _load_registry_overlay()
    effective_registry = get_effective_template_registry()
    matched = effective_registry.get(key, {})
    enabled = matched.get('enabled', True)
    path = matched.get('template_path', '')
    found = bool(path and Path(path).exists())
    status = matched.get('resource_status', 'missing' if not found else 'confirmed')
    if key in overlay and enabled is False:
        return {
            'template_key': key,
            'template_name': matched.get('template_name', template_rule.get('template_name', '')),
            'template_path': path,
            'template_found': False,
            'resource_status': 'disabled',
            'resource_note': matched.get('resource_note', ''),
            'resolver': 'x1-template-resource-registry-overlay-disabled',
        }
    return {
        'template_key': key,
        'template_name': matched.get('template_name', template_rule.get('template_name', '')),
        'template_path': path,
        'template_found': found,
        'resource_status': status,
        'resource_note': matched.get('resource_note', ''),
        'resolver': 'x1-template-resource-registry-overlay' if key in overlay else ('x1-template-resource-registry' if key in effective_registry else 'x1-template-resource-not-found'),
    }


# ============================================================
# 模板管理配置（供后台管理使用）
# ============================================================
TEMPLATE_MAP = {
    'gmp_workshop': {
        'name': 'GMP车间',
        'domain': 'pharma',
        'path': '制药工业/',
        'files': [
            '制药工业GMP车间A级检测报告模板.docx',
            '制药工业GMP车间B级C级检测报告模板.docx',
            '制药工业GMP车间D级检测报告模板.docx'
        ]
    },
    'veterinary_gmp_workshop': {
        'name': '兽药GMP车间',
        'domain': 'vet_pharma',
        'path': '制药工业/',
        'files': [
            '制药工业兽药车间A级检测报告模板.docx',
            '制药工业兽药车间B级C级检测报告模板.docx',
            '制药工业兽药车间D级检测报告模板.docx'
        ]
    },
    'operating_room': {
        'name': '洁净手术部',
        'domain': 'hospital',
        'path': '医院洁净部/',
        'files': [
            '医院洁净部洁净手术部手术室百级检测报告模板.docx',
            '医院洁净部洁净手术部手术室千级检测报告模板.docx',
            '医院洁净部洁净手术部手术室万级检测报告模板.docx',
            '医院洁净部洁净手术部手术室十万级检测报告模板.docx',
            '医院洁净部洁净手术部洁净辅房检测报告模板.docx',
            '医院洁净部洁净手术部眼科手术室百级检测报告模板.docx'
        ]
    },
    'clean_function_room': {
        'name': '洁净功能室',
        'domain': 'hospital',
        'path': '医院洁净部/',
        'files': ['医院洁净部洁净功能用房检测报告模板.docx']
    },
    'negative_pressure': {
        'name': '负压病房',
        'domain': 'hospital',
        'path': '医院洁净部/',
        'files': ['医院洁净部负压病房检测报告模板.docx']
    },
    'bsl': {
        'name': '生物安全实验室',
        'domain': 'biosafety',
        'path': '生物安全/',
        'files': ['生物安全实验室ISO6、ISO7、ISO8、ISO9检测报告模板.docx']
    },
    'animal_room': {
        'name': '动物房',
        'domain': 'biosafety',
        'path': '生物安全/',
        'files': [
            '生物安全动物房普通环境检测报告模板.docx',
            '生物安全动物房屏障环境主房间检测报告模板.docx',
            '生物安全动物房隔离环境检测报告模板.docx',
            '生物安全动物房屏障环境洁净辅房检测报告模板.docx'
        ]
    },
    'bsc': {
        'name': '生物安全柜',
        'domain': 'biosafety',
        'path': '生物安全/',
        'files': ['生物安全生物安全柜检测报告模板.docx']
    },
    'clean_bench': {
        'name': '洁净工作台',
        'domain': 'biosafety',
        'path': '生物安全/',
        'files': ['生物安全洁净工作台检测报告模板.docx']
    },
    'ivc': {
        'name': 'IVC笼具',
        'domain': 'biosafety',
        'path': '生物安全/',
        'files': ['生物安全IVC笼具检测报告模板.docx']
    },
    'pass_box': {
        'name': '传递窗',
        'domain': 'pharma',
        'path': '制药工业/',
        'files': ['制药工业传递窗检测报告模板.docx']
    },
    'laminar_hood': {
        'name': '层流罩',
        'domain': 'pharma',
        'path': '制药工业/',
        'files': ['制药工业层流罩检测报告模板.docx']
    },
    'food_workshop': {
        'name': '食品车间',
        'domain': 'food',
        'path': '食品加工/',
        'files': [
            '食品加工洁净车间百级检测报告模板.docx',
            '食品加工洁净车间万级十万级三十万级检测报告模板.docx'
        ]
    },
    'electronics_workshop': {
        'name': '电子车间',
        'domain': 'electronics',
        'path': '精密制造/',
        'files': [
            '精密制造电子洁净车间ISO5检测报告模板.docx',
            '精密制造电子洁净车间ISO6、ISO7、ISO8、ISO9检测报告模板.docx'
        ]
    },
}


TEMPLATE_OBJECT_OPTIONS = {
    'gmp_workshop': {'name': 'GMP车间', 'domain': 'pharma', 'path': '制药工业/'},
    'veterinary_gmp_workshop': {'name': '兽药GMP车间', 'domain': 'pharma', 'path': '制药工业/'},
    'food_workshop': {'name': '食品车间', 'domain': 'food', 'path': '食品加工/'},
    'electronics_workshop': {'name': '电子车间', 'domain': 'electronics', 'path': '精密制造/'},
    'operating_room': {'name': '洁净手术部', 'domain': 'hospital', 'path': '医院洁净部/'},
    'clean_function_room': {'name': '洁净功能用房', 'domain': 'hospital', 'path': '医院洁净部/'},
    'negative_pressure': {'name': '负压病房', 'domain': 'hospital', 'path': '医院洁净部/'},
    'bsl': {'name': '生物安全实验室', 'domain': 'biosafety', 'path': '生物安全/'},
    'animal_room': {'name': '动物房', 'domain': 'biosafety', 'path': '生物安全/'},
    'pass_box': {'name': '传递窗', 'domain': 'pharma', 'path': '制药工业/'},
    'laminar_hood': {'name': '层流罩', 'domain': 'pharma', 'path': '制药工业/'},
    'bsc': {'name': '生物安全柜', 'domain': 'biosafety', 'path': '生物安全/'},
    'clean_bench': {'name': '洁净工作台', 'domain': 'biosafety', 'path': '生物安全/'},
    'ivc': {'name': 'IVC笼具', 'domain': 'biosafety', 'path': '生物安全/'},
}
