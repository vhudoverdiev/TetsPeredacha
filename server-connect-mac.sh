#!/bin/zsh
set -euo pipefail

# Заполните данные сервера перед первым использованием.
SERVER_USER="root"
SERVER_IP="135.106.139.229"
SERVER_PORT="22"

if [[ -z "$SERVER_IP" || "$SERVER_IP" == *"ВСТАВЬТЕ"* || "$SERVER_IP" == *"IP_СЕРВЕРА"* ]]; then
  echo "Откройте server-connect-mac.sh и укажите SERVER_IP."
  exit 1
fi

echo "Подключаюсь к ${SERVER_USER}@${SERVER_IP}:${SERVER_PORT}..."
exec ssh -p "$SERVER_PORT" "${SERVER_USER}@${SERVER_IP}"
