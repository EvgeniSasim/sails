"""Промпты для LLM-скрапинга (Crawl4AI, ScrapeGraph). Синхрон с yandex_agents search/enrich."""

TENDER_LIST_PROMPT = """На странице результатов поиска закупок извлеки список записей, релевантных ключевому слову и опросам/HR/CX/исследованиям (FeedBackTalk).
Для каждой: title, url (полная https-ссылка на карточку), external_id если есть, status_hint (active|completed|unknown), customer_hint.
Только данные со страницы. Ответ — только JSON без markdown: {"items": [...]} или {"items": []}."""

TENDER_DETAIL_PROMPT = """На странице карточки закупки извлеки только видимые данные (не выдумывай):
title, customer_name, customer_inn, price, publish_date, end_date (YYYY-MM-DD или null), status, description_snippet,
contacts — массив {name, role, phone, email, organization} или [].
Ответ — только JSON без markdown с этими полями."""
