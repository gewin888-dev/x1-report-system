#!/usr/bin/env python3
from pathlib import Path
import subprocess
import sys


def main():
    base_dir = Path(__file__).parent
    app = base_dir / 'app_x1.py'
    if not app.exists():
        raise FileNotFoundError(f'未找到主入口: {app}')
    cmd = [sys.executable, str(app)]
    raise SystemExit(subprocess.call(cmd, cwd=str(base_dir)))


if __name__ == '__main__':
    main()
