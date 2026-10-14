#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-5000}"

if [[ -x "$PROJECT_DIR/venv/bin/python" ]]; then
  PYTHON="$PROJECT_DIR/venv/bin/python"
elif [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  PYTHON="$PROJECT_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

echo "Peredacha CRM: http://${HOST}:${PORT}"
echo "Для остановки нажмите Ctrl+C"
exec "$PYTHON" -m flask --app wsgi run --host "$HOST" --port "$PORT"
