TENDER_LIST_PROMPT = """На странице результатов поиска закупок/тендеров извлеки список записей.
Для каждой записи верни: title, url (полная ссылка на карточку), external_id если есть,
status_hint (активна/завершена/неизвестно), customer_hint (заказчик если виден).
Верни JSON: {"items": [...]}"""

TENDER_DETAIL_PROMPT = """На странице карточки закупки/тендера извлеки:
title, customer_name, customer_inn, price, publish_date, end_date, status,
description_snippet (кратко), contacts — массив объектов с полями name, role, phone, email, organization.
Верни JSON с этими полями."""
