#!/usr/bin/env bash
# Синхронизация проекта на прод (с Mac).
# Использование: ./deploy/rsync-to-server.sh
# Опционально: RSYNC_DEST=ts-ai-es:~/agents ./deploy/rsync-to-server.sh

set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEST="${RSYNC_DEST:-ts-ai-es:~/agents}"

rsync -avz --delete \
  --exclude '.venv/' \
  --exclude '.git/' \
  --exclude '.env' \
  --exclude 'data/' \
  --exclude '__pycache__/' \
  --exclude '*.py[cod]' \
  --exclude '.pytest_cache/' \
  --exclude '.ruff_cache/' \
  --exclude '.DS_Store' \
  --exclude '*.egg-info/' \
  --exclude 'dist/' \
  --exclude 'web_server.log' \
  "$ROOT/" "$DEST/"

echo "OK → $DEST"
