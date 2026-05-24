import asyncio
import csv
import logging
import os
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from tender_agents.agents.orchestrator import Orchestrator
from tender_agents.config_loader import load_keywords, load_sources
from tender_agents.db import create_repository
from tender_agents.scrape.factory import get_backend

app = typer.Typer(help="Система агентов для сбора лидов с площадок закупок и открытых источников")
yandex_app = typer.Typer(help="Yandex AI Studio — агенты и модели")
open_app = typer.Typer(help="Открытые источники: СМИ, рейтинги, подборки (не тендеры)")
app.add_typer(yandex_app, name="yandex")
app.add_typer(open_app, name="open")
console = Console()


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


platform_app = typer.Typer(help="Задачи платформы Osminog (ключи, аналитика, связи)")
app.add_typer(platform_app, name="platform")


@platform_app.command("keyword-plan")
def platform_keyword_plan(
    task: str = typer.Argument(..., help="Задача менеджера"),
    save: bool = typer.Option(False, "--save", help="Записать в keywords.yaml"),
    merge_hr_cx: bool = typer.Option(False, "--merge-hr-cx"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Сгенерировать ключевые слова из формулировки задачи."""
    _setup_logging(verbose)

    async def _go():
        from tender_agents.agents.keyword_planner_agent import plan_keywords
        from tender_agents.web.config_store import ConfigStore

        plan = await plan_keywords(task, merge_hr_cx=merge_hr_cx)
        if save:
            ConfigStore().save_keywords(plan["keywords"], merge_extra=merge_hr_cx)
        return plan

    plan = asyncio.run(_go())
    console.print("[green]Ключи:[/green]", plan.get("keywords"))
    console.print(plan.get("notes", ""))


@platform_app.command("scout")
def platform_source_scout(
    url: str = typer.Argument(..., help="URL площадки"),
    save: bool = typer.Option(True, "--save/--no-save"),
    stub: bool = typer.Option(False, "--stub", help="Показать черновик Python-адаптера"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Разведка новой площадки → JSON в config/sources.d/."""
    _setup_logging(verbose)

    async def _go():
        from tender_agents.agents.source_scout_agent import (
            render_adapter_stub,
            save_spec_to_sources_d,
            scout_source,
        )

        spec = await scout_source(url)
        path = save_spec_to_sources_d(spec) if save else None
        return spec, path

    spec, path = asyncio.run(_go())
    console.print(spec)
    if path:
        console.print(f"[green]Сохранено:[/green] {path}")
    if stub:
        from tender_agents.agents.source_scout_agent import render_adapter_stub

        console.print(render_adapter_stub(spec))


@platform_app.command("link-resolve")
def platform_link_resolve(verbose: bool = typer.Option(False, "-v")):
    """Пересобрать suggested-связи тендер ↔ ЛПР."""
    _setup_logging(verbose)

    async def _go():
        from tender_agents.agents.link_resolver_agent import resolve_links_batch

        repo = create_repository()
        await repo.init()
        return await resolve_links_batch(repo)

    result = asyncio.run(_go())
    console.print("[green]Готово[/green]", result)


@platform_app.command("analyst")
def platform_analyst(
    period_days: int = typer.Option(90, help="Дней назад"),
    output: Path | None = typer.Option(None, "-o", help="JSON-отчёт в файл"),
    verbose: bool = typer.Option(False, "-v"),
):
    """Аналитика истории тендеров за период."""
    _setup_logging(verbose)
    from datetime import date, timedelta

    async def _go():
        from tender_agents.agents.tender_analyst_agent import analyze_tender_history

        repo = create_repository()
        await repo.init()
        d_from = date.today() - timedelta(days=period_days)
        return await analyze_tender_history(repo, date_from=d_from)

    report = asyncio.run(_go())
    if output:
        import json

        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        console.print(f"[green]Отчёт:[/green] {output}")
    else:
        console.print(report.get("summary", ""))
        console.print(report.get("stats", {}))


@app.command()
def run(
    source: list[str] = typer.Option(
        None,
        "--source",
        "-s",
        help="Площадка: zakupki, b2b_center, sberbank_ast, gosplan",
    ),
    keyword: list[str] = typer.Option(
        None,
        "--keyword",
        "-k",
        help="Ключевые слова (по умолчанию + config/keywords.yaml)",
    ),
    keywords_only: bool = typer.Option(
        False,
        "--keywords-only",
        help="Использовать только -k, без config/keywords.yaml",
    ),
    max_per_keyword: int = typer.Option(10, help="Макс. карточек на ключ × площадку"),
    date_from: str = typer.Option("", help="Дата размещения с (YYYY-MM-DD)"),
    date_to: str = typer.Option("", help="Дата размещения по"),
    period_days: int = typer.Option(
        0,
        help="Если date_from пуст — взять последние N дней",
    ),
    skip_enrich: bool = typer.Option(
        False,
        help="Только поиск (без захода в карточки)",
    ),
    backend: str = typer.Option(
        None,
        "--backend",
        "-b",
        help="httpx | playwright | crawl4ai | yandex | scrapegraph",
    ),
    yandex_agent: bool = typer.Option(
        False,
        "--yandex-agent",
        help="Запустить Search/Enrich/Orchestrator через Yandex AI Studio",
    ),
    agent_provider: str = typer.Option(
        None,
        "--agent-provider",
        help="local | yandex (alias: --yandex-agent)",
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Запустить пайплайн: поиск → обогащение → сохранение."""
    _setup_logging(verbose)
    if backend:
        os.environ["SCRAPER_BACKEND"] = backend
    provider = agent_provider or ("yandex" if yandex_agent else None)
    if provider == "yandex" or yandex_agent:
        os.environ["AGENT_PROVIDER"] = "yandex"
        if not backend:
            backend = "yandex"

    if keywords_only and keyword:
        keywords = list(dict.fromkeys(keyword))
    elif keyword:
        keywords = list(dict.fromkeys(load_keywords() + list(keyword)))
    else:
        keywords = load_keywords()

    be = get_backend(backend)
    console.print(f"Бэкенд: [cyan]{be.name}[/cyan]")
    if provider == "yandex" or yandex_agent:
        console.print("Агенты: [cyan]Yandex AI Studio[/cyan]")
    from datetime import date, timedelta
    from tender_agents.platform_jobs import parse_optional_date

    d_from = parse_optional_date(date_from or None)
    d_to = parse_optional_date(date_to or None)
    if not d_from and period_days > 0:
        d_from = date.today() - timedelta(days=period_days)

    orch = Orchestrator(
        keywords=keywords,
        source_ids=source or None,
        backend=be,
        agent_provider=provider or ("yandex" if yandex_agent else None),
        date_from=d_from,
        date_to=d_to,
    )
    stats = asyncio.run(
        orch.run_pipeline(max_per_keyword=max_per_keyword, skip_enrich=skip_enrich)
    )
    console.print("[green]Готово[/green]", stats)


@app.command()
def serve(
    host: str = typer.Option(None, help="Хост (по умолчанию из .env)"),
    port: int = typer.Option(None, help="Порт"),
    reload: bool = typer.Option(
        False,
        "--reload",
        "-r",
        help="Автоперезагрузка при изменении кода (удобно в разработке)",
    ),
):
    """Веб-дашборд лидов."""
    from tender_agents.web.app import run_server
    from tender_agents.settings import settings

    if host:
        settings.dashboard_host = host
    if port:
        settings.dashboard_port = port
    console.print(
        f"Дашборд: http://{settings.dashboard_host}:{settings.dashboard_port}/"
    )
    run_server(reload=reload)


@app.command("contact-research")
def contact_research_cmd(
    contact_id: int = typer.Argument(..., help="ID из раздела «Контакты»"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Агент: поиск в выдаче по ФИО/компании, обход страниц, запись в карточку."""
    _setup_logging(verbose)

    async def _go():
        from tender_agents.agents.contact_research_agent import report_summary, run_contact_research

        repo = create_repository()
        await repo.init()
        return await run_contact_research(repo, contact_id)

    try:
        report = asyncio.run(_go())
        console.print("[green]" + report_summary(report) + "[/green]")
    except Exception as e:
        console.print(f"[red]Ошибка:[/red] {e}")
        raise typer.Exit(1) from e


@app.command("list")
def list_leads(
    limit: int = typer.Option(50, help="Сколько записей показать"),
    min_score: int = typer.Option(0, help="Минимальный скор"),
    segment: str = typer.Option("", help="Сегмент: hr, cx, research, gov"),
):
    """Показать сохранённые лиды (по скору)."""
    from tender_agents.db import LeadFilters

    repo = create_repository()

    async def _list():
        await repo.init()
        flt = LeadFilters(min_score=min_score, segment=segment or None)
        return await repo.list_filtered(flt, limit=limit)

    leads = asyncio.run(_list())
    table = Table(title="Лиды")
    table.add_column("Скор")
    table.add_column("Сегм.")
    table.add_column("Заголовок")
    table.add_column("Заказчик")
    table.add_column("Дедлайн")
    table.add_column("ID")
    for lead in leads:
        table.add_row(
            str(lead.score),
            lead.segment.value,
            lead.title[:55],
            (lead.customer_name or "—")[:35],
            (lead.end_date or "—")[:12],
            str(lead.id or ""),
        )
    console.print(table)


@app.command()
def export(
    output: Path = typer.Option(Path("data/leads_export.csv"), "-o", "--output"),
    limit: int = typer.Option(500),
):
    """Экспорт в CSV для CRM."""
    repo = create_repository()

    async def _export():
        await repo.init()
        return await repo.list_all(limit=limit)

    leads = asyncio.run(_export())
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as f:
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
                "status",
                "customer_name",
                "customer_inn",
                "end_date",
                "matched_keyword",
                "contact_emails",
                "contact_phones",
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
                    lead.status.value,
                    lead.customer_name or "",
                    lead.customer_inn or "",
                    lead.end_date or "",
                    lead.matched_keyword or "",
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
    console.print(f"[green]Экспорт:[/green] {output} ({len(leads)} строк)")


@app.command()
def rescore(
    limit: int = typer.Option(5000, help="Сколько лидов пересчитать"),
):
    """Пересчитать скор, сегмент и питч для всех лидов в БД."""
    from tender_agents.agents.store_agent import prepare_lead

    repo = create_repository()

    async def _rescore():
        await repo.init()
        leads = await repo.list_all(limit=limit)
        for lead in leads:
            await repo.upsert(prepare_lead(lead))
        return len(leads)

    n = asyncio.run(_rescore())
    console.print(f"[green]Пересчитано:[/green] {n} лидов")


@app.command()
def clean(
    dry_run: bool = typer.Option(False, "--dry-run", help="Только показать, что удалится"),
    low_score: int = typer.Option(
        0,
        help="Удалить лиды со скором ниже N (0 = не удалять по скору)",
    ),
):
    """Удалить из БД мусор и нерелевантные записи."""
    from tender_agents.config_loader import load_keywords
    from tender_agents.scrape.filters import is_junk_title, is_relevant_to_keyword

    repo = create_repository()

    async def _clean():
        await repo.init()
        leads = await repo.list_all(limit=5000)
        keywords = load_keywords()
        remove: list[str] = []
        for lead in leads:
            if is_junk_title(lead.title):
                remove.append(lead.url)
                continue
            if keywords and not any(
                is_relevant_to_keyword(lead.title, kw) for kw in keywords
            ):
                remove.append(lead.url)
        score_deleted = 0
        if low_score > 0 and not dry_run:
            score_deleted = await repo.delete_low_score(low_score)
        elif low_score > 0 and dry_run:
            score_deleted = sum(1 for l in leads if (l.score or 0) < low_score)

        if dry_run:
            return len(remove), remove[:20], score_deleted
        deleted = await repo.delete_by_urls(remove)
        return deleted, remove[:10], score_deleted

    deleted, sample, score_deleted = asyncio.run(_clean())
    if dry_run:
        console.print(f"[yellow]Будет удалено (мусор):[/yellow] {deleted} записей")
        if low_score:
            console.print(f"[yellow]Будет удалено (скор < {low_score}):[/yellow] {score_deleted}")
    else:
        console.print(f"[green]Удалено (мусор):[/green] {deleted} записей")
        if score_deleted:
            console.print(f"[green]Удалено (низкий скор):[/green] {score_deleted}")
    if sample:
        console.print("Примеры:", sample)


@app.command()
def backends():
    """Доступные бэкенды скрапинга."""
    rows = [
        ("httpx", "Бесплатно", "По умолчанию. zakupki — нативный парсер; остальное — базовый HTML"),
        ("playwright", "Бесплатно", "JS-сайты (B2B, Сбербанк-АСТ). pip install -e '.[playwright]'"),
        ("crawl4ai", "Бесплатно + Ollama", "LLM локально. pip install -e '.[crawl4ai]'"),
        ("yandex", "Yandex Cloud", "Агенты AI Studio. pip install -e '.[yandex]' + --yandex-agent"),
        ("scrapegraph", "Платно", "Облако ScrapeGraphAI, нужен SGAI_API_KEY"),
    ]
    for name, cost, desc in rows:
        console.print(f"• [bold]{name}[/bold] ({cost}) — {desc}")


@app.command()
def sources():
    """Список настроенных площадок."""
    for sid, cfg in load_sources().items():
        console.print(f"• [bold]{sid}[/bold] — {cfg.get('name')} — {cfg.get('search_url')}")


@app.command()
def keywords():
    """Список ключевых слов из конфига."""
    for kw in load_keywords():
        console.print(f"• {kw}")


@open_app.command("ingest")
def open_ingest(
    url: str = typer.Argument(..., help="URL (напр. https://www.kommersant.ru/doc/7180193)"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Не писать в БД, только показать число лидов"),
    limit: int = typer.Option(0, "--limit", help="Сохранить не больше N (0 = все)"),
    html_file: str | None = typer.Option(
        None,
        "--html-file",
        "-f",
        help="Локальный сохранённый HTML страницы (если по сети приходит страница без таблицы)",
    ),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Собрать лиды из открытой страницы (СМИ / рейтинг). Сейчас: kommersant.ru с таблицей ФИО."""
    _setup_logging(verbose)
    from tender_agents.agents.store_agent import StoreAgent
    from tender_agents.channels.ingest import ingest_url

    async def _go() -> tuple[int, list]:
        leads = await ingest_url(url.strip(), html_file=html_file)
        if limit and limit > 0:
            leads = leads[:limit]
        if dry_run:
            return len(leads), leads
        repo = create_repository()
        await repo.init()
        saved = await StoreAgent(repo).run(leads)
        return saved, leads

    n, leads = asyncio.run(_go())
    if dry_run:
        console.print(f"[yellow]DRY RUN:[/yellow] распознано {len(leads)} профилей")
        for L in leads[:5]:
            console.print(f"  • {L.title[:70]}…")
        if len(leads) > 5:
            console.print(f"  … и ещё {len(leads) - 5}")
    else:
        console.print(f"[green]Сохранено в базу контактов:[/green] {n} записей")


@open_app.command("bookmarks")
def open_bookmarks(
    dry_run: bool = typer.Option(False, "--dry-run"),
    verbose: bool = typer.Option(False, "-v", "--verbose"),
):
    """Загрузить все URL с enabled: true из config/channels.yaml."""
    import yaml

    from tender_agents.settings import CONFIG_DIR

    _setup_logging(verbose)
    path = CONFIG_DIR / "channels.yaml"
    if not path.exists():
        console.print(f"[red]Нет файла[/red] {path}")
        raise typer.Exit(1)
    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    marks = [b for b in data.get("bookmarks", []) if isinstance(b, dict) and b.get("enabled")]
    if not marks:
        console.print("Нет закладок с enabled: true — см. config/channels.yaml")
        raise typer.Exit(0)
    for b in marks:
        u = (b.get("url") or "").strip()
        if not u:
            continue
        console.print(f"→ {u}")
        open_ingest(url=u, dry_run=dry_run, limit=0, verbose=verbose)


@yandex_app.command("check")
def yandex_check():
    """Проверить YANDEX_API_KEY и доступ к модели."""
    from tender_agents.yandex.client import YandexStudioClient, YandexStudioError

    async def _check():
        client = YandexStudioClient()
        return await client.health_check()

    try:
        result = asyncio.run(_check())
        console.print("[green]Yandex AI Studio OK[/green]", result)
    except (YandexStudioError, ImportError) as e:
        console.print(f"[red]Ошибка:[/red] {e}")
        raise typer.Exit(1) from e


@yandex_app.command("run")
def yandex_run(
    source: list[str] = typer.Option(None, "--source", "-s"),
    keyword: list[str] = typer.Option(None, "--keyword", "-k"),
    keywords_only: bool = typer.Option(True, "--keywords-only/--all-keywords"),
    max_per_keyword: int = typer.Option(10),
    skip_enrich: bool = typer.Option(False),
    verbose: bool = typer.Option(False, "-v"),
):
    """Пайплайн только через агентов Yandex (--yandex-agent)."""
    run(
        source=source,
        keyword=keyword,
        keywords_only=keywords_only,
        max_per_keyword=max_per_keyword,
        skip_enrich=skip_enrich,
        backend="yandex",
        yandex_agent=True,
        agent_provider="yandex",
        verbose=verbose,
    )


if __name__ == "__main__":
    app()
