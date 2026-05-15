#!/usr/bin/env python3
import json
from pathlib import Path


def load_x1_config(base_dir: Path):
    cfg_path = base_dir / 'x1_config.json'
    if not cfg_path.exists():
        raise FileNotFoundError(f'缺少配置文件: {cfg_path}')
    with open(cfg_path, 'r', encoding='utf-8') as f:
        return json.load(f)
