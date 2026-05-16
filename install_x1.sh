#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== X1 install check =="

command -v python3 >/dev/null || { echo "[FAIL] python3 不存在"; exit 1; }
python3 --version

if command -v node >/dev/null 2>&1; then
  node -v
else
  echo "[WARN] node 未安装；若不需要重新构建前端，可暂时忽略"
fi

if [ -f requirements.txt ]; then
  echo "== pip install =="
  python3 -m pip install -r requirements.txt
else
  echo "[WARN] requirements.txt 不存在，跳过 pip 安装"
fi

if [ -f package.json ]; then
  echo "== npm install =="
  npm install || echo "[WARN] npm install 失败，请按需处理"
fi

echo "[OK] install_x1.sh 执行完成"
