import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Блокируем явно некорректные или опасные домены
DISALLOWED_DOMAINS = {
    "localhost",
    "127.0.0.1",
    "internal.network",
}

def is_allowed_source_url(url: str) -> bool:
    """Проверка, что источник является публичным веб-ресурсом."""
    if not url:
        return False
    try:
        p = urlparse(url)
        if p.scheme not in ("http", "https"):
            return False
        host = p.netloc.lower().split(":")[0]
        if host in DISALLOWED_DOMAINS:
            return False
        return True
    except Exception:
        return False

async def record_provenance(
    repo,
    profile_id: int,
    source_url: str,
    field: str,
    value: str,
    collected_at: datetime | None = None
):
    """
    Записывает происхождение данных (provenance) в лог.
    Используется для соблюдения 152-ФЗ (подтверждение источника открытых данных).
    """
    if not is_allowed_source_url(source_url):
        logger.warning("Attempted to record provenance from disallowed URL: %s", source_url)
        return

    collected_at = collected_at or datetime.now(timezone.utc)

    # Мы будем использовать метод из ContactRepository
    cr = repo.contacts_repo()
    await cr.log_provenance(
        profile_id=profile_id,
        source_url=source_url,
        field=field,
        value=value,
        collected_at=collected_at
    )
