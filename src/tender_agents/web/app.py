"""Дашборд продаж FeedBackTalk: очередь, воронка, аналитика."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import BackgroundTasks, FastAPI, Form, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, PlainTextResponse, RedirectResponse

from tender_agents.contacts_db import ContactListFilters
from tender_agents.db import LeadFilters, create_repository
from tender_agents.models import LeadSegment, PipelineStatus
from tender_agents.settings import settings
from tender_agents.web.config_store import UNCHANGED, ConfigStore
from tender_agents.web.html_pages import (
    _e,
    _score_class,
    _tender_scope_options,
    analytics_page,
    contact_detail_page,
    contacts_list_page,
    lead_detail_page,
    pipeline_page,
    queue_page,
    settings_page,
)

logger = logging.getLogger(__name__)
app = FastAPI(title="FeedBackTalk Tender Leads", version="0.3.0")
store = ConfigStore()


def _contacts_url_with_flash(return_query: str, flash: str) -> str:
    rq = (return_query or "").strip()
    if "://" in rq or rq.startswith("//"):
        base = "/contacts"
    else:
        base = "/contacts" + ("?" + rq if rq else "")
    sep = "&" if "?" in base else "?"
    return base + sep + "flash=" + quote(flash)


def _contact_summary(contacts) -> str:
    parts = []
    for c in contacts:
        bit = c.name or c.email or c.phone or ""
        if bit:
            parts.append(bit)
    return ", ".join(parts[:2]) or "—"


def _secret_field(value: str | None) -> str:
    if not value or not value.strip():
        return UNCHANGED
    if "••••" in value:
        return UNCHANGED
    return value.strip()


def _build_filter_options(
    leads_sources: set[str],
    *,
    source: str,
    segment: str,
) -> tuple[str, str]:
    source_opts = '<option value="">Все площадки</option>' + "".join(
        f'<option value="{_e(sid)}"{" selected" if sid == source else ""}>{_e(sid)}</option>'
        for sid in sorted(leads_sources)
    )
    seg_opts = '<option value="">Все сегменты</option>' + "".join(
        f'<option value="{_e(s.value)}"{" selected" if s.value == segment else ""}>{_e(s.value)}</option>'
        for s in LeadSegment
    )
    return source_opts, seg_opts


def _queue_rows(leads, *, show_rank: bool = False) -> str:
    rows = []
    for i, lead in enumerate(leads, 1):
        if not lead.id:
            continue
        sc = _score_class(lead.score)
        seg = lead.segment.value
        first = f"<td class='rank'>{i}</td>" if show_rank else "<td class='rank'> </td>"
        kw_hint = (
            f"<br><span class='hint'>{_e((lead.matched_keyword or '')[:40])}</span>"
            if lead.matched_keyword
            else ""
        )
        rows.append(
            f"<tr>"
            f"{first}"
            f"<td><span class='score {sc}'>{lead.score}</span></td>"
            f"<td><span class='seg {seg}'>{_e(seg)}</span></td>"
            f"<td><span class='badge'>{_e(lead.source)}</span></td>"
            f"<td><a href='/lead/{lead.id}'>{_e(lead.title[:90])}</a>{kw_hint}</td>"
            f"<td>{_e((lead.customer_name or '—')[:60])}</td>"
            f"<td>{_e(lead.end_date or '—')}</td>"
            f"<td>{_e(lead.pipeline_status.value)}</td>"
            f"<td><a href='{_e(lead.url)}' target='_blank'>↗</a></td>"
            f"</tr>"
        )
    return "\n".join(rows) or (
        "<tr><td colspan='9'>Нет тендеров — <a href='/settings?tab=run'>запустите сбор</a> или "
        "<a href='/settings?tab=channels'>импорт контактов из СМИ</a> (раздел «Контакты»)</td></tr>"
    )


@app.get("/", response_class=HTMLResponse)
async def dashboard(
    q: str = Query(""),
    source: str = Query(""),
    segment: str = Query(""),
    pipeline_status: str = Query(""),
    min_score: int = Query(0),
    hot_only: str = Query(""),
    current_keys: str = Query(""),
    channel: str = Query("tender"),
    sort: str = Query("score"),
    order: str = Query("desc"),
    limit: int = Query(200, le=500),
):
    from tender_agents.settings import settings as s

    ch = (channel or "tender").strip()
    if ch not in ("tender", "all"):
        ch = "tender"
    ch_filter = None if ch == "all" else "tender"

    if hot_only:
        min_score = max(min_score, 60)

    allowed_sort = {
        "score",
        "segment",
        "source",
        "title",
        "customer",
        "end_date",
        "pipeline",
        "updated",
        "urgency",
    }
    if sort not in allowed_sort:
        sort = "score"
    if order not in ("asc", "desc"):
        order = "desc"

    filter_params: dict[str, str | int] = {}
    if q:
        filter_params["q"] = q
    if min_score:
        filter_params["min_score"] = min_score
    if segment:
        filter_params["segment"] = segment
    if source:
        filter_params["source"] = source
    if pipeline_status:
        filter_params["pipeline_status"] = pipeline_status
    if hot_only:
        filter_params["hot_only"] = "1"
    if current_keys:
        filter_params["current_keys"] = "1"
    if ch == "all":
        filter_params["channel"] = "all"
    filter_query = urlencode(filter_params)

    def _lead_qs(**overrides: str | int) -> str:
        merged = {**filter_params, "sort": sort, "order": order, **overrides}
        return urlencode({k: v for k, v in merged.items() if v not in (None, "", 0)})

    hot_href = "/?" + _lead_qs(min_score=60)
    urgency_href = "/?" + _lead_qs(sort="urgency", order="desc")

    from tender_agents.config_loader import describe_keywords_setup, load_keywords

    kw_setup = describe_keywords_setup()
    active_kw = kw_setup["effective"] if current_keys else None

    repo = create_repository()
    await repo.init()
    flt = LeadFilters(
        min_score=min_score,
        segment=segment or None,
        pipeline_status=pipeline_status or None,
        source=source or None,
        q=q,
        channel=ch_filter,
        matched_keywords=active_kw,
    )
    leads = await repo.list_filtered(flt, limit=limit, sort_by=sort, order=order)
    stats = await repo.stats(channel=ch_filter)
    all_leads = await repo.list_filtered(LeadFilters(channel=ch_filter), limit=500)
    sources = {lead.source for lead in all_leads}
    source_opts, seg_opts = _build_filter_options(sources, source=source, segment=segment)

    ch_opts = _tender_scope_options(scope=ch)
    html = queue_page(
        backend=s.scraper_backend,
        stats=stats,
        q=q,
        min_score=min_score,
        segment=segment,
        pipeline_status=pipeline_status,
        source=source,
        channel=ch,
        channel_options=ch_opts,
        hot_only=bool(hot_only),
        source_options=source_opts,
        segment_options=seg_opts,
        rows=_queue_rows(leads, show_rank=(sort == "urgency")),
        sort=sort,
        order=order,
        filter_query=filter_query,
        hot_href=hot_href,
        urgency_href=urgency_href,
        keywords_effective=kw_setup["effective"],
        keywords_merge_extra=kw_setup["merge_extra"],
        current_keys_filter=bool(current_keys),
    )
    return HTMLResponse(html)


@app.get("/lead/{lead_id}", response_class=HTMLResponse)
async def lead_detail(lead_id: int, saved: str = Query(""), msg: str = Query("")):
    repo = create_repository()
    await repo.init()
    lead = await repo.get_by_id(lead_id)
    if not lead:
        return HTMLResponse("<h1>Лид не найден</h1><a href='/'>← Тендеры</a>", status_code=404)
    flash = "Сохранено" if saved else (msg or "")
    links = await repo.contacts_repo().list_tender_contact_links_for_lead(lead_id)
    return HTMLResponse(lead_detail_page(lead, flash=flash, tender_contact_links=links))


@app.post("/lead/{lead_id}/pipeline")
async def lead_pipeline_update(
    lead_id: int,
    pipeline_status: Annotated[str, Form()],
    notes: Annotated[str, Form()] = "",
):
    repo = create_repository()
    await repo.init()
    ok = await repo.update_pipeline(lead_id, pipeline_status=pipeline_status, notes=notes)
    if not ok:
        return RedirectResponse("/", status_code=303)
    return RedirectResponse(f"/lead/{lead_id}?saved=1", status_code=303)


@app.get("/pipeline", response_class=HTMLResponse)
async def pipeline_view():
    repo = create_repository()
    await repo.init()
    leads = await repo.list_filtered(LeadFilters(min_score=0, channel="tender"), limit=500)
    columns: dict[str, list[str]] = {s.value: [] for s in PipelineStatus}
    for lead in leads:
        if not lead.id:
            continue
        ps = lead.pipeline_status.value
        card = (
            f'<div class="kcard"><a href="/lead/{lead.id}">{_e(lead.title[:50])}</a>'
            f'<br><span class="score {_score_class(lead.score)}">{lead.score}</span> '
            f'<span class="seg {lead.segment.value}">{_e(lead.segment.value)}</span></div>'
        )
        columns.setdefault(ps, []).append(card)
    cols_str = {k: "".join(v[:20]) for k, v in columns.items()}
    return HTMLResponse(pipeline_page(cols_str))


@app.get("/analytics", response_class=HTMLResponse)
async def analytics_view():
    repo = create_repository()
    await repo.init()
    stats = await repo.stats(channel="tender")
    by_segment = await repo.count_by_segment(channel="tender")
    by_pipeline = await repo.count_by_pipeline(channel="tender")
    return HTMLResponse(analytics_page(stats=stats, by_segment=by_segment, by_pipeline=by_pipeline))


@app.get("/contacts", response_class=HTMLResponse)
async def contacts_list_view(
    q: str = Query(""),
    organization: str = Query(""),
    has_email: str = Query(""),
    has_phone: str = Query(""),
    has_linkedin_hint: str = Query(""),
    within_years: int = Query(0, ge=0, le=10),
    sort: str = Query("last_seen"),
    order: str = Query("desc"),
    group_org: str = Query(""),
    limit: int = Query(200, le=500),
    offset: int = Query(0, ge=0),
    flash: str = Query(""),
):
    allowed = {"last_seen", "organization", "full_name", "appearances", "position"}
    if sort not in allowed:
        sort = "last_seen"
    if order not in ("asc", "desc"):
        order = "desc"
    repo = create_repository()
    await repo.init()
    cr = repo.contacts_repo()
    flt = ContactListFilters(
        q=q,
        organization=organization,
        has_email=bool(has_email),
        has_phone=bool(has_phone),
        has_linkedin_hint=bool(has_linkedin_hint),
        within_years=within_years,
    )
    total = await cr.count_list(flt)
    profiles = await cr.list_profiles(flt, sort_by=sort, order=order, limit=limit, offset=offset)
    cstats = await cr.stats_summary(within_years=within_years)
    link_stats = await cr.count_links_by_status()
    go = group_org in ("1", "on", "true")
    fp: dict[str, str | int] = {}
    if q:
        fp["q"] = q
    if organization.strip():
        fp["organization"] = organization.strip()
    if has_email:
        fp["has_email"] = "1"
    if has_phone:
        fp["has_phone"] = "1"
    if has_linkedin_hint:
        fp["has_linkedin_hint"] = "1"
    fp["within_years"] = within_years
    if go:
        fp["group_org"] = "1"
    filter_query = urlencode(fp)
    html = contacts_list_page(
        stats=cstats,
        profiles=profiles,
        total=total,
        filter_query=filter_query,
        sort=sort,
        order=order,
        group_org=go,
        q=q,
        organization=organization,
        within_years=within_years,
        has_email=bool(has_email),
        has_phone=bool(has_phone),
        has_linkedin_hint=bool(has_linkedin_hint),
        link_stats=link_stats,
        flash=flash,
    )
    return HTMLResponse(html)


@app.post("/contacts/rebuild-links")
async def contacts_rebuild_links(
    background_tasks: BackgroundTasks,
    return_query: Annotated[str, Form()] = "",
):
    async def job() -> None:
        r = create_repository()
        await r.init()
        n = await r.contacts_repo().rebuild_suggested_tender_contact_links()
        logger.info("rebuild tender-contact links finished, inserted=%s", n)

    background_tasks.add_task(job)
    loc = _contacts_url_with_flash(
        return_query, "Пересчёт связей запущен в фоне — обновите страницу через несколько секунд."
    )
    return RedirectResponse(loc, status_code=303)


@app.post("/contacts/enrich-batch")
async def contacts_enrich_batch(
    background_tasks: BackgroundTasks,
    return_query: Annotated[str, Form()] = "",
):
    async def job() -> None:
        from tender_agents.agents.profile_enrich_agent import enrich_contacts_batch

        r = create_repository()
        await r.init()
        n = await enrich_contacts_batch(r, limit=12)
        logger.info("contact enrich batch finished, profiles=%s", n)

    background_tasks.add_task(job)
    loc = _contacts_url_with_flash(
        return_query, "Обогащение из поиска запущено в фоне (до 12 контактов) — обновите через минуту."
    )
    return RedirectResponse(loc, status_code=303)


@app.get("/contact/{contact_id}", response_class=HTMLResponse)
async def contact_detail_view(contact_id: int, flash: str = Query("")):
    repo = create_repository()
    await repo.init()
    p = await repo.contacts_repo().get_by_id(contact_id, with_appearances=True)
    if not p:
        return HTMLResponse(
            "<h1>Контакт не найден</h1><a href='/contacts'>← Контакты</a>",
            status_code=404,
        )
    tlinks = await repo.contacts_repo().list_tender_contact_links_for_contact(contact_id)
    return HTMLResponse(contact_detail_page(p, flash=flash, tender_links=tlinks))


@app.post("/contact/{contact_id}/research")
async def contact_research_post(contact_id: int):
    repo = create_repository()
    await repo.init()
    try:
        from tender_agents.agents.contact_research_agent import report_summary, run_contact_research

        report = await run_contact_research(repo, contact_id)
        msg = report_summary(report)
    except Exception as e:
        logger.exception("contact research %s", contact_id)
        msg = "ERR:" + str(e)[:500]
    return RedirectResponse(f"/contact/{contact_id}?flash=" + quote(msg), status_code=303)


@app.post("/contact/{contact_id}/sanitize-channels")
async def contact_sanitize_channels(contact_id: int):
    repo = create_repository()
    await repo.init()
    cleared = await repo.contacts_repo().sanitize_contact_channels(contact_id)
    if cleared:
        msg = "Удалено: " + ", ".join(cleared)
    else:
        msg = "Некорректных e-mail/телефона не найдено (или поля уже пустые)."
    return RedirectResponse(f"/contact/{contact_id}?flash=" + quote(msg), status_code=303)


@app.post("/contact/{contact_id}/enrich")
async def contact_enrich_post(contact_id: int):
    repo = create_repository()
    await repo.init()
    try:
        from tender_agents.agents.profile_enrich_agent import enrich_contact_profile

        found = await enrich_contact_profile(repo, contact_id)
        bits = [f"{k}={v}" for k, v in found.items() if v]
        msg = "Обновлено: " + ", ".join(bits) if bits else "Запрос выполнен; новых явных полей в выдаче не найдено."
    except Exception as e:
        logger.exception("contact enrich %s", contact_id)
        msg = "ERR:" + str(e)[:400]
    return RedirectResponse(f"/contact/{contact_id}?flash=" + quote(msg), status_code=303)


@app.post("/tender-link/{link_id}/status")
async def tender_link_status(
    link_id: int,
    lead_id: Annotated[int, Form()],
    status: Annotated[str, Form()],
):
    if status not in ("confirmed", "rejected"):
        return RedirectResponse(
            f"/lead/{lead_id}?flash=" + quote("ERR:Недопустимый статус"),
            status_code=303,
        )
    repo = create_repository()
    await repo.init()
    ok = await repo.contacts_repo().set_tender_contact_link_status(link_id, status)
    if not ok:
        return RedirectResponse(
            f"/lead/{lead_id}?flash=" + quote("ERR:Связь не найдена"),
            status_code=303,
        )
    ru = "Связь подтверждена" if status == "confirmed" else "Связь снята / отклонена"
    return RedirectResponse(f"/lead/{lead_id}?flash=" + quote(ru), status_code=303)


@app.get("/settings", response_class=HTMLResponse)
async def settings_view(
    tab: str = Query("project"),
    saved: str = Query(""),
    err: str = Query(""),
):
    if err:
        flash = f"ERR:{err}"
    elif saved:
        flash = saved if saved != "1" else "Сохранено"
    else:
        flash = ""
    cfg = store.load_public_config()
    return HTMLResponse(settings_page(cfg, flash=flash, tab=tab))


@app.post("/settings/project")
async def settings_project_save(
    scraper_backend: Annotated[str, Form()],
    agent_provider: Annotated[str, Form()],
    request_delay_sec: Annotated[float, Form()],
    database_url: Annotated[str, Form()],
):
    cfg = store.load_public_config()
    store.save_env_settings(
        scraper_backend=scraper_backend,
        agent_provider=agent_provider,
        request_delay_sec=request_delay_sec,
        database_url=database_url,
        yandex_folder_id=cfg.get("yandex_folder_id", ""),
        yandex_model=cfg.get("yandex_model", "yandexgpt"),
        yandex_base_url=cfg.get("yandex_base_url", ""),
        yandex_use_responses_api=cfg.get("yandex_use_responses_api", True),
        yandex_enable_web_search=cfg.get("yandex_enable_web_search", False),
        gosplan_api_url=cfg.get("gosplan_api_url", ""),
        ollama_base_url=cfg.get("ollama_base_url", ""),
        ollama_model=cfg.get("ollama_model", ""),
    )
    return RedirectResponse("/settings?tab=project&saved=1", status_code=303)


@app.post("/settings/apis")
async def settings_apis_save(
    yandex_api_key: Annotated[str, Form()] = "",
    yandex_folder_id: Annotated[str, Form()] = "",
    yandex_model: Annotated[str, Form()] = "yandexgpt",
    yandex_use_responses_api: Annotated[str | None, Form()] = None,
    yandex_enable_web_search: Annotated[str | None, Form()] = None,
    sgai_api_key: Annotated[str, Form()] = "",
    gosplan_api_url: Annotated[str, Form()] = "",
    gosplan_api_key: Annotated[str, Form()] = "",
    ollama_base_url: Annotated[str, Form()] = "",
    ollama_model: Annotated[str, Form()] = "",
):
    cfg = store.load_public_config()
    store.save_env_settings(
        scraper_backend=cfg["scraper_backend"],
        agent_provider=cfg["agent_provider"],
        request_delay_sec=cfg["request_delay_sec"],
        database_url=cfg["database_url"],
        yandex_folder_id=yandex_folder_id,
        yandex_model=yandex_model,
        yandex_use_responses_api=yandex_use_responses_api is not None,
        yandex_enable_web_search=yandex_enable_web_search is not None,
        gosplan_api_url=gosplan_api_url,
        ollama_base_url=ollama_base_url,
        ollama_model=ollama_model,
        yandex_api_key=_secret_field(yandex_api_key),
        sgai_api_key=_secret_field(sgai_api_key),
        gosplan_api_key=_secret_field(gosplan_api_key),
    )
    return RedirectResponse("/settings?tab=apis&saved=1", status_code=303)


@app.post("/settings/test-yandex")
async def settings_test_yandex(
    yandex_api_key: Annotated[str, Form()] = "",
    yandex_folder_id: Annotated[str, Form()] = "",
):
    if yandex_api_key.strip() and "••••" not in yandex_api_key:
        store.save_env_settings(
            scraper_backend=store.load_public_config()["scraper_backend"],
            agent_provider=store.load_public_config()["agent_provider"],
            request_delay_sec=store.load_public_config()["request_delay_sec"],
            database_url=store.load_public_config()["database_url"],
            yandex_folder_id=yandex_folder_id,
            yandex_api_key=yandex_api_key.strip(),
        )
    elif yandex_folder_id:
        cfg = store.load_public_config()
        store.save_env_settings(
            scraper_backend=cfg["scraper_backend"],
            agent_provider=cfg["agent_provider"],
            request_delay_sec=cfg["request_delay_sec"],
            database_url=cfg["database_url"],
            yandex_folder_id=yandex_folder_id,
        )
    try:
        from tender_agents.yandex.client import YandexStudioClient

        result = await YandexStudioClient().health_check()
        msg = quote(f"Yandex OK: {result.get('reply', '')[:40]}")
        return RedirectResponse(f"/settings?tab=apis&saved={msg}", status_code=303)
    except Exception as e:
        return RedirectResponse(
            f"/settings?tab=apis&err={quote(str(e)[:200])}",
            status_code=303,
        )


@app.post("/settings/sources")
async def settings_sources_save(
    source_enabled: Annotated[list[str] | None, Form()] = None,
):
    store.save_sources(source_enabled or [])
    return RedirectResponse("/settings?tab=sources&saved=1", status_code=303)


@app.post("/settings/keywords")
async def settings_keywords_save(
    keywords_text: Annotated[str, Form()],
    merge_extra: Annotated[str | None, Form()] = None,
):
    keywords = [line.strip() for line in keywords_text.splitlines() if line.strip()]
    store.save_keywords(keywords, merge_extra=merge_extra is not None)
    return RedirectResponse("/settings?tab=keywords&saved=1", status_code=303)


@app.post("/settings/agents")
async def settings_agents_save(
    search_instructions: Annotated[str, Form()],
    enrich_instructions: Annotated[str, Form()],
    orchestrator_instructions: Annotated[str, Form()],
):
    store.save_agents(
        search_instructions=search_instructions,
        enrich_instructions=enrich_instructions,
        orchestrator_instructions=orchestrator_instructions,
    )
    return RedirectResponse("/settings?tab=agents&saved=1", status_code=303)


async def _run_channels_bookmarks(*, dry: bool) -> int:
    import yaml

    from tender_agents.agents.store_agent import StoreAgent
    from tender_agents.channels.ingest import ingest_url
    from tender_agents.settings import CONFIG_DIR

    path = CONFIG_DIR / "channels.yaml"
    if not path.exists():
        logger.warning("channels.yaml not found at %s", path)
        return 0
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    repo = create_repository()
    await repo.init()
    store = StoreAgent(repo)
    total = 0
    for b in data.get("bookmarks") or []:
        if not isinstance(b, dict) or not b.get("enabled"):
            continue
        url = (b.get("url") or "").strip()
        if not url:
            continue
        try:
            leads = await ingest_url(url)
        except Exception:
            logger.exception("Bookmark ingest failed: %s", url)
            continue
        if dry:
            total += len(leads)
        else:
            await store.run(leads)
            total += len(leads)
    logger.info("Channels bookmarks job finished dry=%s profiles=%s", dry, total)
    return total


def _channels_bookmarks_background(dry: bool) -> None:
    asyncio.run(_run_channels_bookmarks(dry=dry))


async def _run_pipeline_job(*, max_per_keyword: int, skip_enrich: bool):
    from tender_agents.agents.orchestrator import Orchestrator
    from tender_agents.config_loader import load_keywords
    from tender_agents.scrape.factory import get_backend

    cfg = store.load_public_config()
    keywords = load_keywords()
    logger.info("Pipeline keywords (%s): %s", len(keywords), keywords)
    orch = Orchestrator(
        keywords=keywords,
        backend=get_backend(cfg["scraper_backend"]),
        agent_provider=cfg["agent_provider"],
    )
    try:
        stats = await orch.run_pipeline(
            max_per_keyword=max_per_keyword,
            skip_enrich=skip_enrich,
        )
        logger.info("Dashboard pipeline done: %s", stats)
    except Exception:
        logger.exception("Dashboard pipeline failed")


@app.post("/settings/run")
async def settings_run_pipeline(
    background_tasks: BackgroundTasks,
    max_per_keyword: Annotated[int, Form()] = 10,
    skip_enrich: Annotated[str | None, Form()] = None,
):
    background_tasks.add_task(
        _run_pipeline_job,
        max_per_keyword=max_per_keyword,
        skip_enrich=skip_enrich is not None,
    )
    return RedirectResponse("/settings?tab=run&saved=Запуск+в+фоне", status_code=303)


@app.post("/settings/channels-ingest")
async def settings_channels_ingest(
    page_url: Annotated[str, Form()],
    limit: Annotated[str, Form()] = "0",
    dry_run: Annotated[str | None, Form()] = None,
):
    from tender_agents.agents.store_agent import StoreAgent
    from tender_agents.channels.ingest import ingest_url

    try:
        try:
            lim = max(0, int((limit or "0").strip()))
        except ValueError:
            lim = 0
        try:
            leads = await ingest_url(page_url.strip())
        except Exception as e:
            return RedirectResponse(
                f"/settings?tab=channels&err={quote(str(e)[:400])}",
                status_code=303,
            )
        if lim > 0:
            leads = leads[:lim]
        if dry_run is not None:
            msg = quote(f"Проверка: найдено {len(leads)} записей (БД не менялась).")
            return RedirectResponse(f"/settings?tab=channels&saved={msg}", status_code=303)
        repo = create_repository()
        await repo.init()
        n = await StoreAgent(repo).run(leads)
        msg = quote(f"В базу контактов: {n} записей (распознано {len(leads)}).")
        return RedirectResponse(f"/settings?tab=channels&saved={msg}", status_code=303)
    except Exception as e:
        logger.exception("channels-ingest failed")
        return RedirectResponse(
            f"/settings?tab=channels&err={quote(str(e)[:400])}",
            status_code=303,
        )


@app.get("/settings/channels-ingest")
async def settings_channels_ingest_get():
    """POST-only: при открытии URL в браузере ведём в настройки."""
    return RedirectResponse("/settings?tab=channels", status_code=307)


@app.post("/settings/channels-bookmarks")
async def settings_channels_bookmarks(
    background_tasks: BackgroundTasks,
    dry_run: Annotated[str | None, Form()] = None,
):
    if dry_run is not None:
        n = await _run_channels_bookmarks(dry=True)
        msg = quote(f"Сухой прогон закладок: всего {n} записей (БД не менялась).")
        return RedirectResponse(f"/settings?tab=channels&saved={msg}", status_code=303)
    background_tasks.add_task(_channels_bookmarks_background, False)
    msg = quote("Закладки: импорт в фоне — обновите очередь через минуту.")
    return RedirectResponse(f"/settings?tab=channels&saved={msg}", status_code=303)


@app.get("/api/settings")
async def api_settings():
    return store.load_public_config()


@app.get("/api/leads")
async def api_leads(limit: int = 100, min_score: int = 0):
    repo = create_repository()
    await repo.init()
    flt = LeadFilters(min_score=min_score)
    leads = await repo.list_filtered(flt, limit=limit)
    return [lead.model_dump() for lead in leads]


@app.post("/contacts/import/upload")
async def contacts_import_upload(
    file: UploadFile,
    use_yandex: Annotated[str | None, Form()] = None,
):
    import uuid
    from tender_agents.excel_ingest.excel_import import parse_workbook, suggest_mapping

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return RedirectResponse("/settings?tab=channels&err=File+too+large+(max+5MB)", status_code=303)

    orig_fn = file.filename or "import.xlsx"
    # Безопасное имя файла для хранения
    safe_fn = str(uuid.uuid4()) + Path(orig_fn).suffix

    import_dir = Path("data/imports")
    import_dir.mkdir(parents=True, exist_ok=True)

    # Сохраняем временно
    tmp_path = import_dir / safe_fn
    tmp_path.write_bytes(content)

    try:
        rows = parse_workbook(content, orig_fn)
        if not rows:
            return RedirectResponse("/settings?tab=channels&err=No+data+found+in+file", status_code=303)

        headers = list(rows[0].keys())
        mapping = await suggest_mapping(headers, rows, use_yandex=bool(use_yandex))

        from tender_agents.web.html_pages import import_mapping_page
        return HTMLResponse(import_mapping_page(safe_fn, headers, rows[:10], mapping))
    except Exception as e:
        logger.exception("Import upload failed")
        return RedirectResponse(f"/settings?tab=channels&err={quote(str(e)[:200])}", status_code=303)


@app.post("/contacts/import/commit")
async def contacts_import_commit(
    request: Request,
    filename: Annotated[str, Form()],
):
    from tender_agents.excel_ingest.excel_import import MAPPING_FIELDS, apply_mapping, parse_workbook

    # Валидация filename (должен быть просто именем файла без путей)
    if "/" in filename or "\\" in filename:
        return RedirectResponse("/settings?tab=channels&err=Invalid+filename", status_code=303)

    form_data = await request.form()
    mapping = {}
    for field in MAPPING_FIELDS:
        val = form_data.get(f"map_{field}")
        if val:
            mapping[field] = str(val)

    import_dir = Path("data/imports")
    tmp_path = import_dir / filename
    if not tmp_path.exists():
        return RedirectResponse("/settings?tab=channels&err=Temp+file+lost", status_code=303)

    try:
        content = tmp_path.read_bytes()
        rows = parse_workbook(content, filename)
        profiles, appearances = apply_mapping(rows, mapping)

        repo = create_repository()
        await repo.init()
        n = await repo.contacts_repo().upsert_contacts_batch(profiles, appearances)

        # Чистим
        tmp_path.unlink()

        msg = quote(f"Импорт завершен: добавлено / обновлено {n} контактов.")
        return RedirectResponse(f"/contacts?flash={msg}", status_code=303)
    except Exception as e:
        logger.exception("Import commit failed")
        return RedirectResponse(f"/settings?tab=channels&err={quote(str(e)[:200])}", status_code=303)


@app.get("/api/export")
async def api_export(min_score: int = 0):
    path = Path("data/leads_export.csv")
    path.parent.mkdir(parents=True, exist_ok=True)
    repo = create_repository()
    await repo.init()
    leads = await repo.list_filtered(LeadFilters(min_score=min_score), limit=500)
    import csv

    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(
            [
                "score",
                "segment",
                "pipeline_status",
                "channel",
                "source",
                "context_url",
                "title",
                "url",
                "customer_name",
                "customer_inn",
                "end_date",
                "emails",
                "phones",
                "linkedin_search",
                "pitch",
            ]
        )
        for lead in leads:
            w.writerow(
                [
                    lead.score,
                    lead.segment.value,
                    lead.pipeline_status.value,
                    lead.channel,
                    lead.source,
                    lead.context_url or "",
                    lead.title,
                    lead.url,
                    lead.customer_name or "",
                    lead.customer_inn or "",
                    lead.end_date or "",
                    " | ".join(c.email or "" for c in lead.contacts),
                    " | ".join(c.phone or "" for c in lead.contacts),
                    " | ".join(
                        (c.linkedin_search_url or "")
                        for c in lead.contacts
                        if c.linkedin_search_url
                    ),
                    (lead.pitch or "").replace("\n", " "),
                ]
            )
    return PlainTextResponse(f"Exported {len(leads)} rows to {path}")


def run_server(*, reload: bool = False) -> None:
    import uvicorn

    uvicorn.run(
        "tender_agents.web.app:app",
        host=settings.dashboard_host,
        port=settings.dashboard_port,
        reload=reload,
    )
