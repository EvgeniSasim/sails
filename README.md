# Tender Lead Agents

Переписываем **с нуля**. Работаем через **консоль**; дашборд — позже, когда цикл сбора станет ясным.

## Задача 1

Менеджер задаёт **URL площадки** (пилот: [Сбербанк-АСТ](https://www.sberbank-ast.ru/)) и **ключевые слова** — система в браузере имитирует человека: cookie, поиск, фильтры, пагинация, карточки тендеров.

**ТЗ:** [docs/task-01-spec.md](docs/task-01-spec.md)  
**Jules (ручной запуск):** [prompts/jules-task01-roadmap.md](prompts/jules-task01-roadmap.md)

## Установка

```bash
pip install -e ".[browser]"
playwright install chromium
```

## Использование

### Проверка статуса
```bash
tender-leads status
```

### Smoke-тест браузера
```bash
tender-leads browse --url https://www.sberbank-ast.ru/
```

### Сбор тендеров (план)
```bash
tender-leads collect \
  --platform-url https://www.sberbank-ast.ru/ \
  -k "опрос сотрудников" \
  -k "CRM" \
  --date-from 2026-05-01 \
  -v
```

Секреты — в `.env` (не коммитить). См. `.env.example`.
