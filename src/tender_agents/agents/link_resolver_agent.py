"""Связи тендер ↔ компания ↔ ЛПР (эвристика + опционально LLM)."""

from __future__ import annotations

import logging
from typing import Any

from tender_agents.db import LeadRepository

logger = logging.getLogger(__name__)


async def resolve_links_batch(
    repo: LeadRepository,
    *,
    max_tenders: int = 350,
    max_contacts: int = 2500,
    rebuild: bool = True,
) -> dict[str, Any]:
    """Пересобрать suggested-связи по совпадению организаций."""
    cr = repo.contacts_repo()
    if rebuild:
        added = await cr.rebuild_suggested_tender_contact_links(
            max_tenders=max_tenders,
            max_contacts=max_contacts,
        )
    else:
        added = 0
    by_status = await cr.count_links_by_status()
    return {
        "suggested_added": added,
        "links_by_status": by_status,
        "notes": "Подтвердите связи в карточке тендера или /queue.",
    }
