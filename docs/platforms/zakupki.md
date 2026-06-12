# zakupki.gov.ru (ЕИС)

## Тип адаптера
- **httpx** (без Playwright)
- `needs_browser = false`

## Поиск
- URL: `https://zakupki.gov.ru/epz/order/extendedsearch/results.html`
- Параметры: `searchString`, `pageNumber`, `sortBy=UPDATE_DATE`

## Парсинг
- Ссылки: `href="/epz/order/notice/.../common-info.html?regNumber=..."`
- Карточка: текстовые метки ЕИС (реестровый номер, цена, даты)

## Ограничения
- Только публичный поиск, без логина и платного API
- С датацентровых IP возможна блокировка — нужен сервер в РФ

## Установка
```bash
pip install -e ".[httpx]"
tender-leads probe-search --platform-url https://zakupki.gov.ru -k "crm" --max-per-keyword 3
```
