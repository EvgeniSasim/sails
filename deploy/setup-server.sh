#!/usr/bin/env bash
# Первичная настройка на Ubuntu 24.04 (запускать НА СЕРВЕРЕ в ~/agents).
set -euo pipefail
cd "$(dirname "$0")/.."
AGENTS_ROOT="$(pwd)"

echo "==> APT packages"
sudo apt-get update -qq
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
  python3 python3-venv python3-pip rsync nginx

echo "==> venv + install"
python3 -m venv .venv
.venv/bin/pip install -U pip wheel
.venv/bin/pip install -e ".[web,excel]"

mkdir -p data/imports

if [[ ! -f .env ]]; then
  cp deploy/env.production.example .env
  echo "Создан .env из deploy/env.production.example — добавьте секреты: nano .env"
fi

echo "==> systemd"
sudo cp deploy/tender-agents.service /etc/systemd/system/tender-agents.service
sudo systemctl daemon-reload
sudo systemctl enable tender-agents.service
sudo systemctl restart tender-agents.service

echo "==> nginx (optional)"
if command -v nginx >/dev/null; then
  sudo cp deploy/nginx-tender-agents.conf /etc/nginx/sites-available/tender-agents
  sudo ln -sf /etc/nginx/sites-available/tender-agents /etc/nginx/sites-enabled/tender-agents
  sudo rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
  sudo nginx -t
  sudo systemctl enable nginx
  sudo systemctl reload nginx
fi

echo "==> ufw"
if command -v ufw >/dev/null; then
  sudo ufw allow OpenSSH
  sudo ufw allow 80/tcp
  sudo ufw allow 443/tcp
  sudo ufw allow 8765/tcp
  sudo ufw --force enable || true
fi

echo "==> status"
systemctl is-active tender-agents.service
curl -sf -o /dev/null -w "local:%{http_code}\n" http://127.0.0.1:8765/ || true
