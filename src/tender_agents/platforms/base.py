from abc import ABC, abstractmethod
from typing import List
from tender_agents.browser.session import HumanSession
from tender_agents.models import ListingItem, CollectFilters

class PlatformAdapter(ABC):
    """
    Абстрактный базовый класс для адаптеров торговых площадок.
    """

    @abstractmethod
    def matches_url(self, url: str) -> bool:
        """Подходит ли этот адаптер для данного URL."""
        pass

    @abstractmethod
    async def open_home(self, session: HumanSession):
        """Открыть главную страницу площадки и подготовить сессию (cookie и т.д.)."""
        pass

    @abstractmethod
    async def search(
        self, session: HumanSession, keyword: str, filters: CollectFilters
    ) -> List[ListingItem]:
        """Выполнить поиск по ключевому слову и вернуть список найденных лотов."""
        pass
