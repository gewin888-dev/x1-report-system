#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: ./run_x1_restore_flow.sh <template_bundle.tar.gz>"
  exit 1
fi

ROOT="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$1"
cd "$ROOT"

echo "== 1/4 init env =="
./init_x1_env.sh

echo
echo "== 2/4 restore template bundle =="
python3 restore_x1_template_bundle.py "$BUNDLE"

echo
echo "== 3/4 doctor =="
python3 doctor_x1_migration.py

echo
echo "== 4/4 smoke test =="
python3 smoke_test_x1.py

echo
echo "[OK] restore flow done"
