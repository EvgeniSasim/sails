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
pip install -e ".[browser,dev]"
playwright install chromium

# 0. Тесты (offline)
pytest -m "not network"

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

# 4. Снимок страницы для отладки
tender-leads snapshot --url https://www.sberbank-ast.ru/purchaseview.aspx?id=123

tender-leads list --last 10
```

Если `найдено ссылок: 0` — селекторы в `docs/platforms/sberbank-ast.md` не совпадают с сайтом; править в `sberbank_ast.py` после просмотра с `--headed`.

## Если `ERR_CONNECTION_TIMED_OUT`

Сайт **не открывается с вашей сети** (не баг парсера). Проверьте в обычном Chrome: https://www.sberbank-ast.ru/

- Для полноценного сбора требуется российский IP (VPN или сервер в РФ, например `111.88.147.92`).
- С Mac без доступа к площадке сбор не пойдёт — только smoke `browse`/`collect` на сервере.
