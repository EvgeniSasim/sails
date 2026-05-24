import pytest
from datetime import datetime, timezone
from tender_agents.research.fetchers import ManualCaptchaFetcher, CaptchaException
from tender_agents.compliance import is_allowed_source_url

class MockFetcher:
    def __init__(self, html):
        self.html = html
    async def fetch(self, url):
        return self.html

@pytest.mark.asyncio
async def test_captcha_detection():
    # Test common captcha markers
    captcha_html = "<html><body><h1>Please verify you are not a robot</h1><div id='showcaptcha'></div></body></html>"
    fetcher = ManualCaptchaFetcher(MockFetcher(captcha_html))

    with pytest.raises(CaptchaException) as excinfo:
        await fetcher.fetch("https://yandex.ru/search")
    assert excinfo.value.engine == "yandex"

    normal_html = "<html><body><h1>Search Results</h1><p>Some content here</p></body></html>"
    fetcher = ManualCaptchaFetcher(MockFetcher(normal_html))
    assert await fetcher.fetch("https://yandex.ru/search") == normal_html

def test_is_allowed_source_url():
    assert is_allowed_source_url("https://google.com") is True
    assert is_allowed_source_url("http://example.org/path") is True
    assert is_allowed_source_url("https://localhost/api") is False
    assert is_allowed_source_url("http://127.0.0.1:8000") is False
    assert is_allowed_source_url("ftp://files.com") is False
    assert is_allowed_source_url("") is False

@pytest.mark.asyncio
async def test_provenance_logging(tmp_path):
    from tender_agents.db import LeadRepository
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from tender_agents.compliance import record_provenance
    from datetime import datetime, timezone

    db_path = tmp_path / "test.db"
    db_url = f"sqlite+aiosqlite:///{db_path}"

    engine = create_async_engine(db_url, echo=False)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    repo = LeadRepository(factory, engine)
    await repo.init()
    cr = repo.contacts_repo()

    # Create a profile
    async with repo._session_factory() as session:
        from tender_agents.contacts_db import ContactProfileRow, DataProvenanceLogRow
        from sqlalchemy import select
        p = ContactProfileRow(
            dedup_key="test|test",
            organization="Test Org",
            full_name="Test Name",
            first_seen_at=datetime.now(timezone.utc),
            last_seen_at=datetime.now(timezone.utc)
        )
        session.add(p)
        await session.commit()
        profile_id = p.id

    # Record provenance
    await record_provenance(
        repo,
        profile_id=profile_id,
        source_url="https://example.com/staff",
        field="email",
        value="test@example.com"
    )

    # Verify
    async with repo._session_factory() as session:
        r = await session.execute(select(DataProvenanceLogRow).where(DataProvenanceLogRow.profile_id == profile_id))
        logs = r.scalars().all()
        assert len(logs) == 1
        assert logs[0].value == "test@example.com"
        assert logs[0].source_url == "https://example.com/staff"
