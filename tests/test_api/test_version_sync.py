import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]


def _cfg_version():
    with open(BASE_DIR / 'x1_config.json', 'r', encoding='utf-8') as f:
        return json.load(f).get('version')


def test_login_page_uses_config_version(client):
    version = _cfg_version()
    resp = client.get('/login')
    text = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert version in text


def test_record_page_template_uses_dynamic_version_placeholder():
    tpl = (BASE_DIR / 'templates' / 'record_index.html').read_text(encoding='utf-8')
    assert '{{ version }}' in tpl
    assert 'X4.7' not in tpl
    assert 'X4.6' not in tpl


def test_admin_template_uses_dynamic_version_fallback():
    tpl = (BASE_DIR / 'templates' / 'admin.html').read_text(encoding='utf-8')
    assert "'{{ version }}'" in tpl
    assert "'X4.6'" not in tpl
    assert "'X4.7'" not in tpl


def test_source_tree_has_no_hardcoded_runtime_versions():
    targets = [
        BASE_DIR / 'app_x1.py',
        BASE_DIR / 'routes' / 'settings.py',
        BASE_DIR / 'routes' / 'template_mgmt.py',
        BASE_DIR / 'helpers' / 'settings_utils.py',
        BASE_DIR / 'helpers' / 'export_utils.py',
        BASE_DIR / 'static' / 'x-model.js',
        BASE_DIR / 'templates' / 'login.html',
        BASE_DIR / 'templates' / 'record_index.html',
        BASE_DIR / 'templates' / 'admin.html',
    ]
    forbidden_exact = ["'X4.6'", '"X4.6"', "'X4.7'", '"X4.7"', "'X4.7.1'", '"X4.7.1"', "'X4.7.2'", '"X4.7.2"']
    for path in targets:
        text = path.read_text(encoding='utf-8')
        for item in forbidden_exact:
            assert item not in text, f'{path} still contains hardcoded version literal: {item}'
