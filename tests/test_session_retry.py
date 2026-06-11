import pytest
import asyncio
from unittest.mock import AsyncMock, patch
from tender_agents.browser.session import HumanSession
from tender_agents.browser.exceptions import SiteUnreachableError

@pytest.mark.asyncio
async def test_goto_retry_success():
    session = HumanSession()
    session.page = AsyncMock()

    # First call fails with a network-like error, second succeeds
    session.page.goto.side_effect = [
        Exception("net::ERR_CONNECTION_TIMED_OUT"),
        AsyncMock()
    ]

    with patch.object(session, "check_captcha", AsyncMock()), \
         patch.object(session, "human_delay", AsyncMock()), \
         patch("tender_agents.browser.session.accept_cookies", AsyncMock()):

        # We also need to mock asyncio.sleep to avoid waiting 3s in test
        with patch("asyncio.sleep", AsyncMock()):
            await session.goto("http://example.com")

    assert session.page.goto.call_count == 2

@pytest.mark.asyncio
async def test_goto_retry_failure_eventually():
    session = HumanSession()
    session.page = AsyncMock()

    # Both calls fail
    session.page.goto.side_effect = Exception("net::ERR_CONNECTION_TIMED_OUT")

    with patch.object(session, "check_captcha", AsyncMock()), \
         patch.object(session, "human_delay", AsyncMock()), \
         patch.object(session, "save_screenshot", AsyncMock()), \
         patch("tender_agents.browser.session.accept_cookies", AsyncMock()):

        with patch("asyncio.sleep", AsyncMock()):
            with pytest.raises(SiteUnreachableError) as excinfo:
                await session.goto("http://example.com")

            assert "Попробуйте VPN/прокси в РФ." in str(excinfo.value)

    assert session.page.goto.call_count == 2
