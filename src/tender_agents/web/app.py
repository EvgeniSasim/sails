"""Дашборд продаж FeedBackTalk: очередь, воронка, аналитика."""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from pathlib import Path
from typing import Annotated
from urllib.parse import quote, urlencode

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, RedirectResponse

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
    platform_job_detail_page,
    help_page,
    settings_page,
)

logger = logging.getLogger(__name__)
app = FastAPI(title="FeedBackTalk Tender Leads", version="0.3.0")
store = ConfigStore()


@app.get("/robots.txt", response_class=PlainTextResponse, include_in_schema=False)
async def robots_txt() -> str:
    return "User-agent: *\nDisallow:\n"


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
    date_from: str = Query(""),
    date_to: str = Query(""),
    period: str = Query(""),
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

    d_from: date | None = None
    d_to: date | None = None
    if period == "7d":
        d_to = date.today()
        d_from = d_to - timedelta(days=7)
    elif period == "30d":
        d_to = date.today()
        d_from = d_to - timedelta(days=30)
    elif period == "quarter":
        d_to = date.today()
        d_from = d_to - timedelta(days=92)
    elif date_from:
        try:
            d_from = date.fromisoformat(date_from[:10])
        except ValueError:
            d_from = None
    if date_to and not d_to:
        try:
            d_to = date.fromisoformat(date_to[:10])
        except ValueError:
            d_to = None

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
    if d_from:
        filter_params["date_from"] = d_from.isoformat()
    if d_to:
        filter_params["date_to"] = d_to.isoformat()
    if period:
        filter_params["period"] = period
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
        date_from=d_from,
        date_to=d_to,
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
        date_from=d_from.isoformat() if d_from else "",
        date_to=d_to.isoformat() if d_to else "",
        period=period,
        filtered_count=len(leads),
    )
    return HTMLResponse(html)


@app.get("/queue", response_class=HTMLResponse)
async def manager_queue(
    tab: str = Query("hot"),
    ready: str = Query(""),
):
    from tender_agents.web.html_pages import manager_queue_page

    repo = create_repository()
    await repo.init()
    hot = await repo.list_filtered(
        LeadFilters(min_score=60, channel="tender", date_from=date.today() - timedelta(days=30)),
        limit=80,
        sort_by="urgency",
    )
    cr = repo.contacts_repo()
    cflt = ContactListFilters(has_email=True)
    if ready:
        profiles = await cr.list_profiles(cflt, limit=80)
        profiles = [p for p in profiles if getattr(p, "channel_verified_at", None)]
    else:
        profiles = await cr.list_profiles(cflt, limit=80)
    linked_rows: list[str] = []
    for p in profiles[:40]:
        if not p.id:
            continue
        tlinks = await cr.list_tender_contact_links_for_contact(p.id)
        confirmed = [t for t in tlinks if (t.get("status") or "") == "confirmed"]
        if not confirmed:
            continue
        linked_rows.append(
            f"<tr><td><a href='/contact/{p.id}'>{_e(p.full_name)}</a></td>"
            f"<td>{_e(p.organization[:60])}</td>"
            f"<td>{len(confirmed)}</td></tr>"
        )
    html = manager_queue_page(tab=tab, hot_leads=hot, contacts=profiles, linked_rows=linked_rows)
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


@app.get("/deal/{lead_id}", response_class=HTMLResponse)
async def deal_card(lead_id: int, msg: str = Query("")):
    from tender_agents.web.html_pages import deal_card_page

    repo = create_repository()
    await repo.init()
    lead = await repo.get_by_id(lead_id)
    if not lead:
        return HTMLResponse("<h1>Сделка не найдена</h1><a href='/'>← Тендеры</a>", status_code=404)
    links = await repo.contacts_repo().list_tender_contact_links_for_lead(lead_id)
    return HTMLResponse(deal_card_page(lead, tender_contact_links=links, flash=msg))


@app.get("/analyst", response_class=HTMLResponse)
async def analyst_view(
    date_from: str = Query(""),
    date_to: str = Query(""),
    period_days: str = Query("90"),
):
    from tender_agents.platform_jobs import parse_optional_date
    from tender_agents.web.html_pages import analyst_page

    repo = create_repository()
    await repo.init()
    d_from = parse_optional_date(date_from)
    d_to = parse_optional_date(date_to)
    if not d_from and period_days.strip().isdigit():
        d_from = date.today() - timedelta(days=int(period_days.strip()))
    report = None
    if d_from or d_to:
        from tender_agents.agents.tender_analyst_agent import analyze_tender_history

        report = await analyze_tender_history(repo, date_from=d_from, date_to=d_to)
    return HTMLResponse(
        analyst_page(
            report=report,
            date_from=d_from.isoformat() if d_from else "",
            date_to=d_to.isoformat() if d_to else "",
            period_days=period_days,
        )
    )


@app.get("/api/tenders/history.csv")
async def tenders_history_csv(
    date_from: str = Query(""),
    date_to: str = Query(""),
    limit: int = Query(2000, ge=1, le=10000),
):
    import csv
    import io

    from tender_agents.platform_jobs import parse_optional_date

    repo = create_repository()
    await repo.init()
    flt = LeadFilters(
        channel="tender",
        date_from=parse_optional_date(date_from),
        date_to=parse_optional_date(date_to),
    )
    leads = await repo.list_filtered(flt, limit=limit, sort_by="updated", order="desc")
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(
        [
            "id",
            "score",
            "segment",
            "source",
            "title",
            "customer_name",
            "customer_inn",
            "publish_date",
            "end_date",
            "matched_keyword",
            "url",
            "pipeline_status",
        ]
    )
    for L in leads:
        w.writerow(
            [
                L.id,
                L.score,
                L.segment.value,
                L.source,
                L.title,
                L.customer_name or "",
                L.customer_inn or "",
                L.publish_date or "",
                L.end_date or "",
                L.matched_keyword or "",
                L.url,
                L.pipeline_status.value,
            ]
        )
    return PlainTextResponse(
        "\ufeff" + buf.getvalue(),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=tender_history.csv"},
    )


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
    job = await repo.research_jobs().latest_for_profile(contact_id)
    return HTMLResponse(contact_detail_page(p, flash=flash, tender_links=tlinks, research_job=job))


@app.post("/contact/{contact_id}/research")
async def contact_research_post(contact_id: int, background_tasks: BackgroundTasks):
    repo = create_repository()
    await repo.init()
    p = await repo.contacts_repo().get_by_id(contact_id, with_appearances=False)
    if not p:
        return RedirectResponse("/contacts", status_code=303)
    from tender_agents.agents.contact_research_agent import build_research_queries, execute_research_job

    q = build_research_queries(p.full_name, p.organization, p.position)[0]
    job = await repo.research_jobs().create_job(contact_id, q)

    async def _bg():
        r = create_repository()
        await r.init()
        try:
            await execute_research_job(r, job.id)
        except Exception:
            logger.exception("research job %s", job.id)

    background_tasks.add_task(_bg)
    return RedirectResponse(
        f"/contact/{contact_id}?flash=" + quote("Исследование запущено (job #%s) — обновите страницу." % job.id),
        status_code=303,
    )


@app.get("/contact/{contact_id}/research/status")
async def contact_research_status(contact_id: int, format: str = Query("json")):
    repo = create_repository()
    await repo.init()
    job = await repo.research_jobs().latest_for_profile(contact_id)
    if not job:
        payload = {"status": "none"}
    else:
        payload = {
            "job_id": job.id,
            "status": job.status,
            "error": job.error,
            "challenge_url": job.challenge_url,
            "search_engine": job.search_engine,
        }
    if format == "text":
        if payload.get("status") == "none":
            return PlainTextResponse("no job")
        return PlainTextResponse(f"{payload['status']}|{payload.get('error') or ''}")
    return JSONResponse(payload)


@app.post("/contact/research/{job_id}/resume")
async def contact_research_resume(
    job_id: int,
    background_tasks: BackgroundTasks,
    cookies_text: Annotated[str, Form()] = "",
    html_upload: UploadFile | None = File(None),
):
    repo = create_repository()
    await repo.init()
    job = await repo.research_jobs().get_job(job_id)
    if not job:
        return RedirectResponse("/contacts?flash=" + quote("ERR:задача не найдена"), status_code=303)
    html_len = 0
    if html_upload and html_upload.filename:
        raw = await html_upload.read()
        html_len = len(raw)
        imp_dir = Path("data") / "imports"
        imp_dir.mkdir(parents=True, exist_ok=True)
        (imp_dir / f"captcha_{job_id}.html").write_bytes(raw[:5_000_000])
    await repo.research_jobs().update_job(
        job_id,
        status="pending",
        result={"resume_cookies": cookies_text[:4000], "resume_html_len": html_len},
    )

    async def _bg():
        r = create_repository()
        await r.init()
        from tender_agents.agents.contact_research_agent import execute_research_job

        await execute_research_job(r, job_id)

    background_tasks.add_task(_bg)
    return RedirectResponse(
        f"/contact/{job.profile_id}?flash=" + quote("Продолжаем исследование…"),
        status_code=303,
    )


@app.get("/research/jobs", response_class=HTMLResponse)
async def research_jobs_list():
    from tender_agents.web.html_pages import research_jobs_page

    repo = create_repository()
    await repo.init()
    jobs = await repo.research_jobs().list_needs_captcha()
    return HTMLResponse(research_jobs_page(jobs))


@app.post("/contact/{contact_id}/bio")
async def contact_bio_save(contact_id: int, bio: Annotated[str, Form()] = ""):
    repo = create_repository()
    await repo.init()
    await repo.contacts_repo().update_bio(contact_id, bio)
    return RedirectResponse(f"/contact/{contact_id}?flash=" + quote("Описание сохранено"), status_code=303)


@app.post("/contact/{contact_id}/appearance")
async def contact_appearance_add(
    contact_id: int,
    appearance_type: Annotated[str, Form()],
    source_title: Annotated[str, Form()],
    source_url: Annotated[str, Form()] = "",
    snippet: Annotated[str, Form()] = "",
):
    repo = create_repository()
    await repo.init()
    await repo.contacts_repo().add_manual_appearance(
        contact_id,
        appearance_type=appearance_type or "event",
        source_title=source_title,
        source_url=source_url,
        snippet=snippet or None,
    )
    return RedirectResponse(f"/contact/{contact_id}?flash=" + quote("Мероприятие добавлено"), status_code=303)


@app.post("/contact/{contact_id}/verify-channel")
async def contact_verify_channel(contact_id: int):
    repo = create_repository()
    await repo.init()
    await repo.contacts_repo().verify_channel(contact_id)
    return RedirectResponse(
        f"/contact/{contact_id}?flash=" + quote("Канал отмечен как проверенный"),
        status_code=303,
    )


@app.post("/contacts/import/upload")
async def contacts_import_upload(
    file: UploadFile,
    use_yandex: Annotated[str | None, Form()] = None,
):
    import uuid

    from tender_agents.excel_ingest.excel_import import parse_workbook, suggest_mapping
    from tender_agents.web.html_pages import import_mapping_page

    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        return RedirectResponse(
            "/settings?tab=channels&flash=" + quote("ERR:файл больше 5 МБ"),
            status_code=303,
        )

    orig_fn = file.filename or "import.xlsx"
    safe_fn = str(uuid.uuid4()) + Path(orig_fn).suffix

    import_dir = Path("data/imports")
    import_dir.mkdir(parents=True, exist_ok=True)
    tmp_path = import_dir / safe_fn
    tmp_path.write_bytes(content)

    try:
        rows = parse_workbook(content, orig_fn)
        if not rows:
            return RedirectResponse(
                "/settings?tab=channels&flash=" + quote("ERR:в файле нет данных"),
                status_code=303,
            )
        headers = list(rows[0].keys())
        mapping = await suggest_mapping(headers, rows, use_yandex=bool(use_yandex))
        return HTMLResponse(import_mapping_page(safe_fn, headers, rows[:10], mapping))
    except Exception as e:
        logger.exception("Import upload failed")
        return RedirectResponse(
            f"/settings?tab=channels&flash=" + quote(f"ERR:{str(e)[:200]}"),
            status_code=303,
        )


@app.post("/contacts/import/commit")
async def contacts_import_commit(
    request: Request,
    filename: Annotated[str, Form()],
):
    from tender_agents.excel_ingest.excel_import import MAPPING_FIELDS, apply_mapping, parse_workbook

    if "/" in filename or "\\" in filename or ".." in filename:
        return RedirectResponse(
            "/settings?tab=channels&flash=" + quote("ERR:некорректное имя файла"),
            status_code=303,
        )

    form_data = await request.form()
    mapping: dict[str, str] = {}
    for field in MAPPING_FIELDS:
        val = form_data.get(f"map_{field}")
        if val:
            mapping[field] = str(val)

    import_dir = (Path("data/imports")).resolve()
    import_dir.mkdir(parents=True, exist_ok=True)
    try:
        tmp_path = (import_dir / Path(filename).name).resolve()
    except (OSError, ValueError):
        return RedirectResponse(
            "/settings?tab=channels&flash=" + quote("ERR:некорректное имя файла"),
            status_code=303,
        )
    if tmp_path.parent != import_dir or not tmp_path.is_file():
        return RedirectResponse(
            "/settings?tab=channels&flash=" + quote("ERR:временный файл не найден"),
            status_code=303,
        )

    try:
        content = tmp_path.read_bytes()
        rows = parse_workbook(content, filename)
        profiles, appearances = apply_mapping(rows, mapping)
        repo = create_repository()
        await repo.init()
        n = await repo.contacts_repo().upsert_contacts_batch(profiles, appearances)
        tmp_path.unlink(missing_ok=True)
        return RedirectResponse(
            "/contacts?flash=" + quote(f"Импорт завершён: {n} контактов."),
            status_code=303,
        )
    except Exception as e:
        logger.exception("Import commit failed")
        return RedirectResponse(
            f"/settings?tab=channels&flash=" + quote(f"ERR:{str(e)[:200]}"),
            status_code=303,
        )


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


@app.get("/help", response_class=HTMLResponse)
async def help_faq() -> str:
    return help_page()


@app.get("/faq", include_in_schema=False)
async def faq_redirect():
    return RedirectResponse("/help", status_code=301)


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
    jobs = await _list_platform_jobs(25) if tab == "jobs" else []
    return HTMLResponse(settings_page(cfg, flash=flash, tab=tab, platform_jobs=jobs))


async def _list_platform_jobs(limit: int = 25):
    from tender_agents.platform_jobs import create_platform_job_repository

    jr = create_platform_job_repository()
    await jr.ensure_tables()
    return await jr.list_recent(limit)


@app.get("/settings/platform-job/{job_id}", response_class=HTMLResponse)
async def settings_platform_job_detail(job_id: int):
    """Полный result_json / error для завершённой задачи."""
    from tender_agents.platform_jobs import create_platform_job_repository

    jr = create_platform_job_repository()
    await jr.ensure_tables()
    job = await jr.get(job_id)
    if not job:
        raise HTTPException(404, "Задача не найдена")
    return HTMLResponse(platform_job_detail_page(job))


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


@app.post("/settings/keyword-plan")
async def settings_keyword_plan(
    background_tasks: BackgroundTasks,
    manager_task: Annotated[str, Form()],
    merge_extra: Annotated[str | None, Form()] = None,
    save_keywords: Annotated[str | None, Form()] = None,
):
    from tender_agents.platform_jobs import create_platform_job_repository

    jr = create_platform_job_repository()
    await jr.ensure_tables()
    job = await jr.create(
        "keyword_plan",
        {
            "task": manager_task.strip(),
            "merge_hr_cx": merge_extra is not None,
            "save": save_keywords is not None,
        },
    )
    background_tasks.add_task(_platform_jobs_background, job.id)
    return RedirectResponse(
        f"/settings?tab=jobs&saved={quote('Планирование ключей запущено (задача #' + str(job.id) + ')')}",
        status_code=303,
    )


@app.post("/settings/platform-job")
async def settings_platform_job(
    background_tasks: BackgroundTasks,
    job_type: Annotated[str, Form()],
    date_from: Annotated[str, Form()] = "",
    date_to: Annotated[str, Form()] = "",
    period_days: Annotated[str, Form()] = "",
    scout_url: Annotated[str, Form()] = "",
    contact_id: Annotated[str, Form()] = "",
):
    from tender_agents.platform_jobs import create_platform_job_repository

    payload: dict = {}
    if date_from.strip():
        payload["date_from"] = date_from.strip()
    if date_to.strip():
        payload["date_to"] = date_to.strip()
    if period_days.strip().isdigit():
        payload["period_days"] = int(period_days.strip())
    if scout_url.strip():
        payload["url"] = scout_url.strip()
        payload["save"] = True
    if contact_id.strip().isdigit():
        payload["contact_id"] = int(contact_id.strip())

    jr = create_platform_job_repository()
    await jr.ensure_tables()
    job = await jr.create(job_type, payload)
    background_tasks.add_task(_platform_jobs_background, job.id)
    return RedirectResponse(
        f"/settings?tab=jobs&saved={quote('Задача #' + str(job.id) + ' (' + job_type + ') в очереди')}",
        status_code=303,
    )


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


async def _run_pipeline_job(
    *,
    max_per_keyword: int,
    skip_enrich: bool,
    date_from: str | None = None,
    date_to: str | None = None,
    period_days: int | None = None,
):
    from tender_agents.platform_job_runner import _run_tender_pipeline

    payload: dict = {
        "max_per_keyword": max_per_keyword,
        "skip_enrich": skip_enrich,
        "date_from": date_from,
        "date_to": date_to,
    }
    if period_days:
        payload["period_days"] = period_days
    try:
        stats = await _run_tender_pipeline(payload)
        logger.info("Dashboard pipeline done: %s", stats)
    except Exception:
        logger.exception("Dashboard pipeline failed")


def _platform_jobs_background(job_id: int) -> None:
    from tender_agents.platform_job_runner import execute_platform_job

    asyncio.run(execute_platform_job(job_id))


@app.post("/settings/run")
async def settings_run_pipeline(
    background_tasks: BackgroundTasks,
    max_per_keyword: Annotated[int, Form()] = 10,
    skip_enrich: Annotated[str | None, Form()] = None,
    date_from: Annotated[str, Form()] = "",
    date_to: Annotated[str, Form()] = "",
    period_days: Annotated[str, Form()] = "",
):
    from tender_agents.scrape.factory import _YANDEX_BACKEND_NAMES
    from tender_agents.yandex.config import is_yandex_configured

    cfg = store.load_public_config()
    saved = "Запуск в фоне"
    backend = (cfg.get("scraper_backend") or "httpx").lower()
    if backend in _YANDEX_BACKEND_NAMES and not is_yandex_configured():
        saved = "Запуск в фоне (httpx: Yandex API не задан — см. Настройки → API)"
    pd = None
    if (period_days or "").strip().isdigit():
        pd = int(period_days.strip())
    background_tasks.add_task(
        _run_pipeline_job,
        max_per_keyword=max_per_keyword,
        skip_enrich=skip_enrich is not None,
        date_from=(date_from or "").strip() or None,
        date_to=(date_to or "").strip() or None,
        period_days=pd,
    )
    period_hint = ""
    if pd or date_from or date_to:
        period_hint = " (с фильтром периода)"
    return RedirectResponse(
        "/settings?tab=run&saved=" + quote(saved + period_hint),
        status_code=303,
    )


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
