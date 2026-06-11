# Jules 06 — collect orchestrator

**Branch:** `jules/task01-06-orchestrator`  
**Depends on:** merge 05

```markdown
You work on complete SberbankAstAdapter (search, pagination, detail).

## Goal
Wire `tender-leads collect` to run full browser collection for all keywords in one session.

## Read first
- src/tender_agents/cli.py (collect command from step 01)
- src/tender_agents/platforms/
- docs/task-01-spec.md step 6

## Implement
1. `src/tender_agents/collect/orchestrator.py`:
   - `async def run_collect(plan: CollectPlan) -> CollectResult`
   - One `HumanSession` for entire run
   - For each keyword: search → pages → details up to max_per_keyword
   - Russian INFO logs: «Ищу: {keyword}, страница {n}», «Сохранено лотов: …»
   - Handle Ctrl+C / asyncio.CancelledError: partial result summary
2. `CollectResult`: totals per keyword, errors count, records list
3. Connect `tender-leads collect` to orchestrator (remove plan-only stub behavior)
4. Flags: `--headed`, `-v`

## Success criteria
```bash
tender-leads collect --platform-url https://www.sberbank-ast.ru/ -k "crm" -k "опрос" --max-per-keyword 3 --max-pages 2 -v
```
runs end-to-end in browser; final Russian summary table per keyword.

Network may fail in CI — add unit tests for orchestrator with fake adapter.

## Do not
- File persistence yet (returns records in memory / prints sample); step 07 adds JSONL.
```
