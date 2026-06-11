# Jules 11 — offline HTML fixtures

**Branch:** `jules/task02-11-fixtures`  
**Depends on:** merge 10

```markdown
You work on page_context + text_blocks extraction layer.

## Goal
CI and local `pytest` must validate Sberbank parsing without live network.

## Read first
- src/tender_agents/browser/page_context.py (`_EXTRACT_LEAF_LISTINGS_JS`)
- src/tender_agents/browser/text_blocks.py
- tests/test_text_blocks.py

## Implement
1. Add sanitized HTML fixtures (trim scripts if needed, keep DOM structure):
   - `tests/fixtures/sberbank/listing_crm.html` — 2+ procedures with `content="leaf:*"` fields
   - `tests/fixtures/sberbank/detail_sample.html` — card with Russian labels from live site
   Capture from real pages or reconstruct minimal valid DOM; no secrets/cookies.
2. Helper `tests/fixture_browser.py` or use `playwright.sync_api` in tests:
   - `load_fixture_html(path) -> str` loaded via `page.set_content(html, wait_until="domcontentloaded")`
3. Tests:
   - `test_leaf_listing_from_fixture` — ≥2 items, each with url + title
   - `test_detail_text_from_fixture` — external_id, title, customer_name from fixture innerText
4. Mark any remaining network tests `@pytest.mark.network` and document in README:
   ```bash
   pytest -m "not network"
   ```
5. Optional: `conftest.py` registers `network` marker

## Success criteria
- `pytest -m "not network"` green in CI without VPN
- Fixtures committed; total offline tests ≥20

## Do not
- Download fixtures at test runtime from internet.
- Change collect orchestrator behavior.
```
