import asyncio
from typing import List, Optional
from datetime import datetime
import typer
from rich.console import Console
from pydantic import ValidationError
from tender_agents.models import CollectFilters, CollectPlan

import logging
from rich.logging import RichHandler

app = typer.Typer(help="Сбор тендеров по ключевым словам и фильтрам")
console = Console()

logging.basicConfig(
    level="INFO",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(
        rich_tracebacks=True,
        console=console,
        show_path=False,
        show_time=True,
        show_level=True
    )]
)


@app.callback()
def main() -> None:
    """Пока пусто — следующий шаг: первая команда сбора."""


@app.command()
def export(
    last: int = typer.Option(100, "--last", help="Количество последних тендеров для экспорта"),
    format: str = typer.Option("csv", "--format", help="Формат экспорта (csv)"),
    output: Optional[str] = typer.Option(None, "--output", help="Путь к файлу"),
    platform: Optional[str] = typer.Option(None, "--platform", help="Фильтр по площадке"),
) -> None:
    """Экспорт тендеров в CSV для Excel."""
    import os
    import csv
    from datetime import datetime
    from tender_agents.collect.db import DbStore

    if format != "csv":
        console.print(f"[red]Формат {format} пока не поддерживается. Используйте csv.[/red]")
        raise typer.Exit(code=1)

    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/leads.db")
    store = DbStore(db_url)

    async def _export():
        records = await store.list_last(limit=last, platform=platform)
        if not records:
            console.print("[yellow]Нет тендеров для экспорта.[/yellow]")
            return

        export_dir = "data/export"
        os.makedirs(export_dir, exist_ok=True)

        if not output:
            date_str = datetime.now().strftime("%Y-%m-%d")
            out_path = os.path.join(export_dir, f"tenders-{date_str}.csv")
        else:
            out_path = output

        columns = [
            "external_id", "title", "customer_name", "price",
            "publish_date", "deadline", "url", "matched_keyword", "collected_at"
        ]

        try:
            with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for r in records:
                    row = {col: getattr(r, col) for col in columns}
                    writer.writerow(row)

            console.print(f"[bold green]Экспорт завершен:[/bold green] {out_path} ({len(records)} строк)")
        except Exception as e:
            console.print(f"[red]Ошибка при записи файла:[/red] {e}")
            raise typer.Exit(code=1)

    try:
        asyncio.run(_export())
    except Exception as e:
        console.print(f"[red]Ошибка экспорта:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def show(
    external_id: Optional[str] = typer.Option(None, "--id", help="External ID тендера"),
    url: Optional[str] = typer.Option(None, "--url", help="URL тендера"),
) -> None:
    """Просмотр детальной информации о тендере."""
    import os
    from tender_agents.collect.db import DbStore
    from rich.panel import Panel
    from rich.table import Table

    if not external_id and not url:
        console.print("[red]Нужно указать --id или --url[/red]")
        raise typer.Exit(code=1)

    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/leads.db")
    store = DbStore(db_url)

    async def _show():
        record = await store.get_tender(external_id=external_id, url=url)
        if not record:
            console.print("[yellow]Тендер не найден.[/yellow]")
            return

        table = Table.grid(padding=(0, 1))
        table.add_column(style="bold cyan", justify="right")
        table.add_column()

        table.add_row("ID:", record.external_id or "—")
        table.add_row("Площадка:", record.platform)
        table.add_row("Заголовок:", record.title)
        table.add_row("URL:", record.url)
        table.add_row("Заказчик:", record.customer_name or "—")
        table.add_row("Цена:", record.price or "—")
        table.add_row("Опубликовано:", str(record.publish_date) if record.publish_date else "—")
        table.add_row("Дедлайн:", str(record.deadline) if record.deadline else "—")
        table.add_row("Ключевое слово:", record.matched_keyword or "—")
        table.add_row("Контакты:", record.contacts or "—")
        table.add_row("Собрано:", record.collected_at.strftime("%Y-%m-%d %H:%M:%S"))

        console.print(Panel(table, title="Детали тендера", expand=False))

    try:
        asyncio.run(_show())
    except Exception as e:
        console.print(f"[red]Ошибка при чтении из БД:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def status() -> None:
    """Проверка, что CLI установлен."""
    from tender_agents import __version__

    console.print(
        f"tender-leads [cyan]{__version__}[/cyan] — сбор тендеров (CLI + Playwright)"
    )


@app.command()
def collect(
    platform_url: str = typer.Option(..., "--platform-url", help="URL площадки"),
    keywords: List[str] = typer.Option(..., "-k", "--keyword", help="Ключевые слова"),
    date_from: Optional[str] = typer.Option(None, "--date-from", help="Дата начала (ГГГГ-ММ-ДД)"),
    date_to: Optional[str] = typer.Option(None, "--date-to", help="Дата окончания (ГГГГ-ММ-ДД)"),
    max_per_keyword: int = typer.Option(10, "--max-per-keyword", help="Макс. лотов на ключ"),
    max_pages: int = typer.Option(5, "--max-pages", help="Макс. страниц на ключ"),
    output: Optional[str] = typer.Option(None, "--output", help="Путь к файлу для сохранения"),
    store: str = typer.Option("both", "--store", help="Тип хранилища: sqlite, jsonl, both"),
    headed: bool = typer.Option(False, "--headed", help="Запустить в видимом режиме"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Подробный лог"),
) -> None:
    """Сбор тендеров по заданным параметрам."""
    from tender_agents.collect.orchestrator import run_collect
    from tender_agents.models import CollectResult
    from rich.table import Table
    import tender_agents.platforms  # noqa: F401 — регистрация адаптеров

    if store not in ("sqlite", "jsonl", "both"):
        console.print(f"[red]Неизвестный --store:[/red] {store}")
        raise typer.Exit(code=1)

    if verbose:
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)
        for handler in logger.handlers:
            handler.setLevel(logging.DEBUG)

    try:
        filters = CollectFilters(
            date_from=datetime.strptime(date_from, "%Y-%m-%d").date() if date_from else None,
            date_to=datetime.strptime(date_to, "%Y-%m-%d").date() if date_to else None,
        )
        plan = CollectPlan(
            platform_url=platform_url,
            keywords=keywords,
            filters=filters,
            max_per_keyword=max_per_keyword,
            max_pages=max_pages,
        )
    except (ValueError, ValidationError) as e:
        console.print(f"[red]Ошибка валидации:[/red] {e}")
        raise typer.Exit(code=1)

    # Summary in Russian
    console.print("[bold green]План сбора сформирован[/bold green]")
    console.print(f"  [bold]Площадка:[/bold] {plan.platform_url.host}")
    console.print(f"  [bold]Ключевые слова:[/bold] {', '.join(plan.keywords)}")

    period_str = "не задан"
    if plan.filters.date_from and plan.filters.date_to:
        period_str = f"с {plan.filters.date_from} по {plan.filters.date_to}"
    elif plan.filters.date_from:
        period_str = f"с {plan.filters.date_from}"
    elif plan.filters.date_to:
        period_str = f"по {plan.filters.date_to}"

    console.print(f"  [bold]Период:[/bold] {period_str}")
    console.print(f"  [bold]Лимиты:[/bold] {plan.max_per_keyword} лотов на ключ, {plan.max_pages} страниц")

    if verbose:
        console.print(f"[dim]Полный URL: {plan.platform_url}[/dim]")

    result = CollectResult()
    try:
        asyncio.run(run_collect(plan, headed=headed, result=result, output_path=output, store_type=store))
    except (KeyboardInterrupt, asyncio.CancelledError):
        console.print("\n[yellow]Сбор прерван пользователем. Вывожу частичные результаты.[/yellow]")
    except Exception as e:
        console.print(f"[red]Ошибка при сборе:[/red] {e}")
        # Не делаем raise, чтобы показать частичные результаты, если они есть

    try:
        if result.keyword_stats:
            table = Table(title="Итоги сбора по ключевым словам")
            table.add_column("Ключ", style="cyan")
            table.add_column("Сохранено", justify="right", style="green")
            table.add_column("Фильтр", justify="right", style="blue")
            table.add_column("Дубли", justify="right", style="yellow")
            table.add_column("Ошибки", justify="right", style="red")
            table.add_column("Время", justify="right")

            total_skipped_filter = 0
            for kw, stats in result.keyword_stats.items():
                total_skipped_filter += stats.skipped_filter
                table.add_row(
                    kw,
                    str(stats.saved),
                    str(stats.skipped_filter),
                    str(stats.skipped_duplicate),
                    str(stats.errors),
                    f"{stats.duration_seconds:.1f}с"
                )

            table.add_section()
            table.add_row(
                "ИТОГО",
                str(len(result.records)),
                str(result.filtered_count),
                str(result.duplicates_count),
                str(result.errors_count),
                f"{result.duration_seconds:.1f}с",
                style="bold"
            )
            console.print(table)

    except Exception as e:
        console.print(f"[red]Ошибка при сборе:[/red] {e}")
        raise typer.Exit(code=1)


@app.command(name="list")
def list_tenders(
    last: int = typer.Option(20, "--last", help="Показать последние N тендеров"),
) -> None:
    """Просмотр последних собранных тендеров из базы данных."""
    import os
    from tender_agents.collect.db import DbStore
    from rich.table import Table

    db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/leads.db")
    store = DbStore(db_url)

    async def _list():
        records = await store.list_last(limit=last)

        if not records:
            console.print("[yellow]Тендеров пока нет в базе данных.[/yellow]")
            return

        table = Table(title=f"Последние {len(records)} тендеров")
        table.add_column("ID", style="cyan")
        table.add_column("Площадка", style="dim")
        table.add_column("Заголовок", style="green")
        table.add_column("Цена", justify="right")
        table.add_column("Дедлайн", justify="right")

        for r in records:
            table.add_row(
                r.external_id or "—",
                r.platform,
                r.title[:50] + "..." if len(r.title) > 50 else r.title,
                r.price or "—",
                str(r.deadline) if r.deadline else "—"
            )
        console.print(table)

    try:
        asyncio.run(_list())
    except Exception as e:
        console.print(f"[red]Ошибка при чтении из БД:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def browse(
    url: str = typer.Option(..., "--url", help="URL для открытия"),
    headed: bool = typer.Option(False, "--headed", help="Запустить в видимом режиме"),
) -> None:
    """Открыть сайт и принять cookie (smoke-тест браузера)."""
    from tender_agents.browser.session import HumanSession

    async def _browse():
        async with HumanSession(headed=headed) as session:
            await session.goto(url)
            # Внутри session.goto уже есть логирование и accept_cookies
            console.print("[bold green]Готово[/bold green]")

    try:
        asyncio.run(_browse())
    except Exception as e:
        console.print(f"[red]Ошибка браузера:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def probe_search(
    platform_url: str = typer.Option(..., "--platform-url", help="URL площадки"),
    keyword: str = typer.Option(..., "-k", "--keyword", help="Ключевое слово"),
    max_pages: int = typer.Option(1, "--max-pages", help="Макс. страниц для сбора"),
    max_per_keyword: int = typer.Option(5, "--max-per-keyword", help="Макс. деталей на ключ"),
    fetch_details: bool = typer.Option(False, "--fetch-details", help="Собирать детали"),
    headed: bool = typer.Option(False, "--headed", help="Запустить в видимом режиме"),
) -> None:
    """Smoke-тест поиска: открыть площадку, ввести ключ, вернуть ссылки или детали."""
    from tender_agents.browser.session import HumanSession
    from tender_agents.platforms.registry import get_adapter
    from rich.table import Table

    import tender_agents.platforms  # noqa: F401

    async def _probe():
        adapter = get_adapter(platform_url)
        if not adapter:
            console.print(f"[red]Адаптер для {platform_url} не найден.[/red]")
            raise typer.Exit(code=1)

        async with HumanSession(headed=headed) as session:
            console.print(f"Использую адаптер: [cyan]{adapter.__class__.__name__}[/cyan]")
            await adapter.open_home(session)

            filters = CollectFilters()
            ctx = await adapter.search(session, keyword, filters)

            items = []
            async for item in adapter.iter_listing_pages(session, ctx, max_pages=max_pages):
                items.append(item)
                if len(items) >= max_per_keyword and not fetch_details:
                    break

            console.print(f"Всего уникальных ссылок найдено: [bold]{len(items)}[/bold]")

            if not fetch_details:
                for item in items[:max_per_keyword]:
                    console.print(f"  - {item.url} ([dim]{item.title}[/dim])")
                return

            records = []
            for i, item in enumerate(items[:max_per_keyword], 1):
                title_preview = (item.title or "—")[:60]
                console.print(
                    f"Карточка {i}/{min(len(items), max_per_keyword)}: {title_preview}..."
                )
                record = await adapter.open_detail(session, item, keyword, filters)
                if record:
                    records.append(record)

            if records:
                table = Table(title=f"Результаты для '{keyword}'")
                table.add_column("ID", style="cyan")
                table.add_column("Заголовок", style="green")
                table.add_column("Заказчик")
                table.add_column("Цена", justify="right")
                table.add_column("Дата", justify="right")

                for r in records:
                    table.add_row(
                        r.external_id or "—",
                        r.title[:50] + "..." if len(r.title) > 50 else r.title,
                        r.customer_name[:30] + "..." if r.customer_name and len(r.customer_name) > 30 else (r.customer_name or "—"),
                        r.price or "—",
                        str(r.publish_date) if r.publish_date else "—"
                    )
                console.print(table)
            else:
                console.print("[yellow]Детали не были собраны (возможно, отфильтрованы по дате).[/yellow]")

    try:
        asyncio.run(_probe())
    except Exception as e:
        console.print(f"[red]Ошибка при поиске:[/red] {e}")
        raise typer.Exit(code=1)


@app.command()
def snapshot(
    url: str = typer.Option(..., "--url", help="URL для снимка"),
    headed: bool = typer.Option(False, "--headed", help="Запустить в видимом режиме"),
    output: Optional[str] = typer.Option(None, "-o", "--output", help="Путь к файлу (txt)"),
) -> None:
    """Сделать снимок страницы (текст + leaf-данные) для отладки."""
    import json
    import os
    from datetime import datetime
    from tender_agents.browser.session import HumanSession
    from tender_agents.browser.page_context import capture_snapshot

    async def _snapshot():
        debug_dir = "data/debug"
        os.makedirs(debug_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        txt_path = output or os.path.join(debug_dir, f"snapshot-{timestamp}.txt")
        json_path = os.path.splitext(txt_path)[0] + ".json"

        try:
            async with HumanSession(headed=headed) as session:
                await session.goto(url)
                snap = await capture_snapshot(session.page)

                main_text_limit = 20_000
                main_text = snap.main_text[:main_text_limit]
                if len(snap.main_text) > main_text_limit:
                    main_text += "\n... (truncated)"

                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(f"URL: {snap.url}\n")
                    f.write(f"MARKER: {snap.results_marker or 'Not found'}\n")
                    f.write("-" * 20 + "\n")
                    f.write("LISTING ITEMS (JSON):\n")
                    f.write(json.dumps(snap.listing_items, ensure_ascii=False, indent=2))
                    f.write("\n" + "-" * 20 + "\n")
                    f.write("MAIN TEXT:\n")
                    f.write(main_text)

                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(snap.listing_items, f, ensure_ascii=False, indent=2)

                console.print(f"Снимок сохранён: [cyan]{txt_path}[/cyan]")
                console.print(f"Данные сохранены: [cyan]{json_path}[/cyan]")

        except Exception as e:
            console.print(f"[red]Ошибка при создании снимка:[/red] {e}")
            raise typer.Exit(code=1)

    try:
        asyncio.run(_snapshot())
    except Exception as e:
        console.print(f"[red]Критическая ошибка:[/red] {e}")
        raise typer.Exit(code=1)
