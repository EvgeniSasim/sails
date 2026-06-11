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
