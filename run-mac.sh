#!/bin/zsh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

CRM_HOST="${CRM_HOST:-127.0.0.1}"
CRM_PORT="${PORT:-5000}"

if [[ -x "$PROJECT_DIR/venv/bin/python" ]]; then
  PYTHON="$PROJECT_DIR/venv/bin/python"
elif [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  PYTHON="$PROJECT_DIR/.venv/bin/python"
else
  PYTHON="python3"
fi

echo "Peredacha CRM: http://127.0.0.1:${CRM_PORT}"
echo "Для остановки нажмите Ctrl+C"
exec "$PYTHON" -m flask --app wsgi run --host "$CRM_HOST" --port "$CRM_PORT"
