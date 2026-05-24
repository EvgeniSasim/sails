"""HTML-страницы дашборда."""

from __future__ import annotations

from html import escape

from tender_agents.web.config_store import SECRET_MASK

COMMON_CSS = """
:root { font-family: system-ui, sans-serif; background: #0f1419; color: #e7ecf3; }
body { max-width: 1280px; margin: 0 auto; padding: 1.5rem; }
nav { display: flex; gap: 1rem; margin-bottom: 1.5rem; padding-bottom: 0.75rem; border-bottom: 1px solid #2a3544; }
nav a { color: #8b9cb3; text-decoration: none; }
nav a.active, nav a:hover { color: #6eb5ff; }
h1 { font-size: 1.35rem; margin: 0 0 0.5rem; }
h2 { font-size: 1.05rem; margin: 1.25rem 0 0.6rem; color: #b8c5d9; }
.meta { color: #8b9cb3; font-size: 0.9rem; margin-bottom: 1rem; }
.card { background: #1a2332; border: 1px solid #2a3544; border-radius: 10px; padding: 1.25rem; margin-bottom: 1rem; }
.tabs { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem; }
.tabs a { padding: 0.4rem 0.85rem; border-radius: 6px; background: #243044; color: #b8c5d9; text-decoration: none; font-size: 0.85rem; }
.tabs a.active { background: #2563eb; color: #fff; }
label { display: block; font-size: 0.8rem; color: #8b9cb3; margin: 0.6rem 0 0.25rem; }
input, select, textarea { width: 100%; box-sizing: border-box; background: #0f1419; border: 1px solid #2a3544;
  color: #e7ecf3; padding: 0.45rem 0.6rem; border-radius: 6px; font-size: 0.9rem; }
textarea { min-height: 120px; font-family: ui-monospace, monospace; font-size: 0.8rem; }
.row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
@media (max-width: 700px) { .row2 { grid-template-columns: 1fr; } }
button, .btn { background: #2563eb; color: white; border: none; padding: 0.5rem 1rem;
  border-radius: 6px; cursor: pointer; font-size: 0.9rem; text-decoration: none; display: inline-block; }
button.secondary { background: #374151; }
.flash { padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1rem; font-size: 0.9rem; }
.flash.ok { background: #14532d; border: 1px solid #22c55e; }
.flash.err { background: #450a0a; border: 1px solid #ef4444; }
table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
th, td { text-align: left; padding: 0.5rem 0.6rem; border-bottom: 1px solid #2a3544; }
th { color: #8b9cb3; }
/* Ссылки: читаемый цвет на тёмном фоне (нав / вкладки / .btn переопределяют свои цвета) */
a { color: #a5d8ff; text-decoration: none; }
a:hover { color: #f0f9ff; text-decoration: underline; text-underline-offset: 2px; }
tbody td a { color: #bae6fd; font-weight: 500; text-decoration: underline; text-decoration-color: rgba(186, 230, 253, 0.45); }
tbody td a:hover { color: #ffffff; text-decoration-color: rgba(255, 255, 255, 0.75); }
.badge { display: inline-block; padding: 0.15rem 0.45rem; border-radius: 4px; background: #1e3a5f; font-size: 0.75rem; }
.chk { display: flex; align-items: center; gap: 0.5rem; margin: 0.4rem 0; }
.chk input { width: auto; }
.status-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 6px; vertical-align: middle; }
.status-dot.on { background: #22c55e; }
.status-dot.off { background: #6b7280; }
.hint { font-size: 0.75rem; color: #6b7c93; margin-top: 0.25rem; }
.hidden { display: none; }
.settings-section { margin-top: 1.25rem; padding-top: 1rem; border-top: 1px solid #2a3544; }
.settings-section:first-child { margin-top: 0; padding-top: 0; border-top: none; }
.toolbar { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; margin-bottom: 1rem; }
.toolbar input[name=q] { width: 220px; }
.toolbar select { width: auto; min-width: 120px; }
.score { font-weight: 600; font-variant-numeric: tabular-nums; }
.score.hot { color: #4ade80; }
.score.warm { color: #fbbf24; }
.score.cold { color: #9ca3af; }
.seg { font-size: 0.7rem; padding: 0.1rem 0.35rem; border-radius: 4px; background: #312e81; color: #c4b5fd; }
.seg.hr { background: #713f12; color: #fcd34d; }
.seg.cx { background: #134e4a; color: #5eead4; }
.seg.research { background: #1e3a5f; color: #93c5fd; }
.seg.gov { background: #3f1d1d; color: #fca5a5; }
.stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 0.75rem; margin-bottom: 1rem; }
.stat { background: #1a2332; border: 1px solid #2a3544; border-radius: 8px; padding: 0.75rem 1rem; }
.stat b { font-size: 1.4rem; display: block; color: #6eb5ff; }
.kanban { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 0.75rem; }
.kcol { background: #1a2332; border: 1px solid #2a3544; border-radius: 8px; padding: 0.6rem; min-height: 120px; }
.kcol h3 { font-size: 0.8rem; margin: 0 0 0.5rem; color: #8b9cb3; }
.kcard { background: #0f1419; border: 1px solid #2a3544; border-radius: 6px; padding: 0.5rem; margin-bottom: 0.4rem; font-size: 0.78rem; }
.kcard a { color: #bae6fd; text-decoration: none; font-weight: 500; }
.kcard a:hover { color: #f0f9ff; text-decoration: underline; }
.pitch { white-space: pre-wrap; font-size: 0.85rem; line-height: 1.45; background: #0f1419; padding: 1rem; border-radius: 8px; border: 1px solid #2a3544; }
.reasons { font-size: 0.8rem; color: #8b9cb3; margin: 0.5rem 0; }
.reasons li { margin: 0.2rem 0; }
.pill { display: inline-block; padding: 0.2rem 0.5rem; border-radius: 999px; font-size: 0.75rem; margin-right: 0.35rem; }
.pill.active { background: #14532d; color: #86efac; }
.pill.done { background: #374151; color: #9ca3af; }
th a.sort { color: #8b9cb3; text-decoration: none; white-space: nowrap; }
th a.sort:hover, th a.sort.active { color: #6eb5ff; }
th a.sort .arrow { font-size: 0.7rem; opacity: 0.9; }
td.rank { color: #6b7c93; font-size: 0.8rem; width: 2rem; text-align: right; }
tr.grp td { background: #1e293b; font-weight: 600; color: #94a3b8; padding-top: 0.75rem; }
.qual-fresh { color: #4ade80; }
.qual-aging { color: #fbbf24; }
.qual-stale { color: #f87171; }
.qual-partial { color: #94a3b8; }
.inline-form { display: inline; margin: 0; padding: 0; }
.inline-form button { margin: 0 0.15rem 0 0; padding: 0.35rem 0.65rem; font-size: 0.8rem; }
table.dense td, table.dense th { vertical-align: top; }
.toolbar-actions { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: center; margin-top: 0.5rem; }
.toolbar-actions form { display: inline; }
.toolbar-actions button { width: auto; }
.link-stats { font-size: 0.8rem; color: #8b9cb3; margin: 0.25rem 0 0.5rem; }
"""


def _e(s: str) -> str:
    return escape(s or "", quote=True)


def _nav(active: str) -> str:
    items = [
        ("tenders", "/", "Тендеры"),
        ("contacts", "/contacts", "Контакты"),
        ("pipeline", "/pipeline", "Воронка"),
        ("analytics", "/analytics", "Аналитика"),
        ("analyst", "/analyst", "История"),
        ("channels", "/settings?tab=channels", "Импорт СМИ"),
        ("settings", "/settings", "Настройки"),
    ]
    return "\n    ".join(
        f'<a href="{href}" class="{"active" if active == key else ""}">{label}</a>'
        for key, href, label in items
    )


def _layout(title: str, active: str, body: str, flash: str = "") -> str:
    flash_html = ""
    if flash:
        cls = "err" if flash.startswith("ERR:") else "ok"
        msg = flash[4:] if flash.startswith("ERR:") else flash
        flash_html = f'<div class="flash {cls}">{_e(msg)}</div>'
    return f"""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>{_e(title)} — FeedBackTalk Leads</title>
  <style>{COMMON_CSS}</style>
</head>
<body>
  <nav>
    {_nav(active)}
  </nav>
  {flash_html}
  {body}
</body>
</html>"""


def _score_class(score: int) -> str:
    if score >= 60:
        return "hot"
    if score >= 40:
        return "warm"
    return "cold"


def _sort_th(col: str, label: str, *, sort: str, order: str, query: str) -> str:
    if sort == col:
        next_order = "asc" if order == "desc" else "desc"
        active = "active"
        arrow = " ▲" if order == "asc" else " ▼"
    else:
        next_order = "desc" if col in ("score", "updated", "source") else "asc"
        active = ""
        arrow = ""
    sep = "&" if query else ""
    href = f"/?{query}{sep}sort={col}&order={next_order}"
    return f'<th><a class="sort {active}" href="{href}">{_e(label)}<span class="arrow">{arrow}</span></a></th>'


def _urgency_th(*, sort: str, query: str) -> str:
    sep = "&" if query else ""
    if sort == "urgency":
        href = f"/?{query}{sep}sort=score&order=desc"
        return f'<th><a class="sort active" href="{href}" title="Сбросить на скор">Срочность<span class="arrow"> ★</span></a></th>'
    href = f"/?{query}{sep}sort=urgency&order=desc"
    return (
        f'<th><a class="sort" href="{href}" title="Сначала ближайший дедлайн (по календарю), затем скор">'
        f"{_e('Срочность')}</a></th>"
    )


def _queue_sort_headers(*, sort: str, order: str, query: str) -> str:
    return (
        "<tr>"
        + _urgency_th(sort=sort, query=query)
        + _sort_th("score", "Скор", sort=sort, order=order, query=query)
        + _sort_th("segment", "Сегмент", sort=sort, order=order, query=query)
        + _sort_th("source", "Площадка", sort=sort, order=order, query=query)
        + _sort_th("title", "Закупка", sort=sort, order=order, query=query)
        + _sort_th("customer", "Заказчик", sort=sort, order=order, query=query)
        + _sort_th("end_date", "Дедлайн", sort=sort, order=order, query=query)
        + _sort_th("pipeline", "Этап", sort=sort, order=order, query=query)
        + "<th></th>"
        + "</tr>"
    )


def _pipeline_filter_options(selected: str) -> str:
    opts = [
        ("", "Все этапы"),
        ("new", "Новый"),
        ("qualified", "Квалиф."),
        ("proposal", "КП"),
        ("demo", "Демо"),
        ("won", "Выигран"),
        ("lost", "Проигран"),
    ]
    return "".join(
        f'<option value="{v}"{" selected" if v == selected else ""}>{lbl}</option>'
        for v, lbl in opts
    )


def _tender_scope_options(*, scope: str) -> str:
    opts = [("tender", "Только тендеры"), ("all", "Все записи в БД")]
    return "".join(
        f'<option value="{_e(v)}"{" selected" if v == scope else ""}>{_e(lbl)}</option>'
        for v, lbl in opts
    )


def queue_page(
    *,
    backend: str,
    stats: dict,
    q: str,
    min_score: int,
    segment: str,
    pipeline_status: str,
    source: str,
    hot_only: bool,
    source_options: str,
    segment_options: str,
    rows: str,
    sort: str = "score",
    order: str = "desc",
    filter_query: str = "",
    hot_href: str = "/?min_score=60",
    urgency_href: str = "/?sort=urgency&order=desc",
    channel: str = "",
    channel_options: str = "",
    page_title: str = "Тендеры",
    keywords_effective: list | None = None,
    keywords_merge_extra: bool = False,
    current_keys_filter: bool = False,
    date_from: str = "",
    date_to: str = "",
    period: str = "",
    filtered_count: int = 0,
) -> str:
    headers = _queue_sort_headers(sort=sort, order=order, query=filter_query)
    kw_list = keywords_effective or []
    kw_preview = _e(", ".join(kw_list[:8])) + ("…" if len(kw_list) > 8 else "")
    ck = " checked" if current_keys_filter else ""
    keys_hint = (
        f"<p class='hint'><strong>Ключи для сбора</strong> ({len(kw_list)}): {kw_preview or '—'}. "
        f"Список ниже — всё из БД; смена ключей в настройках не пересобирает автоматически → "
        f"<a href='/settings?tab=run'>Запуск → Сбор</a>. "
        f"{'Включены также keywords_hr/cx.' if keywords_merge_extra else 'Только keywords.yaml (без HR/CX).'}</p>"
    )
    body = f"""
  <h1>{_e(page_title)}</h1>
  <p class="meta">Закупки и площадки · бэкенд <strong>{_e(backend)}</strong> · людей из СМИ смотрите в «Контакты»</p>
  {keys_hint}
  <div class="stats">
    <div class="stat"><b>{stats.get('total', 0)}</b>всего</div>
    <div class="stat"><b>{stats.get('hot', 0)}</b>горячих ≥60</div>
    <div class="stat"><b>{stats.get('avg_score', 0)}</b>ср. скор</div>
    <div class="stat"><b>{stats.get('with_contact', 0)}</b>с e-mail/тел.</div>
  </div>
  <div class="toolbar">
    <form method="get" action="/">
      <input name="q" placeholder="Поиск..." value="{_e(q)}"/>
      <select name="min_score">
        <option value="0"{" selected" if min_score == 0 else ""}>Любой скор</option>
        <option value="40"{" selected" if min_score == 40 else ""}>≥ 40</option>
        <option value="60"{" selected" if min_score == 60 else ""}>≥ 60</option>
      </select>
      <select name="segment">{segment_options}</select>
      <select name="source">{source_options}</select>
      <select name="pipeline_status">{_pipeline_filter_options(pipeline_status)}</select>
      <select name="channel">{channel_options}</select>
      <label class="chk" style="display:inline-flex;margin:0"><input type="checkbox" name="hot_only" value="1"{" checked" if hot_only else ""}/> горячие</label>
      <label class="chk" style="display:inline-flex;margin:0"><input type="checkbox" name="current_keys" value="1"{ck}/> только текущие ключи</label>
      <input type="date" name="date_from" value="{_e(date_from)}" title="Дата с"/>
      <input type="date" name="date_to" value="{_e(date_to)}" title="Дата по"/>
      <select name="period">
        <option value="">Период…</option>
        <option value="7d"{" selected" if period == "7d" else ""}>7 дней</option>
        <option value="30d"{" selected" if period == "30d" else ""}>30 дней</option>
        <option value="quarter"{" selected" if period == "quarter" else ""}>Квартал</option>
      </select>
      <input type="hidden" name="sort" value="{_e(sort)}"/>
      <input type="hidden" name="order" value="{_e(order)}"/>
      <button type="submit">Фильтр</button>
    </form>
    <a href="{_e(hot_href)}" class="btn secondary">Горячие ≥60</a>
    <a href="{_e(urgency_href)}" class="btn secondary">По срочности</a>
    <a href="/contacts" class="btn secondary">Контакты</a>
    <a href="/settings?tab=channels" class="btn secondary">Импорт СМИ</a>
    <a href="/api/export" class="btn secondary">CSV</a>
    <a href="/settings?tab=run" class="btn secondary">Сбор</a>
  </div>
  <p class="hint">Поиск и лимит применяются в БД до сортировки. Дедлайн — по календарю (дд.мм.гггг). Фильтр «Только тендеры» / «Все записи» — если в БД остались старые смешанные строки.{" Показано: <strong>" + str(filtered_count) + "</strong>." if filtered_count else ""}</p>
  <p><a href="/queue" class="btn secondary">Очередь менеджера</a> <a href="/research/jobs" class="btn secondary">Капча / задачи</a></p>
  <table>
    <thead>{headers}</thead>
    <tbody>{rows}</tbody>
  </table>"""
    return _layout(page_title, "tenders", body)


def _tender_contact_links_block(lead_id: int, links: list[dict]) -> str:
    if not links:
        return ""
    rows = []
    for L in links:
        lid = int(L["link_id"])
        cid = int(L["contact_id"])
        st = L.get("status") or "suggested"
        st_ru = {"suggested": "кандидат", "confirmed": "подтверждено", "rejected": "отклонено"}.get(st, st)
        conf = L.get("confidence", 0)
        meth = _e(str(L.get("method") or ""))
        actions = ""
        if st == "suggested":
            actions = (
                f'<form method="post" action="/tender-link/{lid}/status" class="inline-form">'
                f'<input type="hidden" name="lead_id" value="{lead_id}"/>'
                '<input type="hidden" name="status" value="confirmed"/>'
                '<button type="submit" class="btn secondary">Подтвердить</button></form> '
                f'<form method="post" action="/tender-link/{lid}/status" class="inline-form">'
                f'<input type="hidden" name="lead_id" value="{lead_id}"/>'
                '<input type="hidden" name="status" value="rejected"/>'
                '<button type="submit" class="btn secondary">Не тот человек</button></form>'
            )
        elif st == "confirmed":
            actions = (
                f'<form method="post" action="/tender-link/{lid}/status" class="inline-form">'
                f'<input type="hidden" name="lead_id" value="{lead_id}"/>'
                '<input type="hidden" name="status" value="rejected"/>'
                '<button type="submit" class="btn secondary">Снять подтверждение</button></form>'
            )
        rows.append(
            "<tr>"
            f"<td><strong>{_e(L.get('full_name') or '')}</strong><br/>"
            f"<span class='hint'>{_e((L.get('organization') or '')[:120])}</span></td>"
            f"<td>{conf} · <span class='hint'>{meth}</span></td>"
            f"<td><span class='pill active'>{_e(st_ru)}</span></td>"
            f"<td><a href=\"/contact/{cid}\">карточка контакта</a> · {actions}</td>"
            "</tr>"
        )
    return f"""
  <div class="card">
    <h2>Связь с базой контактов</h2>
    <p class="hint">По совпадению названия организации заказчика тендера с компанией в профиле контакта. Подтверждайте вручную перед работой с человеком.</p>
    <table class="dense">
      <thead><tr><th>Контакт</th><th>Уверенность</th><th>Статус</th><th></th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>"""


def lead_detail_page(lead, *, flash: str = "", tender_contact_links: list | None = None) -> str:
    from tender_agents.models import PipelineStatus

    sc = _score_class(lead.score)
    seg = lead.segment.value
    status_cls = "active" if lead.status.value == "active" else "done"
    reasons = "".join(f"<li>{_e(r)}</li>" for r in (lead.score_reasons or []))
    contacts = ""
    for c in lead.contacts:
        line = " · ".join(filter(None, [c.name, c.role, c.phone, c.email]))
        if line:
            contacts += f"<div class='card' style='padding:0.75rem;margin-bottom:0.5rem'>"
            contacts += f"<p><strong>{_e(line)}</strong></p>"
            if c.organization and c.organization not in (line or ""):
                contacts += f"<p class='hint'>{_e(c.organization)}</p>"
            if c.source_snippet:
                contacts += f"<p class='hint'>{_e(c.source_snippet[:280])}</p>"
            if c.linkedin_search_url:
                contacts += (
                    f"<p><a href=\"{_e(c.linkedin_search_url)}\" target=\"_blank\" rel=\"noopener\">"
                    f"Поиск в LinkedIn ↗</a></p>"
                )
            if c.yandex_search_url:
                contacts += (
                    f"<p><a href=\"{_e(c.yandex_search_url)}\" target=\"_blank\" rel=\"noopener\">"
                    f"Поиск в Яндексе ↗</a></p>"
                )
            contacts += "</div>"
    if not contacts:
        contacts = "<p class='hint'>Контакты не извлечены</p>"
    tlinks = ""
    if lead.id:
        tlinks = _tender_contact_links_block(lead.id, tender_contact_links or [])
    pipe_opts = "".join(
        f'<option value="{s.value}"{" selected" if lead.pipeline_status == s else ""}>{s.value}</option>'
        for s in PipelineStatus
    )
    ctx_inner = ""
    if lead.context_url:
        ctx_inner = (
            f'<p><a href="{_e(lead.context_url)}" target="_blank" rel="noopener">'
            f"Материал (статья / рейтинг) ↗</a></p>"
            f"<p>{_e(lead.context_title or '')}</p>"
        )
    link_label = "Ссылка на запись" if lead.channel == "open_media" else "Карточка на площадке ↗"
    body = f"""
  <h1>{_e(lead.title[:200])}</h1>
  <p class="meta">
    <span class="score {sc}">{lead.score}</span> ·
    <span class="seg {seg}">{seg}</span> ·
    <span class="pill {status_cls}">{_e(lead.status.value)}</span> ·
    канал: <strong>{_e(lead.channel)}</strong>
  </p>
  <ul class="reasons">{reasons}</ul>
  <div class="card">
    <h2>Контекст</h2>
    <p class="hint">Источник: {_e(lead.source)}</p>
    {ctx_inner}
  </div>
  <div class="card">
    <h2>Заказчик / компания</h2>
    <p>{_e(lead.customer_name or '—')}</p>
    <p class="hint">ИНН: {_e(lead.customer_inn or '—')} · {_e(lead.price or '')}</p>
    <p class="hint">Окончание: {_e(lead.end_date or '—')}</p>
    <p><a href="{_e(lead.url)}" target="_blank" rel="noopener">{_e(link_label)} ↗</a></p>
  </div>
  <div class="card"><h2>Контакты</h2>{contacts}</div>
  {tlinks}
  <div class="card">
    <h2>Питч FeedBackTalk</h2>
    <div class="pitch" id="pitch">{_e(lead.pitch or '')}</div>
    <p style="margin-top:0.75rem">
      <button type="button" onclick="navigator.clipboard.writeText(document.getElementById('pitch').innerText)">Копировать</button>
    </p>
  </div>
  <div class="card">
    <h2>Воронка</h2>
    <form method="post" action="/lead/{lead.id}/pipeline">
      <label>Этап</label>
      <select name="pipeline_status">{pipe_opts}</select>
      <label>Заметки</label>
      <textarea name="notes">{_e(lead.notes or '')}</textarea>
      <p style="margin-top:0.75rem"><button type="submit">Сохранить</button>
      <a href="/deal/{lead.id}" class="btn secondary" style="margin-left:0.5rem">Сделка</a>
      <a href="/" class="btn secondary" style="margin-left:0.5rem">← Тендеры</a></p>
    </form>
  </div>"""
    return _layout("Лид", "tenders", body, flash=flash)


def pipeline_page(columns: dict[str, str]) -> str:
    labels = {
        "new": "Новый",
        "qualified": "Квалификация",
        "proposal": "КП",
        "demo": "Демо",
        "won": "Выигран",
        "lost": "Проигран",
    }
    cols_html = ""
    for key, label in labels.items():
        inner = columns.get(key, "<p class='hint'>—</p>")
        cols_html += f'<div class="kcol"><h3>{label}</h3>{inner}</div>'
    body = f"""
  <h1>Воронка</h1>
  <p class="meta">Откройте лид → смените этап в карточке</p>
  <div class="kanban">{cols_html}</div>"""
    return _layout("Воронка", "pipeline", body)


def _dt_fmt(dt) -> str:
    if dt is None:
        return "—"
    if hasattr(dt, "strftime"):
        try:
            return dt.strftime("%d.%m.%Y")
        except Exception:
            pass
    return str(dt)[:16]


_QUAL_RU = {"fresh": "≤1 г", "aging": "1–2 г", "stale": ">2 г", "partial": "нет даты"}

_APPEARANCE_KIND_RU = {
    "kommersant_open": "Рейтинг / СМИ",
    "hr_ratings": "HR-рейтинг",
    "ai_open_media": "ИИ (любой сайт)",
    "listing_catalog": "Каталог (список)",
    "open_media": "Открытый источник",
    "web_mention": "Упоминание в сети",
    "web_contact": "Контакты компании",
    "web_speech": "Выступление",
    "web_interview": "Интервью",
    "web_profile": "Профиль",
    "web_rating": "Рейтинг",
}


def _appearance_meta_html(meta: dict | None) -> str:
    from tender_agents.text_utils import is_usable_research_url

    if not meta:
        return ""
    bits: list[str] = []
    for em in (meta.get("emails") or [])[:2]:
        bits.append(f"e-mail: {_e(str(em))}")
    for ph in (meta.get("phones") or [])[:1]:
        bits.append(f"тел.: {_e(str(ph))}")
    li = meta.get("linkedin_url")
    if li and is_usable_research_url(str(li)):
        bits.append(f'<a href="{_e(str(li))}" target="_blank" rel="noopener">LinkedIn</a>')
    if meta.get("telegram"):
        bits.append(_e(str(meta["telegram"])))
    if meta.get("vk"):
        bits.append(f'<a href="{_e(meta["vk"])}" target="_blank" rel="noopener">VK</a>')
    if not bits:
        return ""
    return f"<p class='hint'>На странице: {' · '.join(bits)}</p>"


def _appearances_section_html(apps: list, *, title: str, empty_hint: str) -> str:
    from tender_agents.text_utils import is_usable_research_url

    if not apps:
        return f"<p class='hint'>{_e(empty_hint)}</p>"
    blocks: list[str] = []
    for a in apps:
        if not is_usable_research_url(a.source_url or ""):
            continue
        kind = a.source_kind or ""
        kind_ru = _APPEARANCE_KIND_RU.get(kind, kind or "источник")
        st = _e((a.source_title or a.source_url or "")[:120])
        blocks.append(
            f"<div class='card' style='padding:0.75rem;margin-bottom:0.5rem'>"
            f"<p><strong>{_dt_fmt(a.appeared_at)}</strong> · <span class='badge'>{_e(kind_ru)}</span></p>"
            f"<p><a href=\"{_e(a.source_url)}\" target=\"_blank\" rel=\"noopener\">{st}</a></p>"
            f"<p class='hint'>{_e((a.snippet or '')[:600])}</p>"
            f"{_appearance_meta_html(getattr(a, 'meta_json', None))}"
            f"</div>"
        )
    return "\n".join(blocks)


def _contacts_sort_th(col: str, label: str, *, sort: str, order: str, query: str) -> str:
    if sort == col:
        next_order = "asc" if order == "desc" else "desc"
        active = "active"
        arrow = " ▲" if order == "asc" else " ▼"
    else:
        next_order = "desc" if col in ("last_seen", "appearances") else "asc"
        active = ""
        arrow = ""
    sep = "&" if query else ""
    href = f"/contacts?{query}{sep}sort={col}&order={next_order}"
    return f'<th><a class="sort {active}" href="{href}">{_e(label)}<span class="arrow">{arrow}</span></a></th>'


def _contacts_table_headers(*, sort: str, order: str, query: str) -> str:
    return (
        "<tr>"
        + _contacts_sort_th("organization", "Организация", sort=sort, order=order, query=query)
        + _contacts_sort_th("full_name", "ФИО", sort=sort, order=order, query=query)
        + _contacts_sort_th("position", "Должность", sort=sort, order=order, query=query)
        + _contacts_sort_th("last_seen", "Последнее появл.", sort=sort, order=order, query=query)
        + _contacts_sort_th("appearances", "Упоминаний", sort=sort, order=order, query=query)
        + "<th>Актуальн.</th><th>E-mail</th><th>Телефон</th><th>Поиск / соц.</th><th></th>"
        + "</tr>"
    )


def _contact_channels_cell(p) -> str:
    parts: list[str] = []
    if getattr(p, "linkedin_search_url", None):
        parts.append(
            f'<a href="{_e(p.linkedin_search_url)}" target="_blank" rel="noopener">LinkedIn</a>'
        )
    if getattr(p, "yandex_search_url", None):
        parts.append(f'<a href="{_e(p.yandex_search_url)}" target="_blank" rel="noopener">Яндекс</a>')
    if getattr(p, "linkedin_url", None):
        parts.append(f'<a href="{_e(p.linkedin_url)}" target="_blank" rel="noopener">профиль Li</a>')
    if getattr(p, "telegram", None):
        parts.append(_e(p.telegram))
    if getattr(p, "vk", None):
        parts.append(f'<a href="{_e(p.vk)}" target="_blank" rel="noopener">VK</a>')
    return " · ".join(parts) if parts else "—"


def _contacts_rows_html(profiles: list, *, group_org: bool) -> str:
    rows: list[str] = []
    last_org = None
    for p in profiles:
        if group_org and p.organization != last_org:
            rows.append(
                f'<tr class="grp"><td colspan="10"><strong>{_e(p.organization)}</strong></td></tr>'
            )
            last_org = p.organization
        qcls = f"qual-{_e(p.data_quality)}" if p.data_quality else "qual-partial"
        rows.append(
            "<tr>"
            f"<td>{_e((p.organization or '')[:80])}</td>"
            f"<td><strong>{_e(p.full_name or '')}</strong></td>"
            f"<td>{_e((p.position or '—')[:80])}</td>"
            f"<td>{_dt_fmt(p.last_seen_at)}</td>"
            f"<td>{p.appearance_count}</td>"
            f"<td><span class=\"{qcls}\">{_e(_QUAL_RU.get(p.data_quality, p.data_quality))}</span></td>"
            f"<td>{_e(p.email or '—')}</td>"
            f"<td>{_e(p.phone or '—')}</td>"
            f"<td>{_contact_channels_cell(p)}</td>"
            f"<td><a href=\"/contact/{p.id}\">открыть</a></td>"
            "</tr>"
        )
    return "\n".join(rows) or (
        "<tr><td colspan='10'>Пока пусто — в <a href='/settings?tab=channels'>Импорт СМИ</a> вставьте URL и нажмите «Импортировать», "
        "или в терминале: <code>tender-leads open ingest URL</code> "
        "(если таблица не находится по сети — добавьте <code>--html-file сохранённая_страница.html</code>). "
        "Для массовых закладок в <code>config/channels.yaml</code> нужно <code>enabled: true</code>.</td></tr>"
    )


def contacts_list_page(
    *,
    stats: dict,
    profiles: list,
    total: int,
    filter_query: str,
    sort: str,
    order: str,
    group_org: bool,
    q: str,
    organization: str,
    within_years: int,
    has_email: bool,
    has_phone: bool,
    has_linkedin_hint: bool,
    link_stats: dict[str, int] | None = None,
    flash: str = "",
) -> str:
    headers = _contacts_table_headers(sort=sort, order=order, query=filter_query)
    rows = _contacts_rows_html(profiles, group_org=group_org)
    grp_checked = " checked" if group_org else ""
    ye = within_years if within_years in (0, 1, 2, 3, 5) else 0
    yopts = "".join(
        f'<option value="{v}"{" selected" if v == ye else ""}>{lbl}</option>'
        for v, lbl in (
            (0, "За всё время"),
            (1, "Последний год"),
            (2, "Последние 2 года"),
            (3, "Последние 3 года"),
            (5, "Последние 5 лет"),
        )
    )
    he = " checked" if has_email else ""
    hp = " checked" if has_phone else ""
    hl = " checked" if has_linkedin_hint else ""
    ls = link_stats or {}
    parts_ls = [f"{k}: {v}" for k, v in sorted(ls.items()) if v]
    link_stats_html = (
        f"<p class='link-stats'>Связи тендер↔контакт в БД: {_e(', '.join(parts_ls) if parts_ls else 'пока нет')}</p>"
    )
    fq_esc = _e(filter_query)
    body = f"""
  <h1>База контактов</h1>
  <p class="meta">Организация, должность, ФИО, где светились в открытых источниках; поля под e-mail, телефон и соцсети. Тендеры — в разделе «Тендеры».</p>
  <div class="stats">
    <div class="stat"><b>{stats.get('total', 0)}</b>в выборке</div>
    <div class="stat"><b>{stats.get('with_email', 0)}</b>с e-mail</div>
    <div class="stat"><b>{stats.get('with_phone', 0)}</b>с телефоном</div>
    <div class="stat"><b>{stats.get('appearance_sum', 0)}</b>всего упоминаний</div>
  </div>
  {link_stats_html}
  <div class="toolbar">
    <form method="get" action="/contacts">
      <input name="q" placeholder="ФИО, компания, должность…" value="{_e(q)}"/>
      <input name="organization" placeholder="Организация" value="{_e(organization)}" style="width:180px"/>
      <select name="within_years">{yopts}</select>
      <label class="chk" style="display:inline-flex;margin:0"><input type="checkbox" name="has_email" value="1"{he}/> есть e-mail</label>
      <label class="chk" style="display:inline-flex;margin:0"><input type="checkbox" name="has_phone" value="1"{hp}/> есть тел.</label>
      <label class="chk" style="display:inline-flex;margin:0"><input type="checkbox" name="has_linkedin_hint" value="1"{hl}/> LinkedIn/поиск</label>
      <label class="chk" style="display:inline-flex;margin:0"><input type="checkbox" name="group_org" value="1"{grp_checked}/> группа по орг.</label>
      <input type="hidden" name="sort" value="{_e(sort)}"/>
      <input type="hidden" name="order" value="{_e(order)}"/>
      <button type="submit">Фильтр</button>
    </form>
    <a href="/settings?tab=channels" class="btn secondary">Импорт СМИ / Excel</a>
    <a href="/" class="btn secondary">← Тендеры</a>
  </div>
  <div class="toolbar-actions">
    <form method="post" action="/contacts/rebuild-links">
      <input type="hidden" name="return_query" value="{fq_esc}"/>
      <button type="submit">Пересчитать связи тендер ↔ контакт</button>
    </form>
    <form method="post" action="/contacts/enrich-batch">
      <input type="hidden" name="return_query" value="{fq_esc}"/>
      <button type="submit" class="btn secondary">Обогатить из поиска (до 12 без LinkedIn)</button>
    </form>
  </div>
  <p class="hint">Под фильтр попадает <strong>{total}</strong> контактов. Актуальность — по дате последнего появления в источниках (карточка → хронология «где светился»). Кнопка обогащения ходит в Яндекс/DuckDuckGo по вашим ссылкам поиска в карточке контакта — не злоупотребляйте частотой.</p>
  <table>
    <thead>{headers}</thead>
    <tbody>{rows}</tbody>
  </table>"""
    return _layout("Контакты", "contacts", body, flash=flash)


def _contact_tender_links_block(tender_links: list) -> str:
    if not tender_links:
        return ""
    rows = []
    for L in tender_links:
        lid = int(L["lead_id"])
        rows.append(
            "<tr>"
            f"<td><a href=\"/lead/{lid}\">{_e((L.get('title') or '')[:120])}</a></td>"
            f"<td>{_e((L.get('customer_name') or '')[:100])}</td>"
            f"<td>{int(L.get('confidence') or 0)}</td>"
            f"<td><span class='hint'>{_e(L.get('status') or '')}</span></td>"
            "</tr>"
        )
    return f"""
  <div class="card">
    <h2>Связанные тендеры</h2>
    <p class="hint">Сопоставление по организации заказчика и компании в вашем профиле. Откройте тендер и подтвердите связь, если это тот же заказчик.</p>
    <table class="dense">
      <thead><tr><th>Тендер</th><th>Заказчик</th><th>Уверенность</th><th>Статус</th></tr></thead>
      <tbody>{"".join(rows)}</tbody>
    </table>
  </div>"""


def _event_appearances_table(apps: list) -> str:
    event_types = {"conference", "exhibition", "talk", "interview", "rating", "article", "event"}
    rows = []
    for a in apps:
        t = (a.appearance_type or a.source_kind or "").replace("web_", "")
        if t not in event_types and (a.source_kind or "") not in ("manual", "import_excel"):
            continue
        rows.append(
            f"<tr><td>{_dt_fmt(a.appeared_at)}</td><td>{_e(t)}</td>"
            f"<td>{_e((a.source_title or '')[:120])}</td>"
            f"<td>{_e((a.snippet or '')[:80])}</td>"
            f"<td><a href='{_e(a.source_url)}' target='_blank' rel='noopener'>↗</a></td></tr>"
        )
    if not rows:
        return "<p class='hint'>Пока нет мероприятий — добавьте вручную или импортируйте из Excel.</p>"
    return (
        "<table class='dense'><thead><tr><th>Дата</th><th>Тип</th><th>Название</th>"
        "<th>Место / заметка</th><th>Ссылка</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def contact_detail_page(p, *, flash: str = "", tender_links: list | None = None, research_job=None) -> str:
    media_apps = [a for a in p.appearances if (a.source_kind or "") == "kommersant_open"]
    web_apps = [a for a in p.appearances if (a.source_kind or "").startswith("web_")]
    media_block = _appearances_section_html(
        media_apps,
        title="",
        empty_hint="Нет импорта из СМИ — добавьте через «Импорт СМИ».",
    )
    web_block = _appearances_section_html(
        web_apps,
        title="",
        empty_hint="Пока нет — нажмите «Исследовать в сети» (поиск по ФИО и компании, обход выдачи).",
    )
    qcls = f"qual-{_e(p.data_quality)}" if p.data_quality else "qual-partial"
    tlinks = _contact_tender_links_block(tender_links or [])
    compliance_banner = (
        '<p class="hint" style="background:#fef3c7;padding:0.5rem 0.75rem;border-radius:6px">'
        "Данные только из открытых источников; перед КП подтвердите канал кнопкой ниже.</p>"
    )
    verified = ""
    if getattr(p, "channel_verified_at", None):
        verified = f"<p class='hint'>Канал проверен: {_dt_fmt(p.channel_verified_at)}</p>"
    captcha_block = ""
    if research_job and getattr(research_job, "status", "") in ("needs_captcha", "needs_manual"):
        url = _e(research_job.challenge_url or "")
        captcha_block = f"""
    <div class="card" style="border-color:#f59e0b">
      <h2>Нужна капча</h2>
      <p>{_e(research_job.instructions or '')}</p>
      <p><a href="{url}" target="_blank" rel="noopener" class="btn secondary">Открыть страницу поиска</a></p>
      <form method="post" action="/contact/research/{research_job.id}/resume" enctype="multipart/form-data">
        <label>Cookie (опционально)</label>
        <textarea name="cookies_text" rows="2" placeholder="sessionid=…"></textarea>
        <label>HTML страницы после капчи</label>
        <input type="file" name="html_upload" accept=".html,.htm"/>
        <button type="submit">Я прошёл капчу — продолжить</button>
      </form>
    </div>"""
    bio_val = _e(getattr(p, "bio", None) or "")
    events_tbl = _event_appearances_table(p.appearances)
    research = ""
    if p.id:
        research = (
            f'<div class="card"><h2>Исследование в сети</h2>'
            f"<p class='hint'>Запрос как вручную: «ФИО + компания + контакт email». "
            f"Выдача: Brave → Яндекс → DuckDuckGo; при капче — форма ниже.</p>"
            f'<p style="margin-top:0.75rem">'
            f'<form method="post" action="/contact/{p.id}/research" style="display:inline">'
            f'<button type="submit">Исследовать в сети</button></form> '
            f'<form method="post" action="/contact/{p.id}/enrich" style="display:inline">'
            f'<button type="submit" class="btn secondary">Быстро: только каналы</button></form> '
            f'<form method="post" action="/contact/{p.id}/sanitize-channels" style="display:inline">'
            f'<button type="submit" class="btn secondary">Убрать мусор (e-mail/тел./битые ссылки)</button></form>'
            f"</p></div>"
        )
    body = f"""
  {compliance_banner}
  <h1>{_e(p.full_name)}</h1>
  <p class="meta">{_e(p.organization)} · {_e(p.position or 'должность не указана')}</p>
  {verified}
  {captcha_block}
  <p>Актуальность данных: <span class="{qcls}"><strong>{_e(_QUAL_RU.get(p.data_quality, p.data_quality))}</strong></span>
     · последнее появление: <strong>{_dt_fmt(p.last_seen_at)}</strong>
     · упоминаний: <strong>{p.appearance_count}</strong></p>
  {research}
  <div class="row2">
    <div class="card">
      <h2>Каналы связи</h2>
      <p>E-mail: {_e(p.email or '—')}</p>
      <p>Телефон: {_e(p.phone or '—')}</p>
      <p>Telegram: {_e(p.telegram or '—')}</p>
      <p>VK: {_e(p.vk or '—')}</p>
      <p>{_contact_channels_cell(p)}</p>
      <form method="post" action="/contact/{p.id}/verify-channel" style="margin-top:1rem">
        <button type="submit" class="btn secondary">Канал проверен</button>
      </form>
    </div>
    <div class="card">
      <h2>Описание</h2>
      <form method="post" action="/contact/{p.id}/bio">
        <textarea name="bio" rows="5" style="width:100%">{bio_val}</textarea>
        <p style="margin-top:0.5rem"><button type="submit">Сохранить описание</button></p>
      </form>
    </div>
    <div class="card">
      <h2>Заметки</h2>
      <p class="hint">{_e(p.notes or '—')}</p>
    </div>
  </div>
  <div class="card">
    <h2>Мероприятия и выступления</h2>
    {events_tbl}
    <form method="post" action="/contact/{p.id}/appearance" style="margin-top:1rem">
      <label>Тип</label>
      <select name="appearance_type">
        <option value="conference">Конференция</option>
        <option value="exhibition">Выставка</option>
        <option value="talk">Доклад</option>
        <option value="interview">Интервью</option>
        <option value="event">Другое</option>
      </select>
      <label>Название</label>
      <input name="source_title" required/>
      <label>Ссылка</label>
      <input name="source_url" type="url"/>
      <label>Место / дата (текст)</label>
      <input name="snippet"/>
      <button type="submit">Добавить мероприятие</button>
    </form>
  </div>
  <div class="card">
    <h2>Импорт из СМИ / рейтингов</h2>
    {media_block}
  </div>
  <div class="card">
    <h2>Находки агента (поиск в интернете)</h2>
    {web_block}
  </div>
  {tlinks}
  <p><a href="/contacts" class="btn secondary">← К списку контактов</a></p>"""
    return _layout("Контакт", "contacts", body, flash=flash)


def analytics_page(*, stats: dict, by_segment: dict, by_pipeline: dict) -> str:
    def bars(data: dict[str, int]) -> str:
        if not data:
            return "<p class='hint'>Нет данных</p>"
        mx = max(data.values()) or 1
        out = ""
        for k, v in sorted(data.items(), key=lambda x: -x[1]):
            w = int(100 * v / mx)
            out += (
                f'<p><strong>{_e(k)}</strong> {v}'
                f'<span style="display:block;height:6px;background:#2563eb;width:{w}%;'
                f'max-width:300px;border-radius:3px;margin-top:2px"></span></p>'
            )
        return out

    body = f"""
  <h1>Аналитика тендеров</h1>
  <p class="meta">Только закупки (канал tender). Контакты из СМИ — в разделе «Контакты».</p>
  <div class="stats">
    <div class="stat"><b>{stats.get('total', 0)}</b>тендеров</div>
    <div class="stat"><b>{stats.get('hot', 0)}</b>горячих</div>
    <div class="stat"><b>{stats.get('avg_score', 0)}</b>средний скор</div>
    <div class="stat"><b>{stats.get('with_contact', 0)}</b>с e-mail/тел.</div>
  </div>
  <div class="row2">
    <div class="card"><h2>По сегменту</h2>{bars(by_segment)}</div>
    <div class="card"><h2>По воронке</h2>{bars(by_pipeline)}</div>
  </div>"""
    return _layout("Аналитика", "analytics", body)


def leads_page(*, backend: str, count: int, q: str, source_options: str, rows: str) -> str:
    return queue_page(
        backend=backend,
        stats={
            "total": count,
            "hot": 0,
            "avg_score": 0,
            "with_contact": 0,
            "with_search_hints": 0,
            "by_channel": {},
        },
        q=q,
        min_score=0,
        segment="",
        pipeline_status="",
        source="",
        channel="tender",
        channel_options=_tender_scope_options(scope="tender"),
        hot_only=False,
        source_options=source_options,
        segment_options='<option value="">Все сегменты</option>',
        rows=rows,
    )


def channels_settings_section(cfg: dict) -> str:
    ch = cfg.get("channels") or {}
    bookmarks = ch.get("bookmarks") or []
    rows: list[str] = []
    for b in bookmarks:
        if not isinstance(b, dict):
            continue
        en = "да" if b.get("enabled") else "нет"
        url = (b.get("url") or "").strip()
        url_e = _e(url)
        short = url[:72] + ("…" if len(url) > 72 else "")
        note = _e((b.get("note") or "").strip())
        rows.append(
            f"<tr><td>{en}</td><td><a href=\"{url_e}\" target=\"_blank\" rel=\"noopener\">{_e(short)}</a></td><td>{note}</td></tr>"
        )
    table = (
        "<table><thead><tr><th>Вкл.</th><th>URL</th><th>Заметка</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
        if rows
        else "<p class='hint'>Список пуст — отредактируйте <code>config/channels.yaml</code></p>"
    )
    return import_excel_section() + f"""
  <div class="settings-section">
    <h2>Импорт по URL (СМИ / рейтинги)</h2>
    <p class="hint"><strong>Закладки:</strong> в <code>config/channels.yaml</code> у URL должно быть <code>enabled: true</code>, иначе кнопка «все включённые» их пропускает. Импорт попадает в раздел «Контакты».</p>
    <p class="hint"><strong>Любой URL</strong> (новости, саммиты, рейтинги): YandexGPT извлекает людей; <strong>каталоги</strong> (globalmsk и др.) — HTML-парсер обходит <strong>все страницы пагинации</strong> (offset/page). Дубликаты по ФИО+компания дополняют карточку. <a href="/settings?tab=apis">Yandex API</a> для статей без списка ссылок. Playwright при 403. Офлайн: <code>--html-file</code> (одна страница).</p>
    <form method="post" action="/settings/channels-ingest">
      <label>URL материала</label>
      <input name="page_url" type="url" required placeholder="https://hrsummit.ru/hrclubnews/… или любой материал с ФИО"/>
      <label>Макс. записей (0 = все)</label>
      <input type="number" name="limit" value="0" min="0" max="500"/>
      <label class="chk"><input type="checkbox" name="dry_run"/> Только проверка (в БД не писать)</label>
      <p style="margin-top:1rem"><button type="submit">Импортировать</button></p>
    </form>
  </div>
  <div class="settings-section">
    <h2>Закладки из конфига</h2>
    {table}
    <form method="post" action="/settings/channels-bookmarks" style="margin-top:1rem">
      <label class="chk"><input type="checkbox" name="dry_run"/> Сухой прогон (не писать в БД)</label>
      <p style="margin-top:1rem"><button type="submit">Загрузить все включённые закладки</button></p>
    </form>
    <p class="hint">Массовый импорт в фоне — затем откройте раздел «Контакты».</p>
  </div>"""


def _tab_link(name: str, label: str, active: str) -> str:
    cls = "active" if active == name else ""
    return f'<a href="/settings?tab={name}" class="{cls}">{label}</a>'


def _panel_visible(tab: str, panel: str) -> str:
    return "" if tab == panel else "hidden"


def platform_job_detail_page(job) -> str:
    """Полная карточка фоновой задачи."""
    import json

    status = (getattr(job, "status", None) or "").lower()
    detail = "<p class='hint'>Задача ещё выполняется</p>"
    if status in ("completed", "failed"):
        chunks: list[str] = []
        if getattr(job, "error", None):
            chunks.append(
                f"<p style='color:#fca5a5'><strong>Ошибка:</strong> {_e(str(job.error))}</p>"
            )
        if getattr(job, "result", None):
            body = json.dumps(job.result, ensure_ascii=False, indent=2)
            chunks.append(
                f"<pre style='white-space:pre-wrap;font-size:0.8rem'>{_e(body)}</pre>"
            )
        detail = "".join(chunks) or "<p class='hint'>Нет данных</p>"
    body = f"""
  <h1>Задача #{job.id}</h1>
  <p class="meta">{_e(job.job_type)} · {_e(job.status)}</p>
  <div class="card"><h2>Результат</h2>{detail}</div>
  <p><a href="/settings?tab=jobs">← Настройки → Задачи</a></p>"""
    return _layout(f"Задача #{job.id}", "settings", body)


def _platform_job_details_html(job) -> str:
    """Результат / ошибка для завершённых задач (expand row)."""
    status = (getattr(job, "status", None) or "").lower()
    if status not in ("completed", "failed"):
        return "—"
    parts: list[str] = []
    err = getattr(job, "error", None)
    if err:
        parts.append(
            f"<p style='margin:0.35rem 0;color:#fca5a5;font-size:0.8rem'>"
            f"<strong>Ошибка:</strong> {_e(str(err)[:1500])}</p>"
        )
    result = getattr(job, "result", None)
    if result:
        import json

        body = json.dumps(result, ensure_ascii=False, indent=2)
        if len(body) > 6000:
            body = body[:6000] + "\n…"
        parts.append(
            f"<pre style='margin:0.35rem 0 0;font-size:0.72rem;white-space:pre-wrap;"
            f"max-height:14rem;overflow:auto'>{_e(body)}</pre>"
        )
    if not parts:
        return "—"
    link = f" <a href='/settings/platform-job/{job.id}' style='margin-left:0.35rem'>полностью</a>"
    return (
        "<details style='font-size:0.8rem'>"
        "<summary style='cursor:pointer;color:#6eb5ff'>Показать</summary>"
        f"{''.join(parts)}{link}</details>"
    )


def _platform_jobs_rows(jobs: list) -> str:
    if not jobs:
        return "<tr><td colspan='5'>Задач пока нет</td></tr>"
    rows = []
    for j in jobs:
        created = ""
        if getattr(j, "created_at", None):
            created = str(j.created_at)[:19]
        rows.append(
            f"<tr><td>{j.id}</td><td>{_e(j.job_type)}</td><td>{_e(j.status)}</td>"
            f"<td>{_e(created)}</td><td>{_platform_job_details_html(j)}</td></tr>"
        )
    return "".join(rows)


def deal_card_page(lead, *, tender_contact_links: list | None = None, flash: str = "") -> str:
    """Единая карточка сделки: тендер + ЛПР + питч."""
    from tender_agents.models import PipelineStatus

    sc = _score_class(lead.score)
    seg = lead.segment.value
    lpr_rows = ""
    for link in tender_contact_links or []:
        cid = link.get("contact_id")
        conf = link.get("confidence") or 0
        st = link.get("status") or ""
        lpr_rows += (
            f"<tr><td><a href='/contact/{cid}'>{_e(link.get('full_name') or '')}</a></td>"
            f"<td>{_e((link.get('organization') or '')[:50])}</td>"
            f"<td>{conf}</td><td>{_e(st)}</td></tr>"
        )
    if not lpr_rows:
        lpr_rows = "<tr><td colspan='4'>Нет связей — запустите «Связи» в Настройки → Задачи</td></tr>"
    pipe_opts = "".join(
        f'<option value="{s.value}"{" selected" if lead.pipeline_status == s else ""}>{s.value}</option>'
        for s in PipelineStatus
    )
    body = f"""
  <h1>Сделка</h1>
  <p class="meta"><span class="score {sc}">{lead.score}</span> · <span class="seg {seg}">{seg}</span></p>
  <h2 style="font-size:1.1rem;margin-top:0">{_e(lead.title[:200])}</h2>
  <p class="hint">Заказчик: {_e(lead.customer_name or '—')} · до {_e(lead.end_date or '—')}</p>
  <p><a href="{_e(lead.url)}" target="_blank" rel="noopener">Карточка закупки ↗</a>
     · <a href="/lead/{lead.id}">Полная карточка лида</a></p>
  <div class="card">
    <h2>ЛПР (связи)</h2>
    <table class="dense"><thead><tr><th>ФИО</th><th>Организация</th><th>Увер.</th><th>Статус</th></tr></thead>
    <tbody>{lpr_rows}</tbody></table>
  </div>
  <div class="card">
    <h2>Питч</h2>
    <div class="pitch">{_e(lead.pitch or '')}</div>
  </div>
  <div class="card">
    <h2>Воронка</h2>
    <form method="post" action="/lead/{lead.id}/pipeline">
      <select name="pipeline_status">{pipe_opts}</select>
      <textarea name="notes" placeholder="Заметки">{_e(lead.notes or '')}</textarea>
      <p style="margin-top:0.75rem"><button type="submit">Сохранить</button>
      <a href="/queue" class="btn secondary" style="margin-left:0.5rem">Очередь</a></p>
    </form>
  </div>"""
    return _layout("Сделка", "tenders", body, flash=flash)


def analyst_page(
    *,
    report: dict | None,
    date_from: str = "",
    date_to: str = "",
    period_days: str = "90",
) -> str:
    report_html = "<p class='hint'>Задайте период и откройте страницу с параметрами или нажмите «Анализ».</p>"
    if report:
        stats = report.get("stats") or {}
        recs = report.get("keyword_recommendations") or []
        report_html = f"""
    <p>{_e(report.get('summary') or '')}</p>
    <p class="hint">{_e(report.get('platform_notes') or '')}</p>
    <h3>Статистика</h3>
    <pre style="white-space:pre-wrap;font-size:0.85rem">{_e(str(stats)[:4000])}</pre>
    <h3>Рекомендуемые ключи</h3>
    <ul>{''.join(f'<li>{_e(k)}</li>' for k in recs[:12])}</ul>"""
    body = f"""
  <h1>Аналитика истории тендеров</h1>
  <p class="hint">Выгрузка: <a href="/api/tenders/history.csv">CSV истории</a></p>
  <form method="get" action="/analyst" class="card">
    <div class="row2">
      <div><label>С</label><input type="date" name="date_from" value="{_e(date_from)}"/></div>
      <div><label>По</label><input type="date" name="date_to" value="{_e(date_to)}"/></div>
    </div>
    <label>Или дней назад (если «С» пусто)</label>
    <input type="number" name="period_days" value="{_e(period_days)}" min="7" max="730"/>
    <p style="margin-top:1rem"><button type="submit">Построить отчёт</button></p>
  </form>
  <div class="card">{report_html}</div>"""
    return _layout("Аналитика", "analytics", body)


def settings_page(
    cfg: dict,
    *,
    flash: str = "",
    tab: str = "project",
    platform_jobs: list | None = None,
) -> str:
    kw_text = _e("\n".join(cfg.get("keywords", [])))
    sources = cfg.get("sources", {})
    agents = cfg.get("agents", {})

    def agent_text(role: str) -> str:
        return _e((agents.get(role, {}) or {}).get("instructions", "").strip())

    backends = ["httpx", "playwright", "crawl4ai", "yandex", "scrapegraph"]
    backend_opts = "".join(
        f'<option value="{b}" {"selected" if cfg["scraper_backend"] == b else ""}>{b}</option>'
        for b in backends
    )
    ap_local = "selected" if cfg["agent_provider"] == "local" else ""
    ap_yandex = "selected" if cfg["agent_provider"] == "yandex" else ""

    source_checks = ""
    for sid, sc in sources.items():
        checked = "checked" if sc.get("enabled", True) else ""
        source_checks += f"""
        <label class="chk">
          <input type="checkbox" name="source_enabled" value="{_e(sid)}" {checked}/>
          <span><strong>{_e(sid)}</strong> — {_e(sc.get('name', sid))}</span>
        </label>"""

    yandex_on = "on" if cfg.get("yandex_api_key_set") else "off"
    sgai_on = "on" if cfg.get("sgai_api_key_set") else "off"
    yandex_hint = (
        f"ключ: {_e(cfg.get('yandex_api_key_mask', ''))}"
        if cfg.get("yandex_api_key_set")
        else "ключ не задан"
    )
    yr = "checked" if cfg.get("yandex_use_responses_api") else ""
    yw = "checked" if cfg.get("yandex_enable_web_search") else ""

    channels_html = channels_settings_section(cfg)

    tabs = (
        _tab_link("project", "Проект", tab)
        + _tab_link("apis", "API", tab)
        + _tab_link("sources", "Площадки", tab)
        + _tab_link("keywords", "Ключи", tab)
        + _tab_link("agents", "Агенты", tab)
        + _tab_link("run", "Запуск", tab)
        + _tab_link("jobs", "Задачи", tab)
        + _tab_link("channels", "Каналы", tab)
    )

    nav_active = "channels" if tab == "channels" else "settings"

    body = f"""
  <h1>Настройки</h1>
  <p class="meta">Файлы: config/*.yaml, секреты в .env</p>
  <p class="hint" style="background:#422006;padding:0.5rem 0.75rem;border-radius:6px;margin-bottom:0.75rem">
    Открывайте дашборд через <a href="/settings?tab={_e(tab)}"><strong>http://111.88.147.92</strong></a> (порт 80).
    Прямой доступ к <code>:8765</code> из интернета может обрывать страницу — это не баг вкладки «Агенты».
  </p>
  <div class="tabs">{tabs}</div>

  <div class="card {_panel_visible(tab, 'project')}">
    <form method="post" action="/settings/project">
      <div class="row2">
        <div>
          <label>Бэкенд скрапинга</label>
          <select name="scraper_backend">{backend_opts}</select>
        </div>
        <div>
          <label>Провайдер агентов</label>
          <select name="agent_provider">
            <option value="local" {ap_local}>local</option>
            <option value="yandex" {ap_yandex}>yandex</option>
          </select>
        </div>
      </div>
      <div class="row2">
        <div><label>Задержка (сек)</label>
          <input type="number" step="0.5" name="request_delay_sec" value="{cfg['request_delay_sec']}"/></div>
        <div><label>Database URL</label>
          <input name="database_url" value="{_e(cfg['database_url'])}"/></div>
      </div>
      <p style="margin-top:1rem"><button type="submit">Сохранить</button></p>
    </form>
  </div>

  <div class="card {_panel_visible(tab, 'apis')}">
    <form method="post" action="/settings/apis">
      <h2>Yandex AI Studio</h2>
      <p class="hint"><span class="status-dot {yandex_on}"></span>{yandex_hint}</p>
      <label>API Key <span class="hint">(пусто = не менять)</span></label>
      <input type="password" name="yandex_api_key" placeholder="{SECRET_MASK}" autocomplete="new-password"/>
      <label>ID каталога (Folder ID)</label>
      <input name="yandex_folder_id" value="{_e(cfg.get('yandex_folder_id', ''))}"
        placeholder="b1gai2s8u8p5vdje63jo"/>
      <p class="hint">Из <a href="https://console.yandex.cloud/" target="_blank" rel="noopener">console.yandex.cloud</a> → каталог → ID. Достаточно только этого поля.</p>
      <label>Модель</label>
      <input name="yandex_model" value="{_e(cfg.get('yandex_model', 'yandexgpt'))}"
        placeholder="yandexgpt или gpt://b1g…/yandexgpt"/>
      <p class="hint">Короткое имя (<code>yandexgpt</code>, <code>yandexgpt-lite</code>, <code>yandexgpt-pro</code>) или полный URI <code>gpt://ID_каталога/модель</code> — тогда Folder ID можно не дублировать.</p>
      <label class="chk"><input type="checkbox" name="yandex_use_responses_api" {yr}/> Responses API <span class="hint">(у Yandex Cloud обычно нет — оставьте выкл.)</span></label>
      <label class="chk"><input type="checkbox" name="yandex_enable_web_search" {yw}/> Web Search
        <span class="hint">(только с Responses API; при chat/completions не работает — лучше выкл.)</span></label>

      <h2>ScrapeGraphAI</h2>
      <p class="hint"><span class="status-dot {sgai_on}"></span>{'задан' if cfg.get('sgai_api_key_set') else 'не задан'}</p>
      <label>SGAI_API_KEY</label>
      <input type="password" name="sgai_api_key" placeholder="{SECRET_MASK}" autocomplete="new-password"/>

      <h2>ГосПлан / Ollama</h2>
      <label>GOSPLAN_API_URL</label>
      <input name="gosplan_api_url" value="{_e(cfg.get('gosplan_api_url', ''))}"/>
      <label>GOSPLAN_API_KEY</label>
      <input type="password" name="gosplan_api_key" placeholder="{SECRET_MASK}" autocomplete="new-password"/>
      <div class="row2">
        <div><label>Ollama URL</label><input name="ollama_base_url" value="{_e(cfg.get('ollama_base_url', ''))}"/></div>
        <div><label>Ollama model</label><input name="ollama_model" value="{_e(cfg.get('ollama_model', ''))}"/></div>
      </div>
      <p style="margin-top:1rem">
        <button type="submit">Сохранить API</button>
        <button type="submit" formaction="/settings/test-yandex" class="secondary" style="margin-left:0.5rem">Проверить Yandex</button>
      </p>
    </form>
  </div>

  <div class="card {_panel_visible(tab, 'sources')}">
    <p class="hint">Для стабильного сбора достаточно <strong>zakupki</strong> + бэкенд <code>httpx</code>.
      Сбербанк-АСТ часто недоступен (<code>ERR_CONNECTION_TIMED_OUT</code>) — не включайте без проверки.</p>
    <form method="post" action="/settings/sources">
      {source_checks}
      <p style="margin-top:1rem"><button type="submit">Сохранить площадки</button></p>
    </form>
  </div>

  <div class="card {_panel_visible(tab, 'keywords')}">
    <form method="post" action="/settings/keywords">
      <label>Ключевые слова (по одному на строку)</label>
      <textarea name="keywords_text">{kw_text}</textarea>
      <p class="hint">При сборе — <strong>только этот список</strong>, если не включена опция ниже.</p>
      <label class="chk"><input type="checkbox" name="merge_extra" value="1"{" checked" if cfg.get("keywords_merge_extra") else ""}/> Добавить keywords_hr.yaml и keywords_cx.yaml</label>
      <p class="hint">В сбор пойдёт ({len(cfg.get('keywords_effective', []))}): {_e(', '.join(cfg.get('keywords_effective', [])[:12]))}{'…' if len(cfg.get('keywords_effective', [])) > 12 else ''}</p>
      <p style="margin-top:1rem"><button type="submit">Сохранить</button>
      <a href="/settings?tab=run" class="btn secondary" style="margin-left:0.5rem">→ Запустить сбор</a></p>
    </form>
    <hr style="margin:1.5rem 0;border-color:#2a3544"/>
    <h3>Агент: ключи из задачи</h3>
    <form method="post" action="/settings/keyword-plan">
      <label>Задача менеджера</label>
      <textarea name="manager_task" rows="3" placeholder="Напр.: опросы HR в госсекторе, eNPS, без CRM"></textarea>
      <label class="chk"><input type="checkbox" name="merge_extra" value="1"/> Учесть keywords_hr / keywords_cx</label>
      <label class="chk"><input type="checkbox" name="save_keywords" value="1"/> Сразу записать в keywords.yaml</label>
      <p style="margin-top:0.75rem"><button type="submit">Сгенерировать ключи</button></p>
      <p class="hint">Результат — во вкладке «Задачи» (фон).</p>
    </form>
  </div>

  <div class="card {_panel_visible(tab, 'agents')}">
    <p class="hint">Инструкции для <strong>YandexGPT</strong> (HTML → JSON). Сейчас: провайдер <code>{_e(cfg.get('agent_provider', 'local'))}</code>,
      бэкенд <code>{_e(cfg['scraper_backend'])}</code>.
      Применяются при <a href="/settings?tab=project">Проект → yandex</a> или <code>scraper_backend=yandex</code>.
      При <code>local</code> + <code>httpx</code> — нативный парсер ЕИС, эти тексты не используются.
      Crawl4AI / ScrapeGraph — <code>scrape/prompts.py</code> (синхрон с Search/Enrich).</p>
    <p class="hint">{'<span class="status-dot on"></span>Yandex API задан' if cfg.get('yandex_api_key_set') else '<span class="status-dot off"></span>Yandex API не задан — <a href="/settings?tab=apis">настроить</a> перед запуском'}</p>
    <form method="post" action="/settings/agents">
      <label>Search Agent</label>
      <textarea name="search_instructions">{agent_text('search')}</textarea>
      <label>Enrich Agent</label>
      <textarea name="enrich_instructions">{agent_text('enrich')}</textarea>
      <label>Orchestrator</label>
      <textarea name="orchestrator_instructions">{agent_text('orchestrator')}</textarea>
      <p style="margin-top:1rem"><button type="submit">Сохранить агентов</button></p>
    </form>
  </div>

  <div class="card {_panel_visible(tab, 'run')}">
    <p class="hint"><strong>Активные ключи ({len(cfg.get('keywords_effective', []))}):</strong> {_e(', '.join(cfg.get('keywords_effective', [])))}</p>
    <p class="hint">Бэкенд: <code>{_e(cfg['scraper_backend'])}</code>, провайдер: <code>{_e(cfg.get('agent_provider', 'local'))}</code>.
      {'Yandex API настроен.' if cfg.get('yandex_configured') else '⚠ Yandex API <strong>не задан</strong> — при выборе yandex сбор пойдёт через <strong>httpx</strong> (ЕИС). <a href="/settings?tab=apis">Настроить API</a>.'}</p>
    <p class="hint">Без Playwright на <code>httpx</code> работают <strong>zakupki</strong> и нативные парсеры b2b/Сбер; для JS-вёрстки:
      <code>pip install -e '.[playwright]' &amp;&amp; playwright install chromium</code>.
      Иначе в «Площадки» оставьте только <strong>zakupki</strong>.</p>
    <form method="post" action="/settings/run">
      <div class="row2">
        <div><label>Дата размещения с</label><input type="date" name="date_from"/></div>
        <div><label>по</label><input type="date" name="date_to"/></div>
      </div>
      <label>Или «последние N дней» (если «с» пусто)</label>
      <input type="number" name="period_days" value="" min="1" max="365" placeholder="напр. 30"/>
      <label>Макс. на ключ</label>
      <input type="number" name="max_per_keyword" value="10" min="1" max="50"/>
      <label class="chk"><input type="checkbox" name="skip_enrich"/> Только поиск (без обогащения карточек)</label>
      <p class="hint">Период передаётся в ЕИС (zakupki) и отфильтровывает карточки после enrich. После смены ключей запустите сбор.</p>
      <p style="margin-top:1rem"><button type="submit">▶ Запустить пайплайн</button></p>
    </form>
  </div>

  <div class="card {_panel_visible(tab, 'jobs')}">
    <p class="hint">Фоновые задачи платформы (Osminog). <a href="/analyst">Аналитика истории</a></p>
    <form method="post" action="/settings/platform-job" style="margin-bottom:1rem">
      <label>Тип задачи</label>
      <select name="job_type">
        <option value="link_resolve">Связи тендер ↔ ЛПР</option>
        <option value="tender_analyst">Аналитика тендеров</option>
        <option value="source_scout">Разведка площадки (URL ниже)</option>
      </select>
      <label>URL площадки (для scout)</label>
      <input type="url" name="scout_url" placeholder="https://…"/>
      <div class="row2">
        <div><label>С даты</label><input type="date" name="date_from"/></div>
        <div><label>По</label><input type="date" name="date_to"/></div>
      </div>
      <label>Дней назад</label>
      <input type="number" name="period_days" value="90" min="7"/>
      <p style="margin-top:0.75rem"><button type="submit">Поставить в очередь</button></p>
    </form>
    <table class="dense"><thead><tr><th>#</th><th>Тип</th><th>Статус</th><th>Создана</th><th>Результат</th></tr></thead><tbody>
    {_platform_jobs_rows(platform_jobs or [])}
    </tbody></table>
  </div>

  <div class="card {_panel_visible(tab, 'channels')}">{channels_html}</div>
"""
    return _layout("Настройки", nav_active, body, flash=flash)


def manager_queue_page(*, tab: str, hot_leads: list, contacts: list, linked_rows: list[str]) -> str:
    hot_rows = "".join(
        f"<tr><td><span class='score {_score_class(l.score)}'>{l.score}</span></td>"
        f"<td><a href='/lead/{l.id}'>{_e(l.title[:100])}</a></td>"
        f"<td>{_e((l.customer_name or '')[:60])}</td>"
        f"<td>{_e(l.end_date or '—')}</td></tr>"
        for l in hot_leads
        if l.id
    ) or "<tr><td colspan='4'>Нет горячих тендеров за 30 дней</td></tr>"
    contact_rows = "".join(
        f"<tr><td><a href='/contact/{p.id}'>{_e(p.full_name)}</a></td>"
        f"<td>{_e(p.organization[:50])}</td>"
        f"<td>{_e(p.email or '—')}</td>"
        f"<td>{'✓' if getattr(p, 'channel_verified_at', None) else '—'}</td></tr>"
        for p in contacts
        if p.id
    ) or "<tr><td colspan='4'>Нет контактов с e-mail</td></tr>"
    linked = (
        "<table class='dense'><thead><tr><th>Контакт</th><th>Организация</th><th>Тендеров</th></tr></thead>"
        f"<tbody>{''.join(linked_rows)}</tbody></table>"
        if linked_rows
        else "<p class='hint'>Нет подтверждённых связей</p>"
    )
    body = f"""
  <h1>Очередь менеджера</h1>
  <p class="meta"><a href="/">← Тендеры</a> · <a href="/contacts">Контакты</a></p>
  <div class="card"><h2>Горячие тендеры (≥60, 30 дней)</h2>
    <table class="dense"><thead><tr><th>Скор</th><th>Тендер</th><th>Заказчик</th><th>Дедлайн</th></tr></thead>
    <tbody>{hot_rows}</tbody></table></div>
  <div class="card"><h2>ЛПР с e-mail</h2>
    <table class="dense"><thead><tr><th>ФИО</th><th>Компания</th><th>E-mail</th><th>Проверен</th></tr></thead>
    <tbody>{contact_rows}</tbody></table></div>
  <div class="card"><h2>Связанные (подтверждено)</h2>{linked}</div>"""
    return _layout("Очередь", "tenders", body)


def research_jobs_page(jobs: list) -> str:
    rows = []
    for j in jobs:
        rows.append(
            f"<tr><td>{j.id}</td><td><a href='/contact/{j.profile_id}'>#{j.profile_id}</a></td>"
            f"<td>{_e(j.status)}</td><td>{_e(j.search_engine or '')}</td>"
            f"<td><a href='{_e(j.challenge_url or '')}' target='_blank'>↗</a></td></tr>"
        )
    table = (
        "<table><thead><tr><th>Job</th><th>Контакт</th><th>Статус</th><th>Движок</th><th>URL</th></tr></thead>"
        f"<tbody>{''.join(rows) or '<tr><td colspan=5>Нет задач с капчей</td></tr>'}</tbody></table>"
    )
    body = f"<h1>Задачи исследования (капча)</h1>{table}<p><a href='/contacts'>← Контакты</a></p>"
    return _layout("Капча", "contacts", body)


def import_excel_section() -> str:
    return """
  <div class="settings-section">
    <h2>Импорт из Excel / CSV</h2>
    <p class="hint">Файл до 5 МБ (.xlsx, .csv). После загрузки — превью и сопоставление колонок.</p>
    <form method="post" action="/contacts/import/upload" enctype="multipart/form-data">
      <label>Файл</label>
      <input type="file" name="file" accept=".xlsx,.csv" required/>
      <label class="chk">
        <input type="checkbox" name="use_yandex" value="1"/>
        Использовать Yandex для сопоставления колонок (данные уйдут в облако)
      </label>
      <p style="margin-top:1rem"><button type="submit">Загрузить и настроить маппинг</button></p>
    </form>
  </div>
"""


def import_mapping_page(
    filename: str,
    headers: list[str],
    sample_rows: list[dict],
    suggested_mapping: dict[str, str],
) -> str:
    from tender_agents.excel_ingest.excel_import import MAPPING_FIELDS

    rows_html = ""
    for row in sample_rows[:10]:
        cells = "".join(f"<td>{_e(str(v or ''))}</td>" for v in row.values())
        rows_html += f"<tr>{cells}</tr>"
    header_th = "".join(f"<th>{_e(h)}</th>" for h in headers)
    mapping_rows = ""
    for field, keywords in MAPPING_FIELDS.items():
        options = '<option value="">— пропустить —</option>'
        selected_h = suggested_mapping.get(field, "")
        for h in headers:
            sel = " selected" if h == selected_h else ""
            options += f'<option value="{_e(h)}"{sel}>{_e(h)}</option>'
        mapping_rows += f"""
        <tr>
          <td><strong>{_e(field)}</strong><br><span class="hint">{_e(", ".join(keywords[:3]))}</span></td>
          <td><select name="map_{_e(field)}">{options}</select></td>
        </tr>"""
    body = f"""
  <h1>Импорт: {_e(filename)}</h1>
  <p class="meta">Проверьте сопоставление колонок (первые 10 строк).</p>
  <div class="card" style="overflow-x:auto">
    <h3>Превью</h3>
    <table class="dense"><thead><tr>{header_th}</tr></thead><tbody>{rows_html}</tbody></table>
  </div>
  <div class="card">
    <form method="post" action="/contacts/import/commit">
      <input type="hidden" name="filename" value="{_e(filename)}"/>
      <h3>Сопоставление</h3>
      <table><thead><tr><th>Поле в базе</th><th>Колонка в файле</th></tr></thead>
      <tbody>{mapping_rows}</tbody></table>
      <p style="margin-top:1.5rem">
        <button type="submit">Импортировать</button>
        <a href="/settings?tab=channels" class="btn secondary">Отмена</a>
      </p>
    </form>
  </div>"""
    return _layout("Маппинг импорта", "contacts", body)
