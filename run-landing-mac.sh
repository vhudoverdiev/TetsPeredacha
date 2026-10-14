#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR/landing"

PORT="${LANDING_PORT:-8080}"

echo "Лендинг: http://127.0.0.1:${PORT}"
echo "Для остановки нажмите Ctrl+C"
exec python3 -m http.server "$PORT" --bind 127.0.0.1
