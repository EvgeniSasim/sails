# Tender Lead Agents

Система многоагентного поиска B2B-лидов. Задача 1: сбор тендеров с площадок.

## Основные возможности
- Сбор данных с площадки **Сбербанк-АСТ** (пилотный адаптер).
- Имитация поведения человека: случайные задержки, работа с cookie, прокрутка страниц.
- Автоматическое сохранение в **JSONL** и **SQLite**.
- Скриншоты ошибок и капчи в `data/debug/`.
- Просмотр результатов через CLI.

## Установка

Требуется Python 3.11+.

```bash
# Установка пакета с поддержкой браузера
pip install -e ".[browser]"

# Установка браузеров Playwright
playwright install chromium
```

## Использование

### Сбор тендеров
Команда `collect` запускает процесс сбора по ключевым словам.

```bash
tender-leads collect \
  --platform-url https://www.sberbank-ast.ru/ \
  -k "опрос сотрудников" \
  -k "CRM" \
  --date-from 2024-05-01 \
  --max-per-keyword 10 \
  --max-pages 3 \
  -v
```

**Параметры:**
- `--platform-url`: Базовый URL площадки.
- `-k, --keyword`: Ключевое слово (можно указывать несколько раз).
- `--date-from`: Дата начала публикации (ГГГГ-ММ-ДД).
- `--max-per-keyword`: Лимит лотов на одно ключевое слово (по умолчанию 10).
- `--max-pages`: Макс. количество страниц поиска на ключ (по умолчанию 5).
- `-v, --verbose`: Подробный лог с временными метками.
- `--headed`: Запустить браузер в видимом режиме (для отладки).

### Просмотр результатов
```bash
# Показать последние 20 тендеров из базы данных
tender-leads list --last 20

# Просмотр деталей одного тендера по ID или URL
tender-leads show --id 12345
tender-leads show --url https://www.sberbank-ast.ru/purchaseview.aspx?id=100
```

## Экспорт для Excel
Команда `export` позволяет выгрузить тендеры в формате CSV, который открывается в Excel без проблем с кодировкой (UTF-8 с BOM).

```bash
# Экспорт последних 100 тендеров (путь по умолчанию: data/export/tenders-{date}.csv)
tender-leads export --last 100

# Экспорт с фильтром по площадке и в конкретный файл
tender-leads export --platform sberbank-ast --output my_export.csv
```

## Данные и отладка
- `data/collect/`: Результаты в формате `.jsonl` (именуются по дате и площадке).
- `data/leads.db`: База данных SQLite с собранными тендерами.
- `data/debug/`: Скриншоты страниц при возникновении ошибок или обнаружении капчи.

## Тестирование
Для запуска тестов используйте `pytest`.

```bash
# Запуск всех тестов, кроме тех, что требуют живой сети
pytest -m "not network"
```

## Вторая площадка: zakupki.gov.ru
Сбор через httpx (без браузера):

```bash
pip install -e ".[httpx]"
tender-leads probe-search --platform-url https://zakupki.gov.ru -k "crm" --max-per-keyword 3
```

## LLM fallback (опционально)
Если leaf/текст не дали `title` или `external_id`, можно включить Yandex GPT:

```bash
export YANDEX_API_KEY=...
export YANDEX_FOLDER_ID=...
tender-leads collect --platform-url https://www.sberbank-ast.ru/ -k "crm" --llm-fallback
```

Флаг медленный и платный — не для каждого лота по умолчанию.

```bash
# Тесты, требующие сеть
pytest -m "network"
```

### Снимок страницы для отладки
Если данные не парсятся, можно сохранить текстовый снимок и leaf-поля:
```bash
tender-leads snapshot --url "https://www.sberbank-ast.ru/purchaseList.aspx"
```
Файлы будут сохранены в `data/debug/snapshot-{timestamp}.txt` и `.json`.

**Лимиты и вежливость:**
Система использует одну сессию браузера и последовательно обходит ключи с задержками 0.8–2.5 сек. Не рекомендуется запускать сбор слишком часто во избежание блокировок. Если вы видите в логе «Нужен ручной ввод», значит сработала защита от роботов — остановите сбор и попробуйте позже или с другого IP.

## Документация
- [ТЗ Задача 1](docs/task-01-spec.md)
- [История сессий Jules](docs/jules-sessions.md)
