# Задача 02: стабильность браузера и smoke

После merge задачи 01 (Jules 01–09).

## Что сделано

- `goto` с `domcontentloaded` вместо `networkidle` (меньше таймаутов).
- Карточки через `session.goto` (cookie + captcha).
- Авто-регистрация адаптеров: `import tender_agents.platforms`.
- Ужесточена эвристика капчи (без ложного `"captcha"` в HTML).
- Валидация `--store`, фикс `title is None` в probe-search.

## Smoke (с вашей машины)

```bash
pip install -e ".[browser]"
playwright install chromium

# 1. Браузер
tender-leads browse --url https://www.sberbank-ast.ru/ --headed

# 2. Только ссылки
tender-leads probe-search \
  --platform-url https://www.sberbank-ast.ru/ \
  -k "закупка" --max-pages 1 --headed -v

# 3. Полный сбор (малый лимит)
tender-leads collect \
  --platform-url https://www.sberbank-ast.ru/ \
  -k "crm" --max-per-keyword 3 --max-pages 1 --headed -v

tender-leads list --last 10
```

Если `найдено ссылок: 0` — селекторы в `docs/platforms/sberbank-ast.md` не совпадают с сайтом; править в `sberbank_ast.py` после просмотра с `--headed`.
