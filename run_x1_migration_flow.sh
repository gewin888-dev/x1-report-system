#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== 1/4 doctor =="
python3 doctor_x1_migration.py

echo
echo "== 2/4 pack templates =="
PACK_OUTPUT="$(python3 pack_x1_templates.py)"
echo "$PACK_OUTPUT"
TARBALL="$(printf '%s' "$PACK_OUTPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["tarball"])')"
BUNDLE_DIR="$(printf '%s' "$PACK_OUTPUT" | python3 -c 'import json,sys; print(json.load(sys.stdin)["bundle_dir"])')"

echo
echo "== 3/4 verify template bundle =="
python3 verify_x1_template_bundle.py "$BUNDLE_DIR"

echo
echo "== 4/4 smoke test =="
python3 smoke_test_x1.py

echo
echo "[OK] migration flow done"
echo "bundle_dir=$BUNDLE_DIR"
echo "tarball=$TARBALL"
