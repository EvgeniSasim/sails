import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import os
from tender_agents.browser.session import HumanSession
from tender_agents.browser.exceptions import CaptchaRequiredError, SiteUnreachableError
from tender_agents.browser.page_context import capture_main_text
from tender_agents.models import CollectPlan, CollectResult, TenderRecord, KeywordStats
from tender_agents.platforms.registry import get_adapter
from tender_agents.collect.store import JsonlStore
from tender_agents.collect.db import DbStore, init_db

logger = logging.getLogger(__name__)

async def run_collect(
    plan: CollectPlan,
    headed: bool = False,
    result: Optional[CollectResult] = None,
    output_path: Optional[str] = None,
    store_type: str = "both",
    db_url: Optional[str] = None
) -> CollectResult:
    """
    Оркестратор сбора тендеров: один браузер на все ключевые слова.
    """
    if result is None:
        result = CollectResult()

    result.started_at = datetime.now()
    result.platform_host = plan.platform_url.host

    adapter = get_adapter(str(plan.platform_url))

    stores = []
    if store_type in ("jsonl", "both"):
        if output_path is None:
            today = datetime.now().strftime("%Y-%m-%d")
            host = plan.platform_url.host or "unknown"
            output_path = f"data/collect/{today}-{host}.jsonl"
        stores.append(JsonlStore(output_path))

    if store_type in ("sqlite", "both"):
        if not db_url:
            db_url = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/leads.db")

        # Ensure data directory exists for sqlite
        if ":///" in db_url:
            db_path_str = db_url.split(":///")[1]
            Path(db_path_str).parent.mkdir(parents=True, exist_ok=True)

        await init_db(db_url)
        stores.append(DbStore(db_url))

    if not adapter:
        logger.error(f"Адаптер для {plan.platform_url} не найден.")
        result.errors_count += 1
        return result

    try:
        async with HumanSession(headed=headed) as session:
            logger.info(f"Начинаю сбор на {plan.platform_url.host}")
            await adapter.open_home(session)

            for keyword in plan.keywords:
                logger.info(f"Ищу: {keyword}")
                result.totals_per_keyword[keyword] = 0
                stats = KeywordStats()
                result.keyword_stats[keyword] = stats
                start_ts = time.time()

                try:
                    ctx = await adapter.search(session, keyword, plan.filters)

                    async for item in adapter.iter_listing_pages(session, ctx, max_pages=plan.max_pages):
                        stats.found_links += 1
                        if stats.saved >= plan.max_per_keyword:
                            break

                        try:
                            record = await adapter.open_detail(session, item, keyword, plan.filters)
                            if record:
                                if record.title == "Без названия" and not record.external_id:
                                    main_text = await capture_main_text(session.page)
                                    os.makedirs("data/debug", exist_ok=True)
                                    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                                    filepath = f"data/debug/parse-fail-{ts}.txt"
                                    with open(filepath, "w", encoding="utf-8") as f:
                                        f.write(main_text)
                                    logger.warning(f"Предупреждение: не удалось извлечь заголовок и ID. Снимок текста: {filepath}")

                                saved_any = False
                                for store in stores:
                                    if isinstance(store, DbStore):
                                        if await store.write(record):
                                            saved_any = True
                                    else:
                                        if store.write(record):
                                            saved_any = True

                                if saved_any:
                                    result.records.append(record)
                                    stats.saved += 1
                                    result.totals_per_keyword[keyword] = stats.saved
                                    logger.info(f"Сохранено лотов: {stats.saved}")
                                else:
                                    stats.skipped_duplicate += 1
                                    result.duplicates_count += 1
                                    logger.debug(f"Дубликат пропущен: {record.url}")
                            else:
                                stats.skipped_filter += 1
                                result.filtered_count += 1

                            if stats.saved >= plan.max_per_keyword:
                                break
                        except Exception as e:
                            logger.error(f"Ошибка при обработке лота {item.url}: {e}")
                            await session.save_screenshot("error_detail")
                            stats.errors += 1
                            result.errors_count += 1

                except asyncio.CancelledError:
                    logger.warning(f"Сбор прерван пользователем на ключе '{keyword}'")
                    raise
                except Exception as e:
                    err_msg = str(e).lower()
                    hint = ""
                    if "timeout" in err_msg or "err_connection" in err_msg or "net::" in err_msg:
                        hint = " Для доступа к площадке может потребоваться VPN/прокси в РФ."
                    logger.error(f"Ошибка при поиске по ключу '{keyword}': {e}{hint}")
                    await session.save_screenshot("error_search")
                    stats.errors += 1
                    result.errors_count += 1
                finally:
                    stats.duration_seconds = time.time() - start_ts

    except SiteUnreachableError as e:
        logger.error("%s", e)
        result.errors_count += 1
    except CaptchaRequiredError as e:
        logger.error(f"Нужен ручной ввод: {e}")
        result.errors_count += 1
    except asyncio.CancelledError:
        logger.info("Завершаю работу (прервано)")
    except Exception as e:
        logger.error(f"Критическая ошибка оркестратора: {e}")
        result.errors_count += 1

    finally:
        result.finished_at = datetime.now()
        save_report(plan, result, output_path)

    return result


def save_report(plan: CollectPlan, result: CollectResult, output_path: Optional[str] = None):
    """
    Сохраняет отчет о сборе в JSON файл.
    """
    try:
        if output_path is None:
            today = datetime.now().strftime("%Y-%m-%d")
            host = plan.platform_url.host or "unknown"
            output_path = f"data/collect/{today}-{host}.jsonl"

        report_path = Path(output_path).with_suffix(".json")
        if report_path.suffix == ".json" and report_path.name.endswith("-report.json") is False:
            report_path = report_path.with_name(report_path.stem + "-report.json")

        report_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "plan": plan.model_dump(mode="json"),
            "stats": {
                "started_at": result.started_at.isoformat() if result.started_at else None,
                "finished_at": result.finished_at.isoformat() if result.finished_at else None,
                "duration_seconds": result.duration_seconds,
                "platform_host": result.platform_host,
                "total_saved": len(result.records),
                "total_duplicates": result.duplicates_count,
                "total_filtered": result.filtered_count,
                "total_errors": result.errors_count,
                "per_keyword": {kw: stats.model_dump() for kw, stats in result.keyword_stats.items()}
            },
            "saved_external_ids": [r.external_id for r in result.records if r.external_id]
        }

        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Отчёт: {report_path}")
    except Exception as e:
        logger.error(f"Ошибка при сохранении отчета: {e}")
