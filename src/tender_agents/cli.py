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
    handlers=[RichHandler(rich_tracebacks=True, console=console, show_path=False)]
)


@app.callback()
def main() -> None:
    """Пока пусто — следующий шаг: первая команда сбора."""


@app.command()
def status() -> None:
    """Проверка, что CLI установлен."""
    from tender_agents import __version__

    console.print(f"tender-leads [cyan]{__version__}[/cyan] — каркас, код с нуля")


@app.command()
def collect(
    platform_url: str = typer.Option(..., "--platform-url", help="URL площадки"),
    keywords: List[str] = typer.Option(..., "-k", "--keyword", help="Ключевые слова"),
    date_from: Optional[str] = typer.Option(None, "--date-from", help="Дата начала (ГГГГ-ММ-ДД)"),
    date_to: Optional[str] = typer.Option(None, "--date-to", help="Дата окончания (ГГГГ-ММ-ДД)"),
    max_per_keyword: int = typer.Option(10, "--max-per-keyword", help="Макс. лотов на ключ"),
    max_pages: int = typer.Option(5, "--max-pages", help="Макс. страниц на ключ"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Подробный лог"),
) -> None:
    """Сбор тендеров по заданным параметрам."""
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

    # Импортируем адаптеры, чтобы они зарегистрировались
    import tender_agents.platforms.sberbank_ast  # noqa

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
                console.print(f"Карточка {i}/{min(len(items), max_per_keyword)}: {item.title[:60]}...")
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
