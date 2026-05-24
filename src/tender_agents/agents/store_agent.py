"""Store Agent — сохраняет лиды в БД с скорингом и питчем."""

from __future__ import annotations

import logging

from tender_agents.db import LeadRepository
from tender_agents.models import TenderLead
from tender_agents.pitches import build_pitch
from tender_agents.scoring import score_lead
from tender_agents.text_utils import normalize_title

logger = logging.getLogger(__name__)


def prepare_lead(lead: TenderLead) -> TenderLead:
    lead.title = normalize_title(lead.title)
    score, segment, reasons = score_lead(lead)
    lead.score = score
    lead.segment = segment
    lead.score_reasons = reasons
    lead.pitch = build_pitch(lead, segment)
    return lead


class StoreAgent:
    def __init__(self, repo: LeadRepository):
        self.repo = repo

    async def run(self, leads: list[TenderLead]) -> int:
        tenders = [l for l in leads if l.channel != "open_media"]
        media = [l for l in leads if l.channel == "open_media"]
        saved = 0
        for lead in tenders:
            await self.repo.upsert(prepare_lead(lead))
            saved += 1
            logger.debug("Stored: %s (score=%s)", lead.url, lead.score)
        if media:
            n = await self.repo.contacts_repo().upsert_open_media_batch(media)
            saved += n
            logger.info("StoreAgent: в базу контактов %s записей (open_media)", n)
        logger.info("StoreAgent: сохранено/обновлено %s записей (тендеры + контакты)", saved)
        return saved
