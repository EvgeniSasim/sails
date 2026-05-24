"""Исполнение задач platform_jobs."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from tender_agents.agents.keyword_planner_agent import plan_keywords
from tender_agents.agents.link_resolver_agent import resolve_links_batch
from tender_agents.agents.orchestrator import Orchestrator
from tender_agents.agents.source_scout_agent import save_spec_to_sources_d, scout_source
from tender_agents.agents.tender_analyst_agent import analyze_tender_history
from tender_agents.config_loader import load_keywords
from tender_agents.db import create_repository
from tender_agents.platform_jobs import (
    PlatformJobRepository,
    create_platform_job_repository,
    parse_optional_date,
)
from tender_agents.scrape.factory import get_backend, _YANDEX_BACKEND_NAMES
from tender_agents.web.config_store import ConfigStore
from tender_agents.yandex.config import is_yandex_configured

logger = logging.getLogger(__name__)


async def execute_platform_job(job_id: int, jobs: PlatformJobRepository | None = None) -> dict:
    jobs = jobs or create_platform_job_repository()
    await jobs.ensure_tables()
    job = await jobs.get(job_id)
    if not job:
        raise ValueError(f"Задача {job_id} не найдена")
    await jobs.update(job_id, status="running")
    payload = job.payload
    try:
        result = await _dispatch(job.job_type, payload)
        await jobs.update(job_id, status="completed", result=result)
        return result
    except Exception as e:
        logger.exception("Platform job %s failed", job_id)
        await jobs.update(job_id, status="failed", error=str(e))
        raise


async def _dispatch(job_type: str, payload: dict) -> dict:
    if job_type == "keyword_plan":
        plan = await plan_keywords(
            str(payload.get("task") or ""),
            merge_hr_cx=bool(payload.get("merge_hr_cx")),
        )
        if payload.get("save"):
            ConfigStore().save_keywords(
                plan["keywords"],
                merge_extra=bool(payload.get("merge_hr_cx")),
            )
        return plan

    if job_type == "tender_run":
        return await _run_tender_pipeline(payload)

    if job_type == "tender_analyst":
        repo = create_repository()
        await repo.init()
        d_from = parse_optional_date(payload.get("date_from"))
        d_to = parse_optional_date(payload.get("date_to"))
        if not d_from and payload.get("period_days"):
            d_from = date.today() - timedelta(days=int(payload["period_days"]))
        return await analyze_tender_history(
            repo,
            date_from=d_from,
            date_to=d_to,
            limit=int(payload.get("limit") or 500),
        )

    if job_type == "link_resolve":
        repo = create_repository()
        await repo.init()
        return await resolve_links_batch(
            repo,
            max_tenders=int(payload.get("max_tenders") or 350),
            max_contacts=int(payload.get("max_contacts") or 2500),
        )

    if job_type == "source_scout":
        spec = await scout_source(str(payload.get("url") or ""))
        path = None
        if payload.get("save"):
            path = str(save_spec_to_sources_d(spec))
        return {"spec": spec, "saved_path": path}

    if job_type == "lpr_research":
        from tender_agents.agents.contact_research_agent import (
            report_summary,
            run_contact_research,
        )

        repo = create_repository()
        await repo.init()
        cid = int(payload["contact_id"])
        report = await run_contact_research(repo, cid)
        return {"contact_id": cid, "summary": report_summary(report)}

    raise ValueError(f"Неизвестный тип задачи: {job_type}")


async def _run_tender_pipeline(payload: dict) -> dict:
    cfg = ConfigStore().load_public_config()
    keywords = load_keywords()
    backend_name = (cfg.get("scraper_backend") or "httpx").lower()
    agent_provider = (cfg.get("agent_provider") or "local").lower()
    if backend_name in _YANDEX_BACKEND_NAMES and not is_yandex_configured():
        backend_name = "httpx"
    if agent_provider == "yandex" and not is_yandex_configured():
        agent_provider = "local"

    d_from = parse_optional_date(payload.get("date_from"))
    d_to = parse_optional_date(payload.get("date_to"))
    if not d_from and payload.get("period_days"):
        d_from = date.today() - timedelta(days=int(payload["period_days"]))

    orch = Orchestrator(
        keywords=keywords,
        backend=get_backend(backend_name),
        agent_provider=agent_provider,
        date_from=d_from,
        date_to=d_to,
    )
    return await orch.run_pipeline(
        max_per_keyword=int(payload.get("max_per_keyword") or 10),
        skip_enrich=bool(payload.get("skip_enrich")),
    )
