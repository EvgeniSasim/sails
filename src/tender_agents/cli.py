import typer
from rich.console import Console

app = typer.Typer(help="Сбор тендеров по ключевым словам и фильтрам")
console = Console()


@app.callback()
def main() -> None:
    """Пока пусто — следующий шаг: первая команда сбора."""


@app.command()
def status() -> None:
    """Проверка, что CLI установлен."""
    from tender_agents import __version__

    console.print(f"tender-leads [cyan]{__version__}[/cyan] — каркас, код с нуля")
