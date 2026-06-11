# Tender Lead Agents

Переписываем **с нуля**. Работаем через **консоль**; дашборд — позже, когда цикл сбора станет ясным.

## Задача 1

Менеджер задаёт **URL площадки** (пилот: [Сбербанк-АСТ](https://www.sberbank-ast.ru/)) и **ключевые слова** — система в браузере имитирует человека: cookie, поиск, фильтры, пагинация, карточки тендеров.

**ТЗ:** [docs/task-01-spec.md](docs/task-01-spec.md)  
**Jules (ручной запуск):** [prompts/jules-task01-roadmap.md](prompts/jules-task01-roadmap.md)

## Сейчас

```bash
pip install -e .
tender-leads status
```

Реализация сбора — по плану из ТЗ (шаг 1: CLI `collect`).

## Установка браузера (когда дойдём до шага 2)

```bash
pip install -e ".[browser]"
playwright install chromium
```

Секреты — в `.env` (не коммитить). См. `.env.example`.
