#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: ./run_x1_full_restore.sh <x1_full_bundle.tar.gz> [target_dir]"
  exit 1
fi

BUNDLE="$1"
TARGET_DIR="${2:-$(pwd)}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

python3 restore_x1_full_bundle.py "$BUNDLE" "$TARGET_DIR"
cd "$TARGET_DIR"

./init_x1_env.sh
python3 doctor_x1_migration.py
python3 smoke_test_x1.py

echo "[OK] full restore done: $TARGET_DIR"
