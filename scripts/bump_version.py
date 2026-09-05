#!/usr/bin/env python3
"""
X1系统版本号自动升级工具

用法:
  python scripts/bump_version.py patch   # 4.9.2 -> 4.9.3 (bug修复)
  python scripts/bump_version.py minor   # 4.9.2 -> 4.10.0 (新功能)
  python scripts/bump_version.py major   # 4.9.2 -> 5.0.0 (重大变更)
"""

import json
import sys
import re
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / 'x1_config.json'
CHANGELOG_FILE = BASE_DIR / 'CHANGELOG.md'


def load_config():
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_config(config):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
        f.write('\n')


def parse_version(version_str):
    """解析版本号 '4.9.2' -> (4, 9, 2)"""
    match = re.match(r'(\d+)\.(\d+)\.(\d+)', version_str)
    if not match:
        raise ValueError(f"无效的版本号格式: {version_str}")
    return tuple(map(int, match.groups()))


def bump_version(version_str, bump_type):
    """升级版本号"""
    major, minor, patch = parse_version(version_str)
    
    if bump_type == 'major':
        return f"{major + 1}.0.0"
    elif bump_type == 'minor':
        return f"{major}.{minor + 1}.0"
    elif bump_type == 'patch':
        return f"{major}.{minor}.{patch + 1}"
    else:
        raise ValueError(f"无效的升级类型: {bump_type}，必须是 major/minor/patch")


def update_changelog(old_version, new_version, bump_type):
    """更新CHANGELOG.md"""
    if not CHANGELOG_FILE.exists():
        content = "# X1系统更新日志\n\n"
    else:
        with open(CHANGELOG_FILE, 'r', encoding='utf-8') as f:
            content = f.read()
    
    today = datetime.now().strftime('%Y-%m-%d')
    
    type_labels = {
        'major': '重大版本',
        'minor': '功能更新',
        'patch': 'Bug修复'
    }
    
    new_entry = f"""
## [{new_version}] - {today}

**{type_labels[bump_type]}**

### 变更说明
- 待补充：请在此处添加本次更新的具体内容

"""
    
    # 在第一个 ## 之前插入新条目
    if '## [' in content:
        parts = content.split('## [', 1)
        content = parts[0] + new_entry.lstrip('\n') + '## [' + parts[1]
    else:
        content += new_entry
    
    with open(CHANGELOG_FILE, 'w', encoding='utf-8') as f:
        f.write(content)


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in ['major', 'minor', 'patch']:
        print(__doc__)
        sys.exit(1)
    
    bump_type = sys.argv[1]
    
    # 读取当前版本
    config = load_config()
    old_version = config.get('version', '0.0.0')
    
    # 升级版本号
    new_version = bump_version(old_version, bump_type)
    
    print(f"版本升级: {old_version} -> {new_version}")
    
    # 更新配置文件
    config['version'] = new_version
    save_config(config)
    print(f"✓ 已更新 {CONFIG_FILE}")
    
    # 更新CHANGELOG
    update_changelog(old_version, new_version, bump_type)
    print(f"✓ 已更新 {CHANGELOG_FILE}")
    
    print(f"\n下一步操作:")
    print(f"1. 编辑 CHANGELOG.md 补充本次更新内容")
    print(f"2. git add x1_config.json CHANGELOG.md")
    print(f"3. git commit -m 'chore: 升级版本至 {new_version}'")
    print(f"4. git push origin main")


if __name__ == '__main__':
    main()
