#!/bin/bash
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
exec python3 "$DIR/launcher_x1.py"
