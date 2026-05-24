from tender_agents.scrape.base import ExtractBackend
from tender_agents.scrape.factory import get_backend
from tender_agents.sources.base import SourceAdapter
from tender_agents.sources.b2b_center import B2BCenterAdapter
from tender_agents.sources.gosplan import GosplanAdapter
from tender_agents.sources.sberbank_ast import SberbankAstAdapter
from tender_agents.sources.zakupki import ZakupkiAdapter

ADAPTER_CLASSES: dict[str, type[SourceAdapter]] = {
    "zakupki": ZakupkiAdapter,
    "b2b_center": B2BCenterAdapter,
    "sberbank_ast": SberbankAstAdapter,
    "gosplan": GosplanAdapter,
}


def build_adapters(
    sources_config: dict[str, dict],
    backend: ExtractBackend | None = None,
) -> list[SourceAdapter]:
    backend = backend or get_backend()
    adapters: list[SourceAdapter] = []
    for source_id, cfg in sources_config.items():
        cls = ADAPTER_CLASSES.get(source_id)
        if cls is None:
            continue
        adapters.append(cls(cfg, backend))
    return adapters
