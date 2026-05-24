"""Абстракция бэкенда извлечения данных."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class ExtractBackend(ABC):
    """Унифицированный интерфейс: список результатов и карточка закупки."""

    name: str

    @abstractmethod
    async def extract_list(self, url: str, *, keyword: str, source_name: str) -> dict[str, Any]:
        """Вернуть dict с ключом items: list[dict]."""
        ...

    @abstractmethod
    async def extract_detail(self, url: str, *, keyword: str) -> dict[str, Any]:
        """Вернуть поля карточки закупки (title, contacts, ...)."""
        ...
