#!/usr/bin/env bash
# Ежедневный сбор лидов. Добавьте в crontab:
# 0 8 * * * /path/to/agents/scripts/daily-cron.sh >> /path/to/agents/data/cron.log 2>&1

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

export SCRAPER_BACKEND="${SCRAPER_BACKEND:-httpx}"

VENV="${ROOT}/.venv/bin/tender-leads"
if [[ ! -x "$VENV" ]]; then
  echo "Run: cd $ROOT && python3 -m venv .venv && pip install -e '.[web]'"
  exit 1
fi

mkdir -p data

# zakupki — бесплатный нативный парсер; период 30 дней (OSM-01)
"$VENV" run -s zakupki --period-days 30 --max-per-keyword 15
"$VENV" export -o "data/leads_$(date +%Y%m%d).csv"
"$VENV" platform link-resolve 2>/dev/null || true
ANALYST="data/analyst_$(date +%Y%m%d).json"
"$VENV" platform analyst --period-days 30 -o "$ANALYST" 2>/dev/null || true

ROWS=$(tail -n +2 "data/leads_$(date +%Y%m%d).csv" 2>/dev/null | wc -l | tr -d ' ')
echo "[$(date -Iseconds)] Done. Rows: ${ROWS:-0}. Analyst: ${ANALYST}"
echo "OpenClaw: сообщите менеджеру число лидов, CSV и путь к analyst JSON."
