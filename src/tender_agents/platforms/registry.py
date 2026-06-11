from typing import List, Optional
from tender_agents.platforms.base import PlatformAdapter

class AdapterRegistry:
    def __init__(self):
        self._adapters: List[PlatformAdapter] = []

    def register(self, adapter: PlatformAdapter):
        self._adapters.append(adapter)

    def get_adapter_for_url(self, url: str) -> Optional[PlatformAdapter]:
        for adapter in self._adapters:
            if adapter.matches_url(url):
                return adapter
        return None

registry = AdapterRegistry()

def get_adapter(url: str) -> Optional[PlatformAdapter]:
    return registry.get_adapter_for_url(url)
