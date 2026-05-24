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

# zakupki — бесплатный нативный парсер; для B2B добавьте -b playwright
"$VENV" run -s zakupki -k "проведение онлайн опросов" -k "онлайн опрос" --max-per-keyword 15
"$VENV" export -o "data/leads_$(date +%Y%m%d).csv"

echo "[$(date -Iseconds)] Done. Rows: $(tail -n +2 "data/leads_$(date +%Y%m%d).csv" | wc -l | tr -d ' ')"
