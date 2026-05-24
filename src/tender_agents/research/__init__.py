"""Contact web research: fetchers, captcha handling, job queue."""

from tender_agents.research.fetchers import (
    FetchResult,
    HttpxFetcher,
    detect_captcha,
    fetch_url,
)
from tender_agents.research.jobs import ContactResearchJob, ResearchJobRepository

__all__ = [
    "ContactResearchJob",
    "FetchResult",
    "HttpxFetcher",
    "ResearchJobRepository",
    "detect_captcha",
    "fetch_url",
]
