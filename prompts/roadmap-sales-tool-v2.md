# Prompt Spec: roadmap-sales-tool-v2

| Поле | Значение |
|------|----------|
| ID | `roadmap-sales-tool-v2` |
| Версия | 1.0 |
| North Star | Менеджер быстро получает потенциальных клиентов: тендеры + ЛПР + действие (КП) |
| Исполнители | Cursor Agent (продукт/UI), **Jules** (инфраструктура/обход блокировок) |

## Objective

Согласовать полный scope до реализации: юридика 152-ФЗ, устойчивость ЕИС, research с капчей, тендеры за период, расширенный профиль ЛПР, импорт Excel через агентов.

---

## Prompt (готово к копированию) — для product owner / lead dev

```markdown
## Role
Product architect для tender-lead-agents (FeedBackTalk sales tool).

## North Star
Менеджер за 15–30 мин видит очередь: кому, почему сейчас, что отправить.
Два потока: Тендеры (площадки) + Люди (ЛПР: HR/CX/топ), склейка по организации.

## Новые требования (v2)
1. **152-ФЗ / комплаенс** — только открытые источники; минимизация ПДн; журнал происхождения; флаг «канал проверен»; политика хранения (документ, не юрист).
2. **ЕИС** — устойчивый enrich (не printForm 404); fallback common-info; опция загрузки HTML менеджером.
3. **Contact research** — капча/блокировки: очередь задач; ручной ввод капчи менеджером ИЛИ внешний сервис (env); не автоспам.
4. **Тендеры за период** — фильтр publish/end/created в UI и API.
5. **Профиль ЛПР** — bio + мероприятия (выставка, доклад, конференция, интервью) отдельной сущностью или расширением appearances.
6. **Импорт Excel** — upload → агент маппит колонки → preview → commit в contact_profiles.

## Jules (jules.google.com)
Репозиторий уже подключён. Jules — на **инфраструктурные** задачи (см. prompts/jules-tasks-*.md), не на UX-копирайт.
После Jules — PR → ревью → merge.

## Deliverable
Обновить `docs/product-roadmap-v2.md`:
- Capability map (есть / частично / нет)
- Архитектура (mermaid): сбор → БД → очередь менеджера
- Backlog P0–P2 с owner: `cursor` | `jules` | `manager-process`
- Риски 152-ФЗ (чеклист для юриста)
```

## Output contract

- `docs/product-roadmap-v2.md`
- `prompts/jules-task-*.md` (уже в репо)
- Опционально: `AGENTS.md` в корне для Jules

## Changelog

| Дата | Изменение |
|------|-----------|
| 2026-05-20 | v1.0 — Jules + период + профиль + Excel |
