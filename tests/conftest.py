"""
tests/conftest.py - pytest 配置与共享 fixtures
"""
import sys
import os
from pathlib import Path

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest


@pytest.fixture
def app():
    """创建测试用 Flask app"""
    # 延迟导入避免副作用
    os.environ.setdefault('X1_TESTING', '1')
    from app_x1 import app as flask_app
    flask_app.config['TESTING'] = True
    flask_app.config['WTF_CSRF_ENABLED'] = False
    return flask_app


@pytest.fixture
def client(app):
    """Flask 测试客户端"""
    return app.test_client()


@pytest.fixture
def base_dir():
    """项目根目录"""
    return PROJECT_ROOT
